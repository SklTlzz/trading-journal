from cleaning import run_pipeline
from db_manager import DatabaseManager
from config import DB_USER, DB_HOST, DB_PORT, DB_NAME, DB_PASS


def main():
    clean_df = run_pipeline()

    trades = clean_df.copy()
    trades = trades.drop(labels=["account_size"], axis=1)

    accounts = clean_df[["account_id", "account_size"]].drop_duplicates()

    db = DatabaseManager(
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME
    )

    db.insert_dataframe(df=accounts, table_name="accounts")
    db.insert_dataframe(df=trades, table_name="trades")


if __name__ == "__main__":
    main()
