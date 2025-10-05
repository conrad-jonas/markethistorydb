#!/usr/bin/env python12.9

"""Provides interface functions to access db"""

from misc.data_types import (TimeFrame,
                             SymbolStatus)
from db.db_constants import (QUESTDB_PASSWORD,
                             QUESTDB_CONF_PSYCOPG,
                             SQLITE_DB_PATH,
                             DB_TABLE_NAME_SYMBOL_META,
                             DB_TABLE_NAME_DAILY_PRICE,
                             DB_TABLE_NAME_MINUTE_PRICE,
                             DB_COLUMNS_DAILY_PRICE,
                             DB_COLUMNS_MINUTE_PRICE,
                             DB_COLUMN_TIMESTAMP,
                             DB_COLUMN_SYMBOL_CODE)
import db.db_sql as db_sql

import functools
import logging
import pandas as pd
import psycopg as pg
import sqlite3
import time

from collections.abc    import Callable
from datetime           import datetime
from psycopg            import sql
from questdb.ingress    import Sender, IngressError
from typing             import Any

# Config string http
QUESTDB_CONF_HTTP = "http::addr=localhost:9000;username=admin;password={0};".format(QUESTDB_PASSWORD)
# Time to wait after connection error to host occurred
WAIT_TIME_IN_SECS_AFTER_DB_ERROR = 10
# Maximum number of retries after db connection error occurred
MAX_RETRIES_AFTER_DB_CONNECT_ERROR = 3

def _catch_insert_in_questdb_error(func: Callable) -> Callable:
    """Decorator to catch error during db interaction"""
    @functools.wraps(func)
    def wrapper_catch_insert_in_questdb_error(*args, **kwargs) -> Any:
        """Wrapper function"""
        num_retries = 0
        return_value = None
        error = None
        while num_retries < MAX_RETRIES_AFTER_DB_CONNECT_ERROR:
            # Retries calling function when certain errors caught
            try:
                return_value = func(*args, **kwargs)
                break
            except IngressError as error:
                logging.error("IngressError occurred")
                num_retries += 1
                time.sleep(WAIT_TIME_IN_SECS_AFTER_DB_ERROR)
        else:
            logging.error("Max number of retries of calling function {0} exceeded".format(func))
            logging.error(type(error).__name__, exc_info=True)
            exit(1)
        return return_value
    return wrapper_catch_insert_in_questdb_error

def is_symbol_already_in_db(symbol_code: str, exchange_code: str, time_frame: TimeFrame, symbol_status: SymbolStatus,
                            symbol_name: str) -> bool:
    """Checks if symbol has been already in SQLite DB"""
    # Connects to SQLite DB
    connection = sqlite3.connect(SQLITE_DB_PATH)
    # Queries data
    df_symbol_meta = pd.read_sql(db_sql.SQL_CODE_SELECT_SYMBOL_FROM_SYMBOL_META, con=connection,
                                 params={"symbol_code":symbol_code, "exchange_code":exchange_code,
                                         "time_frame":time_frame.name, "symbol_status":symbol_status.name,
                                         "name":symbol_name})
    connection.close()
    # Checks if symbol exist in DB
    if df_symbol_meta.shape[0] > 0 and df_symbol_meta.at[0, "symbol_code"] == symbol_code:
        symbol_already_in_db = True
    else:
        symbol_already_in_db = False

    return symbol_already_in_db

@_catch_insert_in_questdb_error
def insert_ohlcv_data(df_eod: pd.DataFrame, symbol_code: str, exchange_code: str, time_frame: TimeFrame,
                      symbol_status: SymbolStatus):
    """Insert price data into QuestDB"""
    if time_frame == TimeFrame.DAILY:
        table_name = DB_TABLE_NAME_DAILY_PRICE
        pd_time_column_name = "datetime"
    else:
        table_name = DB_TABLE_NAME_MINUTE_PRICE
        pd_time_column_name = "timestamp"

    with Sender.from_conf(QUESTDB_CONF_HTTP) as sender:
        logging.info("""Inserts {0} price records for symbol {1} ({2}, {3}, {4}) into table {5}""".format(
                     df_eod.shape[0], symbol_code, exchange_code, time_frame.name, symbol_status.name, table_name))
        sender.dataframe(df_eod, table_name=table_name, at=pd_time_column_name)

def select_ohlcv_data(symbol_codes_per_exchange: dict[str, list[str]], start_datetime: datetime, end_datetime: datetime,
                      time_frame: TimeFrame) -> pd.DataFrame:
    """Selects price data for specific symbols of exchanges, time period and time frame from QuestDB"""
    if time_frame == TimeFrame.DAILY:
        query_string = db_sql.SQL_SELECT_ALL_FROM_DAILY_OHLCV
        column_names = DB_COLUMNS_DAILY_PRICE
    else:
        query_string = db_sql.SQL_SELECT_ALL_FROM_MINUTE_OHLCV
        column_names = DB_COLUMNS_MINUTE_PRICE

    df_ohlcv: pd.DataFrame = pd.DataFrame()
    with pg.connect(QUESTDB_CONF_PSYCOPG, cursor_factory=pg.ClientCursor, autocommit=True) as connection:
        df_list: list[pd.DataFrame] = []
        for exchange_code in symbol_codes_per_exchange:
            # Open a cursor to perform database operations
            with connection.cursor() as cur:
                symbol_codes = symbol_codes_per_exchange[exchange_code]
                query = sql.SQL(query_string).format(sql.SQL(', ').join(sql.Placeholder() * len(symbol_codes)))
                params: list[Any] = [exchange_code]
                params.extend(symbol_codes)
                params.extend([start_datetime, end_datetime])
                print(query.as_string())
                print(cur.mogrify(query, tuple(params)))
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
                cur.close()
                df_list.append(pd.DataFrame(rows, columns=column_names))
        df_ohlcv = pd.concat(df_list)
        df_ohlcv.set_index([DB_COLUMN_SYMBOL_CODE, DB_COLUMN_TIMESTAMP], inplace=True)


    return df_ohlcv

def insert_symbol_meta_data(series_exchange_symbol: pd.Series, symbol_code: str, exchange_code: str,
                            time_frame: TimeFrame, symbol_status: SymbolStatus):
    """Insert price data into SQLite DB"""
    try:
        # Connects to SQLite DB
        connection = sqlite3.connect(SQLITE_DB_PATH)
        # Inserts data
        df_exchange_symbol = series_exchange_symbol.to_frame().T
        df_exchange_symbol.to_sql("symbol_meta", connection, if_exists="append", index=False)
        connection.commit()
        connection.close()
    except sqlite3.IntegrityError as error:
        logging.error("""Symbol code {0} ({1}, {2}, {3}) combo already exists table {4}""".format(
                         symbol_code, exchange_code, time_frame.name, symbol_status.name, DB_TABLE_NAME_SYMBOL_META))
        raise error

if __name__ == "__main__":
    symbol_codes = {"NASDAQ": ["AAPL"], "NYSE": ["PLTR"]}
    start_date_str = '2023-02-28 14:30:00'
    end_date_str = '2025-03-03 10:30:00'
    date_format = '%Y-%m-%d %H:%M:%S'
    start_datetime = datetime.strptime(start_date_str, date_format)
    end_datetime = datetime.strptime(end_date_str, date_format)
    time_frame = TimeFrame.MINUTE

    df = select_ohlcv_data(symbol_codes, start_datetime, end_datetime, time_frame)
    print("")