import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import pandas as pd

import config as cfg


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

    st.divider()
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

def day_time_heatmap(df: pd.DataFrame) -> None:
    """
    Отрисовывает тепловую карту зависимости профита от времени (сессии) и дня недели 
    
    Args:
        df: pd.DataFrame - датафрейм, отфильтрованный по классу актива, месяцу, году и аккаунту
    
    Returns:
        None - функция отрисовывает график и ничего не возвращает
    """

    grouped_df = df.groupby(["trade_day", "trade_session"])["profit"].sum().reset_index()
    st.divider()
    st.subheader("Тепловая карта зависимости профита от времени (сессии) и дня недели")

    fig = px.density_heatmap(
        grouped_df, 
        x="trade_day",
        y="trade_session",
        z="profit",
        text_auto=".0f",
        labels={"trade_day": "День", "trade_session": "Сессия"},
        color_continuous_scale=["#EF553B", "#1E1E1E", "#00CC96"],
        color_continuous_midpoint=0,
    )
    fig.update_traces(xgap=3, ygap=3)
    st.plotly_chart(fig, use_container_width=True)
