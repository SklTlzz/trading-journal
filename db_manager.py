from sqlalchemy import create_engine
import pandas as pd


class DatabaseManager:
    def __init__(self, user, password, host, port, dbname):
        db_url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
        self.engine = create_engine(db_url)

    def insert_dataframe(self, df: pd.DataFrame, table_name: str):
        """
            Метод для загрузки датафрейма в таблицу
        """

        df.to_sql(name=table_name, con=self.engine, if_exists="append", index=False)
        print(f"Table {table_name} succesfully updated!")
