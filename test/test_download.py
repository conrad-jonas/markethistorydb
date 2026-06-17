#!/usr/bin/env python12.9

"""Unit tests for download.py"""
from fetch.utils import WriteMode
from fetch                  import download_db

import db.price.access as db_access
import db.price.tables as db_const
import setup.main as db_setup
import db.price.queries as db_sql

import pandas  as pd
import pytest
import psycopg as pg
import sqlite3
import time

from collections.abc    import Callable
from datetime           import datetime, timedelta
from json               import JSONDecodeError
from psycopg            import sql
from pytest_mock        import MockerFixture
from questdb.ingress    import IngressError
from typing             import Any
from unittest.mock      import MagicMock

# Enable pytest asserts in all functions
pytest.register_assert_rewrite('mypackage.utils')
# Redefines constants used in test object to decrease testing time duration:
# Time to wait after connection error to host occurred
download._WAIT_TIME_IN_SECS_AFTER_REQUEST_ERROR = 2
# Time to wait after API used up error
download._WAIT_TIME_IN_SECS_AFTER_API_ERROR = 2

PATH_FUNDAMENTAL_DATA_JSON = rf"test/test_request_eodhd/eodhd_fundamental_data.json"


@pytest.fixture()
def setup_questdb(backup_and_restore_questdb: Callable):
    """Creates QuestDB"""
    # Creates DB
    db_setup.setup_questdb()

@pytest.fixture()
def setup_and_cleanup_sqlite(backup_and_restore_sqlite: Callable):
    """Creates SQLite DB, inserts dummy data and cleans up afterward"""
    # Creates SQLite DB
    db_setup.setup_sqlite()

@pytest.mark.download
@pytest.mark.parametrize("time_frame, symbol_status",
                         [(download.TimeFrame.DAILY, download.SymbolStatus.ACTIVE),
                          (download.TimeFrame.MINUTE, download.SymbolStatus.ACTIVE)])
def test_download_symbol_data_per_exchange_default(setup_test: Callable, time_frame: download.TimeFrame,
                                           symbol_status: download.SymbolStatus, mocker: MockerFixture):
    response_mock = [{
            "Code": "AAPL",
            "Name": "Apple Inc.",
            "Country": "USA",
            "Exchange": "NASDAQ",
            "Currency": "USD",
            "Type": "Common Stock",
            "Isin": "US0378331005"
    }]
    mock_request = mocker.patch("download.download_request._request_data_from_url", return_value=response_mock)

    df_exchanges = pd.DataFrame([{
        "Name": "USAStocks",
        "Code": "US",
        "OperatingMIC": "XNAS,XNYS",
        "Country": "USA",
        "Currency": "USD",
        "CountryISO2": "US",
        "CountryISO3": "USA"
    }])
    exchange_name = "USAStocks"

    result = download._download_symbol_data_per_exchange(df_exchanges, time_frame, symbol_status, exchange_name)

    mock_request.assert_called()

    assert len(result) == 1
    assert result["US"].shape[0] > 0
    assert result["US"].shape[1] == 9
    actual_result_as_series = result["US"].iloc[0]
    assert actual_result_as_series.equals(pd.Series({
                                        db_const.COLUMN_SYMBOL_CODE: "AAPL",
                                        db_const.COLUMN_EXCHANGE_CODE: "NASDAQ",
                                        "time_frame": time_frame.name,
                                        "symbol_status": symbol_status.name,
                                        db_const.COLUMN_SYMBOL_NAME: "Apple Inc.",
                                        db_const.COLUMN_COUNTRY: "USA",
                                        db_const.COLUMN_CURRENCY: "USD",
                                        db_const.COLUMN_SYMBOL_TYPE: "Common Stock",
                                        db_const.COLUMN_ISIN: "US0378331005"}))


@pytest.mark.download
@pytest.mark.parametrize("time_frame, symbol_status",
                         [(download.TimeFrame.DAILY, download.SymbolStatus.DELISTED),
                          (download.TimeFrame.MINUTE, download.SymbolStatus.DELISTED)])
def test_download_symbol_data_per_exchange_empty(setup_test: Callable, time_frame: download.TimeFrame,
                                           symbol_status: download.SymbolStatus, mocker: MockerFixture):
    response_mock = []
    mock_request = mocker.patch("download.download_request._request_data_from_url", return_value=response_mock)

    df_exchanges = pd.DataFrame([{
        "Name": "USAStocks",
        "Code": "US",
        "OperatingMIC": "XNAS,XNYS",
        "Country": "USA",
        "Currency": "USD",
        "CountryISO2": "US",
        "CountryISO3": "USA"
    }])
    exchange_name = "USAStocks"

    result = download._download_symbol_data_per_exchange(df_exchanges, time_frame, symbol_status, exchange_name)

    mock_request.assert_called()

    assert len(result) == 0

@pytest.mark.download
def test_get_time_periods_for_minute_data_requests_1(setup_test: Callable, mocker: MockerFixture):
    # Mocking dependencies
    mocker.patch("download.download._START_DATE_MINUTE_DATA", "01-01-2015")
    mocker.patch("download.download._END_DATE_MINUTE_DATA", "31-12-2016")
    time_periods = download._get_time_periods_for_minute_data_requests()
    expected_time_period = [
        (datetime.strptime("01-01-2015", "%d-%m-%Y"), datetime.strptime("01-05-2015", "%d-%m-%Y")),
        (datetime.strptime("01-05-2015", "%d-%m-%Y"), datetime.strptime("29-08-2015", "%d-%m-%Y")),
        (datetime.strptime("29-08-2015", "%d-%m-%Y"), datetime.strptime("27-12-2015", "%d-%m-%Y")),
        (datetime.strptime("27-12-2015", "%d-%m-%Y"), datetime.strptime("25-04-2016", "%d-%m-%Y")),
        (datetime.strptime("25-04-2016", "%d-%m-%Y"), datetime.strptime("23-08-2016", "%d-%m-%Y")),
        (datetime.strptime("23-08-2016", "%d-%m-%Y"), datetime.strptime("21-12-2016", "%d-%m-%Y")),
        (datetime.strptime("21-12-2016", "%d-%m-%Y"), datetime.strptime("31-12-2016", "%d-%m-%Y"))
    ]
    assert time_periods == expected_time_period

@pytest.mark.download
def test_get_time_periods_for_minute_data_requests_2(setup_test: Callable, mocker: MockerFixture):
    # Mocking dependencies
    mocker.patch("download.download._START_DATE_MINUTE_DATA", "02-01-2015")
    mocker.patch("download.download._END_DATE_MINUTE_DATA", "03-01-2017")
    time_periods = download._get_time_periods_for_minute_data_requests()
    expected_time_period = [
        (datetime.strptime("02-01-2015", "%d-%m-%Y"), datetime.strptime("02-05-2015", "%d-%m-%Y")),
        (datetime.strptime("02-05-2015", "%d-%m-%Y"), datetime.strptime("30-08-2015", "%d-%m-%Y")),
        (datetime.strptime("30-08-2015", "%d-%m-%Y"), datetime.strptime("28-12-2015", "%d-%m-%Y")),
        (datetime.strptime("28-12-2015", "%d-%m-%Y"), datetime.strptime("26-04-2016", "%d-%m-%Y")),
        (datetime.strptime("26-04-2016", "%d-%m-%Y"), datetime.strptime("24-08-2016", "%d-%m-%Y")),
        (datetime.strptime("24-08-2016", "%d-%m-%Y"), datetime.strptime("22-12-2016", "%d-%m-%Y")),
        (datetime.strptime("22-12-2016", "%d-%m-%Y"), datetime.strptime("03-01-2017", "%d-%m-%Y"))
    ]
    assert time_periods == expected_time_period

@pytest.mark.download
def test_download_minute_price_data_from_eodhd_1(setup_test: Callable, mocker: MockerFixture):
    # Mocking dependencies
    mocker.patch("download.download_request._API_TOKEN", "demo")
    mocker.patch("download.download._START_DATE_MINUTE_DATA", "02-01-2015")
    mocker.patch("download.download._END_DATE_MINUTE_DATA", "04-01-2017")


    df: pd.DataFrame = download._get_minute_price_data("AAPL", "US", "NASDAQ")
    assert df.shape[0] > 0
    assert df.shape[1] == 9
    assert set(list(df)) == set(db_const.COLUMNS_MINUTE_PRICE)
    assert df.at[0, "timestamp"].date() == datetime(2015, 1, 2).date()
    assert df.at[df.index[-1], "timestamp"].date() == datetime(2017, 1, 3).date()

@pytest.mark.download
def test_download_minute_price_data_from_eodhd_2(setup_test: Callable, mocker: MockerFixture):
    # Mocking dependencies
    mocker.patch("download.download_request._API_TOKEN", "demo")
    mocker.patch("download.download._START_DATE_MINUTE_DATA", "02-03-2026")
    mocker.patch("download.download._END_DATE_MINUTE_DATA", "10-03-2026")
    mocker.patch("download.download._NUM_OF_DAYS_PER_MINUTE_DATA_REQUEST", 3)

    df: pd.DataFrame = download._get_minute_price_data("AAPL", "US", "NASDAQ")
    assert df.shape[0] > 0
    assert df.shape[1] == 9
    assert set(list(df)) == set(db_const.COLUMNS_MINUTE_PRICE)
    assert df.at[0, "timestamp"].date() == datetime(2026, 3, 2).date()
    assert df.at[df.index[-1], "timestamp"].date() == datetime(2026, 3, 9).date()
    dates = df['timestamp'].dt.date.unique().tolist()
    assert dates == [datetime(2026, 3, 2).date(),
                     datetime(2026, 3, 3).date(),
                     datetime(2026, 3, 4).date(),
                     datetime(2026, 3, 5).date(),
                     datetime(2026, 3, 6).date(),
                     datetime(2026, 3, 7).date(),
                     datetime(2026, 3, 9).date()]

@pytest.mark.download
def test_download_minute_price_data_from_eodhd_3(setup_test: Callable, mocker: MockerFixture):
    # Mocking dependencies
    mocker.patch("download.download_request._API_TOKEN", "demo")
    mocker.patch("download.download._START_DATE_MINUTE_DATA", "02-01-2015")
    mocker.patch("download.download._END_DATE_MINUTE_DATA", "10-03-2026")

    df: pd.DataFrame = download._get_minute_price_data("AAPL", "US", "NASDAQ",
                                                       start_datetime=datetime(2026, 3, 2))
    assert df.shape[0] > 0
    assert df.shape[1] == 9
    assert set(list(df)) == set(db_const.COLUMNS_MINUTE_PRICE)
    assert df.at[0, "timestamp"].date() == datetime(2026, 3, 2).date()
    assert df.at[df.index[-1], "timestamp"].date() == datetime(2026, 3, 9).date()
    dates = df['timestamp'].dt.date.unique().tolist()
    assert dates == [datetime(2026, 3, 2).date(),
                     datetime(2026, 3, 3).date(),
                     datetime(2026, 3, 4).date(),
                     datetime(2026, 3, 5).date(),
                     datetime(2026, 3, 6).date(),
                     datetime(2026, 3, 7).date(),
                     datetime(2026, 3, 9).date()]

@pytest.mark.download
@pytest.mark.parametrize("time_frame, symbol_status",
                         [(download.TimeFrame.DAILY, download.SymbolStatus.ACTIVE),
                          (download.TimeFrame.MINUTE, download.SymbolStatus.ACTIVE)])
def test_download_price_data_into_db_without_start_date_default(setup_test: Callable, setup_questdb: Callable,
                                                                time_frame: download.TimeFrame,
                                                                symbol_status: download.SymbolStatus,
                                                                mocker: MockerFixture):
    # Mocking dependencies
    mocker.patch("download.download_request._API_TOKEN", "demo")
    mocker.patch("download.download._START_DATE_MINUTE_DATA", "04-02-2026")
    mocker.patch("download.download._END_DATE_MINUTE_DATA", "10-03-2026")

    result = download.run("AAPL", "US", "NASDAQ", time_frame, symbol_status)
    assert result == True

    # Queries QuestDB data
    if time_frame == download.TimeFrame.DAILY:
        time.sleep(1)
        query_string = db_sql.SQL_SELECT_ALL_FROM_DAILY_OHLCV
        column_names = db_const.COLUMNS_DAILY_PRICE
    else:
        time.sleep(5)
        query_string = db_sql.SQL_SELECT_ALL_FROM_MINUTE_OHLCV
        column_names = db_const.COLUMNS_MINUTE_PRICE

    with pg.connect(db_const.QUESTDB_CONF_PSYCOPG, cursor_factory=pg.ClientCursor, autocommit=True) as connection:
        # Open a cursor to perform database operations
        with connection.cursor() as cur:
            symbol_codes = ["AAPL"]
            query = sql.SQL(query_string).format(symbol_codes=sql.SQL(', ').join(map(sql.Literal, symbol_codes)))
            params: list[Any] = ["NASDAQ"]
            params.extend([datetime(2026, 1, 1),  datetime(2026, 3, 10)])
            cur.execute(query, params)
            rows = cur.fetchall()
            cur.close()
            df = pd.DataFrame(rows, columns=column_names)
    assert df.shape[1] == 9
    if time_frame == download.TimeFrame.MINUTE:
        assert df.at[0, "timestamp"].date() == datetime(2026, 2, 3).date()
        assert df.at[df.index[-1], "timestamp"].date() == datetime(2026, 3, 9).date()

@pytest.mark.download
@pytest.mark.parametrize("time_frame, symbol_status",
                         [(download.TimeFrame.DAILY, download.SymbolStatus.DELISTED),
                          (download.TimeFrame.MINUTE, download.SymbolStatus.DELISTED)])
def test_download_price_data_into_db_without_start_date_empty(setup_test: Callable, setup_questdb: Callable,
                                                              time_frame: download.TimeFrame,
                                                              symbol_status: download.SymbolStatus,
                                                              mocker: MockerFixture):
    # Mocking dependencies
    mocker.patch("download.download_request._API_TOKEN", "demo")
    mocker.patch("download.download._START_DATE_MINUTE_DATA", "04-02-2026")
    mocker.patch("download.download._END_DATE_MINUTE_DATA", "10-03-2026")

    response_mock = pd.DataFrame()
    if time_frame == download.TimeFrame.DAILY:
        mock_request = mocker.patch("download.download._download_daily_price_data_from_eodhd",
                                    return_value=response_mock)
    else:
        mock_request = mocker.patch("download.download._download_minute_price_data_from_eodhd",
                                    return_value=response_mock)

    result = download.run("AAPL", "US", "NASDAQ", time_frame, symbol_status)
    assert result == False

    mock_request.assert_called_once()

    # Queries QuestDB data
    if time_frame == download.TimeFrame.DAILY:
        time.sleep(1)
        query_string = db_sql.SQL_SELECT_ALL_FROM_DAILY_OHLCV
        column_names = db_const.COLUMNS_DAILY_PRICE
    else:
        time.sleep(5)
        query_string = db_sql.SQL_SELECT_ALL_FROM_MINUTE_OHLCV
        column_names = db_const.COLUMNS_MINUTE_PRICE

    with pg.connect(db_const.QUESTDB_CONF_PSYCOPG, cursor_factory=pg.ClientCursor, autocommit=True) as connection:
        # Open a cursor to perform database operations
        with connection.cursor() as cur:
            symbol_codes = ["AAPL"]
            query = sql.SQL(query_string).format(symbol_codes=sql.SQL(', ').join(map(sql.Literal, symbol_codes)))
            params: list[Any] = ["NASDAQ"]
            params.extend([datetime(2026, 1, 1),  datetime(2026, 3, 10)])
            cur.execute(query, params)
            rows = cur.fetchall()
            cur.close()
            df = pd.DataFrame(rows, columns=column_names)
    assert df.shape[0] == 0

@pytest.mark.download
@pytest.mark.parametrize("time_frame, symbol_status",
                         [(download.TimeFrame.DAILY, download.SymbolStatus.ACTIVE),
                          (download.TimeFrame.MINUTE, download.SymbolStatus.ACTIVE)])
def test_download_price_data_into_db_with_start_date_default(setup_test: Callable, setup_questdb: Callable,
                                                             time_frame: download.TimeFrame,
                                                             symbol_status: download.SymbolStatus,
                                                             mocker: MockerFixture):
    # Mocking dependencies
    mocker.patch("download.download_request._API_TOKEN", "demo")

    result = download.run("AAPL", "US", "NASDAQ", time_frame, symbol_status,
                          start_datetime=datetime(2026, 2, 4))
    assert result == True

    # Queries QuestDB data
    if time_frame == download.TimeFrame.DAILY:
        time.sleep(1)
        query_string = db_sql.SQL_SELECT_ALL_FROM_DAILY_OHLCV
        column_names = db_const.COLUMNS_DAILY_PRICE
    else:
        time.sleep(5)
        query_string = db_sql.SQL_SELECT_ALL_FROM_MINUTE_OHLCV
        column_names = db_const.COLUMNS_MINUTE_PRICE

    with pg.connect(db_const.QUESTDB_CONF_PSYCOPG, cursor_factory=pg.ClientCursor, autocommit=True) as connection:
        # Open a cursor to perform database operations
        with connection.cursor() as cur:
            symbol_codes = ["AAPL"]
            query = sql.SQL(query_string).format(symbol_codes=sql.SQL(', ').join(map(sql.Literal, symbol_codes)))
            params: list[Any] = ["NASDAQ"]
            params.extend([datetime(2026, 1, 1),  datetime(2026, 3, 10)])
            cur.execute(query, params)
            rows = cur.fetchall()
            cur.close()
            df = pd.DataFrame(rows, columns=column_names)
    assert df.shape[1] == 9
    if time_frame == download.TimeFrame.DAILY:
        assert df.at[0, "timestamp"].date() == datetime(2026, 2, 4).date()
        assert df.at[df.index[-1], "timestamp"].date() == datetime(2026, 3, 10).date()
    else:
        assert df.at[0, "timestamp"].date() == datetime(2026, 2, 3).date()
        assert df.at[df.index[-1], "timestamp"].date() == datetime(2026, 3, 9).date()

@pytest.mark.download
@pytest.mark.parametrize("time_frame, symbol_status",
                         [(download.TimeFrame.DAILY, download.SymbolStatus.DELISTED),
                          (download.TimeFrame.MINUTE, download.SymbolStatus.DELISTED)])
def test_download_price_data_into_db_with_start_date_empty(setup_test: Callable, setup_questdb: Callable,
                                                           time_frame: download.TimeFrame,
                                                           symbol_status: download.SymbolStatus,
                                                           mocker: MockerFixture):
    # Mocking dependencies
    mocker.patch("download.download_request._API_TOKEN", "demo")

    response_mock = pd.DataFrame()
    if time_frame == download.TimeFrame.DAILY:
        mock_request = mocker.patch("download.download._download_daily_price_data_from_eodhd",
                                    return_value=response_mock)
    else:
        mock_request = mocker.patch("download.download._download_minute_price_data_from_eodhd",
                                    return_value=response_mock)

    result = download.run("AAPL", "US", "NASDAQ", time_frame, symbol_status,
                          start_datetime=datetime(2026, 2, 4))
    assert result == False
    mock_request.assert_called_once()

    # Queries QuestDB data
    if time_frame == download.TimeFrame.DAILY:
        time.sleep(1)
        query_string = db_sql.SQL_SELECT_ALL_FROM_DAILY_OHLCV
        column_names = db_const.COLUMNS_DAILY_PRICE
    else:
        time.sleep(5)
        query_string = db_sql.SQL_SELECT_ALL_FROM_MINUTE_OHLCV
        column_names = db_const.COLUMNS_MINUTE_PRICE

    with pg.connect(db_const.QUESTDB_CONF_PSYCOPG, cursor_factory=pg.ClientCursor, autocommit=True) as connection:
        # Open a cursor to perform database operations
        with connection.cursor() as cur:
            symbol_codes = ["AAPL"]
            query = sql.SQL(query_string).format(symbol_codes=sql.SQL(', ').join(map(sql.Literal, symbol_codes)))
            params: list[Any] = ["NASDAQ"]
            params.extend([datetime(2026, 1, 1),  datetime(2026, 3, 10)])
            cur.execute(query, params)
            rows = cur.fetchall()
            cur.close()
            df = pd.DataFrame(rows, columns=column_names)
    assert df.shape[0] == 0

def assert_fundamental_data_inserted(id_symbol_meta: int):
    connection = sqlite3.connect(db_const.SQLITE_DB_PATH)
    df_symbol_sector = pd.read_sql(db_sql.SQL_SELECT_ALL_FROM_SYMBOL_SECTOR, con=connection,
                                   params={"id_symbol_meta": id_symbol_meta})
    df_earnings_quarterly = pd.read_sql(db_sql.SQL_SELECT_ALL_FROM_EARNINGS_QUARTERLY, con=connection,
                                        params={"id_symbol_meta": id_symbol_meta})
    df_earnings_annually = pd.read_sql(db_sql.SQL_SELECT_ALL_FROM_EARNINGS_ANNUALLY, con=connection,
                                       params={"id_symbol_meta": id_symbol_meta})
    df_balance_sheet_quarterly = pd.read_sql(db_sql.SQL_SELECT_ALL_FROM_BALANCE_SHEET_QUARTERLY, con=connection,
                                             params={"id_symbol_meta": id_symbol_meta})
    df_balance_sheet_annually = pd.read_sql(db_sql.SQL_SELECT_ALL_FROM_BALANCE_SHEET_ANNUALLY, con=connection,
                                            params={"id_symbol_meta": id_symbol_meta})
    df_cash_flow_quarterly = pd.read_sql(db_sql.SQL_SELECT_ALL_FROM_CASH_FLOW_QUARTERLY, con=connection,
                                         params={"id_symbol_meta": id_symbol_meta})
    df_cash_flow_annually = pd.read_sql(db_sql.SQL_SELECT_ALL_FROM_CASH_FLOW_ANNUALLY, con=connection,
                                        params={"id_symbol_meta": id_symbol_meta})
    df_income_statement_quarterly = pd.read_sql(db_sql.SQL_SELECT_ALL_FROM_INCOME_STATEMENT_QUARTERLY, con=connection,
                                                params={"id_symbol_meta": id_symbol_meta})
    df_income_statement_annually = pd.read_sql(db_sql.SQL_SELECT_ALL_FROM_INCOME_STATEMENT_ANNUALLY, con=connection,
                                               params={"id_symbol_meta": id_symbol_meta})
    connection.close()

    assert df_symbol_sector.shape[0] > 0
    assert df_symbol_sector.at[0, "id_symbol_meta"] == id_symbol_meta
    assert df_earnings_quarterly.shape[0] > 0
    assert df_earnings_quarterly.at[0, "id_symbol_meta"] == id_symbol_meta
    assert df_earnings_annually.shape[0] > 0
    assert df_earnings_annually.at[0, "id_symbol_meta"] == id_symbol_meta
    assert df_balance_sheet_quarterly.shape[0] > 0
    assert df_balance_sheet_quarterly.at[0, "id_symbol_meta"] == id_symbol_meta
    assert df_balance_sheet_annually.shape[0] > 0
    assert df_balance_sheet_annually.at[0, "id_symbol_meta"] == id_symbol_meta
    assert df_cash_flow_quarterly.shape[0] > 0
    assert df_cash_flow_quarterly.at[0, "id_symbol_meta"] == id_symbol_meta
    assert df_cash_flow_annually.shape[0] > 0
    assert df_cash_flow_annually.at[0, "id_symbol_meta"] == id_symbol_meta
    assert df_income_statement_quarterly.shape[0] > 0
    assert df_income_statement_quarterly.at[0, "id_symbol_meta"] == id_symbol_meta
    assert df_income_statement_annually.shape[0] > 0
    assert df_income_statement_annually.at[0, "id_symbol_meta"] == id_symbol_meta

@pytest.mark.download
@pytest.mark.parametrize("time_frame, symbol_status",
                         [(download.TimeFrame.DAILY, download.SymbolStatus.ACTIVE),
                          (download.TimeFrame.MINUTE, download.SymbolStatus.ACTIVE)])
def test_download_fundamental_data_into_db_default(setup_test: Callable, setup_and_cleanup_sqlite: Callable,
                                                   time_frame: download.TimeFrame, symbol_status: download.SymbolStatus,
                                                   mocker: MockerFixture):
    # Mocking dependencies
    mocker.patch("download.download_request._API_TOKEN", "demo")
    response_mock = 1
    mock_function = mocker.patch("db.db_access.get_id_from_symbol_meta", return_value=response_mock)

    result = download.run("AAPL", "Apple Inc.", "US", "NASDAQ", time_frame, symbol_status)
    assert result == True
    mock_function.assert_called_once()
    time.sleep(1)

    assert_fundamental_data_inserted(id_symbol_meta=1)

def assert_no_insert_in_symbol_meta(time_frame: download.TimeFrame, symbol_status: download.SymbolStatus):
    connection = sqlite3.connect(db_const.SQLITE_DB_PATH)
    df_symbol_meta = pd.read_sql(db_sql.SQL_SELECT_ALL_FROM_SYMBOL_META_BY_VALUES, con=connection,
                                 params={"symbol_code": "AAPL", "exchange_code": "NASDAQ",
                                         "time_frame": time_frame.name,
                                         "symbol_status": symbol_status.name, "name": "Apple Inc."})
    connection.close()
    assert df_symbol_meta.shape[0] == 0

@pytest.mark.download
@pytest.mark.parametrize("time_frame, symbol_status",
                         [(download.TimeFrame.DAILY, download.SymbolStatus.DELISTED),
                          (download.TimeFrame.MINUTE, download.SymbolStatus.DELISTED)])
def test_download_fundamental_data_into_db_empty(setup_test: Callable, setup_and_cleanup_sqlite: Callable,
                                                 time_frame: download.TimeFrame, symbol_status: download.SymbolStatus,
                                                 mocker: MockerFixture):
    # Mocking dependencies
    mocker.patch("download.download_request._API_TOKEN", "demo")
    mock_function = mocker.patch("download.download_request.request_fundamental_data_from_eodhd", return_value={})

    result = download.run("AAPL", "Apple Inc.", "US", "NASDAQ", time_frame, symbol_status)
    assert result == False
    mock_function.assert_called_once()
    time.sleep(1)

    assert_no_insert_in_symbol_meta(time_frame, symbol_status)

def get_id_of_inserted_symbol_meta_data(time_frame: download.TimeFrame, symbol_status: download.SymbolStatus) -> int:
    connection = sqlite3.connect(db_const.SQLITE_DB_PATH)
    df_symbol_meta = pd.read_sql(db_sql.SQL_SELECT_ALL_FROM_SYMBOL_META_BY_VALUES, con=connection,
                                 params={"symbol_code": "AAPL", "exchange_code": "NASDAQ",
                                         "time_frame": time_frame.name,
                                         "symbol_status": symbol_status.name, "name": "Apple Inc."})
    connection.close()
    assert df_symbol_meta.shape[0] > 0
    assert df_symbol_meta.at[0, "symbol_code"] == "AAPL"
    id_symbol_meta = int(df_symbol_meta.at[0, "id"])
    return id_symbol_meta

@pytest.mark.download
@pytest.mark.parametrize("time_frame, symbol_status",
                         [(download.TimeFrame.DAILY, download.SymbolStatus.ACTIVE),
                          (download.TimeFrame.MINUTE, download.SymbolStatus.ACTIVE)])
def test_download_price_and_fundamental_data_per_symbol_1_default(
        setup_test: Callable, setup_and_cleanup_sqlite: Callable, setup_questdb: Callable,
        time_frame: download.TimeFrame, symbol_status: download.SymbolStatus, mocker: MockerFixture):
    # Mocking dependencies
    mocker.patch("download.download_request._API_TOKEN", "demo")
    mocker.patch("download.download._START_DATE_MINUTE_DATA", "04-02-2026")
    mocker.patch("download.download._END_DATE_MINUTE_DATA", "10-03-2026")

    series_exchange_symbol = pd.Series({
        db_const.COLUMN_SYMBOL_CODE: "AAPL",
        "time_frame": time_frame.name,
        "symbol_status": symbol_status.name,
        db_const.COLUMN_SYMBOL_NAME: "Apple Inc.",
        db_const.COLUMN_COUNTRY: "USA",
        db_const.COLUMN_EXCHANGE_CODE: "NASDAQ",
        db_const.COLUMN_CURRENCY: "USD",
        db_const.COLUMN_SYMBOL_TYPE: "Common Stock",
        db_const.COLUMN_ISIN: "US0378331005"
    })
    write_mode = WriteMode.IGNORE_IF_EXIST
    download._download_price_and_fundamental_data_for_symbol(series_exchange_symbol, "US",
                                                             time_frame, symbol_status, write_mode)
    time.sleep(1)

    # Queries SQLITE data
    id_symbol_meta = get_id_of_inserted_symbol_meta_data(time_frame, symbol_status)
    assert_fundamental_data_inserted(id_symbol_meta=id_symbol_meta)

    # Queries QuestDB data
    if time_frame == download.TimeFrame.DAILY:
        time.sleep(1)
        query_string = db_sql.SQL_SELECT_ALL_FROM_DAILY_OHLCV
        column_names = db_const.COLUMNS_DAILY_PRICE
    else:
        time.sleep(5)
        query_string = db_sql.SQL_SELECT_ALL_FROM_MINUTE_OHLCV
        column_names = db_const.COLUMNS_MINUTE_PRICE

    with pg.connect(db_const.QUESTDB_CONF_PSYCOPG, cursor_factory=pg.ClientCursor, autocommit=True) as connection:
        with connection.cursor() as cur:
            symbol_codes = ["AAPL"]
            query = sql.SQL(query_string).format(symbol_codes=sql.SQL(', ').join(map(sql.Literal, symbol_codes)))
            params: list[Any] = ["NASDAQ"]
            params.extend([datetime.now() - timedelta(days=3 * 365), datetime.now()])
            cur.execute(query, params)
            rows = cur.fetchall()
            cur.close()
            df = pd.DataFrame(rows, columns=column_names)
    assert df.shape[0] > 0

@pytest.mark.download
@pytest.mark.parametrize("time_frame, symbol_status",
                         [(download.TimeFrame.DAILY, download.SymbolStatus.DELISTED),
                          (download.TimeFrame.MINUTE, download.SymbolStatus.DELISTED)])
def test_download_price_and_fundamental_data_per_symbol_1_empty(
        setup_test: Callable, setup_and_cleanup_sqlite: Callable, setup_questdb: Callable,
        time_frame: download.TimeFrame, symbol_status: download.SymbolStatus, mocker: MockerFixture):
    # Mocking dependencies
    mocker.patch("download.download_request._API_TOKEN", "demo")
    mocker.patch("download.download._START_DATE_MINUTE_DATA", "04-02-2026")
    mocker.patch("download.download._END_DATE_MINUTE_DATA", "10-03-2026")

    response_mock = pd.DataFrame()
    if time_frame == download.TimeFrame.DAILY:
        mock_request = mocker.patch("download.download._download_daily_price_data_from_eodhd",
                                    return_value=response_mock)
    else:
        mock_request = mocker.patch("download.download._download_minute_price_data_from_eodhd",
                                    return_value=response_mock)

    series_exchange_symbol = pd.Series({
        db_const.COLUMN_SYMBOL_CODE: "AAPL",
        "time_frame": time_frame.name,
        "symbol_status": symbol_status.name,
        db_const.COLUMN_SYMBOL_NAME: "Apple Inc.",
        db_const.COLUMN_COUNTRY: "USA",
        db_const.COLUMN_EXCHANGE_CODE: "NASDAQ",
        db_const.COLUMN_CURRENCY: "USD",
        db_const.COLUMN_SYMBOL_TYPE: "Common Stock",
        db_const.COLUMN_ISIN: "US0378331005"
    })
    write_mode = WriteMode.IGNORE_IF_EXIST
    download._download_price_and_fundamental_data_for_symbol(series_exchange_symbol, "US",
                                                             time_frame, symbol_status, write_mode)
    time.sleep(1)
    mock_request.assert_called_once()

    # Queries SQLITE data
    assert_no_insert_in_symbol_meta(time_frame, symbol_status)

    # Queries QuestDB data
    if time_frame == download.TimeFrame.DAILY:
        time.sleep(1)
        query_string = db_sql.SQL_SELECT_ALL_FROM_DAILY_OHLCV
        column_names = db_const.COLUMNS_DAILY_PRICE
    else:
        time.sleep(5)
        query_string = db_sql.SQL_SELECT_ALL_FROM_MINUTE_OHLCV
        column_names = db_const.COLUMNS_MINUTE_PRICE

    with pg.connect(db_const.QUESTDB_CONF_PSYCOPG, cursor_factory=pg.ClientCursor, autocommit=True) as connection:
        with connection.cursor() as cur:
            symbol_codes = ["AAPL"]
            query = sql.SQL(query_string).format(symbol_codes=sql.SQL(', ').join(map(sql.Literal, symbol_codes)))
            params: list[Any] = ["NASDAQ"]
            params.extend([datetime.now() - timedelta(days=3 * 365), datetime.now()])
            cur.execute(query, params)
            rows = cur.fetchall()
            cur.close()
            df = pd.DataFrame(rows, columns=column_names)
    assert df.shape[0] == 0

def insert_pre_existing_data_ending_with_day(mocker: MockerFixture, time_frame: download.TimeFrame,
                                             symbol_status: download.SymbolStatus):
    # Mocking dependencies
    mocker.patch("download.download_request._API_TOKEN", "demo")
    mocker.patch("download.download._START_DATE_MINUTE_DATA", "04-01-2026")

    symbol_code = "AAPL"
    exchange_url_code = "US"
    exchange_code = "NASDAQ"

    # Insert pre-existing data into QUESTDB
    # Requests data
    if time_frame == download.TimeFrame.DAILY:
        df_symbol = download._get_daily_price_data(symbol_code, exchange_url_code, exchange_code,
                                                   time_frame, start_datetime=datetime(2026, 1, 6))
        df_symbol['datetime'] = pd.to_datetime(df_symbol['datetime'])
        df_filtered = df_symbol[df_symbol['datetime'] < '2026-01-30']
    else:
        df_symbol = download._get_minute_price_data(symbol_code, exchange_url_code, exchange_code,
                                                    start_datetime=datetime(2026, 1, 6))
        df_symbol['timestamp'] = pd.to_datetime(df_symbol['timestamp'])
        df_filtered = df_symbol[df_symbol['timestamp'] < '2026-01-30']
    # Insert into db
    download_insert.insert_price_data(df_filtered, symbol_code, exchange_code, time_frame, symbol_status)

    # Insert pre-exiting data into SQLite DB
    data_dict = {"symbol_code": symbol_code, "time_frame": time_frame.name,
                 "symbol_status": symbol_status.name, "name": "Apple Inc.", "country": "testo_country",
                 "exchange_code": exchange_code, "currency": "testo_currency", "type": "testo_type",
                 "isin": "testo_isin"}
    df_exchange_symbol = pd.Series(data_dict).to_frame().T
    db_access.insert_df_into_sqlite(df_exchange_symbol, db_const.TABLE_SYMBOL_META)

    time.sleep(1) if time_frame == download.TimeFrame.DAILY else time.sleep(5)

def insert_pre_existing_data_ending_mid_day(mocker: MockerFixture, time_frame: download.TimeFrame,
                                             symbol_status: download.SymbolStatus):
    # Mocking dependencies
    mocker.patch("download.download_request._API_TOKEN", "demo")
    mocker.patch("download.download._START_DATE_MINUTE_DATA", "04-01-2026")

    symbol_code = "AAPL"
    exchange_url_code = "US"
    exchange_code = "NASDAQ"

    # Insert pre-existing data into QUESTDB
    # Requests data
    if time_frame == download.TimeFrame.DAILY:
        df_symbol = download._get_daily_price_data(symbol_code, exchange_url_code, exchange_code,
                                                   time_frame, start_datetime=datetime(2026, 1, 6))
        df_symbol['datetime'] = pd.to_datetime(df_symbol['datetime'])
        df_filtered = df_symbol[df_symbol['datetime'] < datetime(2026, 1, 29, hour=14)]
    else:
        df_symbol = download._get_minute_price_data(symbol_code, exchange_url_code, exchange_code,
                                                    start_datetime=datetime(2026, 1, 6))
        df_symbol['timestamp'] = pd.to_datetime(df_symbol['timestamp'])
        df_filtered = df_symbol[df_symbol['timestamp'] < datetime(2026, 1, 29, hour=14)]
    # Insert into db
    download_insert.insert_price_data(df_filtered, symbol_code, exchange_code, time_frame, symbol_status)

    # Insert pre-exiting data into SQLite DB
    data_dict = {"symbol_code": symbol_code, "time_frame": time_frame.name,
                 "symbol_status": symbol_status.name, "name": "Apple Inc.", "country": "testo_country",
                 "exchange_code": exchange_code, "currency": "testo_currency", "type": "testo_type",
                 "isin": "testo_isin"}
    df_exchange_symbol = pd.Series(data_dict).to_frame().T
    db_access.insert_df_into_sqlite(df_exchange_symbol, db_const.TABLE_SYMBOL_META)

    time.sleep(1) if time_frame == download.TimeFrame.DAILY else time.sleep(5)

@pytest.mark.download
@pytest.mark.parametrize("time_frame, symbol_status",
                         [(download.TimeFrame.DAILY, download.SymbolStatus.ACTIVE),
                          (download.TimeFrame.DAILY, download.SymbolStatus.DELISTED),
                          (download.TimeFrame.MINUTE, download.SymbolStatus.ACTIVE),
                          (download.TimeFrame.MINUTE, download.SymbolStatus.DELISTED)])
def test_get_start_datetime_1(setup_test: Callable, setup_and_cleanup_sqlite: Callable, setup_questdb: Callable,
                              time_frame: download.TimeFrame, symbol_status: download.SymbolStatus):
    write_mode = WriteMode.IGNORE_IF_EXIST
    symbol_is_already_in_db = False
    symbol_code = "AAPL"
    exchange_code = "NASDAQ"

    result = download._get_start_datetime(write_mode, symbol_is_already_in_db, symbol_code, exchange_code, time_frame)
    assert result is None

@pytest.mark.download
@pytest.mark.parametrize("time_frame, symbol_status",
                         [(download.TimeFrame.DAILY, download.SymbolStatus.ACTIVE),
                          (download.TimeFrame.DAILY, download.SymbolStatus.DELISTED),
                          (download.TimeFrame.MINUTE, download.SymbolStatus.ACTIVE),
                          (download.TimeFrame.MINUTE, download.SymbolStatus.DELISTED)])
def test_get_start_datetime_2(setup_test: Callable, setup_and_cleanup_sqlite: Callable, setup_questdb: Callable,
                              time_frame: download.TimeFrame, symbol_status: download.SymbolStatus,
                              mocker: MockerFixture):
    write_mode = WriteMode.APPEND_IF_EXIST
    symbol_is_already_in_db = True
    symbol_code = "AAPL"
    exchange_code = "NASDAQ"

    result = download._get_start_datetime(write_mode, symbol_is_already_in_db, symbol_code, exchange_code, time_frame)
    assert result is None

@pytest.mark.download
@pytest.mark.parametrize("time_frame, symbol_status",
                         [(download.TimeFrame.DAILY, download.SymbolStatus.ACTIVE),
                          (download.TimeFrame.DAILY, download.SymbolStatus.DELISTED),
                          (download.TimeFrame.MINUTE, download.SymbolStatus.ACTIVE),
                          (download.TimeFrame.MINUTE, download.SymbolStatus.DELISTED)])
def test_get_start_datetime_3(setup_test: Callable, setup_and_cleanup_sqlite: Callable, setup_questdb: Callable,
                              time_frame: download.TimeFrame, symbol_status: download.SymbolStatus,
                              mocker: MockerFixture):
    # Mocking dependencies
    mocker.patch("download.download_request._API_TOKEN", "demo")
    mocker.patch("download.download._START_DATE_MINUTE_DATA", "04-02-2026")
    mocker.patch("download.download._END_DATE_MINUTE_DATA", "10-03-2026")

    insert_pre_existing_data_ending_with_day(mocker, time_frame, symbol_status)

    write_mode = WriteMode.APPEND_IF_EXIST
    symbol_is_already_in_db = True
    symbol_code = "AAPL"
    exchange_code = "NASDAQ"

    result = download._get_start_datetime(write_mode, symbol_is_already_in_db, symbol_code, exchange_code, time_frame)
    assert result == datetime(2026, 1, 30)

@pytest.mark.download
@pytest.mark.parametrize("time_frame, symbol_status",
                         [(download.TimeFrame.DAILY, download.SymbolStatus.ACTIVE),
                          (download.TimeFrame.DAILY, download.SymbolStatus.DELISTED),
                          (download.TimeFrame.MINUTE, download.SymbolStatus.ACTIVE),
                          (download.TimeFrame.MINUTE, download.SymbolStatus.DELISTED)])
def test_get_start_datetime_4(setup_test: Callable, setup_and_cleanup_sqlite: Callable, setup_questdb: Callable,
                              time_frame: download.TimeFrame, symbol_status: download.SymbolStatus,
                              mocker: MockerFixture):
    # Mocking dependencies
    mocker.patch("download.download_request._API_TOKEN", "demo")
    mocker.patch("download.download._START_DATE_MINUTE_DATA", "04-02-2026")
    mocker.patch("download.download._END_DATE_MINUTE_DATA", "10-03-2026")

    insert_pre_existing_data_ending_mid_day(mocker, time_frame, symbol_status)

    write_mode = WriteMode.APPEND_IF_EXIST
    symbol_is_already_in_db = True
    symbol_code = "AAPL"
    exchange_code = "NASDAQ"

    result = download._get_start_datetime(write_mode, symbol_is_already_in_db, symbol_code, exchange_code, time_frame)
    if time_frame == download.TimeFrame.DAILY:
        assert result == datetime(2026, 1, 30)
    else:
        assert result == datetime(2026, 1, 29, hour=14)

def assert_fundamental_data_not_inserted(id_symbol_meta: int):
    connection = sqlite3.connect(db_const.SQLITE_DB_PATH)
    df_symbol_sector = pd.read_sql(db_sql.SQL_SELECT_ALL_FROM_SYMBOL_SECTOR, con=connection,
                                   params={"id_symbol_meta": id_symbol_meta})
    df_earnings_quarterly = pd.read_sql(db_sql.SQL_SELECT_ALL_FROM_EARNINGS_QUARTERLY, con=connection,
                                        params={"id_symbol_meta": id_symbol_meta})
    df_earnings_annually = pd.read_sql(db_sql.SQL_SELECT_ALL_FROM_EARNINGS_ANNUALLY, con=connection,
                                       params={"id_symbol_meta": id_symbol_meta})
    df_balance_sheet_quarterly = pd.read_sql(db_sql.SQL_SELECT_ALL_FROM_BALANCE_SHEET_QUARTERLY, con=connection,
                                             params={"id_symbol_meta": id_symbol_meta})
    df_balance_sheet_annually = pd.read_sql(db_sql.SQL_SELECT_ALL_FROM_BALANCE_SHEET_ANNUALLY, con=connection,
                                            params={"id_symbol_meta": id_symbol_meta})
    df_cash_flow_quarterly = pd.read_sql(db_sql.SQL_SELECT_ALL_FROM_CASH_FLOW_QUARTERLY, con=connection,
                                         params={"id_symbol_meta": id_symbol_meta})
    df_cash_flow_annually = pd.read_sql(db_sql.SQL_SELECT_ALL_FROM_CASH_FLOW_ANNUALLY, con=connection,
                                        params={"id_symbol_meta": id_symbol_meta})
    df_income_statement_quarterly = pd.read_sql(db_sql.SQL_SELECT_ALL_FROM_INCOME_STATEMENT_QUARTERLY, con=connection,
                                                params={"id_symbol_meta": id_symbol_meta})
    df_income_statement_annually = pd.read_sql(db_sql.SQL_SELECT_ALL_FROM_INCOME_STATEMENT_ANNUALLY, con=connection,
                                               params={"id_symbol_meta": id_symbol_meta})
    connection.close()

    assert df_symbol_sector.shape[0] == 0
    assert df_earnings_quarterly.shape[0] == 0
    assert df_earnings_annually.shape[0] == 0
    assert df_balance_sheet_quarterly.shape[0] == 0
    assert df_balance_sheet_annually.shape[0] == 0
    assert df_cash_flow_quarterly.shape[0] == 0
    assert df_cash_flow_annually.shape[0] == 0
    assert df_income_statement_quarterly.shape[0] == 0
    assert df_income_statement_annually.shape[0] == 0

@pytest.mark.download
@pytest.mark.parametrize("time_frame, symbol_status",
                         [(download.TimeFrame.DAILY, download.SymbolStatus.ACTIVE),
                          (download.TimeFrame.DAILY, download.SymbolStatus.DELISTED),
                          (download.TimeFrame.MINUTE, download.SymbolStatus.ACTIVE),
                          (download.TimeFrame.MINUTE, download.SymbolStatus.DELISTED)])
def test_download_price_and_fundamental_data_per_symbol_2(
        setup_test: Callable, setup_and_cleanup_sqlite: Callable, setup_questdb: Callable,
        time_frame: download.TimeFrame, symbol_status: download.SymbolStatus, mocker: MockerFixture):
    # Mocking dependencies
    mocker.patch("download.download_request._API_TOKEN", "demo")
    mocker.patch("download.download._START_DATE_MINUTE_DATA", "04-01-2026")
    mocker.patch("download.download._END_DATE_MINUTE_DATA", "04-04-2026")

    insert_pre_existing_data_ending_with_day(mocker, time_frame, symbol_status)

    series_exchange_symbol = pd.Series({
        db_const.COLUMN_SYMBOL_CODE: "AAPL",
        "time_frame": time_frame.name,
        "symbol_status": symbol_status.name,
        db_const.COLUMN_SYMBOL_NAME: "Apple Inc.",
        db_const.COLUMN_COUNTRY: "USA",
        db_const.COLUMN_EXCHANGE_CODE: "NASDAQ",
        db_const.COLUMN_CURRENCY: "USD",
        db_const.COLUMN_SYMBOL_TYPE: "Common Stock",
        db_const.COLUMN_ISIN: "US0378331005"
    })
    write_mode = WriteMode.IGNORE_IF_EXIST
    download._download_price_and_fundamental_data_for_symbol(series_exchange_symbol, "US",
                                                             time_frame, symbol_status, write_mode)
    time.sleep(1)

    # Queries SQLITE data
    id_symbol_meta = get_id_of_inserted_symbol_meta_data(time_frame, symbol_status)
    assert_fundamental_data_not_inserted(id_symbol_meta)

    # Queries QuestDB data
    if time_frame == download.TimeFrame.DAILY:
        time.sleep(1)
        query_string = db_sql.SQL_SELECT_ALL_FROM_DAILY_OHLCV
        column_names = db_const.COLUMNS_DAILY_PRICE
    else:
        time.sleep(5)
        query_string = db_sql.SQL_SELECT_ALL_FROM_MINUTE_OHLCV
        column_names = db_const.COLUMNS_MINUTE_PRICE

    with pg.connect(db_const.QUESTDB_CONF_PSYCOPG, cursor_factory=pg.ClientCursor, autocommit=True) as connection:
        with connection.cursor() as cur:
            symbol_codes = ["AAPL"]
            query = sql.SQL(query_string).format(symbol_codes=sql.SQL(', ').join(map(sql.Literal, symbol_codes)))
            params: list[Any] = ["NASDAQ"]
            params.extend([datetime.now() - timedelta(days=3 * 365), datetime.now()])
            cur.execute(query, params)
            rows = cur.fetchall()
            cur.close()
            df = pd.DataFrame(rows, columns=column_names)

    assert df.shape[0] > 0
    if time_frame == download.TimeFrame.DAILY:
        assert df.at[df.index[-1], "timestamp"].date() == datetime(2026, 1, 29).date()
    else:
        assert df.at[df.index[-1], "timestamp"].date() == datetime(2026, 1, 29).date()

@pytest.mark.download
@pytest.mark.parametrize("time_frame, symbol_status",
                         [(download.TimeFrame.DAILY, download.SymbolStatus.ACTIVE),
                          (download.TimeFrame.MINUTE, download.SymbolStatus.ACTIVE)])
def test_download_price_and_fundamental_data_per_symbol_3_default(
        setup_test: Callable, setup_and_cleanup_sqlite: Callable, setup_questdb: Callable,
        time_frame: download.TimeFrame, symbol_status: download.SymbolStatus, mocker: MockerFixture):
    # Mocking dependencies
    mocker.patch("download.download_request._API_TOKEN", "demo")
    mocker.patch("download.download._START_DATE_MINUTE_DATA", "04-01-2026")
    mocker.patch("download.download._END_DATE_MINUTE_DATA", "04-04-2026")

    # Insert pre-existing data into DBs
    insert_pre_existing_data_ending_with_day(mocker, time_frame, symbol_status)

    series_exchange_symbol = pd.Series({
        db_const.COLUMN_SYMBOL_CODE: "AAPL",
        "time_frame": time_frame.name,
        "symbol_status": symbol_status.name,
        db_const.COLUMN_SYMBOL_NAME: "Apple Inc.",
        db_const.COLUMN_COUNTRY: "USA",
        db_const.COLUMN_EXCHANGE_CODE: "NASDAQ",
        db_const.COLUMN_CURRENCY: "USD",
        db_const.COLUMN_SYMBOL_TYPE: "Common Stock",
        db_const.COLUMN_ISIN: "US0378331005"
    })
    write_mode = WriteMode.APPEND_IF_EXIST
    download._download_price_and_fundamental_data_for_symbol(series_exchange_symbol, "US",
                                                             time_frame, symbol_status, write_mode)
    time.sleep(1)

    # Queries SQLITE data
    id_symbol_meta = get_id_of_inserted_symbol_meta_data(time_frame, symbol_status)
    assert_fundamental_data_inserted(id_symbol_meta=id_symbol_meta)

    # Queries QuestDB data
    if time_frame == download.TimeFrame.DAILY:
        time.sleep(1)
        query_string = db_sql.SQL_SELECT_ALL_FROM_DAILY_OHLCV
        column_names = db_const.COLUMNS_DAILY_PRICE
    else:
        time.sleep(5)
        query_string = db_sql.SQL_SELECT_ALL_FROM_MINUTE_OHLCV
        column_names = db_const.COLUMNS_MINUTE_PRICE

    with pg.connect(db_const.QUESTDB_CONF_PSYCOPG, cursor_factory=pg.ClientCursor, autocommit=True) as connection:
        with connection.cursor() as cur:
            symbol_codes = ["AAPL"]
            query = sql.SQL(query_string).format(symbol_codes=sql.SQL(', ').join(map(sql.Literal, symbol_codes)))
            params: list[Any] = ["NASDAQ"]
            params.extend([datetime.now() - timedelta(days=3 * 365), datetime.now()])
            cur.execute(query, params)
            rows = cur.fetchall()
            cur.close()
            df = pd.DataFrame(rows, columns=column_names)

    assert df.shape[0] > 0
    if time_frame == download.TimeFrame.DAILY:
        assert df.at[df.index[-1], "timestamp"].date() > datetime(2026, 1, 29).date()
        dates = df['timestamp'].dt.date.unique().tolist()
        assert datetime(2026, 1, 28).date() in dates
        assert datetime(2026, 1, 30).date() in dates
        # 31.02 and 01.02 are weekend days
        assert datetime(2026, 2, 2).date() in dates
    else:
        assert df.at[df.index[-1], "timestamp"].date() > datetime(2026, 1, 30).date()

@pytest.mark.download
@pytest.mark.parametrize("time_frame, symbol_status",
                         [(download.TimeFrame.DAILY, download.SymbolStatus.DELISTED),
                          (download.TimeFrame.MINUTE, download.SymbolStatus.DELISTED)])
def test_download_price_and_fundamental_data_per_symbol_3_empty(
        setup_test: Callable, setup_and_cleanup_sqlite: Callable, setup_questdb: Callable,
        time_frame: download.TimeFrame, symbol_status: download.SymbolStatus, mocker: MockerFixture):
    # Mocking dependencies
    mocker.patch("download.download_request._API_TOKEN", "demo")
    mocker.patch("download.download._START_DATE_MINUTE_DATA", "04-01-2026")
    mocker.patch("download.download._END_DATE_MINUTE_DATA", "04-04-2026")

    # Insert pre-existing data into DBs
    insert_pre_existing_data_ending_with_day(mocker, time_frame, symbol_status)

    response_mock = pd.DataFrame()
    if time_frame == download.TimeFrame.DAILY:
        mock_request = mocker.patch("download.download._download_daily_price_data_from_eodhd",
                                    return_value=response_mock)
    else:
        mock_request = mocker.patch("download.download._download_minute_price_data_from_eodhd",
                                    return_value=response_mock)

    series_exchange_symbol = pd.Series({
        db_const.COLUMN_SYMBOL_CODE: "AAPL",
        "time_frame": time_frame.name,
        "symbol_status": symbol_status.name,
        db_const.COLUMN_SYMBOL_NAME: "Apple Inc.",
        db_const.COLUMN_COUNTRY: "USA",
        db_const.COLUMN_EXCHANGE_CODE: "NASDAQ",
        db_const.COLUMN_CURRENCY: "USD",
        db_const.COLUMN_SYMBOL_TYPE: "Common Stock",
        db_const.COLUMN_ISIN: "US0378331005"
    })
    write_mode = WriteMode.APPEND_IF_EXIST
    download._download_price_and_fundamental_data_for_symbol(series_exchange_symbol, "US",
                                                             time_frame, symbol_status, write_mode)
    time.sleep(1)
    mock_request.assert_called_once()

    # Queries SQLITE data
    id_symbol_meta = get_id_of_inserted_symbol_meta_data(time_frame, symbol_status)
    assert id_symbol_meta

    # Queries QuestDB data
    if time_frame == download.TimeFrame.DAILY:
        time.sleep(1)
        query_string = db_sql.SQL_SELECT_ALL_FROM_DAILY_OHLCV
        column_names = db_const.COLUMNS_DAILY_PRICE
    else:
        time.sleep(5)
        query_string = db_sql.SQL_SELECT_ALL_FROM_MINUTE_OHLCV
        column_names = db_const.COLUMNS_MINUTE_PRICE

    with pg.connect(db_const.QUESTDB_CONF_PSYCOPG, cursor_factory=pg.ClientCursor, autocommit=True) as connection:
        with connection.cursor() as cur:
            symbol_codes = ["AAPL"]
            query = sql.SQL(query_string).format(symbol_codes=sql.SQL(', ').join(map(sql.Literal, symbol_codes)))
            params: list[Any] = ["NASDAQ"]
            params.extend([datetime.now() - timedelta(days=3 * 365), datetime.now()])
            cur.execute(query, params)
            rows = cur.fetchall()
            cur.close()
            df = pd.DataFrame(rows, columns=column_names)

    assert df.shape[0] > 0
    if time_frame == download.TimeFrame.DAILY:
        assert df.at[df.index[-1], "timestamp"].date() == datetime(2026, 1, 29).date()
    else:
        assert df.at[df.index[-1], "timestamp"].date() == datetime(2026, 1, 29).date()

@pytest.mark.download
@pytest.mark.parametrize("time_frame, symbol_status",
                         [(download.TimeFrame.DAILY, download.SymbolStatus.ACTIVE),
                          (download.TimeFrame.DAILY, download.SymbolStatus.DELISTED),
                          (download.TimeFrame.MINUTE, download.SymbolStatus.ACTIVE),
                          (download.TimeFrame.MINUTE, download.SymbolStatus.DELISTED)])
def test_download_price_and_fundamental_data(setup_test: Callable, setup_and_cleanup_sqlite: Callable,
                                             setup_questdb: Callable, time_frame: download.TimeFrame,
                                             symbol_status: download.SymbolStatus, mocker: MockerFixture):
    # Mocking dependencies
    mocker.patch("download.download_request._API_TOKEN", "demo")
    mocker.patch("download.download._START_DATE_MINUTE_DATA", "04-02-2026")
    mocker.patch("download.download._END_DATE_MINUTE_DATA", "11-11-2026")

    symbol_data_per_exchange = {
        "US": pd.DataFrame([{
            db_const.COLUMN_SYMBOL_CODE: "AAPL",
            "time_frame": time_frame.name,
            "symbol_status": symbol_status.name,
            db_const.COLUMN_SYMBOL_NAME: "Apple Inc.",
            db_const.COLUMN_COUNTRY: "USA",
            db_const.COLUMN_EXCHANGE_CODE: "NASDAQ",
            db_const.COLUMN_CURRENCY: "USD",
            db_const.COLUMN_SYMBOL_TYPE: "Common Stock",
            db_const.COLUMN_ISIN: "US0378331005"
        }])
    }
    write_mode = WriteMode.IGNORE_IF_EXIST
    download._download_price_and_fundamental_data(time_frame, symbol_status, symbol_data_per_exchange, write_mode)
    time.sleep(1)

    # Queries SQLITE data
    id_symbol_meta = get_id_of_inserted_symbol_meta_data(time_frame, symbol_status)
    assert_fundamental_data_inserted(id_symbol_meta=id_symbol_meta)

    if time_frame == download.TimeFrame.DAILY:
        time.sleep(1)
    else:
        time.sleep(5)

    df = db_access.select_ohlcv({"NASDAQ": ["AAPL"]}, time_frame)
    assert df.shape[0] > 0


@pytest.mark.download
@pytest.mark.parametrize("time_frame, symbol_status",
                         [(download.TimeFrame.DAILY, download.SymbolStatus.ACTIVE),
                          (download.TimeFrame.DAILY, download.SymbolStatus.DELISTED),
                          (download.TimeFrame.MINUTE, download.SymbolStatus.ACTIVE),
                          (download.TimeFrame.MINUTE, download.SymbolStatus.DELISTED)])
def test_download_for_time_frame_and_symbol_status(setup_test: Callable, setup_and_cleanup_sqlite: Callable,
                                                   setup_questdb: Callable, time_frame: download.TimeFrame,
                                                   symbol_status: download.SymbolStatus, mocker: MockerFixture):
    # Mocking dependencies
    mocker.patch("download.download_request._API_TOKEN", "demo")
    mocker.patch("download.download._START_DATE_MINUTE_DATA", "04-02-2026")
    mocker.patch("download.download._END_DATE_MINUTE_DATA", "11-11-2026")

    response_mock_1 = pd.DataFrame([{
        "Name": "USAStocks",
        "Code": "US",
        "OperatingMIC": "XNAS,XNYS",
        "Country": "USA",
        "Currency": "USD",
        "CountryISO2": "US",
        "CountryISO3": "USA"
    }])
    mock_function_1 = mocker.patch("download.download_request.request_exchanges_data_from_eodhd",
                                  return_value=response_mock_1)

    df_symbol_data = pd.DataFrame([pd.Series({
                    db_const.COLUMN_SYMBOL_CODE: "AAPL",
                    "time_frame": time_frame.name,
                    "symbol_status": symbol_status.name,
                    db_const.COLUMN_SYMBOL_NAME: "Apple Inc.",
                    db_const.COLUMN_COUNTRY: "USA",
                    db_const.COLUMN_EXCHANGE_CODE: "NASDAQ",
                    db_const.COLUMN_CURRENCY: "USD",
                    db_const.COLUMN_SYMBOL_TYPE: "Common Stock",
                    db_const.COLUMN_ISIN: "US0378331005"})])
    response_mock_2 = {"US": df_symbol_data}
    mock_function_2 = mocker.patch("download.download._download_symbol_data_per_exchange", return_value=response_mock_2)

    exchange_name = "NASDAQ"
    write_mode = WriteMode.IGNORE_IF_EXIST
    result = download._download_for_time_frame_and_symbol_status(time_frame, symbol_status, exchange_name, write_mode)

    mock_function_1.assert_called_once()
    mock_function_2.assert_called_once()
    assert result == (1, 1)

    id_symbol_meta = get_id_of_inserted_symbol_meta_data(time_frame, symbol_status)
    assert_fundamental_data_inserted(id_symbol_meta=id_symbol_meta)

    if time_frame == download.TimeFrame.DAILY:
        time.sleep(1)
    else:
        time.sleep(5)

    df = db_access.select_ohlcv({"NASDAQ": ["AAPL"]}, time_frame)
    assert df.shape[0] > 0

def prepare_test_download(mocker: MockerFixture, only_delisted_symbols = False,
                          no_us_exchange = False) -> tuple[MagicMock, MagicMock]:
    # Mocking dependencies
    mocker.patch("download.download_request._API_TOKEN", "demo")
    mocker.patch("download.download._START_DATE_MINUTE_DATA", "04-02-2026")
    mocker.patch("download.download._END_DATE_MINUTE_DATA", "11-11-2026")

    response_mock_1 = pd.DataFrame([{
        "Name": "USAStocks",
        "Code": "US",
        "OperatingMIC": "XNAS,XNYS",
        "Country": "USA",
        "Currency": "USD",
        "CountryISO2": "US",
        "CountryISO3": "USA"
    }])
    mock_function_1 = mocker.patch("download.download_request.request_exchanges_data_from_eodhd",
                                  return_value=response_mock_1)

    def side_effect_func(df_exchanges: pd.DataFrame, time_frame: download.TimeFrame,
                         symbol_status: download.SymbolStatus, exchange_name: str):
        if only_delisted_symbols:
            return {"US": pd.DataFrame()}
        elif no_us_exchange:
            return {}
        else:
            df_symbol_data = pd.DataFrame([pd.Series({
                db_const.COLUMN_SYMBOL_CODE: "AAPL",
                "time_frame": time_frame.name,
                "symbol_status": symbol_status.name,
                db_const.COLUMN_SYMBOL_NAME: "Apple Inc.",
                db_const.COLUMN_COUNTRY: "USA",
                db_const.COLUMN_EXCHANGE_CODE: "NASDAQ",
                db_const.COLUMN_CURRENCY: "USD",
                db_const.COLUMN_SYMBOL_TYPE: "Common Stock",
                db_const.COLUMN_ISIN: "US0378331005"})])
            return {"US": df_symbol_data}

    mock_function_2 = mocker.patch("download.download._download_symbol_data_per_exchange", side_effect=side_effect_func)

    return mock_function_1, mock_function_2

@pytest.mark.download
def test_download_without_flags(setup_test: Callable, setup_and_cleanup_sqlite: Callable,
                                setup_questdb: Callable, mocker: MockerFixture):
    mock_function_1, mock_function_2 = prepare_test_download(mocker)

    target_time_frame = None
    target_symbol_status = None
    target_exchange_name = None
    download.fetch(target_time_frame, target_symbol_status, target_exchange_name)

    mock_function_1.assert_called()
    mock_function_2.assert_called()

    id_symbol_meta = get_id_of_inserted_symbol_meta_data(download.TimeFrame.DAILY, download.SymbolStatus.ACTIVE)
    assert_fundamental_data_inserted(id_symbol_meta=id_symbol_meta)
    id_symbol_meta = get_id_of_inserted_symbol_meta_data(download.TimeFrame.DAILY, download.SymbolStatus.DELISTED)
    assert_fundamental_data_inserted(id_symbol_meta=id_symbol_meta)
    id_symbol_meta = get_id_of_inserted_symbol_meta_data(download.TimeFrame.MINUTE, download.SymbolStatus.ACTIVE)
    assert_fundamental_data_inserted(id_symbol_meta=id_symbol_meta)
    id_symbol_meta = get_id_of_inserted_symbol_meta_data(download.TimeFrame.MINUTE, download.SymbolStatus.DELISTED)
    assert_fundamental_data_inserted(id_symbol_meta=id_symbol_meta)

    time.sleep(5)

    df_daily = db_access.select_ohlcv({"NASDAQ": ["AAPL"]}, download.TimeFrame.DAILY)
    assert df_daily.shape[0] > 0
    df_minute = db_access.select_ohlcv({"NASDAQ": ["AAPL"]}, download.TimeFrame.MINUTE)
    assert df_minute.shape[0] > 0

@pytest.mark.download
def test_download_only_daily_data(setup_test: Callable, setup_and_cleanup_sqlite: Callable,
                                 setup_questdb: Callable, mocker: MockerFixture):
    mock_function_1, mock_function_2 = prepare_test_download(mocker)

    target_time_frame = download.TimeFrame.DAILY
    target_symbol_status = None
    target_exchange_name = None
    download.fetch(target_time_frame, target_symbol_status, target_exchange_name)

    mock_function_1.assert_called()
    mock_function_2.assert_called()

    id_symbol_meta = get_id_of_inserted_symbol_meta_data(download.TimeFrame.DAILY, download.SymbolStatus.ACTIVE)
    assert_fundamental_data_inserted(id_symbol_meta=id_symbol_meta)
    id_symbol_meta = get_id_of_inserted_symbol_meta_data(download.TimeFrame.DAILY, download.SymbolStatus.DELISTED)
    assert_fundamental_data_inserted(id_symbol_meta=id_symbol_meta)

    assert_no_insert_in_symbol_meta(download.TimeFrame.MINUTE, download.SymbolStatus.ACTIVE)
    assert_no_insert_in_symbol_meta(download.TimeFrame.MINUTE, download.SymbolStatus.DELISTED)

    time.sleep(5)

    df_daily = db_access.select_ohlcv({"NASDAQ": ["AAPL"]}, download.TimeFrame.DAILY)
    assert df_daily.shape[0] > 0
    df_minute = db_access.select_ohlcv({"NASDAQ": ["AAPL"]}, download.TimeFrame.MINUTE)
    assert df_minute.shape[0] == 0

@pytest.mark.donwload
def test_download_only_minute_data(setup_test: Callable, setup_and_cleanup_sqlite: Callable,
                                   setup_questdb: Callable, mocker: MockerFixture):
    mock_function_1, mock_function_2 = prepare_test_download(mocker)

    target_time_frame = download.TimeFrame.MINUTE
    target_symbol_status = None
    target_exchange_name = None
    download.fetch(target_time_frame, target_symbol_status, target_exchange_name)

    mock_function_1.assert_called()
    mock_function_2.assert_called()

    assert_no_insert_in_symbol_meta(download.TimeFrame.DAILY, download.SymbolStatus.ACTIVE)
    assert_no_insert_in_symbol_meta(download.TimeFrame.DAILY, download.SymbolStatus.DELISTED)

    id_symbol_meta = get_id_of_inserted_symbol_meta_data(download.TimeFrame.MINUTE, download.SymbolStatus.ACTIVE)
    assert_fundamental_data_inserted(id_symbol_meta=id_symbol_meta)
    id_symbol_meta = get_id_of_inserted_symbol_meta_data(download.TimeFrame.MINUTE, download.SymbolStatus.DELISTED)
    assert_fundamental_data_inserted(id_symbol_meta=id_symbol_meta)

    time.sleep(5)

    df_daily = db_access.select_ohlcv({"NASDAQ": ["AAPL"]}, download.TimeFrame.DAILY)
    assert df_daily.shape[0] == 0
    df_minute = db_access.select_ohlcv({"NASDAQ": ["AAPL"]}, download.TimeFrame.MINUTE)
    assert df_minute.shape[0] > 0

@pytest.mark.download
def test_download_only_active_symbols(setup_test: Callable, setup_and_cleanup_sqlite: Callable,
                                      setup_questdb: Callable, mocker: MockerFixture):
    mock_function_1, mock_function_2 = prepare_test_download(mocker)

    target_time_frame = None
    target_symbol_status = download.SymbolStatus.ACTIVE
    target_exchange_name = None
    download.fetch(target_time_frame, target_symbol_status, target_exchange_name)

    mock_function_1.assert_called()
    mock_function_2.assert_called()

    id_symbol_meta = get_id_of_inserted_symbol_meta_data(download.TimeFrame.DAILY, download.SymbolStatus.ACTIVE)
    assert_fundamental_data_inserted(id_symbol_meta=id_symbol_meta)

    assert_no_insert_in_symbol_meta(download.TimeFrame.DAILY, download.SymbolStatus.DELISTED)

    id_symbol_meta = get_id_of_inserted_symbol_meta_data(download.TimeFrame.MINUTE, download.SymbolStatus.ACTIVE)
    assert_fundamental_data_inserted(id_symbol_meta=id_symbol_meta)

    assert_no_insert_in_symbol_meta(download.TimeFrame.MINUTE, download.SymbolStatus.DELISTED)

    time.sleep(5)

    df_daily = db_access.select_ohlcv({"NASDAQ": ["AAPL"]}, download.TimeFrame.DAILY)
    assert df_daily.shape[0] > 0
    df_minute = db_access.select_ohlcv({"NASDAQ": ["AAPL"]}, download.TimeFrame.MINUTE)
    assert df_minute.shape[0] > 0

@pytest.mark.download
def test_download_only_delisted_symbols(setup_test: Callable, setup_and_cleanup_sqlite: Callable,
                                       setup_questdb: Callable, mocker: MockerFixture):
    mock_function_1, mock_function_2 = prepare_test_download(mocker, only_delisted_symbols=True)

    target_time_frame = None
    target_symbol_status = download.SymbolStatus.DELISTED
    target_exchange_name = None
    download.fetch(target_time_frame, target_symbol_status, target_exchange_name)

    mock_function_1.assert_called()
    mock_function_2.assert_called()

    assert_no_insert_in_symbol_meta(download.TimeFrame.DAILY, download.SymbolStatus.ACTIVE)
    assert_no_insert_in_symbol_meta(download.TimeFrame.DAILY, download.SymbolStatus.DELISTED)
    assert_no_insert_in_symbol_meta(download.TimeFrame.MINUTE, download.SymbolStatus.ACTIVE)
    assert_no_insert_in_symbol_meta(download.TimeFrame.MINUTE, download.SymbolStatus.DELISTED)

    time.sleep(5)

    df_daily = db_access.select_ohlcv({"NASDAQ": ["AAPL"]}, download.TimeFrame.DAILY)
    assert df_daily.shape[0] == 0
    df_minute = db_access.select_ohlcv({"NASDAQ": ["AAPL"]}, download.TimeFrame.MINUTE)
    assert df_minute.shape[0] == 0

@pytest.mark.download
def test_download_no_us_exchange(setup_test: Callable, setup_and_cleanup_sqlite: Callable,
                                 setup_questdb: Callable, mocker: MockerFixture):
    mock_function_1, mock_function_2 = prepare_test_download(mocker, no_us_exchange=True)

    target_time_frame = None
    target_symbol_status = None
    target_exchange_name = "XETRA"
    download.fetch(target_time_frame, target_symbol_status, target_exchange_name)

    mock_function_1.assert_called()
    mock_function_2.assert_called()

    assert_no_insert_in_symbol_meta(download.TimeFrame.DAILY, download.SymbolStatus.ACTIVE)
    assert_no_insert_in_symbol_meta(download.TimeFrame.DAILY, download.SymbolStatus.DELISTED)
    assert_no_insert_in_symbol_meta(download.TimeFrame.MINUTE, download.SymbolStatus.ACTIVE)
    assert_no_insert_in_symbol_meta(download.TimeFrame.MINUTE, download.SymbolStatus.DELISTED)

    time.sleep(5)

    df_daily = db_access.select_ohlcv({"NASDAQ": ["AAPL"]}, download.TimeFrame.DAILY)
    assert df_daily.shape[0] == 0
    df_minute = db_access.select_ohlcv({"NASDAQ": ["AAPL"]}, download.TimeFrame.MINUTE)
    assert df_minute.shape[0] == 0

@pytest.mark.download
def test_download_with_error_ticker_not_found(setup_test: Callable, setup_and_cleanup_sqlite: Callable,
                                              setup_questdb: Callable, mocker: MockerFixture):
    response_mock = MagicMock()
    response_mock.status_code = download_objects.ApiErrorCode.BAD_GATEWAY
    mock_function = mocker.patch("requests.get", return_value=response_mock)

    target_time_frame = None
    target_symbol_status = None
    target_exchange_name = None

    with pytest.raises(SystemExit) as pytest_wrapped_error:
        download.fetch(target_time_frame, target_symbol_status, target_exchange_name)
    assert pytest_wrapped_error.type == SystemExit
    assert pytest_wrapped_error.value.code == download_objects.ErrorCode.REQUEST_ERROR
    assert mock_function.call_count == 3

@pytest.mark.download
def test_download_with_error_unauthorized(setup_test: Callable, setup_and_cleanup_sqlite: Callable,
                                          setup_questdb: Callable, mocker: MockerFixture):
    mocker.patch("download.download_request._WAIT_TIME_IN_SECS_AFTER_REQUEST_ERROR", 1)
    response_mock = MagicMock()
    response_mock.status_code = download_objects.ApiErrorCode.UNAUTHORIZED
    mock_function = mocker.patch("requests.get", return_value=response_mock)

    target_time_frame = None
    target_symbol_status = None
    target_exchange_name = None

    with pytest.raises(SystemExit) as pytest_wrapped_error:
        download.fetch(target_time_frame, target_symbol_status, target_exchange_name)
    assert pytest_wrapped_error.type == SystemExit
    assert pytest_wrapped_error.value.code == download_objects.ErrorCode.REQUEST_ERROR
    assert mock_function.call_count == 3

@pytest.mark.download
def test_download_with_json_decode_error(setup_test: Callable, setup_and_cleanup_sqlite: Callable,
                                         setup_questdb: Callable, mocker: MockerFixture):
    mocker.patch("download.download_request._WAIT_TIME_IN_SECS_AFTER_API_ERROR", 1)
    response_mock = MagicMock()
    response_mock.status_code = 0
    response_mock.json.side_effect = JSONDecodeError("", "", 0)
    mock_function = mocker.patch("requests.get", return_value=response_mock)

    target_time_frame = None
    target_symbol_status = None
    target_exchange_name = None

    with pytest.raises(JSONDecodeError) as pytest_wrapped_error:
        download.fetch(target_time_frame, target_symbol_status, target_exchange_name)
    assert pytest_wrapped_error.type == JSONDecodeError
    assert mock_function.call_count == 1

@pytest.mark.download
def test_download_with_questdb_ingress_error(setup_test: Callable, setup_and_cleanup_sqlite: Callable,
                                             setup_questdb: Callable, mocker: MockerFixture):
    mocker.patch("db.db_access._WAIT_TIME_IN_SECS_AFTER_DB_ERROR", 1)
    mocker.patch.object(db_access, "Sender", autospec=True)
    mock_function_3 = mocker.patch("db.db_access.Sender.from_conf", side_effect=IngressError("None", "None"))
    mock_function_1, mock_function_2 = prepare_test_download(mocker)

    target_time_frame = None
    target_symbol_status = None
    target_exchange_name = None

    with pytest.raises(SystemExit) as pytest_wrapped_error:
        download.fetch(target_time_frame, target_symbol_status, target_exchange_name)
    mock_function_1.assert_called()
    mock_function_2.assert_called()
    assert pytest_wrapped_error.type == SystemExit
    assert mock_function_3.call_count == db_access._MAX_RETRIES_AFTER_DB_CONNECT_ERROR