#!/usr/bin/env python12.9

"""Global db related constants"""

from misc.constants import WORKING_DIR

# SQLite DB path
SQLITE_DB_PATH = WORKING_DIR + "/db/sqlite.db"

# QuestDB password
QUESTDB_PASSWORD = "quest"
# Config string PostgreSQL
QUESTDB_CONF_PSYCOPG = "user=admin password={0} host=127.0.0.1 port=8812 dbname=qdb".format(QUESTDB_PASSWORD)

# Dummy symbol and exchange for test purposes
DUMMY_SYMBOL_CODE   = "DUMMY_SYMBOL"
DUMMY_EXCHANGE_CODE = "DUMMY_EXCHANGE"

# --------- SQLite constants ---------

# EOD meta data table name
DB_TABLE_NAME_SYMBOL_META = "symbol_meta"

# --------- QuestDB constants --------

# Table names
DB_TABLE_NAME_DAILY_PRICE = "daily_ohlcv"
DB_TABLE_NAME_MINUTE_PRICE = "minute_ohlcv"

# Column names of table
DB_COLUMNS_DAILY_PRICE = ["timestamp", "exchange_code", "symbol_code", "open", "high", "low", "close", "adjusted_close",
                          "volume"]
DB_COLUMNS_MINUTE_PRICE = ["timestamp", "exchange_code", "symbol_code", "gmt_offset", "open", "high", "low", "close",
                           "volume"]
# Specific column names
DB_COLUMN_TIMESTAMP = "timestamp"
DB_COLUMN_SYMBOL_CODE = "symbol_code"

# ------------------------------------

