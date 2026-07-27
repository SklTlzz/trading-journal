from cleaning import run_pipeline
from db_manager import DatabaseManager
import os
import pandas as pd
from dotenv import load_dotenv

load_dotenv()


def main():
    clean_df = run_pipeline()

    trades = clean_df.copy()
    trades = trades.drop(labels=["account_size"], axis=1)

    accounts = clean_df[["account_id", "account_size"]].drop_duplicates()

    db = DatabaseManager(
        user="postgres",
        password=os.getenv("DB_PASSWORD"),
        host="localhost",
        port="5432",
        dbname="trading_journal"
    )

    db.insert_dataframe(df=accounts, table_name="accounts")
    db.insert_dataframe(df=trades, table_name="trades")


if __name__ == "__main__":
    main()
