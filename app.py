import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine

from config import DB_USER, DB_HOST, DB_PORT, DB_NAME, DB_PASS


st.set_page_config(page_title="Торговый журнал", layout="wide")

@st.cache_data
def load_data():
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

    return df

def set_asset_choose(df: pd.DataFrame) -> pd.DataFrame:
    assets_list = list(df["asset_type"].unique())

    selected_asset = st.radio("Выбери класс активов", assets_list, horizontal=True)

    df = df[df["asset_type"] == selected_asset]

    return df

def set_account_choose(df: pd.DataFrame) -> pd.DataFrame:
    accounts_list = ["Все"] + list(df["account_size"].unique())

    selected_account = st.radio("Выбери счет", accounts_list, horizontal=True)

    if selected_account != "Все":
        df = df[df["account_size"] == selected_account]

    return df


def set_sidebar(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("Фильтры")

    years = ["Все"] + list(df["year_filter"].unique())
    selected_year = st.sidebar.selectbox("Выбери год", years)

    if selected_year == "Все":
        months = ["Все"] + list(df["month_filter"].unique())
    else:
        selected_year_mask = df["year_filter"] == selected_year
        months = ["Все"] + list(df.loc[selected_year_mask, "month_filter"].unique())
        df = df[selected_year_mask]

    selected_month = st.sidebar.selectbox("Выбери месяц", months)

    if selected_month != "Все":
        select_box_mask = df["month_filter"] == selected_month
        df = df[select_box_mask]

    return df

def calculate_main_metrics(df: pd.DataFrame) -> list[float | int]:
    BE_mask = (df["pnl"] <= 0.07) & (df["pnl"] >= -0.07)

    total_profit = df["profit"].sum().round(2)
    total_winrate = (df["win"].sum() / df["win"].count() * 100).round(1)
    winrate_without_BE = (df.loc[~BE_mask, "win"].sum() / df.loc[~BE_mask, "win"].count() * 100).round(1)
    avg_rr = df["rr"].mean().round(2)
    total_trades = len(df)

    return [total_profit, total_winrate, winrate_without_BE, avg_rr, total_trades]

def set_header(total_profit: float, total_winrate: float, winrate_without_BE: float, avg_rr: float, total_trades: int) -> None:
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Общий результат", f"{total_profit}$")
    col2.metric("Общий винрейт", f"{total_winrate}%")
    col3.metric("Винрейт без БУ сделок", f"{winrate_without_BE}%")
    col4.metric("Средний РР", avg_rr)
    col5.metric("Всего сделок", total_trades)

def set_capital_curve(df: pd.DataFrame) -> None:
    smoothing = len(df) // 10

    if len(df["account_id"].unique()) == 1:
        df["equity"] = df["account_size"] + df["profit"].cumsum()
    else:
        df["equity"] = df["profit"].cumsum()

    df["ma"] = df["equity"].rolling(smoothing).mean()

    capital_curve = px.line(
        data_frame=df, 
        x="trade_date", 
        y="equity", 
        labels={"trade_date": "Дата", "equity": "Профит"}, 
        title="Кривая капитала"
    )
    capital_curve.update_traces(
        opacity=0.5,
        hovertemplate='%{x}<br>Профит: %{y:.2f}$<extra></extra>'
    )
    capital_curve.add_scatter(
        x=df["trade_date"],
        y=df["ma"],
        mode="lines",
        name="Скользящее среднее",
        line=dict(color="white", width=2, dash="solid"),
        hovertemplate='%{x}<br>Профит: %{y:.2f}$<extra></extra>'
    )
    st.plotly_chart(capital_curve, use_container_width=True)


def run_pipeline():
    df = load_data()
    df = set_asset_choose(df=df)
    df = set_account_choose(df=df)
    df = set_sidebar(df=df)

    total_profit, total_winrate, winrate_without_BE, avg_rr, total_trades = calculate_main_metrics(df=df)
    set_header(total_profit, total_winrate, winrate_without_BE, avg_rr, total_trades)
    set_capital_curve(df=df)
    

run_pipeline()
