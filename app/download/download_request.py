#!/usr/bin/env python12.9

"""Requests trading data from eodhd.com and inserts it into DB"""

from download.download_helpers import convert_df_column_names_from_camel_to_snake_case
from download.download_objects import (ExitCode, FundamentalType, ApiError, BadGatewayError,
                                       UnauthorizedError, ApiErrorCode, CompatibilityError)
from misc.data_types  import TimeFrame, SymbolStatus

import db.db_const  as db_const

import functools
import logging
import pandas as pd
import requests
import time

from collections.abc import Callable
from datetime        import datetime
from json            import JSONDecodeError
from typing          import Any, Union

# Maximum number of retries after API connection error occurred
_MAX_RETRIES_AFTER_API_CONNECT_ERROR = 3
# Time to wait after connection error to host occurred
_WAIT_TIME_IN_SECS_AFTER_REQUEST_ERROR = 10
# Time to wait after API used up error
_WAIT_TIME_IN_SECS_AFTER_API_ERROR = 3600

# API token for eodhd.com
_API_TOKEN = "YOUR_API_TOKEN"

# Exchanges to download daily and intraday data from
_EXCHANGE_NAMES_EOD    = ["USA Stocks", "London Exchange", "Toronto Exchange", "XETRA Stock Exchange",
                         "Shanghai Stock Exchange", "FOREX", "Cryptocurrencies",
                         "Government Bonds"]
_EXCHANGE_NAMES_MINUTE = ["USA Stocks", "FOREX", "Cryptocurrencies"]

# US exchanges to download daily and intraday data from
_US_EXCHANGE_URL_CODE     = "US"
_US_EXCHANGE_CODES_EOD    = ["NASDAQ", "NYSE", "NYSE ARCA"]
_US_EXCHANGE_CODES_MINUTE = ["NASDAQ", "NYSE"]

# Exchanges for which fundamental data will be downloaded
EXCHANGE_CODES_WITH_FUNDAMENTALS = ["NASDAQ", "NYSE"]


def _catch_download_error(func: Callable) -> Callable:
    """Decorator to catch error during download of eodhd.com data"""
    @functools.wraps(func)
    def wrapper_catch_download_error(*args, **kwargs) -> Any:
        """Wrapper function"""
        num_retries = 0
        return_value = None
        while num_retries < _MAX_RETRIES_AFTER_API_CONNECT_ERROR:
            # Retries calling function when certain errors caught
            try:
                return_value = func(*args, **kwargs)
                break
            except ApiError:
                logging.error("Exception ApiError occurred, wait 60 minutes till next try", exc_info=True)
                num_retries += 1
                time.sleep(_WAIT_TIME_IN_SECS_AFTER_API_ERROR)
            except UnauthorizedError:
                logging.error("Exception UnauthorizedError occurred")
                num_retries += 1
                time.sleep(_WAIT_TIME_IN_SECS_AFTER_REQUEST_ERROR)
            except BadGatewayError:
                logging.error("Exception BadGatewayError occurred")
                num_retries += 1
                time.sleep(_WAIT_TIME_IN_SECS_AFTER_REQUEST_ERROR)
            except requests.exceptions.Timeout:
                logging.error("Exception Timeout occurred")
                num_retries += 1
                time.sleep(_WAIT_TIME_IN_SECS_AFTER_REQUEST_ERROR)
            except requests.exceptions.ConnectionError:
                logging.error("Exception ConnectionError occurred")
                num_retries += 1
                time.sleep(_WAIT_TIME_IN_SECS_AFTER_REQUEST_ERROR)
        else:
            logging.error("Max number of retries of calling function {0} exceeded".format(func))
            exit(ExitCode.MAX_NUM_OF_REQUEST_TRIES_ERROR)
        return return_value
    return wrapper_catch_download_error

@_catch_download_error
def _request_data_from_url(url: str, params: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Requests data from URL"""
    response = requests.get(url, params=params)
    # Catches errors
    if response.status_code == ApiErrorCode.TICKER_NOT_FOUND:
        # Ticker not found error occurred
        data_request = None
    elif response.status_code == ApiErrorCode.BAD_GATEWAY:
        # Bad gateway error occurred
        raise BadGatewayError(response.text, response.status_code)
    elif response.status_code == ApiErrorCode.UNAUTHORIZED:
        # Unauthorized error occurred
        raise UnauthorizedError(response.text, response.status_code)
    elif response.status_code in ApiErrorCode:
        # API used up
        raise ApiError(response.text, response.status_code)
    else:
        try:
            data_request = response.json()
        except JSONDecodeError as error:
            logging.error("Request status '{0}' with status code {1} occurred".format(
                response.text, response.status_code))
            raise error

    return data_request

def _has_columns(df: pd.DataFrame, expected_column_names: list[str]):
    if list(df)[:len(expected_column_names)] != expected_column_names:
        return False
    return True

def _check_exchange_data(df_exchanges: pd.DataFrame):
    if not _has_columns(df_exchanges, ["Name", "Code"]):
        raise CompatibilityError("Exchange data has unexpected structure!")

def _check_symbol_data(df_exchange_symbols: pd.DataFrame):
    if not _has_columns(df_exchange_symbols, ["Code", "Name", "Country", "Exchange", "Currency", "Type", "Isin"]):
        raise CompatibilityError("Symbol data has unexpected structure!")

def _check_price_data(df_price: pd.DataFrame, time_frame: TimeFrame):
    if (time_frame == TimeFrame.MINUTE and
            not _has_columns(df_price, ["timestamp", "gmtoffset", "datetime",  "open", "high", "low", "close", "volume"])):
        raise CompatibilityError("Minute price data has unexpected structure!")
    elif (time_frame == TimeFrame.DAILY and
          not _has_columns(df_price, ["date", "open", "high", "low", "close", "adjusted_close", "volume"])):
        raise CompatibilityError("Daily price data has unexpected structure!")

def _check_fundamental_data(dict_symbol_fundamental: dict[FundamentalType, Union[pd.Series, pd.DataFrame]]):
    if not (dict_symbol_fundamental[FundamentalType.SECTOR_AND_INDUSTRY].shape[0]
            == len(db_const.COLUMNS_SYMBOL_SECTOR[2:])):
        raise CompatibilityError("Sector and industry data has unexpected structure!")

    df_earnings_quarterly = convert_df_column_names_from_camel_to_snake_case(
        dict_symbol_fundamental[FundamentalType.EARNINGS_QUARTERLY])
    if not _has_columns(df_earnings_quarterly, db_const.COLUMNS_EARNINGS_QUARTERLY[2:]):
        raise CompatibilityError("Earnings quarterly data has unexpected structure!")

    df_earnings_annually = convert_df_column_names_from_camel_to_snake_case(
        dict_symbol_fundamental[FundamentalType.EARNINGS_ANNUALLY])
    if not _has_columns(df_earnings_annually, db_const.COLUMNS_EARNINGS_ANNUALLY[2:]):
        raise CompatibilityError("Earnings annually data has unexpected structure!")

    df_balance_sheet_quarterly = convert_df_column_names_from_camel_to_snake_case(
        dict_symbol_fundamental[FundamentalType.BALANCE_SHEET_QUARTERLY])
    if not _has_columns(df_balance_sheet_quarterly, db_const.COLUMNS_BALANCE_SHEET_QUARTERLY[2:]):
        raise CompatibilityError("Balance sheet quarterly data has unexpected structure!")

    df_balance_sheet_annually = convert_df_column_names_from_camel_to_snake_case(
        dict_symbol_fundamental[FundamentalType.BALANCE_SHEET_QUARTERLY])
    if not _has_columns(df_balance_sheet_annually, db_const.COLUMNS_BALANCE_SHEET_ANNUALLY[2:]):
        raise CompatibilityError("Balance sheet annually data has unexpected structure!")

    df_cash_flow_quarterly = convert_df_column_names_from_camel_to_snake_case(
        dict_symbol_fundamental[FundamentalType.CASH_FLOW_QUARTERLY])
    if not _has_columns(df_cash_flow_quarterly, db_const.COLUMNS_CASH_FLOW_QUARTERLY[2:]):
        raise CompatibilityError("Cash flow quarterly data has unexpected structure!")

    df_cash_flow_annually = convert_df_column_names_from_camel_to_snake_case(
        dict_symbol_fundamental[FundamentalType.CASH_FLOW_ANNUALLY])
    if not _has_columns(df_cash_flow_annually, db_const.COLUMNS_CASH_FLOW_ANNUALLY[2:]):
        raise CompatibilityError("Cash flow annually data has unexpected structure!")

    df_income_statement_quarterly = convert_df_column_names_from_camel_to_snake_case(
        dict_symbol_fundamental[FundamentalType.INCOME_STATEMENT_QUARTERLY])
    if not _has_columns(df_income_statement_quarterly, db_const.COLUMNS_INCOME_STATEMENT_QUARTERLY[2:]):
        raise CompatibilityError("Income statement quarterly data has unexpected structure!")

    df_income_statement_annually = convert_df_column_names_from_camel_to_snake_case(
        dict_symbol_fundamental[FundamentalType.INCOME_STATEMENT_ANNUALLY])
    if not _has_columns(df_income_statement_annually, db_const.COLUMNS_INCOME_STATEMENT_ANNUALLY[2:]):
        raise CompatibilityError("Income statement annually data has unexpected structure!")

def request_exchanges_data_from_eodhd(time_frame: TimeFrame) -> pd.DataFrame:
    """Requests exchanges meta data"""
    url_exchanges = "https://eodhd.com/api/exchanges-list/?"
    params = {"api_token": _API_TOKEN, "fmt": "json"}
    # Requests data
    data_exchanges = _request_data_from_url(url_exchanges, params)

    # Creates and formats df
    df_exchanges = pd.DataFrame(data_exchanges)
    _check_exchange_data(df_exchanges)

    if time_frame == TimeFrame.DAILY:
        df_exchanges_filtered = df_exchanges[df_exchanges["Name"].isin(_EXCHANGE_NAMES_EOD)]
    else:
        df_exchanges_filtered = df_exchanges[df_exchanges["Name"].isin(_EXCHANGE_NAMES_MINUTE)]

    return df_exchanges_filtered

def request_exchange_symbols_from_eodhd(exchange_code: str, time_frame: TimeFrame,
                                        symbol_status: SymbolStatus) -> pd.DataFrame:
    """Requests exchange symbol meta data"""
    if symbol_status == SymbolStatus.ACTIVE:
        url_exchange_symbols = "https://eodhd.com/api/exchange-symbol-list/{0}?".format(exchange_code)
        params = {"api_token": _API_TOKEN, "fmt": "json"}
    else:
        url_exchange_symbols = "https://eodhd.com/api/exchange-symbol-list/{0}?".format(exchange_code)
        params = {"api_token": _API_TOKEN, "fmt": "json", "delisted": "1"}
    # Requests data
    data_exchange_symbols = _request_data_from_url(url_exchange_symbols, params)
    if data_exchange_symbols:
        # Creates and formats df
        df_exchange_symbols = pd.DataFrame(data_exchange_symbols)
        _check_symbol_data(df_exchange_symbols)

        if exchange_code == _US_EXCHANGE_URL_CODE and time_frame == TimeFrame.DAILY:
            df_exchange_symbols_filtered = df_exchange_symbols[df_exchange_symbols["Exchange"].isin(_US_EXCHANGE_CODES_EOD)]
        elif exchange_code == _US_EXCHANGE_URL_CODE and time_frame == TimeFrame.MINUTE:
            df_exchange_symbols_filtered = df_exchange_symbols[df_exchange_symbols["Exchange"].isin(_US_EXCHANGE_CODES_MINUTE)]
        else:
            df_exchange_symbols_filtered = df_exchange_symbols
        df_exchange_symbols_filtered = df_exchange_symbols_filtered.rename(
            columns={"Code": db_const.COLUMN_SYMBOL_CODE, "Name": db_const.COLUMN_SYMBOL_NAME,
                     "Country": db_const.COLUMN_COUNTRY, "Exchange": db_const.COLUMN_EXCHANGE_CODE,
                     "Currency": db_const.COLUMN_CURRENCY, "Type": db_const.COLUMN_SYMBOL_TYPE,
                     "Isin": db_const.COLUMN_ISIN})
        df_exchange_symbols_filtered.insert(1, "time_frame", time_frame.name)
        df_exchange_symbols_filtered.insert(2, "symbol_status", symbol_status.name)
        df_exchange_symbols_filtered = df_exchange_symbols_filtered[db_const.COLUMNS_SYMBOL_META[2:]]
    else:
        df_exchange_symbols_filtered = pd.DataFrame()

    return df_exchange_symbols_filtered

def request_price_data_from_eodhd(symbol_code: str, exchange_url_code: str, exchange_code: str, time_frame: TimeFrame,
                                  start_datetime: datetime = None, end_datetime: datetime = None) -> pd.DataFrame:
    """Requests price data for symbol"""
    if time_frame == TimeFrame.DAILY:
        if start_datetime:
            url_price = "https://eodhd.com/api/eod/{0}.{1}?".format(symbol_code, exchange_url_code)
            params = {"api_token": _API_TOKEN, "fmt": "json", "from": start_datetime}
        else:
            url_price = "https://eodhd.com/api/eod/{0}.{1}?".format(symbol_code, exchange_url_code)
            params = {"api_token": _API_TOKEN, "fmt": "json"}
    else:
        if not start_datetime or not end_datetime:
            raise ValueError
        url_price = "https://eodhd.com/api/intraday/{0}.{1}?".format(symbol_code, exchange_url_code)
        params = {"api_token": _API_TOKEN, "fmt": "json", "from": start_datetime.timestamp(),
                  "to": end_datetime.timestamp(), "interval": "1m"}
    # Requests data
    data_price = _request_data_from_url(url_price, params)
    # Creates and formats df
    if data_price:
        df_price = pd.DataFrame(data_price)
        _check_price_data(df_price, time_frame)

        df_price.insert(0, "exchange_code", exchange_code)
        df_price.insert(1, "symbol_code", symbol_code)

        if time_frame == TimeFrame.MINUTE:
            df_price = df_price.rename(columns={"gmtoffset": "gmt_offset"})
            df_price["timestamp"] = pd.to_datetime(df_price["timestamp"], unit='s')
            df_price = df_price.drop("datetime", axis=1)
        else:
            df_price["datetime"] = pd.to_datetime(df_price["date"])
            df_price = df_price.drop("date", axis=1)
            df_price = df_price[df_price["datetime"] >= datetime.fromtimestamp(0)]
    else:
        df_price = pd.DataFrame()

    return df_price

def request_fundamental_data_from_eodhd(
        symbol_code: str, exchange_url_code: str) -> dict[FundamentalType, Union[pd.Series, pd.DataFrame]]:
    """Requests fundamental data for symbol"""
    url_symbol = "https://eodhd.com/api/fundamentals/{0}.{1}?".format(symbol_code, exchange_url_code)
    filter_value = ("General::Sector,General::Industry,General::GicSector,General::GicGroup,General::GicIndustry,"
                    "General::GicSubIndustry,Earnings::History,Earnings::Annual,Financials::Balance_Sheet,"
                    "Financials::Cash_Flow,Financials::Income_Statement")
    params = {"api_token": _API_TOKEN, "fmt": "json", "filter": filter_value}
    # Requests data
    data_symbol = _request_data_from_url(url_symbol, params)

    if data_symbol:
        # Creates and formats dataframe
        series_sector_and_industry = pd.Series([data_symbol["General::Sector"], data_symbol["General::Industry"],
                                                data_symbol["General::GicSector"], data_symbol["General::GicGroup"],
                                                data_symbol["General::GicIndustry"],
                                                data_symbol["General::GicSubIndustry"]])
        dict_symbol_fundamental = {
            FundamentalType.SECTOR_AND_INDUSTRY:        series_sector_and_industry,
            FundamentalType.EARNINGS_QUARTERLY:         pd.DataFrame(data_symbol["Earnings::History"]).T,
            FundamentalType.EARNINGS_ANNUALLY:          pd.DataFrame(data_symbol["Earnings::Annual"]).T,
            FundamentalType.BALANCE_SHEET_QUARTERLY:    pd.DataFrame(data_symbol["Financials::Balance_Sheet"]["quarterly"]).T,
            FundamentalType.BALANCE_SHEET_ANNUALLY:     pd.DataFrame(data_symbol["Financials::Balance_Sheet"]["yearly"]).T,
            FundamentalType.CASH_FLOW_QUARTERLY:        pd.DataFrame(data_symbol["Financials::Cash_Flow"]["quarterly"]).T,
            FundamentalType.CASH_FLOW_ANNUALLY:         pd.DataFrame(data_symbol["Financials::Cash_Flow"]["yearly"]).T,
            FundamentalType.INCOME_STATEMENT_QUARTERLY: pd.DataFrame(data_symbol["Financials::Income_Statement"]["quarterly"]).T,
            FundamentalType.INCOME_STATEMENT_ANNUALLY:  pd.DataFrame(data_symbol["Financials::Income_Statement"]["yearly"]).T}

        # Drops unused columns
        dict_symbol_fundamental[FundamentalType.BALANCE_SHEET_QUARTERLY] =(
            dict_symbol_fundamental[FundamentalType.BALANCE_SHEET_QUARTERLY].drop("preferredStockRedeemable", axis=1))
        dict_symbol_fundamental[FundamentalType.BALANCE_SHEET_ANNUALLY] = (
            dict_symbol_fundamental[FundamentalType.BALANCE_SHEET_ANNUALLY].drop("preferredStockRedeemable", axis=1))
        dict_symbol_fundamental[FundamentalType.INCOME_STATEMENT_QUARTERLY] = (
            dict_symbol_fundamental[FundamentalType.INCOME_STATEMENT_QUARTERLY].drop("preferredStockAndOtherAdjustments", axis=1))
        dict_symbol_fundamental[FundamentalType.INCOME_STATEMENT_ANNUALLY] = (
            dict_symbol_fundamental[FundamentalType.INCOME_STATEMENT_ANNUALLY].drop("preferredStockAndOtherAdjustments", axis=1))
    else:
        dict_symbol_fundamental = {}

    _check_fundamental_data(dict_symbol_fundamental)

    return dict_symbol_fundamental