import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

import config as cfg


@st.cache_data
def load_data():
    """
    Loads data from the database
    """
    
    db_url = f"postgresql://{cfg.DB_USER}:{cfg.DB_PASS}@{cfg.DB_HOST}:{cfg.DB_PORT}/{cfg.DB_NAME}"
    engine = create_engine(db_url)

    query = """
        SELECT
            *
        FROM accounts

        JOIN trades USING (account_id)

        ORDER BY trade_date
    """

    df = pd.read_sql(query, engine)
    df["trade_date"] = pd.to_datetime(df["trade_date"])

    df["month_filter"] = df["trade_date"].dt.month_name()
    df["year_filter"] = df["trade_date"].dt.year

    df["trade_day"] = pd.Categorical(df["trade_day"], categories=cfg.DAYS_ORDER, ordered=True)
    df["trade_session"] = pd.Categorical(df["trade_session"], categories=cfg.SESSIONS_ORDER, ordered=True)

    return df
