from sqlalchemy import create_engine
import pandas as pd


class DatabaseManager:
    def __init__(self, user, password, host, port, dbname):
        db_url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
        self.engine = create_engine(db_url)

    def insert_dataframe(self, df: pd.DataFrame, table_name: str):
        """
        Loads a dataframe into a table

        Args:
            df: pd.DataFrame - pre-cleaned dataframe
            table_name: str - name of the target table
        
        Returns:
            None - the method only writes data to the DB
        """

        df.to_sql(name=table_name, con=self.engine, if_exists="append", index=False)
