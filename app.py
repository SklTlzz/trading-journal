import streamlit as st

from app_data.loader import load_data
from app_data.filters import set_asset_choose, set_sidebar, set_account_choose
from app_sections.main_board import calculate_main_metrics, set_header, set_capital_curve, set_months_chart, \
                                set_analytics_group, set_counter_trend_analytics, set_metrics_group 
from app_sections.emotions import set_emotional_section
from app_sections.statistics import select_trades_per_acc, simulation_monte_carlo, kelly_criterion, day_time_heatmap, pair_session_heatmap


st.set_page_config(page_title="Trading Journal", layout="wide")

def run_pipeline():
    """
    Runs and integrates all previously declared functions
    """
    
    df = load_data()
    df_raw = df.copy()
    df = set_asset_choose(df=df)
    df = set_account_choose(df=df)
    df = set_sidebar(df=df)

    st.title("Metrics and Charts")

    total_profit, total_winrate, winrate_without_BE, avg_rr, total_trades, expected_value = calculate_main_metrics(df=df)
    set_header(total_profit, total_winrate, winrate_without_BE, avg_rr, total_trades, expected_value)

    col1, col2 = st.columns(2)
    with col1:
        set_capital_curve(df=df)
    with col2:
        set_months_chart(df=df)

    if df.empty:
        st.warning("No trades found for the selected filters")
        st.stop()

    st.divider()

    set_analytics_group(df, ["trade_day", "trade_session"], ["Stats by Day of Week", "Stats by Session"])
    set_analytics_group(df, ["pattern", "setup"], ["Stats by Pattern", "Stats by Setup"])
    set_analytics_group(df, ["trade_position", "pair"], ["Stats by Position", "Stats by Pair"])

    set_counter_trend_analytics(df=df)

    set_metrics_group(df=df, total_trades=total_trades)


    st.divider()
    st.divider()
    st.title("Emotions and Mistakes")

    set_emotional_section(df=df)


    st.divider()
    st.divider()
    st.title("Statistical Metrics")

    trades_per_acc = select_trades_per_acc()
    simulation_monte_carlo(df=df_raw, trades_per_acc=trades_per_acc)

    kelly_criterion(total_winrate/100, avg_rr)

    day_time_heatmap(df=df)

    pair_session_heatmap(df=df)


run_pipeline()
