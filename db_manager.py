from sqlalchemy import create_engine
import pandas as pd


class DatabaseManager:
    def __init__(self, user, password, host, port, dbname):
        db_url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
        self.engine = create_engine(db_url)

    def insert_dataframe(self, df: pd.DataFrame, table_name: str):
        """
        Загружает датафрейм в таблицу

        Args:
            df: pd.DataFrame - предварительно очищенный датафрейм
            table_name: str - название таблицы, в которую загружать данные
        
        Returns:
            None - метод только записывает данные в БД
        """

        df.to_sql(name=table_name, con=self.engine, if_exists="append", index=False)
