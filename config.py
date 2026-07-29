import os
from dotenv import load_dotenv

load_dotenv()


DB_USER = "postgres"
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "trading_journal"
DB_PASS = os.getenv("DB_PASSWORD")

ALL_ACCOUNTS_SUM_SIZE = 40_000  # Сумма купленных счетов (5к + 10к + 25к)
ACCOUNTS_IDS = {5000: 1, 10000: 2, 25000: 3}  # Словарь с ID аккаунтов для заполнения колонки account_id
SPLIT_ACCOUNTS = {5000: [5000], 10000: [10000], 15000: [5000, 10000], 25000: [25000], 40000: [5000, 10000, 25000]}  # Словарь для разбиения скомбинированных счетов в реальные счета
