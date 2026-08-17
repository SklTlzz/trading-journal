import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import pandas as pd

import config as cfg


def monte_carlo_charts(series_worst: pd.Series, series_mid: pd.Series, series_best: pd.Series) -> None:
    """
    Draws charts for Monte Carlo simulation (best, average, and worst equity)
    
    Args:
        series_worst: pd.DataFrame - dataframe consisting of cumulative profit for the worst account
        series_mid: pd.DataFrame - dataframe consisting of cumulative profit for the average account
        series_best: pd.DataFrame - dataframe consisting of cumulative profit for the best account
    
    Returns:
        None - the function sets up the chart and returns nothing
    """

    st.subheader("Monte Carlo Simulation Charts (Assuming an initial deposit of 5000)")

    fig = go.Figure()

    steps = list(range(1, 61))

    fig.add_trace(go.Scatter(x=steps, y=series_best, mode="lines", name="Best Case", line=dict(color="green")))
    fig.add_trace(go.Scatter(x=steps, y=series_worst, mode="lines", name="Worst Case", line=dict(color="red")))
    fig.add_trace(go.Scatter(x=steps, y=series_mid, mode="lines", name="Average Case", line=dict(color="grey")))

    st.plotly_chart(fig, use_container_width=True)

def select_trades_per_acc() -> int:
    """
    Sets up a slider to select the trade limit per account

    Args:
        None - the function takes no arguments
    Returns:
        int - the function returns a number representing the selected trade limit per account
    """

    trades = st.select_slider("Select trade limit per account", [i for i in range(40, 71, 5)])

    return trades

@st.cache_data
def simulation_monte_carlo(df: pd.DataFrame, trades_per_acc: int) -> None:
    """
    Creates and runs a Monte Carlo simulation. Checking daily drawdown is unnecessary here. 
        In my trading, the maximum number of positions per day is 3 with a 1% risk per trade. 
        Blowing an account with a 5% daily drawdown is physically impossible with my strategy.

    Args:
        df: pd.DataFrame - raw dataframe without filters

    Returns:
        None - the function sets up metrics and charts and returns nothing
    """

    np.random.seed(0)

    account_size = 5000
    accounts_count = 1000

    new_df = df[(df["account_id"] == 1) & (df["asset_type"] == "RWA")].reset_index().copy()  # The 5k RWA account has the most trades, and trades on 10k/25k are copy-pasted, so we only take the 5k RWA account from the raw array
    chosen_trades = np.random.choice(np.array(new_df.index), size=(accounts_count, trades_per_acc), replace=True)

    def pass_step(chunk: pd.DataFrame, target: int, profit_days: int) -> tuple[bool, int]:
        """
        Checks if the phase will be passed based on the trades from the chunk with given target and profit_days parameters

        Args:
            chunk: pd.DataFrame - dataframe of generated trades
            target: int - total profit target
            profit_days: int - target for total profitable days
    
        Returns:
            tuple[bool, int] - the function returns a tuple containing a boolean (whether the account passed/failed the phase)
                and the trade index from the chunk where the phase was passed
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
        "step": ["Accounts Purchased", "Passed Phase 1", "Passed Phase 2", "Received Payout"],
        "survived": [accounts_count, phase1_passed_count, phase2_passed_count, payout_count]
    }
    df_funnel = pd.DataFrame(funnel_data)

    st.subheader("Conversion Funnel")

    with st.container(border=True):
        fig = px.funnel(df_funnel, x="survived", y="step", labels={"survived": "Survived", "step": "Stage"})
        fig.update_traces(textinfo="value+percent initial")
        st.plotly_chart(fig, use_container_width=True, key="funnel_monte_carlo")

    metric_cols = st.columns(5)

    metric_cols[0].metric("Relative Conversion:", f"{reg_payout_prc}%")
    metric_cols[1].metric("Absolute Conversion:", f"{abs_payout_prc}%")
    metric_cols[2].metric("Avg. trades for Phase 1:", (sum(trades_1phase) // len(trades_1phase)) if trades_1phase else "No accounts")
    metric_cols[3].metric("Avg. trades for Phase 2:", (sum(trades_2phase) // len(trades_2phase)) if trades_2phase else "No accounts")
    metric_cols[4].metric("Avg. trades to Payout:", (sum(trades_funded) // len(trades_funded)) if trades_funded else "No accounts")

    st.divider()
    monte_carlo_charts(series_worst, series_mid, series_best)

def kelly_criterion(winrate: float, avg_rr: float) -> None:
    """
    Calculates and displays the Kelly Criterion on the dashboard

    Args:
        winrate: float - overall winrate as a fraction from 0 to 1 (including BE trades)
        avg_rr: float - average RR (risk/reward)

    Returns:
        None - the function displays the metric and returns nothing
    """

    criterion = round((avg_rr*winrate - (1 - winrate)) / avg_rr * 100, 2) if avg_rr != 0 else 0.0

    if criterion > 0:
        col = st.columns(1)
        col[0].metric("Optimal equity allocation per trade to maximize profit (ignoring prop firm limits):", f"{criterion}%")
    else:
        st.warning("Strategy is unprofitable")

def day_time_heatmap(df: pd.DataFrame) -> None:
    """
    Draws a heatmap showing profit dependence on time (session) and day of the week
    
    Args:
        df: pd.DataFrame - dataframe filtered by asset class, month, year, and account
    
    Returns:
        None - the function draws the chart and returns nothing
    """

    grouped_df = df.groupby(["trade_day", "trade_session"])["profit"].sum().reset_index()
    st.divider()
    st.subheader("Heatmap: Profit dependence on Session and Day of the week")

    fig = px.density_heatmap(
        grouped_df, 
        x="trade_day",
        y="trade_session",
        z="profit",
        text_auto=".0f",
        labels={"trade_day": "Day", "trade_session": "Session"},
        color_continuous_scale=["#EF553B", "#1E1E1E", "#00CC96"],
        color_continuous_midpoint=0,
    )
    fig.update_traces(xgap=3, ygap=3)
    st.plotly_chart(fig, use_container_width=True)
