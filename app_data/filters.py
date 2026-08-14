import streamlit as st
import pandas as pd


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
