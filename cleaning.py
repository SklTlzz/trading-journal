from pathlib import Path
import pandas as pd

from config import ALL_ACCOUNTS_SUM_SIZE, ACCOUNTS_IDS, SPLIT_ACCOUNTS


def load_and_prepare_data(data_path: str) -> pd.DataFrame:
    """
    Подготавливает и загружает вводные данные

    Args:
        data_path: str - название папки, где лежат сырые данные
    
    Returns:
        pd.DataFrame - исходный, грязный датафрейм
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
    all_dataframes["Mistake"] = all_dataframes["Mistake"].fillna("No data")

    return all_dataframes

def set_account_info(df: pd.DataFrame) -> pd.DataFrame:
    """
    Устанавливает размер аккаунта

    Args:
        df: pd.DataFrame - исходный датафрейм
    
    Returns:
        pd.DataFrame - датафрейм c имеющейся колонкой "account_size"
    """

    may_account_mask = (df["Date"].dt.month_name().str.lower() == "may") & (df["Date"].dt.year == 2026)
    april_account_mask = (df["Date"].dt.month_name().str.lower() == "april") & (df["Date"].dt.year == 2026)
    accounts_from_folders = df["asset_type"].str.extract(r"(\d+)", expand=False).astype(float)
    
    df["account_size"] = accounts_from_folders * 1000
    df.loc[may_account_mask, "account_size"] = ALL_ACCOUNTS_SUM_SIZE
    df.loc[april_account_mask, "account_size"] = ((df.loc[april_account_mask, "Profit"] / (df.loc[april_account_mask, "PNL"] / 100)) / 1000).round(0) * 1000

    df["account_size"] = df["account_size"].fillna(5000)

    return df

def recover_profit(df: pd.DataFrame) -> pd.DataFrame:
    """
    Восстанавливает отсутствующие колонки "Profit" и "PNL"

    Args:
        df: pd.DataFrame - исходный датафрейм
    
    Returns:
        pd.DataFrame - датафрейм c восставновленными "Profit" и "PNL" 
    """

    mask_win = df["PNL"].isna() & (df["Win?"] == "Yes")
    mask_lose = df["PNL"].isna() & (df["Win?"] == "No")

    df.loc[mask_win, "PNL"] = df.loc[mask_win, "Risk"] * df.loc[mask_win, "RR"]
    df.loc[mask_lose, "PNL"] = -df.loc[mask_lose, "Risk"]
    df.loc[df["Profit"].isna(), "Profit"] = ALL_ACCOUNTS_SUM_SIZE * (df.loc[df["Profit"].isna(), "PNL"] / 100)

    return df

def clean_folder_name(df: pd.DataFrame) -> pd.DataFrame:
    """
    Обрабатывает названия папок вида "RWA-10k", оставляя в колонке класса актива только "RWA"
    
    Args:
        df: pd.DataFrame - обработанный раннее датафрейм
    
    Returns:
        pd.DataFrame - датафрейм, в котором класс активов называется как надо
    """
    
    mask_rwa = df["asset_type"].str.contains("RWA")
    mask_crypto = ~df["asset_type"].str.contains("RWA")

    df.loc[mask_rwa, "asset_type"] = "RWA"
    df.loc[mask_crypto, "asset_type"] = "Crypto"

    return df

def filter_crypto(df: pd.DataFrame) -> pd.DataFrame:
    """
    Устанавливает класс активов "Crypto"
    На 10к счете у меня доступна торговля и криптой, и RWA, на остальных счетах только RWA

    Args:
        df: pd.DataFrame - обработанный раннее датафрейм
    
    Returns:
        pd.DataFrame - датафрейм, в котором установлен класс активов и размер аккаунта для крипты
    """

    mask_crypto = df["Pair"].str.endswith("USDT")

    df.loc[mask_crypto, "asset_type"] = "Crypto"
    df.loc[mask_crypto, "account_size"] = 10000.0

    return df

def spliting_accounts(df: pd.DataFrame) -> pd.DataFrame:
    """
    Разделяет счета, которые склеились (15к и 40к), на соответствующие 5к, 10к и 25к

    Args:
        df: pd.DataFrame - обработанный раннее датафрейм
    
    Returns:
        pd.DataFrame - датафрейм, в котором склеившиеся счета, разбиты
    """

    df["account_size"] = df["account_size"].astype(int)

    df["account_size"] = df["account_size"].map(SPLIT_ACCOUNTS)
    df = df.explode("account_size")
    df["Profit"] = df["account_size"] * (df["PNL"] / 100)

    df["account_id"] = df["account_size"].map(ACCOUNTS_IDS)

    change_mask = (df["account_id"] == 3) & (df["Date"] == "2026-05-11")  # В данных есть 1 кривая сделка, где на счетах в 5к и 10к был тейк, а на счете в 25к - стоп
    df.loc[change_mask, "Profit"] = -250
    df.loc[change_mask, "PNL"] = -1

    return df


def run_pipeline() -> pd.DataFrame:
    """
    Запускает очистку данных
    """

    df = load_and_prepare_data(data_path="data")
    df = recover_profit(df=df)
    df = set_account_info(df=df)
    df = clean_folder_name(df=df)
    df = filter_crypto(df=df)
    df = spliting_accounts(df=df)

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
        "Win?": "win",
        "Mistake": "mistake"
    })
    df["win"] = df["win"].replace({"Yes": True, "No": False})
    mask_for_nan = df.isna().any(axis=1)

    if not df[mask_for_nan].empty:  # Если вдруг где-либо отсутствуют данные, мы останавливаем выполнение скрипта во избежание потери данных и разбираемся c проблемой
        print(df[mask_for_nan])
        raise ValueError(f"Есть данные c NaN, исправить")

    return df
