'''
Список проблем грязных данных, которые надо решить:
1. Начиная c June имеются только папки вида "RWA-<account_size>", тк я не торговал уже криптой
2. В июне на счете в 10к была 1 сделка по битку. Но это находится в папке RWA-10k
3. В мае почти все трейды c пустыми profit и pnl, искусственно, но аналитически исправить этот недочет. 
    Известно, что там, где profit и pnl пустые, был куплен еще счет на 10к и на 25к, поэтому суммарный profit и pnl будут считаться от 40к
'''

from pathlib import Path
import pandas as pd


accounts_summ_size = 40_000  # Сумма купленных счетов (5к + 10к + 25к)
accounts_ids = {5000.0: 1, 10000.0: 2, 15000.0: 3, 25000.0: 4, 40000.0: 5}  # Словарь с ID аккаунтов для заполнения колонки account_id

def load_and_prepare_data(data_path: str) -> pd.DataFrame:
    """
        Функция подготовки и загрузки вводных данных
    """

    all_dataframes = []

    for file_path in Path(data_path).rglob("*.csv"):
        df = pd.read_csv(file_path)
        df = df.drop(labels=["Day"], axis=1)  # Во избежание ситуации с отсутствием данных по дням, я удаляю эту колонку, тк ее легко восстановить из даты
        df = df.dropna(subset=["Date", "Pair", "Position", "RR", "Risk"])
        df["asset_type"] = file_path.parts[2]
        all_dataframes.append(df)

    all_dataframes = pd.concat(all_dataframes, ignore_index=True)
    all_dataframes["Date"] = pd.to_datetime(all_dataframes["Date"])
    all_dataframes["Day"] = all_dataframes["Date"].dt.day_name()  # Восстанавливаем данные по дням
    all_dataframes["Risk"] = all_dataframes["Risk"].str.replace("%", "").astype(float)  # Приводим колонку "Risk" к числовому формату
    all_dataframes["RR"] = all_dataframes["RR"].str.lower().str.replace("1к", "").str.replace("1k", "").astype(float)  # Приводим колонку "RR" к числовому формату

    return all_dataframes

def set_account_info(df: pd.DataFrame) -> pd.DataFrame:
    """
        Функция для установки ID аккаунта и его размера (в долларах)
    """

    may_account_mask = (df["Date"].dt.month_name().str.lower() == "may") & (df["Date"].dt.year == 2026)
    april_account_mask = (df["Date"].dt.month_name().str.lower() == "april") & (df["Date"].dt.year == 2026)
    accounts_from_folders = df["asset_type"].str.extract(r"(\d+)", expand=False).astype(float)
    
    df["account_size"] = accounts_from_folders * 1000
    df.loc[may_account_mask, "account_size"] = 40000
    df.loc[april_account_mask, "account_size"] = ((df.loc[april_account_mask, "Profit"] / (df.loc[april_account_mask, "PNL"] / 100)) / 1000).round(0) * 1000

    df["account_size"] = df["account_size"].fillna(5000)

    df["account_id"] = df["account_size"].map(accounts_ids)

    return df


def recover_profit(df: pd.DataFrame) -> pd.DataFrame:
    """
        Функция для восстановления отсутствующих колонок 'Profit' и 'PNL'
    """

    mask_win = df["PNL"].isna() & (df["Win?"] == "Yes")
    mask_lose = df["PNL"].isna() & (df["Win?"] == "No")

    df.loc[mask_win, "PNL"] = df.loc[mask_win, "Risk"] * df.loc[mask_win, "RR"]
    df.loc[mask_lose, "PNL"] = -df.loc[mask_lose, "Risk"]
    df.loc[df["Profit"].isna(), "Profit"] = accounts_summ_size * (df.loc[df["Profit"].isna(), "PNL"] / 100)

    return df

def clean_folder_name(df: pd.DataFrame) -> pd.DataFrame:
    """
        Функция для решения проблемы c измененным названием папок (начиная c июня папки называются в виде: RWA-<account_size>)
    """
    
    mask_rwa = df["asset_type"].str.contains("RWA")
    mask_crypto = ~df["asset_type"].str.contains("RWA")

    df.loc[mask_rwa, "asset_type"] = "RWA"
    df.loc[mask_crypto, "asset_type"] = "Crypto"

    return df

def filter_crypto(df: pd.DataFrame) -> pd.DataFrame:
    """
        Функция для фильтрации сделок Crypto и RWA (в папке вида "RWA-<account_size>" есть как минимум 1 сделка по Crypto)
    """

    mask_crypto = df["Pair"].str.endswith("USDT")

    df.loc[mask_crypto, "asset_type"] = "Crypto"

    return df


def run_pipeline() -> pd.DataFrame:
    df = load_and_prepare_data(data_path="data")
    df = recover_profit(df=df)
    df = set_account_info(df=df)
    df = clean_folder_name(df=df)
    df = filter_crypto(df=df)

    df = df.drop(labels=["Trade"], axis=1)
    df = df.rename(columns={
        "Date": "trade_date",
        "Day": "trade_day",
        "Session": "trade_session",
        "Pair": "pair",
        "Pattern": "pattern",
        "Setup": "setup",
        "Trend type": "trend_type",
        "Position": "trade_position",
        "Risk": "risk",
        "RR": "rr",
        "Profit": "profit",
        "PNL": "pnl",
        "Win?": "win"
    })
    df["win"] = df["win"].replace({"Yes": True, "No": False})

    return df
