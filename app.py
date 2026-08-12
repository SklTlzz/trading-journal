import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine

import config as cfg


st.set_page_config(page_title="Торговый журнал", layout="wide")

@st.cache_data
def load_data():
    """
    Загружает данные c БД
    """
    
    db_url = f"postgresql://{cfg.DB_USER}:{cfg.DB_PASS}@{cfg.DB_HOST}:{cfg.DB_PORT}/{cfg.DB_NAME}"
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

    df["trade_day"] = pd.Categorical(df["trade_day"], categories=cfg.DAYS_ORDER, ordered=True)
    df["trade_session"] = pd.Categorical(df["trade_session"], categories=cfg.SESSIONS_ORDER, ordered=True)

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
    expected_value = df["profit"].mean().round(2)

    return [total_profit, total_winrate, winrate_without_BE, avg_rr, total_trades, expected_value]

def set_header(total_profit: float, total_winrate: float, winrate_without_BE: float, avg_rr: float, total_trades: int, expected_value: float) -> None:
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

    header_cols = st.columns(6)

    header_cols[0].metric("Общий результат", f"{total_profit}$")
    header_cols[1].metric("Общий винрейт", f"{total_winrate}%")
    header_cols[2].metric("Винрейт без БУ сделок", f"{winrate_without_BE}%")
    header_cols[3].metric("Средний РР", avg_rr)
    header_cols[4].metric("Всего сделок", total_trades)
    header_cols[5].metric("Мат. ожидание от сделки", expected_value)

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
        hovertemplate=f"%{{x}}<br>{equity}: %{{y:.2f}}{cfg.PROFIT_PNL_SYMBS[selected_item]}<extra></extra>"
    )
    capital_curve.add_scatter(
        x=df["trade_date"],
        y=df["ma"],
        mode="lines",
        name="Скользящее среднее",
        line=dict(color="white", width=2, dash="solid"),
        hovertemplate=f"%{{x}}<br>{equity}: %{{y:.2f}}{cfg.PROFIT_PNL_SYMBS[selected_item]}<extra></extra>"
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
    fig = px.bar(grouped_df, x="profit", y=group_col, orientation="h", labels={"profit": "Профит"})

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
        },
        labels={"count": "Количество", "trade_result": "Результат"}
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

    df["counter_trend_dest"] = df["trade_position"].map(cfg.COUNTER_TREND)

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

    def get_extremes(col_name: str, min_trades: int) -> tuple[str, float, str, float]:
        """
        Рассчитывает экстремальные значения винрейта и профита

        Args:
            col_name: str - метрика, по которой ведется расчет
            min_trades: int - минимальное кол-во сделок, необходимое для учета экстремума

        Returns:
            tuple[str, float, str, float] - функция возвращает экстремальные значения профита и винрейта
        """

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

def set_emotional_section(df: pd.DataFrame) -> None:
    """
    Устанавливает часть ТЖ по эмоциям и ошибкам (отрисовывет графики, расчитывает метрики)

    Args:
        df: pd.DataFrame - датафрейм, отфильтрованный по классу актива, месяцу, году и аккаунту
            
    Returns:
        None - функция устанавливает метрики и графики и ничего не возвращает
    """

    df_with_data = df[df["mistake"] != "No data"].copy()
    metric_col = st.columns(1)
    metric_col[0].metric("Всего ошибок:", len(df_with_data))

    chart_cols = st.columns(3)

    with chart_cols[0]:
        with st.container(border=True):
            if df_with_data.empty:
                st.warning("Нет данных")

            st.subheader("Ошибки и их количество")
            mistake_counts = df_with_data["mistake"].value_counts().reset_index()

            fig = px.bar(mistake_counts, x="count", y="mistake", orientation="h", labels={"count": "Количество", "mistake": "Ошибка"})
            st.plotly_chart(fig, use_container_width=True, key="bar_count_mistake")
    with chart_cols[1]:
        with st.container(border=True):
            if df_with_data.empty:
                st.warning("Нет данных")

            st.subheader("Ошибки по сессиям")
            session_data = df_with_data.groupby(["trade_session"])["mistake"].count().reset_index()

            fig = px.pie(
                session_data,
                names="trade_session",
                values="mistake",
                color="trade_session",
                color_discrete_map={
                    "New York": "#2962ffff",
                    "London": "#ff9900ff",
                    "Asia": "#ffeb3bff"
                },
                labels={"trade_session": "Сессия", "mistake": "Количество"}
            )
            st.plotly_chart(fig, use_container_width=True, key="pie_session_mistake")
    with chart_cols[2]:
        with st.container(border=True):
            if df_with_data.empty:
                st.warning("Нет данных")

            st.subheader("Цена ошибки")
            grouped_df = df_with_data.groupby(["mistake"])["profit"].sum().reset_index()

            fig = px.bar(grouped_df, x="profit", y="mistake", orientation="h", labels={"profit": "Профит", "mistake": "Ошибка"})
            st.plotly_chart(fig, use_container_width=True, key="bar_price_mistake")

def monte_carlo_charts(series_worst: pd.Series, series_mid: pd.Series, series_best: pd.Series) -> None:
    """
    Отрисовывет графики по симуляции Монте-Карло (лучший эквити, средний и худший)
    
    Args:
        series_worst: pd.DataFrame - датафрейм, состоящий из кумулятивного профита лучшего аккаунта
        series_mid: pd.DataFrame - датафрейм, состоящий из кумулятивного профита среднего аккаунта
        series_best: pd.DataFrame - датафрейм, состоящий из кумулятивного профита худшего аккаунта
    
    Returns:
        None - функция устанавливает график и ничего не возвращает
    """

    st.subheader("Графики симуляции Монте-Карло. Считаем, что изначальный депозит - 5000")

    fig = go.Figure()

    steps = list(range(1, 61))

    fig.add_trace(go.Scatter(x=steps, y=series_best, mode="lines", name="Лучший сценарий", line=dict(color="green")))
    fig.add_trace(go.Scatter(x=steps, y=series_worst, mode="lines", name="Худший сценарий", line=dict(color="red")))
    fig.add_trace(go.Scatter(x=steps, y=series_mid, mode="lines", name="Средний сценарий", line=dict(color="grey")))

    st.plotly_chart(fig, use_container_width=True)

def select_trades_per_acc() -> int:
    """
    Устанавливает ползунок для выбора лимита сделок на аккаунт

    Args:
        None - функция ничего не принимает в качестве аргумента
    Returns:
        int - функция возвращает число - выбранный лимит сделок для аккаунта
    """

    trades = st.select_slider("Выберите лимит сделок на аккаунт", [i for i in range(40, 71, 5)])

    return trades

@st.cache_data
def simulation_monte_carlo(df: pd.DataFrame, trades_per_acc: int) -> None:
    """
    Создает и запускает симуляцию Монте-Карло. Проверять дневную просадку - излишне. 
        В моей торговле максимальное количество позиций в день - 3 c риском 1% на каждую. 
        Слить счет c дневной просадкой в 5% по моей симуляции и торговой стратегии не получится физически 

    Args:
        df: pd.DataFrame - исходный датафрейм без фильтраций

    Returns:
        None - функция устанавливает метрики и график и ничего не возвращает
    """

    np.random.seed(0)

    account_size = 5000
    accounts_count = 1000

    new_df = df[(df["account_id"] == 1) & (df["asset_type"] == "RWA")].reset_index().copy()  # На 5к RWA счете больше всего сделок, а также сделки на 10к и 25к счетах - копипаст сделок 5к счета, поэтому берем из сырого массива только 5к RWA счет
    chosen_trades = np.random.choice(np.array(new_df.index), size=(accounts_count, trades_per_acc), replace=True)

    def pass_step(chunk: pd.DataFrame, target: int, profit_days: int) -> tuple[bool, int]:
        """
        Проверяет, будет ли пройдена фаза по сделкам из chunk по заданным параметрам target и profit_days 

        Args:
            chunk: pd.DataFrame - датафрейм сгенерированных сделок
            target: int - цель общего профита
            profit_days: int - цель для общих прибыльных дней
    
        Returns:
            tuple[bool, int] - функция возвращает список, где лежит bool-значение (аккаунт прошел/не прошел фазу) 
                и номер сделки из chunk, на которой он прошел фазу
        """

        mask_profit_day = chunk["profit"] >= account_size * 0.005
        
        chunk.loc[mask_profit_day, "is_profit_day"] = True
        chunk.loc[~mask_profit_day, "is_profit_day"] = False
        chunk.loc[chunk["trade_date"] == chunk["trade_date"].shift(1), "is_profit_day"] = False

        profitable_days = chunk["is_profit_day"].cumsum(axis=0)
        cum_profit = chunk["profit"].cumsum(axis=0)

        mask_lose = ((cum_profit / account_size) * 100) <= cfg.TOTAL_DRAWDOWN
        mask_pass = (((cum_profit / account_size) * 100) >= target) & (profitable_days >= profit_days)

        lose_moment = mask_lose.idxmax() if mask_lose.any() else 999
        pass_moment = mask_pass.idxmax() if mask_pass.any() else 999

        return (pass_moment < lose_moment, pass_moment)

    phase1_passed_count = 0
    phase2_passed_count = 0
    payout_count = 0
    trades_1phase = []
    trades_2phase = []
    trades_funded = []
    cum_profit_list = []

    for chunk in chosen_trades:
        simulation_trades = new_df.iloc[chunk].reset_index(drop=True).copy()
        target = cfg.TARGET_1PHASE_PRC
        profit_days = cfg.PROFITABLE_DAYS_1PHASE

        cum_profit = simulation_trades["profit"].cumsum(axis=0)
        cum_profit_list.append(cum_profit)

        phase1_result, pass_moment_1phase = pass_step(simulation_trades, target, profit_days)

        if phase1_result:
            target = cfg.TARGET_2PHASE_PRC
            profit_days = cfg.PROFITABLE_DAYS_2PHASE
            phase1_passed_count += 1
            trades_1phase.append(pass_moment_1phase + 1)

            simulation_trades = simulation_trades.iloc[pass_moment_1phase+1:].reset_index(drop=True)
            phase2_result, pass_moment_2phase = pass_step(simulation_trades, target, profit_days)

            if phase2_result:
                target = 1
                profit_days = cfg.PROFITABLE_DAYS_FUNDED
                phase2_passed_count += 1
                trades_2phase.append(pass_moment_2phase + 1)

                simulation_trades = simulation_trades.iloc[pass_moment_2phase+1:].reset_index(drop=True)
                funded_result, pass_moment_funded = pass_step(simulation_trades, target, profit_days)

                if funded_result:
                    payout_count += 1
                    trades_funded.append(pass_moment_funded + 1)

    final_cum_profits = [cum_profit.iloc[-1] for cum_profit in cum_profit_list]
    mid_cum_profit = round(sum(final_cum_profits) / len(final_cum_profits), 2)

    best_cum_profit_idx = final_cum_profits.index(max(final_cum_profits))
    worst_cum_profit_idx = final_cum_profits.index(min(final_cum_profits))
    mid_cum_profit_idx = min(range(len(final_cum_profits)), key=lambda i: abs(final_cum_profits[i] - mid_cum_profit))

    series_best = cum_profit_list[best_cum_profit_idx] + account_size
    series_worst = cum_profit_list[worst_cum_profit_idx] + account_size
    series_mid = cum_profit_list[mid_cum_profit_idx] + account_size

    reg_payout_prc = round((payout_count / phase2_passed_count) * 100, 2) if phase2_passed_count > 0 else 0.0
    abs_payout_prc = round((payout_count / accounts_count) * 100, 2)

    funnel_data = {
        "step": ["Куплено счетов", "Прошли 1 фазу", "Прошли 2 фазу", "Получили выплату"],
        "survived": [accounts_count, phase1_passed_count, phase2_passed_count, payout_count]
    }
    df_funnel = pd.DataFrame(funnel_data)

    st.subheader("Воронка конверсий")

    with st.container(border=True):
        fig = px.funnel(df_funnel, x="survived", y="step", labels={"survived": "Выжило", "step": "Этап"})
        fig.update_traces(textinfo="value+percent initial")
        st.plotly_chart(fig, use_container_width=True, key="funnel_monte_carlo")

    metric_cols = st.columns(5)

    metric_cols[0].metric("Относительная конверсия:", f"{reg_payout_prc}%")
    metric_cols[1].metric("Абсолютная конверсия:", f"{abs_payout_prc}%")
    metric_cols[2].metric("Среднее кол-во сделок для 1 фазы:", (sum(trades_1phase) // len(trades_1phase)) if trades_1phase else "Нет счетов")
    metric_cols[3].metric("Среднее кол-во сделок для 2 фазы:", (sum(trades_2phase) // len(trades_2phase)) if trades_2phase else "Нет счетов")
    metric_cols[4].metric("Среднее кол-во сделок до пейаута:", (sum(trades_funded) // len(trades_funded)) if trades_funded else "Нет счетов")

    monte_carlo_charts(series_worst, series_mid, series_best)

def kelly_criterion(winrate: float, avg_rr: float) -> None:
    """
    Рассчитывает и выводит в дашборд критерий Келли

    Args:
        winrate: float - общий винрейт в долях от 0 до 1 (с учетом БУ сделок)
        avg_rr: float - средний РР (risk/reward)

    Returns:
        None - функция выводит метрику и ничего не возвращает
    """

    criterion = round((avg_rr*winrate - (1 - winrate)) / avg_rr * 100, 2) if avg_rr != 0 else 0.0

    if criterion > 0:
        col = st.columns(1)
        col[0].metric("Оптимальный размер позиции от капитала на 1 сделку для максимизации профита (если убрать ограничения от пропа):", f"{criterion}%")
    else:
        st.warning("Стратегия убыточна")


def run_pipeline():
    """
    Запускает и собирает воедино все объявленные ранее функции
    """
    
    df = load_data()
    df_raw = df.copy()
    df = set_asset_choose(df=df)
    df = set_account_choose(df=df)
    df = set_sidebar(df=df)

    st.title("Цифры и графики")

    total_profit, total_winrate, winrate_without_BE, avg_rr, total_trades, expected_value = calculate_main_metrics(df=df)
    set_header(total_profit, total_winrate, winrate_without_BE, avg_rr, total_trades, expected_value)

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


    st.divider()
    st.divider()
    st.title("Эмоции и ошибки")

    set_emotional_section(df=df)


    st.divider()
    st.divider()
    st.title("Статистические метрики")

    trades_per_acc = select_trades_per_acc()
    simulation_monte_carlo(df=df_raw, trades_per_acc=trades_per_acc)

    kelly_criterion(total_winrate/100, avg_rr)


run_pipeline()
