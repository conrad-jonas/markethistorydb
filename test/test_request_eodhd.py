#!/usr/bin/env python12.9

"""Unit tests for request_eodhd.py"""

from db.db_const     import (QUESTDB_CONF_PSYCOPG,
                             SQLITE_DB_PATH,
                             DUMMY_SYMBOL_CODE,
                             DUMMY_EXCHANGE_CODE_A as DUMMY_EXCHANGE_CODE)
from request_data    import request_eodhd
from db              import db_access
from db              import db_sql

import os
import pandas  as pd
import pytest
import psycopg as pg
import requests
import sqlite3
import time

from collections.abc    import Callable
from datetime           import datetime
from os.path            import dirname, abspath

# Redefines constants used in test object to decrease testing time duration:
# Time to wait after connection error to host occurred
request_eodhd.WAIT_TIME_IN_SECS_AFTER_REQUEST_ERROR = 2
# Time to wait after API used up error
request_eodhd.WAIT_TIME_IN_SECS_AFTER_API_ERROR = 2

@pytest.fixture()
def setup_test():
    """Sets up test environment"""
    os.chdir(dirname(dirname(abspath(__file__))))
    yield

@pytest.fixture()
def setup_and_cleanup_sqlite():
    """Inserts dummy data into SQLite DB"""
    # Connect / Create SQLite DB
    connection = sqlite3.connect(SQLITE_DB_PATH)
    cursor = connection.cursor()

    # Inserts dummy data
    delete_params = {"symbol_code": DUMMY_SYMBOL_CODE}
    cursor.execute(db_sql.SQL_DELETE_SYMBOL_FROM_SYMBOL_META, delete_params)
    insert_params = {"symbol_code": DUMMY_SYMBOL_CODE, "exchange_code": DUMMY_EXCHANGE_CODE, "name": "test_name"}
    cursor.execute(db_sql.SQL_INSERT_DUMMY_SYMBOL_INTO_SYMBOL_META, insert_params)
    connection.commit()

    # Runs test
    yield

    # Cleans up
    cursor.execute(db_sql.SQL_DELETE_SYMBOL_FROM_SYMBOL_META, delete_params)
    connection.commit()
    connection.close()

@pytest.mark.api
@pytest.mark.parametrize("time_frame", [request_eodhd.TimeFrame.DAILY, request_eodhd.TimeFrame.MINUTE])
def test_request_exchanges_data_from_eodhd(setup_test: Callable, time_frame: request_eodhd.TimeFrame):
    url_exchanges = "https://eodhd.com/api/exchanges-list/?api_token={0}&fmt=json".format(request_eodhd.API_TOKEN)
    response_exchanges = requests.get(url_exchanges)
    if response_exchanges.status_code in [401, 402, 403]:
        with pytest.raises(SystemExit) as pytest_wrapped_error:
            request_eodhd.request_exchanges_data_from_eodhd(time_frame)
        assert pytest_wrapped_error.type == SystemExit
        assert pytest_wrapped_error.value.code == 1

    else:
        df = request_eodhd.request_exchanges_data_from_eodhd(time_frame)
        assert (df.shape[0] > 0)

@pytest.mark.api
@pytest.mark.parametrize("time_frame, symbol_status",
                         [(request_eodhd.TimeFrame.DAILY, request_eodhd.SymbolStatus.ACTIVE),
                          (request_eodhd.TimeFrame.DAILY, request_eodhd.SymbolStatus.DELISTED),
                          (request_eodhd.TimeFrame.MINUTE, request_eodhd.SymbolStatus.ACTIVE),
                          (request_eodhd.TimeFrame.MINUTE, request_eodhd.SymbolStatus.DELISTED)])
def test_request_exchange_symbols_from_eodhd(setup_test: Callable, time_frame: request_eodhd.TimeFrame,
                                             symbol_status: request_eodhd.SymbolStatus):
    exchange_code = "US"
    if symbol_status == request_eodhd.SymbolStatus.ACTIVE:
        url_exchange_symbols = ("https://eodhd.com/api/exchange-symbol-list/{0}?api_token={1}&fmt=json"
                                .format(exchange_code, request_eodhd.API_TOKEN))
    else:
        url_exchange_symbols = ("https://eodhd.com/api/exchange-symbol-list/{0}?delisted=1&api_token={1}&fmt=json"
                                .format(exchange_code, request_eodhd.API_TOKEN))

    response_exchange_symbols = requests.get(url_exchange_symbols)
    if response_exchange_symbols.status_code in [401, 402, 403]:
        with pytest.raises(SystemExit) as pytest_wrapped_error:
            request_eodhd.request_exchange_symbols_from_eodhd(exchange_code, time_frame, symbol_status)
        assert pytest_wrapped_error.type == SystemExit
        assert pytest_wrapped_error.value.code == 1
    else:
        df = request_eodhd.request_exchange_symbols_from_eodhd(exchange_code, time_frame, symbol_status)
        assert (df.shape[0] > 0)

@pytest.mark.api
@pytest.mark.parametrize("time_frame", [request_eodhd.TimeFrame.DAILY, request_eodhd.TimeFrame.MINUTE])
def test_request_price_data_from_eodhd(setup_test: Callable, time_frame: request_eodhd.TimeFrame):
    symbol = "AAPL"
    exchange_code = "US"
    exchange_name = "NASDAQ"

    if time_frame == request_eodhd.TimeFrame.DAILY:
        url_symbol = "https://eodhd.com/api/eod/{0}.{1}?api_token={2}&fmt=json".format(
            symbol, exchange_code, request_eodhd.API_TOKEN)
    else:
        url_symbol = "https://eodhd.com/api/intraday/{0}.{1}?interval=1m&api_token={2}&fmt=json".format(
            symbol, exchange_code, request_eodhd.API_TOKEN)

    response_symbol = requests.get(url_symbol)
    if response_symbol.status_code in [401, 402, 403]:
        with pytest.raises(SystemExit) as pytest_wrapped_error:
            request_eodhd.request_price_data_from_eodhd(symbol, exchange_code, exchange_name, time_frame)
        assert pytest_wrapped_error.type == SystemExit
        assert pytest_wrapped_error.value.code == 1
    else:
        df = request_eodhd.request_price_data_from_eodhd(symbol, exchange_code, exchange_name, time_frame)
        assert (df.shape[0] > 0)

@pytest.mark.db
def test_is_symbol_already_in_db_true(setup_test: Callable, setup_and_cleanup_sqlite: Callable):
    time_frame = request_eodhd.TimeFrame.DAILY
    symbol_status = request_eodhd.SymbolStatus.ACTIVE

    is_symbol_already_in_db = db_access.is_already_in_symbol_meta(DUMMY_SYMBOL_CODE, DUMMY_EXCHANGE_CODE, time_frame,
                                                                  symbol_status, "test_name")
    assert is_symbol_already_in_db == True

@pytest.mark.db
def test_is_symbol_already_in_db_false(setup_test: Callable, setup_and_cleanup_sqlite: Callable):
    symbol_code = "test_code_XYZ"
    time_frame = request_eodhd.TimeFrame.DAILY
    symbol_status = request_eodhd.SymbolStatus.ACTIVE

    assert "test_code_XYZ" != DUMMY_SYMBOL_CODE

    is_symbol_already_in_db = db_access.is_already_in_symbol_meta(symbol_code, DUMMY_EXCHANGE_CODE, time_frame,
                                                                  symbol_status, "test_name")
    assert is_symbol_already_in_db == False

@pytest.mark.db
@pytest.mark.parametrize("time_frame", [request_eodhd.TimeFrame.DAILY, request_eodhd.TimeFrame.MINUTE])
def test_insert_price_data(setup_test: Callable, time_frame: request_eodhd.TimeFrame):
    symbol_status = request_eodhd.SymbolStatus.ACTIVE
    if time_frame == request_eodhd.TimeFrame.DAILY:
        timestamp = datetime.now()
    else:
        timestamp = pd.Timestamp(datetime.now())

    if time_frame == request_eodhd.TimeFrame.DAILY:
        data = {'datetime': [timestamp],
               'exchange_code': [DUMMY_EXCHANGE_CODE],
               'symbol_code': [DUMMY_SYMBOL_CODE],
               'open': [1.0],
               'high': [1.0],
               'low': [1.0],
               'close': [1.0],
               'adjusted_close': [1.0],
               'volume': [1]}
    else:
        data = {'timestamp': [timestamp],
                'exchange_code': [DUMMY_EXCHANGE_CODE],
                'symbol_code': [DUMMY_SYMBOL_CODE],
                'gmt_offset': [0],
                'open': [1.0],
                'high': [1.0],
                'low': [1.0],
                'close': [1.0],
                'volume': [1]}
    df_eod = pd.DataFrame(data)

    db_access.insert_ohlcv_data(df_eod, DUMMY_SYMBOL_CODE, DUMMY_EXCHANGE_CODE, time_frame, symbol_status)

    time.sleep(0.5)
    with pg.connect(QUESTDB_CONF_PSYCOPG, autocommit=True) as connection:
        # Open a cursor to perform database operations
        with connection.cursor() as cur:
            if time_frame == request_eodhd.TimeFrame.DAILY:
                query_string = db_sql.SQL_SELECT_CLOSE_FROM_DAILY_OHLCV
            else:

                query_string = db_sql.SQL_SELECT_CLOSE_FROM_MINUTE_OHLCV
            cur.execute(query_string, (timestamp,))
            rows = cur.fetchall()

            assert len(rows) == 1

@pytest.mark.db
def test_insert_symbol_meta_data(setup_test: Callable, setup_and_cleanup_sqlite: Callable):
    time_frame = request_eodhd.TimeFrame.DAILY
    symbol_status = request_eodhd.SymbolStatus.ACTIVE

    # Inserts data
    connection = sqlite3.connect(SQLITE_DB_PATH)
    data_dict = {"symbol_code": DUMMY_SYMBOL_CODE, "time_frame": time_frame.name, "symbol_status": symbol_status.name,
                 "name": "testo_name", "country": "testo_country", "exchange_code": DUMMY_EXCHANGE_CODE,
                 "currency": "testo_currency", "type": "testo_type", "isin": "testo_isin"}
    row_exchange_symbol = pd.Series(data_dict)
    db_access.insert_symbol_meta_data(row_exchange_symbol.to_frame().T, DUMMY_SYMBOL_CODE, DUMMY_EXCHANGE_CODE,
                                      time_frame, symbol_status)
    time.sleep(0.1)
    # Queries data
    df_symbol_meta = pd.read_sql(db_sql.SQL_SELECT_ALL_FROM_SYMBOL_META_BY_VALUES, con=connection,
                                 params={"symbol_code": DUMMY_SYMBOL_CODE, "exchange_code": DUMMY_EXCHANGE_CODE,
                                         "time_frame": time_frame.name, "symbol_status": symbol_status.name,
                                         "name": "testo_name"})
    assert df_symbol_meta.shape[0] > 0
    assert df_symbol_meta.at[0, "symbol_code"] == DUMMY_SYMBOL_CODE

    connection.close()
