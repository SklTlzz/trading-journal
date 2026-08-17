import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

import config as cfg


def calculate_main_metrics(df: pd.DataFrame) -> list[float | int]:
    """
    Calculates the main numerical metrics located in the dashboard header.
    Assuming breakeven is a trade where -0.07 <= PNL <= 0.07

    Args:
        df: pd.DataFrame - dataframe filtered by asset class, month, year, and account

    Returns:
        list[float | int] - list of 5 main metrics
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
    Sets up the main numerical metrics in the dashboard header

    Args:
        total_profit: float - total profit
        total_winrate: float - overall winrate
        winrate_without_BE: float - winrate excluding breakeven trades
        avg_rr: float - average risk/reward (RR)
        total_trades: int - total number of trades
    
    Returns:
        None - the function only sets up the metrics
    """

    header_cols = st.columns(6)

    header_cols[0].metric("Total Profit", f"{total_profit}$")
    header_cols[1].metric("Total Winrate", f"{total_winrate}%")
    header_cols[2].metric("Winrate w/o BE", f"{winrate_without_BE}%")
    header_cols[3].metric("Average RR", avg_rr)
    header_cols[4].metric("Total Trades", total_trades)
    header_cols[5].metric("Expected Value", expected_value)

def set_capital_curve(df: pd.DataFrame) -> None:
    """
    Sets up the equity curve chart

    Args:
        df: pd.DataFrame - dataframe filtered by asset class, month, year, and account

    Returns:
        None - the function only sets up the chart
    """

    selected_item = st.selectbox("Select view", ["Profit", "PNL"])
    equity = selected_item
    
    smoothing = len(df) // 10  # Dynamic smoothing for the moving average

    # To keep the chart readable, we calculate equity only if a specific account is selected, otherwise we only calculate profit
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
        labels={"trade_date": "Date", "equity": equity}, 
        title="Equity Curve"
    )
    capital_curve.update_traces(
        opacity=0.5,
        hovertemplate=f"%{{x}}<br>{equity}: %{{y:.2f}}{cfg.PROFIT_PNL_SYMBS[selected_item]}<extra></extra>"
    )
    capital_curve.add_scatter(
        x=df["trade_date"],
        y=df["ma"],
        mode="lines",
        name="Moving Average",
        line=dict(color="white", width=2, dash="solid"),
        hovertemplate=f"%{{x}}<br>{equity}: %{{y:.2f}}{cfg.PROFIT_PNL_SYMBS[selected_item]}<extra></extra>"
    )
    st.plotly_chart(capital_curve, use_container_width=True)

def set_months_chart(df: pd.DataFrame) -> None:
    """
    Sets up the bar chart for profit by months

    Args:
        df: pd.DataFrame - dataframe filtered by asset class, month, year, and account

    Returns:
        None - the function only sets up the chart
    """

    df["months"] = df["trade_date"].dt.strftime("%Y-%m")
    grouping_by_months = df.groupby(by=["months"])["profit"].sum().reset_index()

    fig = px.bar(grouping_by_months, x="months", y="profit")
    fig.update_traces(
        hovertemplate="%{x}<br>Profit: %{y:.2f}$<extra></extra>"
    )
    st.plotly_chart(fig, use_container_width=True)

def create_profit_bar(df: pd.DataFrame, group_col: str) -> go.Figure:
    """
    Creates a horizontal bar chart to display profit

    Args:
        df: pd.DataFrame - dataframe filtered by asset class, month, year, and account
        group_col: str - column to group by

    Returns:
        go.Figure - the function returns a figure object
    """

    grouped_df = df.groupby([group_col])["profit"].sum().reset_index()
    fig = px.bar(grouped_df, x="profit", y=group_col, orientation="h", labels={"profit": "Profit"})

    return fig

def create_winrate_pie(df: pd.DataFrame) -> go.Figure:
    """
    Creates a pie chart for winrate

    Args:
        df: pd.DataFrame - dataframe filtered by asset class, month, year, and account

    Returns:
        go.Figure - the function returns a figure object
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
        labels={"count": "Count", "trade_result": "Result"}
    )

    return fig

def set_analytics_block(df: pd.DataFrame, group_col: str, title: str) -> None:
    """
    Sets up a block consisting of 2 charts - profit and winrate

    Args:
        df: pd.DataFrame - dataframe filtered by asset class, month, year, and account
        group_col: str - column to group by (for the bar chart)
        title: str - title of the chart block
        
    Returns:
        None - the function draws charts and returns nothing
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
                st.warning("No data for winrate")
                return

            selected_item = st.selectbox("Select criterion for winrate", df[group_col].unique(), key=f"select_{group_col}")
            df_pie = df[df[group_col] == selected_item].copy()

            if df_pie.empty:
                st.warning("No data to display")
            else:
                fig_pie = create_winrate_pie(df=df_pie)
                st.plotly_chart(fig_pie, use_container_width=True, key=f"pie_{group_col}")

def set_analytics_group(df: pd.DataFrame, group_cols: list[str], titles: list[str]) -> None:
    """
    Sets up a group consisting of 2 blocks from "set_analytics_block"

    Args:
        df: pd.DataFrame - dataframe filtered by asset class, month, year, and account
        group_cols: list[str] - list of columns to group the 1st and 2nd blocks by respectively (for the bar chart)
        titles: list[str] - list of titles for the 1st and 2nd blocks respectively
        
    Returns:
        None - the function creates blocks for "set_analytics_block" and returns nothing 
    """

    col1, col2 = st.columns(2)

    with col1:
        set_analytics_block(df, group_cols[0], titles[0])
    with col2:
        set_analytics_block(df, group_cols[1], titles[1])

def set_counter_trend_analytics(df: pd.DataFrame) -> None:
    """
    Adds a new column to df for analyzing counter-trend trades
    
    Args:
        df: pd.DataFrame - dataframe filtered by asset class, month, year, and account
        
    Returns:
        None - the function calls "set_analytics_block" and returns nothing
    """

    df["counter_trend_dest"] = df["trade_position"].map(cfg.COUNTER_TREND)

    mask_counter_trend = df["trend_type"] == df["counter_trend_dest"]

    df.loc[mask_counter_trend, "is_counter_trend"] = True
    df.loc[~mask_counter_trend, "is_counter_trend"] = False

    set_analytics_block(df, "is_counter_trend", "Counter-trend Stats")

def set_metrics_group(df: pd.DataFrame, total_trades: int) -> None:
    """
    Sets up extreme numerical metrics (best/worst)
    
    Args:
        df: pd.DataFrame - dataframe filtered by asset class, month, year, and account
        
    Returns:
        None - the function sets up metrics and returns nothing
    """

    BE_mask = (df["pnl"] <= 0.07) & (df["pnl"] >= -0.07)
    df_filtered = df[~BE_mask]
    min_trades = round(total_trades / 10)

    def get_extremes(col_name: str, min_trades: int) -> tuple[str, float, str, float]:
        """
        Calculates extreme values for winrate and profit

        Args:
            col_name: str - the metric being calculated
            min_trades: int - minimum number of trades required to consider the extreme

        Returns:
            tuple[str, float, str, float] - the function returns extreme values of profit and winrate
        """

        is_enough_trades = df_filtered[col_name].value_counts() >= min_trades
        temp_df = df_filtered[df_filtered[col_name].isin(is_enough_trades[is_enough_trades == True].index)]

        if temp_df[col_name].empty:
            return "Not enough data", 0.0, "Not enough data", 0.0
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

    st.subheader("Best Performers")
    cols_best = st.columns(6)
    
    cols_best[0].metric("Day:", best_day, delta=f"+ WR: {best_day_value}%")
    cols_best[1].metric("Session:", best_session, delta=f"+ WR: {best_session_value}%")
    cols_best[2].metric("Pattern:", best_pattern, delta=f"+ WR: {best_pattern_value}%")
    cols_best[3].metric("Setup:", best_setup, delta=f"+ WR: {best_setup_value}%")
    cols_best[4].metric("Position:", best_position, delta=f"+ WR: {best_position_value}%")
    cols_best[5].metric("Pair:", best_pair, delta=f"+ WR: {best_pair_value}%")

    st.divider()

    st.subheader("Worst Performers")
    cols_worst = st.columns(6)
    
    cols_worst[0].metric("Day:", worst_day, delta=f"- WR: {worst_day_value}%")
    cols_worst[1].metric("Session:", worst_session, delta=f"- WR: {worst_session_value}%")
    cols_worst[2].metric("Pattern:", worst_pattern, delta=f"- WR: {worst_pattern_value}%")
    cols_worst[3].metric("Setup:", worst_setup, delta=f"- WR: {worst_setup_value}%")
    cols_worst[4].metric("Position:", worst_position, delta=f"- WR: {worst_position_value}%")
    cols_worst[5].metric("Pair:", worst_pair, delta=f"- WR: {worst_pair_value}%")
