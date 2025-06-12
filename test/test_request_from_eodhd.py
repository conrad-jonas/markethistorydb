#!/usr/bin/env python12.9

"""Unit tests for request_eodhd.py"""

import app.request_eodhd as request_eodhd

from app.db import CONF_PSYCOPG

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

# Query to select price data from table daily_ohlcv
SQL_SELECT_SYMBOL_FROM_DAILY_OHLCV = "SELECT close FROM daily_ohlcv WHERE timestamp = %s"
# Query to select price data from table daily_ohlcv
SQL_SELECT_SYMBOL_FROM_MINUTE_OHLCV = "SELECT close FROM minute_ohlcv WHERE timestamp = %s"
# Query to select symbol from table symbol_meta
SQL_SELECT_SYMBOL_FROM_SYMBOL_META = """SELECT code FROM symbol_meta WHERE code=:code AND time_frame=:time_frame AND 
                                        symbol_status=:symbol_status AND name=:name"""

@pytest.fixture(scope="session")
def setup_test():
    os.chdir(dirname(dirname(abspath(__file__))))
    yield

@pytest.mark.api
@pytest.mark.parametrize("time_frame", [request_eodhd.TimeFrame.DAILY, request_eodhd.TimeFrame.MINUTE])
def test_request_exchanges_data_from_eodhd(setup_test: Callable, time_frame: request_eodhd.TimeFrame):
    url_exchanges = "https://eodhd.com/api/exchanges-list/?api_token={0}&fmt=json".format(request_eodhd.API_TOKEN)
    response_exchanges = requests.get(url_exchanges)
    if response_exchanges.status_code in [402, 403]:
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
    if response_exchange_symbols.status_code in [402, 403]:
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
    if response_symbol.status_code in [402, 403]:
        with pytest.raises(SystemExit) as pytest_wrapped_error:
            request_eodhd.request_price_data_from_eodhd(symbol, exchange_code, exchange_name, time_frame)
        assert pytest_wrapped_error.type == SystemExit
        assert pytest_wrapped_error.value.code == 1
    else:
        df = request_eodhd.request_price_data_from_eodhd(symbol, exchange_code, exchange_name, time_frame)
        assert (df.shape[0] > 0)

@pytest.mark.db
def test_is_symbol_already_in_db_true(setup_test: Callable):
    time_frame = request_eodhd.TimeFrame.DAILY
    symbol_status = request_eodhd.SymbolStatus.ACTIVE

    is_symbol_already_in_db = request_eodhd.is_symbol_already_in_db("test_code", time_frame, symbol_status,
                                                                         "test_name")
    assert is_symbol_already_in_db == True

@pytest.mark.db
def test_is_symbol_already_in_db_false(setup_test: Callable):
    time_frame = request_eodhd.TimeFrame.DAILY
    symbol_status = request_eodhd.SymbolStatus.ACTIVE

    is_symbol_already_in_db = request_eodhd.is_symbol_already_in_db("test_code_XYZ", time_frame, symbol_status,
                                                                         "test_name")
    assert is_symbol_already_in_db == False

@pytest.mark.db
@pytest.mark.parametrize("time_frame", [request_eodhd.TimeFrame.DAILY, request_eodhd.TimeFrame.MINUTE])
def test_insert_price_data(setup_test: Callable, time_frame: request_eodhd.TimeFrame):
    symbol_code = "DSCHOOONAS"
    if time_frame == request_eodhd.TimeFrame.DAILY:
        timestamp = datetime.now()
    else:
        timestamp = pd.Timestamp(datetime.now())

    if time_frame == request_eodhd.TimeFrame.DAILY:
        data = {'datetime': [timestamp],
               'exchange_code': ["NASDAQ"],
               'symbol_code': [symbol_code],
               'open': [1.0],
               'high': [1.0],
               'low': [1.0],
               'close': [1.0],
               'adjusted_close': [1.0],
               'volume': [1]}
    else:
        data = {'timestamp': [timestamp],
                'exchange_code': ["NASDAQ"],
                'symbol_code': [symbol_code],
                'gmt_offset': [0],
                'open': [1.0],
                'high': [1.0],
                'low': [1.0],
                'close': [1.0],
                'volume': [1]}
    df_eod = pd.DataFrame(data)

    request_eodhd.insert_price_data(df_eod, time_frame, symbol_code)

    time.sleep(0.1)
    with pg.connect(CONF_PSYCOPG, autocommit=True) as connection:
        # Open a cursor to perform database operations
        with connection.cursor() as cur:
            if time_frame == request_eodhd.TimeFrame.DAILY:
                query_string = SQL_SELECT_SYMBOL_FROM_DAILY_OHLCV
            else:

                query_string = SQL_SELECT_SYMBOL_FROM_MINUTE_OHLCV
            cur.execute(query_string, (timestamp,))
            rows = cur.fetchall()

            assert len(rows) == 1

@pytest.mark.db
def test_insert_symbol_meta_data(setup_test: Callable):
    symbol_code = "DSCHOOONAS"

    def clean_table_symbol_meta(db_connection: sqlite3.Connection):
        # Prepare
        cursor = db_connection.cursor()
        cursor.execute("DELETE FROM symbol_meta WHERE code = ?", (symbol_code,))
        db_connection.commit()

    # Inserts data
    connection = sqlite3.connect(os.getcwd() + "/db/sqlite.db")
    clean_table_symbol_meta(connection)
    data_dict = {"code": symbol_code, "time_frame": "DAILY", "symbol_status": "ACTIVE", "name": "testo_name",
                "country": "testo_country", "exchange": "testo_exchange", "currency": "testo_currency",
                "type": "testo_type", "isin": "testo_isin"}
    row_exchange_symbol = pd.Series(data_dict)
    request_eodhd.insert_symbol_meta_data(row_exchange_symbol, symbol_code)

    # Queries data
    connection = sqlite3.connect(os.getcwd() + "/db/sqlite.db")
    df_symbol_meta = pd.read_sql(SQL_SELECT_SYMBOL_FROM_SYMBOL_META, con=connection,
                                 params={"code": symbol_code, "time_frame": "DAILY", "symbol_status": "ACTIVE",
                                         "name": "testo_name"})
    assert df_symbol_meta.shape[0] > 0
    assert df_symbol_meta.at[0, "code"] == symbol_code

    # Cleanup
    clean_table_symbol_meta(connection)
    connection.close()
