import os
from dotenv import load_dotenv

load_dotenv()


DB_USER = os.getenv("DB_USER")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_PASS = os.getenv("DB_PASSWORD")

ALL_ACCOUNTS_SUM_SIZE = 40_000  # Сумма купленных счетов (5к + 10к + 25к)
ACCOUNTS_IDS = {5000: 1, 10000: 2, 25000: 3}  # Словарь с ID аккаунтов для заполнения колонки account_id
SPLIT_ACCOUNTS = {5000: [5000], 10000: [10000], 15000: [5000, 10000], 25000: [25000], 40000: [5000, 10000, 25000]}  # Словарь для разбиения скомбинированных счетов в реальные счета
DAYS_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
SESSIONS_ORDER = ["Asia", "Frankfurt", "London", "New York"]
PROFIT_PNL_SYMBS = {"Profit": "$", "PNL": "%"}
COUNTER_TREND = {"Long": "Down", "Short": "Up"}
TARGET_1PHASE_PRC = 5
TARGET_2PHASE_PRC = 8
PROFITABLE_DAYS_1PHASE = 3
PROFITABLE_DAYS_2PHASE = 5
PROFITABLE_DAYS_FUNDED = 5
TOTAL_DRAWDOWN = -10
