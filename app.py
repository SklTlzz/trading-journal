import streamlit as st

from app_data.loader import load_data
from app_data.filters import set_asset_choose, set_sidebar, set_account_choose
from app_sections.main_board import calculate_main_metrics, set_header, set_capital_curve, set_months_chart, \
                                set_analytics_group, set_counter_trend_analytics, set_metrics_group 
from app_sections.emotions import set_emotional_section
from app_sections.statistics import select_trades_per_acc, simulation_monte_carlo, kelly_criterion, day_time_heatmap


st.set_page_config(page_title="Торговый журнал", layout="wide")

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

    day_time_heatmap(df=df)


run_pipeline()
