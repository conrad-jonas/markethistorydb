#!/usr/bin/env python12.9

"""Unit tests for download_request.py"""
from download import download_request, download_helpers

import db.db_const  as db_const

import pandas  as pd
import pytest
import requests

from collections.abc     import Callable
from datetime            import datetime, timedelta
from json                import JSONDecodeError
from pytest_mock         import MockerFixture
from unittest.mock       import MagicMock

# Redefines constants used in test object to decrease testing time duration:
# Time to wait after connection error to host occurred
download_request._WAIT_TIME_IN_SECS_AFTER_REQUEST_ERROR = 2
# Time to wait after API used up error
download_request._WAIT_TIME_IN_SECS_AFTER_API_ERROR = 2

PATH_FUNDAMENTAL_DATA_JSON = rf"test/test_request_eodhd/eodhd_fundamental_data.json"

@pytest.mark.api
def test_request_data_from_url_ticker_not_found(setup_test: Callable, mocker: MockerFixture):
    # Mocking dependencies
    response_mock = MagicMock()
    response_mock.status_code = download_request.ApiErrorCode.TICKER_NOT_FOUND
    mock_request = mocker.patch("requests.get", return_value=response_mock)

    url_api_error = "https://eodhd.com/api/intraday/AAPL.US?"
    params = {"api_token": "demo", "fmt": "json", "from": "1627896900", "to": "1630575300"}
    result = download_request._request_data_from_url(url_api_error, params)

    assert result is None
    mock_request.assert_called_once()
    assert url_api_error in mock_request.call_args[0][0]

@pytest.mark.api
def test_request_data_from_url_bad_gateway(setup_test: Callable, mocker: MockerFixture):
    # Mocking dependencies
    mocker.patch("download.download_request._WAIT_TIME_IN_SECS_AFTER_REQUEST_ERROR", 1)
    response_mock = MagicMock()
    response_mock.status_code = download_request.ApiErrorCode.BAD_GATEWAY
    mock_request = mocker.patch("requests.get", return_value=response_mock)

    with pytest.raises(SystemExit) as pytest_wrapped_error:
        url_api_error = "https://eodhd.com/api/intraday/AAPL.US?"
        params = {"api_token": "demo", "fmt": "json", "from": "1627896900", "to": "1630575300"}
        download_request._request_data_from_url(url_api_error, params)
    assert pytest_wrapped_error.type == SystemExit
    assert pytest_wrapped_error.value.code == download_request.ExitCode.MAX_NUM_OF_REQUEST_TRIES_ERROR
    assert mock_request.call_count == 3
    assert url_api_error in mock_request.call_args[0][0]

@pytest.mark.api
def test_request_data_from_url_unauthorized(setup_test: Callable, mocker: MockerFixture):
    # Mocking dependencies
    mocker.patch("download.download_request._WAIT_TIME_IN_SECS_AFTER_REQUEST_ERROR", 1)
    response_mock = MagicMock()
    response_mock.status_code = download_request.ApiErrorCode.UNAUTHORIZED
    mock_request = mocker.patch("requests.get", return_value=response_mock)

    with pytest.raises(SystemExit) as pytest_wrapped_error:
        url_api_error = "https://eodhd.com/api/intraday/AAPL.US?"
        params = {"api_token": "demo", "fmt": "json", "from": "1627896900", "to": "1630575300"}
        download_request._request_data_from_url(url_api_error, params)
    assert pytest_wrapped_error.type == SystemExit
    assert pytest_wrapped_error.value.code == download_request.ExitCode.MAX_NUM_OF_REQUEST_TRIES_ERROR
    assert mock_request.call_count == 3
    assert url_api_error in mock_request.call_args[0][0]

@pytest.mark.api
def test_request_data_from_url_other_api_error(setup_test: Callable, mocker: MockerFixture):
    # Mocking dependencies
    mocker.patch("download.download_request._WAIT_TIME_IN_SECS_AFTER_API_ERROR", 1)
    response_mock = MagicMock()
    response_mock.status_code = download_request.ApiErrorCode.DATA_LIMIT_REACHED
    mock_request = mocker.patch("requests.get", return_value=response_mock)

    with pytest.raises(SystemExit) as pytest_wrapped_error:
        url_api_error = "https://eodhd.com/api/intraday/AAPL.US?"
        params = {"api_token": "demo", "fmt": "json", "from": "1627896900", "to": "1630575300"}
        download_request._request_data_from_url(url_api_error, params)
    assert pytest_wrapped_error.type == SystemExit
    assert pytest_wrapped_error.value.code == download_request.ExitCode.MAX_NUM_OF_REQUEST_TRIES_ERROR
    assert mock_request.call_count == 3
    assert url_api_error in mock_request.call_args[0][0]

@pytest.mark.api
def test_request_data_from_url_json_error(setup_test: Callable, mocker: MockerFixture):
    # Mocking dependencies
    mocker.patch("download.download_request._WAIT_TIME_IN_SECS_AFTER_API_ERROR", 1)
    response_mock = MagicMock()
    response_mock.status_code = 0
    response_mock.json.side_effect = JSONDecodeError("", "", 0)
    mock_request = mocker.patch("requests.get", return_value=response_mock)

    with pytest.raises(JSONDecodeError) as pytest_wrapped_error:
        url_api_error = "https://eodhd.com/api/intraday/AAPL.US?"
        params = {"api_token": "demo", "fmt": "json", "from": "1627896900", "to": "1630575300"}
        download_request._request_data_from_url(url_api_error, params)
    assert pytest_wrapped_error.type == JSONDecodeError
    assert mock_request.call_count == 1
    assert url_api_error in mock_request.call_args[0][0]

@pytest.mark.api
def test_request_data_from_url_success(setup_test: Callable, mocker: MockerFixture):
    # Mocking dependencies
    response_mock = MagicMock()
    response_mock.status_code = 0
    expected_response = {
        "12/25": "Christmas",
        "7/4": "Independence Day",
    }
    response_mock.json.return_value = expected_response
    mock_request = mocker.patch("requests.get", return_value=response_mock)

    url_api = "https://eodhd.com/api/intraday/AAPL.US?"
    params = {"api_token": "demo", "fmt": "json", "from": "1627896900", "to": "1630575300"}
    result = download_request._request_data_from_url(url_api, params)

    assert result == expected_response
    mock_request.assert_called_once()
    assert url_api in mock_request.call_args[0][0]

@pytest.mark.api
@pytest.mark.parametrize("time_frame", [download_request.TimeFrame.DAILY, download_request.TimeFrame.MINUTE])
def test_request_exchanges_data_from_eodhd_success(setup_test: Callable, time_frame: download_request.TimeFrame,
                                                   mocker: MockerFixture):
    # Mocking dependencies
    response_mock = [{
        "Name": "USA Stocks",
        "Code": "US",
        "OperatingMIC": "XNAS,XNYS",
        "Country": "USA",
        "Currency": "USD",
        "CountryISO2": "US",
        "CountryISO3": "USA"
        },
        {
        "Name": "London Exchange",
        "Code": "LSE",
        "OperatingMIC": "XLON",
        "Country": "UK",
        "Currency": "GBP",
        "CountryISO2": "GB",
        "CountryISO3": "GBR"
    }]
    mock_request = mocker.patch("download.download_request._request_data_from_url", return_value=response_mock)

    df = download_request.request_exchanges_data_from_eodhd(time_frame)
    assert not df.empty and df.shape[0] > 0
    mock_request.assert_called_once()

@pytest.mark.api
@pytest.mark.parametrize("time_frame", [download_request.TimeFrame.DAILY, download_request.TimeFrame.MINUTE])
def test_request_exchanges_data_from_eodhd_filtered(setup_test: Callable, time_frame: download_request.TimeFrame,
                                                    mocker: MockerFixture):
    # Mocking dependencies
    response_mock = [{
        "Name": "USAStocks",
        "Code": "US",
        "OperatingMIC": "XNAS,XNYS",
        "Country": "USA",
        "Currency": "USD",
        "CountryISO2": "US",
        "CountryISO3": "USA"
        },
        {
        "Name": "LondonExchange",
        "Code": "LSE",
        "OperatingMIC": "XLON",
        "Country": "UK",
        "Currency": "GBP",
        "CountryISO2": "GB",
        "CountryISO3": "GBR"
    }]
    mock_request = mocker.patch("download.download_request._request_data_from_url", return_value=response_mock)

    df = download_request.request_exchanges_data_from_eodhd(time_frame)
    assert df.empty
    mock_request.assert_called_once()

@pytest.mark.api
@pytest.mark.parametrize("time_frame", [download_request.TimeFrame.DAILY, download_request.TimeFrame.MINUTE])
def test_request_exchanges_data_from_eodhd_without_mock(setup_test: Callable, time_frame: download_request.TimeFrame):
    url_exchanges = "https://eodhd.com/api/exchanges-list/?"
    params = {"api_token": download_request._API_TOKEN, "fmt": "json"}
    response_exchanges = requests.get(url_exchanges, params)
    if response_exchanges.status_code in [401, 402, 403]:
        with pytest.raises(SystemExit) as pytest_wrapped_error:
            download_request.request_exchanges_data_from_eodhd(time_frame)
        assert pytest_wrapped_error.type == SystemExit
        assert pytest_wrapped_error.value.code == 3
    else:
        df = download_request.request_exchanges_data_from_eodhd(time_frame)
        assert not df.empty and df.shape[0] > 0

@pytest.mark.api
@pytest.mark.parametrize("time_frame, symbol_status",
                         [(download_request.TimeFrame.DAILY, download_request.SymbolStatus.ACTIVE),
                          (download_request.TimeFrame.DAILY, download_request.SymbolStatus.DELISTED),
                          (download_request.TimeFrame.MINUTE, download_request.SymbolStatus.ACTIVE),
                          (download_request.TimeFrame.MINUTE, download_request.SymbolStatus.DELISTED)])
def test_request_exchange_symbols_from_eodhd_success(setup_test: Callable, time_frame: download_request.TimeFrame,
                                                     symbol_status: download_request.SymbolStatus,
                                                     mocker: MockerFixture):
    # Mocking dependencies
    response_mock = [{
        "Code": "CDR",
        "Name": "CD PROJEKT SA",
        "Country": "Poland",
        "Exchange": "NASDAQ",
        "Currency": "PLN",
        "Type": "Common Stock",
        "Isin": "PLOPTTC00011"
        },
        {
        "Code": "PKN",
        "Name": "PKN Orlen SA",
        "Country": "Poland",
        "Exchange": "NASDAQ",
        "Currency": "PLN",
        "Type": "Common Stock",
        "Isin": "PLPKN0000018"
    }]
    mock_request = mocker.patch("download.download_request._request_data_from_url", return_value=response_mock)

    exchange_code = "US"
    df = download_request.request_exchange_symbols_from_eodhd(exchange_code, time_frame, symbol_status)
    mock_request.assert_called_once()

    # Verify column names
    assert (df.shape[0] > 0)
    assert df.shape[1] == len(db_const.COLUMNS_SYMBOL_META[2:])
    assert (list(download_helpers.convert_df_column_names_from_camel_to_snake_case(df)) ==
            db_const.COLUMNS_SYMBOL_META[2:])

@pytest.mark.api
@pytest.mark.parametrize("time_frame, symbol_status",
                         [(download_request.TimeFrame.DAILY, download_request.SymbolStatus.ACTIVE),
                          (download_request.TimeFrame.DAILY, download_request.SymbolStatus.DELISTED),
                          (download_request.TimeFrame.MINUTE, download_request.SymbolStatus.ACTIVE),
                          (download_request.TimeFrame.MINUTE, download_request.SymbolStatus.DELISTED)])
def test_request_exchange_symbols_from_eodhd_filtered(setup_test: Callable, time_frame: download_request.TimeFrame,
                                                      symbol_status: download_request.SymbolStatus,
                                                      mocker: MockerFixture):
    # Mocking dependencies
    response_mock = [{
        "Code": "CDR",
        "Name": "CD PROJEKT SA",
        "Country": "Poland",
        "Exchange": "WAR",
        "Currency": "PLN",
        "Type": "Common Stock",
        "Isin": "PLOPTTC00011"
        },
        {
        "Code": "PKN",
        "Name": "PKN Orlen SA",
        "Country": "Poland",
        "Exchange": "WAR",
        "Currency": "PLN",
        "Type": "Common Stock",
        "Isin": "PLPKN0000018"
    }]
    mock_request = mocker.patch("download.download_request._request_data_from_url", return_value=response_mock)

    exchange_code = "US"
    df = download_request.request_exchange_symbols_from_eodhd(exchange_code, time_frame, symbol_status)
    assert df.empty
    mock_request.assert_called_once()

@pytest.mark.api
@pytest.mark.parametrize("time_frame, symbol_status",
                         [(download_request.TimeFrame.DAILY, download_request.SymbolStatus.ACTIVE),
                          (download_request.TimeFrame.DAILY, download_request.SymbolStatus.DELISTED),
                          (download_request.TimeFrame.MINUTE, download_request.SymbolStatus.ACTIVE),
                          (download_request.TimeFrame.MINUTE, download_request.SymbolStatus.DELISTED)])
def test_request_exchange_symbols_from_eodhd_without_mock(setup_test: Callable, time_frame: download_request.TimeFrame,
                                             symbol_status: download_request.SymbolStatus):
    exchange_code = "US"
    if symbol_status == download_request.SymbolStatus.ACTIVE:
        url_exchange_symbols = "https://eodhd.com/api/exchange-symbol-list/{0}?".format(exchange_code)
        params = {"api_token": download_request._API_TOKEN, "fmt": "json"}
    else:
        url_exchange_symbols = "https://eodhd.com/api/exchange-symbol-list/{0}?".format(exchange_code)
        params = {"api_token": download_request._API_TOKEN, "fmt": "json", "delisted": "1"}

    response_exchange_symbols = requests.get(url_exchange_symbols, params)
    if response_exchange_symbols.status_code in [401, 402, 403]:
        with pytest.raises(SystemExit) as pytest_wrapped_error:
            download_request.request_exchange_symbols_from_eodhd(exchange_code, time_frame, symbol_status)
        assert pytest_wrapped_error.type == SystemExit
        assert pytest_wrapped_error.value.code == 3
    else:
        df = download_request.request_exchange_symbols_from_eodhd(exchange_code, time_frame, symbol_status)
        assert df.shape[0] > 0
        assert df.shape[1] == len(db_const.COLUMNS_SYMBOL_META[2:])
        assert (list(download_helpers.convert_df_column_names_from_camel_to_snake_case(df)) ==
                db_const.COLUMNS_SYMBOL_META[2:])

@pytest.mark.api
@pytest.mark.parametrize("time_frame", [download_request.TimeFrame.DAILY, download_request.TimeFrame.MINUTE])
def test_request_price_data_from_eodhd_success(setup_test: Callable, time_frame: download_request.TimeFrame,
                                               mocker: MockerFixture):
    # Mocking dependencies
    if time_frame == download_request.TimeFrame.DAILY:
        response_mock = [{
            "date": "2023-01-03",
            "open": 110.47,
            "high": 110.8,
            "low": 104.64,
            "close": 108.1,
            "adjusted_close": 108.1,
            "volume": 231402797
            },
            {
            "date": "2023-01-04",
            "open": 109.11,
            "high": 114.59,
            "low": 107.52,
            "close": 113.64,
            "adjusted_close": 113.64,
            "volume": 180388984
            },
            {
            "date": "2023-01-05",
            "open": 110.51,
            "high": 111.75,
            "low": 107.1601,
            "close": 110.34,
            "adjusted_close": 110.34,
            "volume": 157986297
            },
            {
            "date": "2023-01-06",
            "open": 103,
            "high": 114.39,
            "low": 101.81,
            "close": 113.06,
            "adjusted_close": 113.06,
            "volume": 220911109
        }]
    else:
        response_mock = [
            {
              "timestamp": 1742895000,
              "gmtoffset": 0,
              "datetime": "2025-03-25 09:30:00",
              "open": 172.45,
              "high": 172.60,
              "low": 172.30,
              "close": 172.55,
              "volume": 120345
            },
            {
              "timestamp": 1742895060,
              "gmtoffset": 0,
              "datetime": "2025-03-25 09:31:00",
              "open": 172.55,
              "high": 172.70,
              "low": 172.50,
              "close": 172.65,
              "volume": 98560
            },
            {
              "timestamp": 1742895120,
              "gmtoffset": 0,
              "datetime": "2025-03-25 09:32:00",
              "open": 172.65,
              "high": 172.80,
              "low": 172.60,
              "close": 172.75,
              "volume": 87654
        }]
    mock_request = mocker.patch("download.download_request._request_data_from_url", return_value=response_mock)

    if time_frame == download_request.TimeFrame.DAILY:
        start_date = None
        end_date = None
    else:
        start_date = datetime(2026, 1, 1)
        end_date = datetime(2026, 1, 31)

    symbol = "AAPL"
    exchange_code = "US"
    exchange_name = "NASDAQ"
    df = download_request.request_price_data_from_eodhd(symbol, exchange_code, exchange_name, time_frame, start_date,
                                                        end_date)
    assert not df.empty and df.shape[0] > 0
    mock_request.assert_called_once()

@pytest.mark.api
def test_request_price_data_from_eodhd_no_dates(setup_test: Callable):
    time_frame = download_request.TimeFrame.MINUTE
    start_date = None
    end_date = None
    symbol = "AAPL"
    exchange_code = "US"
    exchange_name = "NASDAQ"

    with pytest.raises(ValueError) as pytest_wrapped_error:
        download_request.request_price_data_from_eodhd(symbol, exchange_code, exchange_name, time_frame, start_date,
                                                       end_date)
    assert pytest_wrapped_error.type == ValueError

@pytest.mark.api
@pytest.mark.parametrize("time_frame", [download_request.TimeFrame.DAILY, download_request.TimeFrame.MINUTE])
def test_request_price_data_from_eodhd_without_mock_1(setup_test: Callable, time_frame: download_request.TimeFrame,
                                                      mocker: MockerFixture):
    mocker.patch("download.download_request._API_TOKEN", "demo")
    symbol = "AAPL"
    exchange_code = "US"
    exchange_name = "NASDAQ"

    if time_frame == download_request.TimeFrame.DAILY:
        start_date = None
        end_date = None
    else:
        start_date = datetime(2026, 1, 5)
        end_date = datetime(2026, 2, 3)

    df = download_request.request_price_data_from_eodhd(symbol, exchange_code, exchange_name, time_frame, start_date,
                                                        end_date)
    assert (df.shape[0] > 0)
    if time_frame == download_request.TimeFrame.MINUTE:
        assert df.at[0, "timestamp"].date() == start_date.date()
        assert df.at[df.index[-1], "timestamp"].date() == end_date.date() - timedelta(days=1)

@pytest.mark.api
def test_request_price_data_from_eodhd_without_mock_2(setup_test: Callable, mocker: MockerFixture):
    mocker.patch("download.download_request._API_TOKEN", "demo")
    symbol = "AAPL"
    exchange_code = "US"
    exchange_name = "NASDAQ"
    time_frame = download_request.TimeFrame.DAILY
    start_date = datetime(2026, 1, 1)
    end_date = None

    df = download_request.request_price_data_from_eodhd(symbol, exchange_code, exchange_name, time_frame, start_date,
                                                     end_date)
    assert (df.shape[0] > 0)
    # On 2026.1.1 exchange was closed
    assert df.at[0, "datetime"].date() == start_date.date() + timedelta(days=1)

@pytest.mark.api
@pytest.mark.parametrize("time_frame", [download_request.TimeFrame.DAILY, download_request.TimeFrame.MINUTE])
def test_request_fundamental_data_from_eodhd(setup_test: Callable, time_frame: download_request.TimeFrame,
                                             mocker: MockerFixture):
    # Mocking dependencies
    mocker.patch("download.download_request._API_TOKEN", "demo")

    result = download_request.request_fundamental_data_from_eodhd("AAPL", "US")

    assert len(result) == 9
    assert isinstance(result[download_request.FundamentalType.SECTOR_AND_INDUSTRY], pd.Series)
    assert isinstance(result[download_request.FundamentalType.EARNINGS_QUARTERLY], pd.DataFrame)
    assert isinstance(result[download_request.FundamentalType.EARNINGS_ANNUALLY], pd.DataFrame)
    assert isinstance(result[download_request.FundamentalType.BALANCE_SHEET_QUARTERLY], pd.DataFrame)
    assert isinstance(result[download_request.FundamentalType.BALANCE_SHEET_ANNUALLY], pd.DataFrame)
    assert isinstance(result[download_request.FundamentalType.CASH_FLOW_QUARTERLY], pd.DataFrame)
    assert isinstance(result[download_request.FundamentalType.CASH_FLOW_ANNUALLY], pd.DataFrame)
    assert isinstance(result[download_request.FundamentalType.INCOME_STATEMENT_QUARTERLY], pd.DataFrame)
    assert isinstance(result[download_request.FundamentalType.INCOME_STATEMENT_ANNUALLY], pd.DataFrame)

    # Verify column dropping logic for Balance Sheet
    df_balance_sheet = result[download_request.FundamentalType.BALANCE_SHEET_QUARTERLY]
    assert "preferredStockRedeemable" not in df_balance_sheet.columns

    # Verify column dropping logic for Income Statement
    df_income_statement = result[download_request.FundamentalType.INCOME_STATEMENT_QUARTERLY]
    assert "preferredStockAndOtherAdjustments" not in df_income_statement.columns

    # Verify column names
    assert result[download_request.FundamentalType.SECTOR_AND_INDUSTRY].shape[0] == len(db_const.COLUMNS_SYMBOL_SECTOR[2:])
    df_earnings_quarterly = download_helpers.convert_df_column_names_from_camel_to_snake_case(
        result[download_request.FundamentalType.EARNINGS_QUARTERLY])
    assert list(df_earnings_quarterly) == db_const.COLUMNS_EARNINGS_QUARTERLY[2:]
    df_earnings_annually = download_helpers.convert_df_column_names_from_camel_to_snake_case(
        result[download_request.FundamentalType.EARNINGS_ANNUALLY])
    assert list(df_earnings_annually) == db_const.COLUMNS_EARNINGS_ANNUALLY[2:]
    df_balance_sheet_quarterly = download_helpers.convert_df_column_names_from_camel_to_snake_case(
        result[download_request.FundamentalType.BALANCE_SHEET_QUARTERLY])
    assert list(df_balance_sheet_quarterly) == db_const.COLUMNS_BALANCE_SHEET_QUARTERLY[2:]
    df_balance_sheet_annually = download_helpers.convert_df_column_names_from_camel_to_snake_case(
        result[download_request.FundamentalType.BALANCE_SHEET_QUARTERLY])
    assert list(df_balance_sheet_annually) == db_const.COLUMNS_BALANCE_SHEET_ANNUALLY[2:]
    df_cash_flow_quarterly = download_helpers.convert_df_column_names_from_camel_to_snake_case(
        result[download_request.FundamentalType.CASH_FLOW_QUARTERLY])
    assert list(df_cash_flow_quarterly) == db_const.COLUMNS_CASH_FLOW_QUARTERLY[2:]
    df_cash_flow_annually = download_helpers.convert_df_column_names_from_camel_to_snake_case(
        result[download_request.FundamentalType.CASH_FLOW_ANNUALLY])
    assert list(df_cash_flow_annually) == db_const.COLUMNS_CASH_FLOW_ANNUALLY[2:]
    df_income_statement_quarterly = download_helpers.convert_df_column_names_from_camel_to_snake_case(
        result[download_request.FundamentalType.INCOME_STATEMENT_QUARTERLY])
    assert list(df_income_statement_quarterly) == db_const.COLUMNS_INCOME_STATEMENT_QUARTERLY[2:]
    df_income_statement_annually = download_helpers.convert_df_column_names_from_camel_to_snake_case(
        result[download_request.FundamentalType.INCOME_STATEMENT_ANNUALLY])
    assert list(df_income_statement_annually) == db_const.COLUMNS_INCOME_STATEMENT_ANNUALLY[2:]