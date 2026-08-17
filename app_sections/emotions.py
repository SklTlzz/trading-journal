import streamlit as st
import pandas as pd
import plotly.express as px


def set_emotional_section(df: pd.DataFrame) -> None:
    """
    Sets up the trading journal section for emotions and mistakes (draws charts, calculates metrics)

    Args:
        df: pd.DataFrame - dataframe filtered by asset class, month, year, and account
            
    Returns:
        None - the function sets up metrics and charts and returns nothing
    """

    df_with_data = df[df["mistake"] != "No data"].copy()
    metric_col = st.columns(1)
    metric_col[0].metric("Total Mistakes:", len(df_with_data))

    chart_cols = st.columns(3)

    with chart_cols[0]:
        with st.container(border=True):
            if df_with_data.empty:
                st.warning("No data")

            st.subheader("Mistakes Count")
            mistake_counts = df_with_data["mistake"].value_counts().reset_index()

            fig = px.bar(mistake_counts, x="count", y="mistake", orientation="h", labels={"count": "Count", "mistake": "Mistake"})
            st.plotly_chart(fig, use_container_width=True, key="bar_count_mistake")
    with chart_cols[1]:
        with st.container(border=True):
            if df_with_data.empty:
                st.warning("No data")

            st.subheader("Mistakes by Session")
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
                labels={"trade_session": "Session", "mistake": "Count"}
            )
            st.plotly_chart(fig, use_container_width=True, key="pie_session_mistake")
    with chart_cols[2]:
        with st.container(border=True):
            if df_with_data.empty:
                st.warning("No data")

            st.subheader("Cost of Mistake")
            grouped_df = df_with_data.groupby(["mistake"])["profit"].sum().reset_index()

            fig = px.bar(grouped_df, x="profit", y="mistake", orientation="h", labels={"profit": "Profit", "mistake": "Mistake"})
            st.plotly_chart(fig, use_container_width=True, key="bar_price_mistake")
