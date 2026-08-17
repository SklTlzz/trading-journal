import streamlit as st
import pandas as pd


def set_asset_choose(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filters the dataframe by the selected asset class (Crypto or RWA)
    
    Args:
        df: pd.DataFrame - initial dataframe with all trades

    Returns:
        pd.DataFrame - filtered dataframe containing only the selected asset class
    """

    assets_list = list(df["asset_type"].unique())

    selected_asset = st.sidebar.radio("Select asset class", assets_list, horizontal=True)

    df = df[df["asset_type"] == selected_asset]

    return df

def set_sidebar(df: pd.DataFrame) -> pd.DataFrame:
    """
    Sets up the sidebar with filters for all charts and metrics

    Args:
        df: pd.DataFrame - dataframe filtered by asset class

    Returns:
        pd.DataFrame - dataframe filtered by selected year and month
    """

    st.sidebar.header("Filters")

    years = ["All"] + list(df["year_filter"].unique())
    selected_year = st.sidebar.selectbox("Select year", years)

    if selected_year == "All":
        months = ["All"] + list(df["month_filter"].unique())
    else:
        selected_year_mask = df["year_filter"] == selected_year
        months = ["All"] + list(df.loc[selected_year_mask, "month_filter"].unique())
        df = df[selected_year_mask]

    selected_month = st.sidebar.selectbox("Select month", months)

    if selected_month != "All":
        select_box_mask = df["month_filter"] == selected_month
        df = df[select_box_mask]

    return df

def set_account_choose(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filters the dataframe by the selected account (All, 5k, 10k, or 25k)

    Args:
        df: pd.DataFrame - dataframe filtered by asset class, month, and year

    Returns:
        pd.DataFrame - dataframe filtered by accounts
    """

    accounts_list = ["All"] + sorted(list(df["account_size"].unique()))

    selected_account = st.sidebar.radio("Select account", accounts_list, horizontal=True)

    if selected_account != "All":
        df = df[df["account_size"] == selected_account]

    return df
