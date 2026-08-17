from pathlib import Path
import pandas as pd

from config import ALL_ACCOUNTS_SUM_SIZE, ACCOUNTS_IDS, SPLIT_ACCOUNTS


def load_and_prepare_data(data_path: str) -> pd.DataFrame:
    """
    Prepares and loads the initial data

    Args:
        data_path: str - name of the folder where the raw data is located
    
    Returns:
        pd.DataFrame - initial raw dataframe
    """

    all_dataframes = []

    for file_path in Path(data_path).rglob("*.csv"):
        df = pd.read_csv(file_path)
        df = df.drop(labels=["Day"], axis=1)  # To avoid issues with missing data by day, I drop this column since it can be easily recovered from the date
        df = df.dropna(subset=["Date", "Pair", "Position", "RR", "Risk"])
        df["asset_type"] = file_path.parts[2]
        all_dataframes.append(df)

    all_dataframes = pd.concat(all_dataframes, ignore_index=True)
    all_dataframes["Date"] = pd.to_datetime(all_dataframes["Date"])
    all_dataframes["Day"] = all_dataframes["Date"].dt.day_name()  # Recovering day data
    all_dataframes["Risk"] = all_dataframes["Risk"].str.replace("%", "").astype(float)  # Converting "Risk" column to numeric format
    all_dataframes["RR"] = all_dataframes["RR"].str.lower().str.replace("1к", "").str.replace("1k", "").astype(float)  # Converting "RR" column to numeric format
    all_dataframes["Mistake"] = all_dataframes["Mistake"].fillna("No data")

    return all_dataframes

def set_account_info(df: pd.DataFrame) -> pd.DataFrame:
    """
    Sets the account size

    Args:
        df: pd.DataFrame - initial dataframe
    
    Returns:
        pd.DataFrame - dataframe with the new "account_size" column
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
    Recovers missing "Profit" and "PNL" columns

    Args:
        df: pd.DataFrame - initial dataframe
    
    Returns:
        pd.DataFrame - dataframe with recovered "Profit" and "PNL" 
    """

    mask_win = df["PNL"].isna() & (df["Win?"] == "Yes")
    mask_lose = df["PNL"].isna() & (df["Win?"] == "No")

    df.loc[mask_win, "PNL"] = df.loc[mask_win, "Risk"] * df.loc[mask_win, "RR"]
    df.loc[mask_lose, "PNL"] = -df.loc[mask_lose, "Risk"]
    df.loc[df["Profit"].isna(), "Profit"] = ALL_ACCOUNTS_SUM_SIZE * (df.loc[df["Profit"].isna(), "PNL"] / 100)

    return df

def clean_folder_name(df: pd.DataFrame) -> pd.DataFrame:
    """
    Processes folder names like "RWA-10k", keeping only "RWA" in the asset class column
    
    Args:
        df: pd.DataFrame - previously processed dataframe
    
    Returns:
        pd.DataFrame - dataframe with properly formatted asset class names
    """
    
    mask_rwa = df["asset_type"].str.contains("RWA")
    mask_crypto = ~df["asset_type"].str.contains("RWA")

    df.loc[mask_rwa, "asset_type"] = "RWA"
    df.loc[mask_crypto, "asset_type"] = "Crypto"

    return df

def filter_crypto(df: pd.DataFrame) -> pd.DataFrame:
    """
    Sets the "Crypto" asset class.
    On the 10k account, both Crypto and RWA trading are available; other accounts are strictly RWA.

    Args:
        df: pd.DataFrame - previously processed dataframe
    
    Returns:
        pd.DataFrame - dataframe with asset class and account size assigned for crypto trades
    """

    mask_crypto = df["Pair"].str.endswith("USDT")

    df.loc[mask_crypto, "asset_type"] = "Crypto"
    df.loc[mask_crypto, "account_size"] = 10000.0

    return df

def spliting_accounts(df: pd.DataFrame) -> pd.DataFrame:
    """
    Splits combined accounts (15k and 40k) into their respective 5k, 10k, and 25k components

    Args:
        df: pd.DataFrame - previously processed dataframe
    
    Returns:
        pd.DataFrame - dataframe with combined accounts split properly
    """

    df["account_size"] = df["account_size"].astype(int)

    df["account_size"] = df["account_size"].map(SPLIT_ACCOUNTS)
    df = df.explode("account_size")
    df["Profit"] = df["account_size"] * (df["PNL"] / 100)

    df["account_id"] = df["account_size"].map(ACCOUNTS_IDS)

    change_mask = (df["account_id"] == 3) & (df["Date"] == "2026-05-11")  # There is 1 edge case where a trade hit TP on 5k/10k accounts but hit SL on the 25k account
    df.loc[change_mask, "Profit"] = -250
    df.loc[change_mask, "PNL"] = -1

    return df


def run_pipeline() -> pd.DataFrame:
    """
    Runs the data cleaning pipeline
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

    if not df[mask_for_nan].empty:  # If any data is missing, we stop script execution to prevent data loss and investigate the issue
        print(df[mask_for_nan])
        raise ValueError(f"There are NaN values, please fix")

    return df
