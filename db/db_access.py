#!/usr/bin/env python12.9

"""Provides interface functions to access db"""

from misc.data_types import TimeFrame, SymbolStatus

import db.db_const as db_const
import db.db_sql   as db_sql

from collections.abc    import Callable
from datetime           import datetime
from psycopg            import sql
from questdb.ingress    import Sender, IngressError
from typing             import Any
import functools
import logging
import pandas as pd
import psycopg as pg
import sqlite3
import time

# Config string http
_QUESTDB_CONF_HTTP = "http::addr=localhost:9000;username=admin;password={0};".format(db_const.QUESTDB_PASSWORD)
# Time to wait after connection error to host occurred
_WAIT_TIME_IN_SECS_AFTER_DB_ERROR = 10
# Maximum number of retries after db connection error occurred
_MAX_RETRIES_AFTER_DB_CONNECT_ERROR = 3


def _catch_questdb_ingress_error(func: Callable) -> Callable:
    """Decorator to catch error during db interaction"""
    @functools.wraps(func)
    def wrapper_catch_insert_in_questdb_error(*args, **kwargs) -> Any:
        """Wrapper function"""
        num_retries = 0
        error = None
        while num_retries < _MAX_RETRIES_AFTER_DB_CONNECT_ERROR:
            # Retries calling function when certain errors caught
            try:
                return_value = func(*args, **kwargs)
                break
            except IngressError as e:
                error = e
                logging.error("IngressError occurred")
                num_retries += 1
                time.sleep(_WAIT_TIME_IN_SECS_AFTER_DB_ERROR)
        else:
            logging.error("Max number of retries of calling function {0} exceeded".format(func))
            logging.error(type(error).__name__, exc_info=True)
            exit(1)
        return return_value
    return wrapper_catch_insert_in_questdb_error

def get_id_from_symbol_meta(symbol_code: str, exchange_code: str, time_frame: TimeFrame, symbol_status: SymbolStatus,
                            symbol_name: str) -> int | None:
    """Returns symbol ID for passed arguments from table symbol_meta in SQLite DB"""
    # Connects to SQLite DB
    connection = sqlite3.connect(db_const.SQLITE_DB_PATH)
    # Queries data
    df_symbol_meta = pd.read_sql(db_sql.SQL_SELECT_ALL_FROM_SYMBOL_META_BY_VALUES, con=connection,
                                 params={"symbol_code":symbol_code, "exchange_code":exchange_code,
                                         "time_frame":time_frame.name, "symbol_status":symbol_status.name,
                                         "name":symbol_name})
    connection.close()
    # Checks if symbol exist in DB
    symbol_id = None
    if df_symbol_meta.shape[0] > 0 and df_symbol_meta.at[0, "symbol_code"] == symbol_code:
        symbol_id = df_symbol_meta.at[0, "id"]
    return symbol_id

def is_already_in_symbol_meta(symbol_code: str, exchange_code: str, time_frame: TimeFrame, symbol_status: SymbolStatus,
                              symbol_name: str) -> bool:
    """Checks if symbol has been already in SQLite DB"""
    # Checks if symbol exist in DB
    if get_id_from_symbol_meta(symbol_code, exchange_code, time_frame, symbol_status, symbol_name):
        symbol_already_in_db = True
    else:
        symbol_already_in_db = False

    return symbol_already_in_db

@_catch_questdb_ingress_error
def insert_ohlcv_data(df: pd.DataFrame, symbol_code: str, exchange_code: str, time_frame: TimeFrame,
                      symbol_status: SymbolStatus):
    """Insert price data into QuestDB"""
    if time_frame == TimeFrame.DAILY:
        table_name = db_const.TABLE_NAME_DAILY_PRICE
        pd_time_column_name = "datetime"
    else:
        table_name = db_const.TABLE_NAME_MINUTE_PRICE
        pd_time_column_name = "timestamp"

    with Sender.from_conf(_QUESTDB_CONF_HTTP) as sender:
        logging.info("""Inserts {0} price records for symbol {1} ({2}, {3}, {4}) into table {5}""".format(
                     df.shape[0], symbol_code, exchange_code, time_frame.name, symbol_status.name, table_name))
        sender.dataframe(df, table_name=table_name, at=pd_time_column_name)
    print("yrsh")

def select_ohlcv(symbol_codes_per_exchange: dict[str, list[str]], time_frame: TimeFrame,
                 start_datetime: datetime = datetime.min, end_datetime: datetime = datetime.max) -> pd.DataFrame:
    """Selects price data for specific symbols of exchanges, time period and time frame from QuestDB"""
    if time_frame == TimeFrame.DAILY:
        query_string = db_sql.SQL_SELECT_ALL_FROM_DAILY_OHLCV
        column_names = db_const.COLUMNS_DAILY_PRICE
    else:
        query_string = db_sql.SQL_SELECT_ALL_FROM_MINUTE_OHLCV
        column_names = db_const.COLUMNS_MINUTE_PRICE

    df_ohlcv: pd.DataFrame = pd.DataFrame()
    with pg.connect(db_const.QUESTDB_CONF_PSYCOPG, cursor_factory=pg.ClientCursor, autocommit=True) as connection:
        df_list: list[pd.DataFrame] = []
        for exchange_code in symbol_codes_per_exchange:
            with connection.cursor() as cur:
                symbol_codes = symbol_codes_per_exchange[exchange_code]
                query = sql.SQL(query_string).format(symbol_codes=sql.SQL(', ').join(map(sql.Literal, symbol_codes)))
                params: list[Any] = [exchange_code]
                params.extend([start_datetime, end_datetime])
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
                cur.close()
                df_list.append(pd.DataFrame(rows, columns=column_names))
        df_ohlcv = pd.concat(df_list)
        df_ohlcv.set_index([db_const.COLUMN_SYMBOL_CODE, db_const.COLUMN_TIMESTAMP], inplace=True)

    return df_ohlcv

def select_ohlcv_last(symbol_codes_per_exchange: dict[str, list[str]], time_frame: TimeFrame) -> pd.DataFrame:
    if time_frame == TimeFrame.DAILY:
        query_string = db_sql.SQL_SELECT_LAST_FROM_DAILY_OHLCV
        column_names = db_const.COLUMNS_DAILY_PRICE
    else:
        query_string = db_sql.SQL_SELECT_LAST_FROM_MINUTE_OHLCV
        column_names = db_const.COLUMNS_MINUTE_PRICE

    df_ohlcv: pd.DataFrame = pd.DataFrame()
    with pg.connect(db_const.QUESTDB_CONF_PSYCOPG, cursor_factory=pg.ClientCursor, autocommit=True) as connection:
        df_list: list[pd.DataFrame] = []
        for exchange_code in symbol_codes_per_exchange:
            with connection.cursor() as cur:
                symbol_codes = symbol_codes_per_exchange[exchange_code]
                query = sql.SQL(query_string).format(symbol_codes=sql.SQL(', ').join(map(sql.Literal, symbol_codes)))
                params: list[Any] = [exchange_code]
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
                cur.close()
                df_list.append(pd.DataFrame(rows, columns=column_names))
        df_ohlcv = pd.concat(df_list)
        df_ohlcv.set_index([db_const.COLUMN_SYMBOL_CODE, db_const.COLUMN_TIMESTAMP], inplace=True, drop=False)

    return df_ohlcv

def get_last_datetime(symbol_code, exchange_code, time_frame: TimeFrame) -> datetime | None:
    df_existing_ohlcv = select_ohlcv_last({exchange_code: [symbol_code]}, time_frame)
    try:
        last_datetime = df_existing_ohlcv.iloc[0]["timestamp"].to_pydatetime()
    except IndexError:
        last_datetime = None
    return last_datetime

def insert_df_into_sqlite(df, table_name):
    """Insert dataframe into SQLite DB"""
    # Connects to SQLite DB
    connection = sqlite3.connect(db_const.SQLITE_DB_PATH)
    # Inserts data
    df.to_sql(table_name, connection, if_exists="append", index=False)
    connection.commit()
    connection.close()

def insert_symbol_meta_data(df_symbol_meta: pd.DataFrame, symbol_code: str, exchange_code: str,
                            time_frame: TimeFrame, symbol_status: SymbolStatus):
    """Insert symbol meta data into SQLite DB"""
    try:
        insert_df_into_sqlite(df_symbol_meta, db_const.TABLE_SYMBOL_META)
    except sqlite3.IntegrityError as error:
        logging.error("""Symbol code {0} ({1}, {2}, {3}) combo already exists table {4}""".format(
                         symbol_code, exchange_code, time_frame.name, symbol_status.name, db_const.TABLE_SYMBOL_META))
        raise error

if __name__ == "__main__":
    """symbol_codes = {"NASDAQ": ["AAPL"], "NYSE": ["PLTR"]}
    start_date_str = '2023-02-28 14:30:00'
    end_date_str = '2025-03-03 10:30:00'
    date_format = '%Y-%m-%d %H:%M:%S'
    start_datetime = datetime.strptime(start_date_str, date_format)
    end_datetime = datetime.strptime(end_date_str, date_format)
    time_frame = TimeFrame.MINUTE

    df = select_ohlcv_data(symbol_codes, start_datetime, end_datetime, time_frame)
    print("")"""
    pass