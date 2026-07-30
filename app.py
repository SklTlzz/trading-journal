import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine

from config import DB_USER, DB_HOST, DB_PORT, DB_NAME, DB_PASS, DAYS_ORDER, SESSIONS_ORDER, PROFIT_PNL_SYMBS, COUNTER_TREND


st.set_page_config(page_title="Торговый журнал", layout="wide")

@st.cache_data
def load_data():
    """
    Загружает данные c БД
    """
    
    db_url = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    engine = create_engine(db_url)

    query = """
        SELECT
            *
        FROM accounts

        JOIN trades USING (account_id)

        ORDER BY trade_date
    """

    df = pd.read_sql(query, engine)
    df["trade_date"] = pd.to_datetime(df["trade_date"])

    df["month_filter"] = df["trade_date"].dt.month_name()
    df["year_filter"] = df["trade_date"].dt.year

    df["trade_day"] = pd.Categorical(df["trade_day"], categories=DAYS_ORDER, ordered=True)
    df["trade_session"] = pd.Categorical(df["trade_session"], categories=SESSIONS_ORDER, ordered=True)

    return df

def set_asset_choose(df: pd.DataFrame) -> pd.DataFrame:
    """
    Фильтрует датафрейм под выбранный класс активов (Crypto или RWA)
    
    Args:
        df: pd.DataFrame - исходный датафрейм со всеми сделками

    Returns:
        pd.DataFrame - отфильтрованный датафрейм, содержащий только выбранный класс активов
    """

    assets_list = list(df["asset_type"].unique())

    selected_asset = st.sidebar.radio("Выберите класс активов", assets_list, horizontal=True)

    df = df[df["asset_type"] == selected_asset]

    return df

def set_sidebar(df: pd.DataFrame) -> pd.DataFrame:
    """
    Устанавливает сайдбар c фильтрацией для всех графиков и метрик

    Args:
        df: pd.DataFrame - датафрейм, отфильтрованный по классу актива

    Returns:
        pd.DataFrame - датафрейм, отфильтрованный по выбранному году и месяцу
    """

    st.sidebar.header("Фильтры")

    years = ["Все"] + list(df["year_filter"].unique())
    selected_year = st.sidebar.selectbox("Выберите год", years)

    if selected_year == "Все":
        months = ["Все"] + list(df["month_filter"].unique())
    else:
        selected_year_mask = df["year_filter"] == selected_year
        months = ["Все"] + list(df.loc[selected_year_mask, "month_filter"].unique())
        df = df[selected_year_mask]

    selected_month = st.sidebar.selectbox("Выберите месяц", months)

    if selected_month != "Все":
        select_box_mask = df["month_filter"] == selected_month
        df = df[select_box_mask]

    return df

def set_account_choose(df: pd.DataFrame) -> pd.DataFrame:
    """
    Фильтрует датафрейм под выбранный аккаунт (все, 5к, 10к или 25к)

    Args:
        df: pd.DataFrame - датафрейм, отфильтрованный по классу актива, месяцу и году

    Returns:
        pd.DataFrame - датафрейм, отфильтрованный по аккаунтам
    """

    accounts_list = ["Все"] + sorted(list(df["account_size"].unique()))

    selected_account = st.sidebar.radio("Выберите счет", accounts_list, horizontal=True)

    if selected_account != "Все":
        df = df[df["account_size"] == selected_account]

    return df

def calculate_main_metrics(df: pd.DataFrame) -> list[float | int]:
    """
    Рассчитывает основные числовые метрики, находящиеся в хедере дашборда
    Буду считать, что безубыток - это сделка, где -0.07 <= PNL <= 0.07

    Args:
        df: pd.DataFrame - датафрейм, отфильтрованный по классу актива, месяцу, году и аккаунту

    Returns:
        list[float | int] - список из 5-ти основных метрик
    """

    BE_mask = (df["pnl"] <= 0.07) & (df["pnl"] >= -0.07)

    total_profit = df["profit"].sum().round(2)
    total_winrate = (df["win"].sum() / df["win"].count() * 100).round(1)
    winrate_without_BE = (df.loc[~BE_mask, "win"].sum() / df.loc[~BE_mask, "win"].count() * 100).round(1)
    avg_rr = df["rr"].mean().round(2)
    total_trades = len(df)

    return [total_profit, total_winrate, winrate_without_BE, avg_rr, total_trades]

def set_header(total_profit: float, total_winrate: float, winrate_without_BE: float, avg_rr: float, total_trades: int) -> None:
    """
    Устанавливает основные числовые метрики в хедер дашборда

    Args:
        total_profit: float - итоговый профит
        total_winrate: float - общий винрейт
        winrate_without_BE: float - винрейт без учета безубыточных сделок
        avg_rr: float - средний риск/ревард (рр)
        total_trades: int - всего сделок
    
    Returns:
        None - функция только устанавливает метрики
    """

    header_cols = st.columns(5)

    header_cols[0].metric("Общий результат", f"{total_profit}$")
    header_cols[1].metric("Общий винрейт", f"{total_winrate}%")
    header_cols[2].metric("Винрейт без БУ сделок", f"{winrate_without_BE}%")
    header_cols[3].metric("Средний РР", avg_rr)
    header_cols[4].metric("Всего сделок", total_trades)

def set_capital_curve(df: pd.DataFrame) -> None:
    """
    Устанавливает график кривой капитала

    Args:
        df: pd.DataFrame - датафрейм, отфильтрованный по классу актива, месяцу, году и аккаунту

    Returns:
        None - функция только устанавливает график
    """

    selected_item = st.selectbox("Выберите отображение", ["Profit", "PNL"])
    equity = selected_item
    
    smoothing = len(df) // 10  # Динамичное сглаживание для скользящей средней

    # Чтобы график был читаем, считаем эквити только если выбран определенный счет, иначе - считаем только профит
    if selected_item != "PNL" and len(df["account_id"].unique()) == 1:
        equity = "Equity"
        df["equity"] = df["account_size"] + df[selected_item.lower()].cumsum()
    else:
        df["equity"] = df[selected_item.lower()].cumsum()

    df["ma"] = df["equity"].rolling(smoothing).mean()

    capital_curve = px.line(
        data_frame=df, 
        x="trade_date", 
        y="equity", 
        labels={"trade_date": "Дата", "equity": equity}, 
        title="Кривая капитала"
    )
    capital_curve.update_traces(
        opacity=0.5,
        hovertemplate=f"%{{x}}<br>{equity}: %{{y:.2f}}{PROFIT_PNL_SYMBS[selected_item]}<extra></extra>"
    )
    capital_curve.add_scatter(
        x=df["trade_date"],
        y=df["ma"],
        mode="lines",
        name="Скользящее среднее",
        line=dict(color="white", width=2, dash="solid"),
        hovertemplate=f"%{{x}}<br>{equity}: %{{y:.2f}}{PROFIT_PNL_SYMBS[selected_item]}<extra></extra>"
    )
    st.plotly_chart(capital_curve, use_container_width=True)

def set_months_chart(df: pd.DataFrame) -> None:
    """
    Устанавливает столбчатый график профита по месяцам

    Args:
        df: pd.DataFrame - датафрейм, отфильтрованный по классу актива, месяцу, году и аккаунту

    Returns:
        None - функция только устанавливает график
    """

    df["months"] = df["trade_date"].dt.strftime("%Y-%m")
    grouping_by_months = df.groupby(by=["months"])["profit"].sum().reset_index()

    fig = px.bar(grouping_by_months, x="months", y="profit")
    fig.update_traces(
        hovertemplate="%{x}<br>Профит: %{y:.2f}$<extra></extra>"
    )
    st.plotly_chart(fig, use_container_width=True)

def create_profit_bar(df: pd.DataFrame, group_col: str) -> go.Figure:
    """
    Создает горизонтальный столбчатый график для отображения профита

    Args:
        df: pd.DataFrame - датафрейм, отфильтрованный по классу актива, месяцу, году и аккаунту
        group_col: str - колонка, по которой нужно группировать

    Returns:
        go.Figure - функция возвращает объект фигуры
    """

    grouped_df = df.groupby([group_col])["profit"].sum().reset_index()
    fig = px.bar(grouped_df, x="profit", y=group_col, orientation="h")

    return fig

def create_winrate_pie(df: pd.DataFrame) -> go.Figure:
    """
    Создает круговую диаграмму винрейта

    Args:
        df: pd.DataFrame - датафрейм, отфильтрованный по классу актива, месяцу, году и аккаунту

    Returns:
        go.Figure - функция возвращает объект фигуры
    """
    BE_mask = (df["pnl"] <= 0.07) & (df["pnl"] >= -0.07)
    win_mask = df["win"] == True
    lose_mask = df["win"] == False

    df.loc[win_mask, "trade_result"] = "Win"
    df.loc[lose_mask, "trade_result"] = "Lose"
    df.loc[BE_mask, "trade_result"] = "BE"

    pie_data = df["trade_result"].value_counts().reset_index()

    fig = px.pie(
        data_frame=pie_data, 
        names="trade_result",
        values="count",
        color="trade_result",
        color_discrete_map={
            "Win": "#00CC96",
            "Lose": "#EF553B",
            "BE": "#b1b1b1",
        }
    )

    return fig

def set_analytics_block(df: pd.DataFrame, group_col: str, title: str) -> None:
    """
    Устанавливает блок, состоящий из 2-ух графиков - профит и винрейт

    Args:
        df: pd.DataFrame - датафрейм, отфильтрованный по классу актива, месяцу, году и аккаунту
        group_col: str - колонка, по которой нужно группировать (для столбчатого графика)
        title: str - название блока графиков
        
    Returns:
        None - функция рисует графики и ничего не возвращает
    """

    with st.container(border=True):
        st.subheader(title)
        col1, col2 = st.columns(2)

        with col1:
            fig_bar = create_profit_bar(df=df, group_col=group_col)
            st.plotly_chart(fig_bar, use_container_width=True, key=f"bar_{group_col}")
        with col2:
            unique_items = df[group_col].dropna().unique()
            
            if len(unique_items) == 0:
                st.warning("Нет данных для винрейта")
                return

            selected_item = st.selectbox("Выберите критерий для винрейта", df[group_col].unique(), key=f"select_{group_col}")
            df_pie = df[df[group_col] == selected_item].copy()

            if df_pie.empty:
                st.warning("Нет данных для отображения")
            else:
                fig_pie = create_winrate_pie(df=df_pie)
                st.plotly_chart(fig_pie, use_container_width=True, key=f"pie_{group_col}")

def set_analytics_group(df: pd.DataFrame, group_cols: list[str], titles: list[str]) -> None:
    """
    Устанавливает группу, состоящую из 2-ух блоков из "set_analytics_block"

    Args:
        df: pd.DataFrame - датафрейм, отфильтрованный по классу актива, месяцу, году и аккаунту
        group_cols: list[str] - список колонок, по которым нужно группировать 1 и 2 блоки соответственно (для столбчатого графика)
        titles: list[str] - список названий 1 и 2 блоков соответственно
        
    Returns:
        None - функция создает блоки для "set_analytics_block" и ничего не возвращает 
    """

    col1, col2 = st.columns(2)

    with col1:
        set_analytics_block(df, group_cols[0], titles[0])
    with col2:
        set_analytics_block(df, group_cols[1], titles[1])

def set_counter_trend_analytics(df: pd.DataFrame) -> None:
    """
    Добавляет новую колонку в df для анализа контртренд сделок
    
    Args:
        df: pd.DataFrame - датафрейм, отфильтрованный по классу актива, месяцу, году и аккаунту
        
    Returns:
        None - функция вызывает "set_analytics_block" и ничего не возвращает
    """

    df["counter_trend_dest"] = df["trade_position"].map(COUNTER_TREND)

    mask_counter_trend = df["trend_type"] == df["counter_trend_dest"]

    df.loc[mask_counter_trend, "is_counter_trend"] = True
    df.loc[~mask_counter_trend, "is_counter_trend"] = False

    set_analytics_block(df, "is_counter_trend", "Статистика по контртренду")

def set_metrics_group(df: pd.DataFrame, total_trades: int) -> None:
    """
    Устанавливает числовые экстремальные метрики (лучшие/худшие)
    
    Args:
        df: pd.DataFrame - датафрейм, отфильтрованный по классу актива, месяцу, году и аккаунту
        
    Returns:
        None - функция устанавливает метрики и ничего не возвращает
    """

    BE_mask = (df["pnl"] <= 0.07) & (df["pnl"] >= -0.07)
    df_filtered = df[~BE_mask]
    min_trades = round(total_trades / 10)

    def get_extremes(col_name: str, min_trades: int):
        is_enough_trades = df_filtered[col_name].value_counts() >= min_trades
        temp_df = df_filtered[df_filtered[col_name].isin(is_enough_trades[is_enough_trades == True].index)]

        if temp_df[col_name].empty:
            return "Недостаточно данных", 0.0, "Недостаточно данных", 0.0
        else:
            winrates = (temp_df.groupby(by=[col_name])["win"].sum() / temp_df.groupby(by=[col_name])["win"].count() * 100).round(1).reset_index()
            profits = temp_df.groupby(by=[col_name])["profit"].sum().round(2).reset_index()
            profits_wrs = pd.merge(winrates, profits, on=col_name)
            profits_wrs = profits_wrs.sort_values(by=["win", "profit"], ascending=[False, False])

            return profits_wrs.iloc[0][col_name], profits_wrs.iloc[0]["win"], profits_wrs.iloc[-1][col_name], profits_wrs.iloc[-1]["win"]

    best_day, best_day_value, worst_day, worst_day_value = get_extremes("trade_day", min_trades=min_trades)
    best_session, best_session_value, worst_session, worst_session_value = get_extremes("trade_session", min_trades=min_trades)
    best_pattern, best_pattern_value, worst_pattern, worst_pattern_value = get_extremes("pattern", min_trades=min_trades)
    best_setup, best_setup_value, worst_setup, worst_setup_value = get_extremes("setup", min_trades=min_trades)
    best_position, best_position_value, worst_position, worst_position_value = get_extremes("trade_position", min_trades=min_trades)
    best_pair, best_pair_value, worst_pair, worst_pair_value = get_extremes("pair", min_trades=min_trades)

    st.subheader("Лучшие показатели")
    cols_best = st.columns(6)
    
    cols_best[0].metric("День:", best_day, delta=f"+ WR: {best_day_value}%")
    cols_best[1].metric("Сессия:", best_session, delta=f"+ WR: {best_session_value}%")
    cols_best[2].metric("Паттерн:", best_pattern, delta=f"+ WR: {best_pattern_value}%")
    cols_best[3].metric("Сетап:", best_setup, delta=f"+ WR: {best_setup_value}%")
    cols_best[4].metric("Позиция:", best_position, delta=f"+ WR: {best_position_value}%")
    cols_best[5].metric("Пара:", best_pair, delta=f"+ WR: {best_pair_value}%")

    st.divider()

    st.subheader("Худшие показатели")
    cols_worst = st.columns(6)
    
    cols_worst[0].metric("День:", worst_day, delta=f"- WR: {worst_day_value}%")
    cols_worst[1].metric("Сессия:", worst_session, delta=f"- WR: {worst_session_value}%")
    cols_worst[2].metric("Паттерн:", worst_pattern, delta=f"- WR: {worst_pattern_value}%")
    cols_worst[3].metric("Сетап:", worst_setup, delta=f"- WR: {worst_setup_value}%")
    cols_worst[4].metric("Позиция:", worst_position, delta=f"- WR: {worst_position_value}%")
    cols_worst[5].metric("Пара:", worst_pair, delta=f"- WR: {worst_pair_value}%")


def run_pipeline():
    """
    Запускает и собирает воедино все объявленные ранее функции
    """
    
    df = load_data()
    df = set_asset_choose(df=df)
    df = set_account_choose(df=df)
    df = set_sidebar(df=df)

    total_profit, total_winrate, winrate_without_BE, avg_rr, total_trades = calculate_main_metrics(df=df)
    set_header(total_profit, total_winrate, winrate_without_BE, avg_rr, total_trades)

    col1, col2 = st.columns(2)
    with col1:
        set_capital_curve(df=df)
    with col2:
        set_months_chart(df=df)

    if df.empty:
        st.warning("Нет сделок по выбранным фильтрам")
        st.stop()

    st.divider()

    set_analytics_group(df, ["trade_day", "trade_session"], ["Статистика по дням недели", "Статистика по сессиям"])
    set_analytics_group(df, ["pattern", "setup"], ["Статистика по паттернам", "Статистика по сетапам"])
    set_analytics_group(df, ["trade_position", "pair"], ["Статистика по позициям", "Статистика по парам"])

    set_counter_trend_analytics(df=df)

    set_metrics_group(df=df, total_trades=total_trades)


run_pipeline()
