import streamlit as st
import pandas as pd
import plotly.express as px


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
