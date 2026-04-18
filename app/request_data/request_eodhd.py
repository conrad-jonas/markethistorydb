#!/usr/bin/env python12.9

"""Requests trading data from eodhd.com and inserts it into DB"""

from misc.const      import (WORKING_DIR,
                             LOG_ONLY_TO_TERMINAL)
from misc.data_types import (TimeFrame,
                             SymbolStatus)
from misc            import logger

import db.db_access as db_access

import functools
import logging
import pandas as pd
import os
import requests
import shutil
import time

from collections.abc import Callable
from datetime        import datetime
from enum            import IntEnum
from json            import JSONDecodeError
from typing          import Any

# Minimum amount of free storage space on disk that is demanded before proceeding with downloading data
MIN_FREE_SPACE_IN_GB = 100
# Maximum number of retries after API connection error occurred
MAX_RETRIES_AFTER_API_CONNECT_ERROR = 3
# Time to wait after connection error to host occurred
WAIT_TIME_IN_SECS_AFTER_REQUEST_ERROR = 10
# Time to wait after API used up error
WAIT_TIME_IN_SECS_AFTER_API_ERROR = 3600

# API token for eodhd.com
API_TOKEN = "YOUR_API_TOKEN"

# Exchanges to download daily and intraday data from
EXCHANGE_NAMES_EOD    = ["USA Stocks", "London Exchange", "Toronto Exchange", "XETRA Stock Exchange",
                         "Shanghai Stock Exchange", "FOREX", "Cryptocurrencies",
                         "Government Bonds"]
EXCHANGE_NAMES_MINUTE = ["USA Stocks", "FOREX", "Cryptocurrencies"]
# US exchanges to download daily and intraday data from
US_EXCHANGE_URL_CODE     = "US"
US_EXCHANGE_CODES_EOD    = ["NASDAQ", "NYSE", "NYSE ARCA"]
US_EXCHANGE_CODES_MINUTE = ["NASDAQ", "NYSE"]

class ApiErrorCode(IntEnum):
    """Describes request error codes from eodhd.com API"""
    UNAUTHORIZED       = 401
    DATA_LIMIT_REACHED = 402
    NO_ACCESS_RIGHTS   = 403
    TICKER_NOT_FOUND   = 404
    BAD_GATEWAY        = 502

class StorageError(Exception):
    """Exception raised for API data volume being used up"""
    def __init__(self, message: str):
        """Inits instance"""
        super().__init__(message)
        self.message = message

    def __str__(self):
        """Returns error message"""
        return f"{self.message}"

class RequestError(Exception):
    """Parent for request error exceptions"""
    def __init__(self, message: str, error_code: int):
        """Inits instance"""
        super().__init__(message)
        self.message = message
        self.error_code = error_code

    def __str__(self):
        """Returns error message"""
        return f"{self.message} (Error Code: {self.error_code})"

class ApiError(RequestError):
    """Exception raised for eodhd.com API related error"""
    def __init__(self, message: str, error_code: int):
        """Inits instance"""
        super().__init__(message, error_code)

class BadGatewayError(RequestError):
    """Exception raised for bad gateway while requesting data"""
    def __init__(self, message: str, error_code: int):
        """Inits instance"""
        super().__init__(message, error_code)

class UnauthorizedError(RequestError):
    """Exception raised for unauthorized access while requesting data"""
    def __init__(self, message: str, error_code: int):
        """Inits instance"""
        super().__init__(message, error_code)

def catch_download_error(func: Callable) -> Callable:
    """Decorator to catch error during download of eodhd.com data"""
    @functools.wraps(func)
    def wrapper_catch_download_error(*args, **kwargs) -> Any:
        """Wrapper function"""
        num_retries = 0
        return_value = None
        while num_retries < MAX_RETRIES_AFTER_API_CONNECT_ERROR:
            # Retries calling function when certain errors caught
            try:
                return_value = func(*args, **kwargs)
                break
            except ApiError:
                logging.error("Exception ApiError occurred, wait 60 minutes till next try", exc_info=True)
                time.sleep(WAIT_TIME_IN_SECS_AFTER_API_ERROR)
            except UnauthorizedError as error:
                logging.error("Exception UnauthorizedError occurred")
                num_retries += 1
                time.sleep(WAIT_TIME_IN_SECS_AFTER_REQUEST_ERROR)
            except BadGatewayError as error:
                logging.error("Exception BadGatewayError occurred")
                num_retries += 1
                time.sleep(WAIT_TIME_IN_SECS_AFTER_REQUEST_ERROR)
            except requests.exceptions.Timeout as error:
                logging.error("Exception Timeout occurred")
                num_retries += 1
                time.sleep(WAIT_TIME_IN_SECS_AFTER_REQUEST_ERROR)
            except requests.exceptions.ConnectionError as error:
                logging.error("Exception ConnectionError occurred")
                num_retries += 1
                time.sleep(WAIT_TIME_IN_SECS_AFTER_REQUEST_ERROR)
        else:
            logging.error("Max number of retries of calling function {0} exceeded".format(func))
            exit(1)
        return return_value
    return wrapper_catch_download_error

@catch_download_error
def request_exchanges_data_from_eodhd(time_frame: TimeFrame) -> pd.DataFrame:
    """Requests exchanges meta data"""
    url_exchanges = "https://eodhd.com/api/exchanges-list/?api_token={0}&fmt=json".format(API_TOKEN)
    # Requests data
    response_exchanges = requests.get(url_exchanges)
    if response_exchanges.status_code == ApiErrorCode.BAD_GATEWAY:
        # Bad gateway error occurred
        raise BadGatewayError(response_exchanges.text, response_exchanges.status_code)
    elif response_exchanges.status_code == ApiErrorCode.UNAUTHORIZED:
        # Unauthorized error occurred
        raise UnauthorizedError(response_exchanges.text, response_exchanges.status_code)
    elif response_exchanges.status_code in ApiErrorCode:
        # API used up
        raise ApiError(response_exchanges.text, response_exchanges.status_code)
    try:
        data_exchanges = response_exchanges.json()
    except JSONDecodeError as error:
        logging.error("Request status '{0}' with status code {1} occurred".format(
            response_exchanges.text, response_exchanges.status_code))
        raise error

    # Creates and formats df
    df_exchanges = pd.DataFrame(data_exchanges)
    if time_frame == TimeFrame.DAILY:
        df_exchanges_filtered = df_exchanges[df_exchanges["Name"].isin(EXCHANGE_NAMES_EOD)]
    else:
        df_exchanges_filtered = df_exchanges[df_exchanges["Name"].isin(EXCHANGE_NAMES_MINUTE)]

    return df_exchanges_filtered

@catch_download_error
def request_exchange_symbols_from_eodhd(exchange_code: str, time_frame: TimeFrame,
                                        symbol_status: SymbolStatus) -> pd.DataFrame:
    """Requests exchange symbol meta data"""
    if symbol_status == SymbolStatus.ACTIVE:
        url_exchange_symbols = ("https://eodhd.com/api/exchange-symbol-list/{0}?api_token={1}&fmt=json"
                                .format(exchange_code, API_TOKEN))
    else:
        url_exchange_symbols = ("https://eodhd.com/api/exchange-symbol-list/{0}?delisted=1&api_token={1}&fmt=json"
                                .format(exchange_code, API_TOKEN))
    # Requests data
    response_exchange_symbols = requests.get(url_exchange_symbols)
    if response_exchange_symbols.status_code == ApiErrorCode.BAD_GATEWAY:
        # Bad gateway error occurred
        raise BadGatewayError(response_exchange_symbols.text, response_exchange_symbols.status_code)
    elif response_exchange_symbols.status_code == ApiErrorCode.UNAUTHORIZED:
        # Unauthorized error occurred
        raise UnauthorizedError(response_exchange_symbols.text, response_exchange_symbols.status_code)
    elif response_exchange_symbols.status_code in ApiErrorCode:
        # API used up
        raise ApiError(response_exchange_symbols.text, response_exchange_symbols.status_code)
    try:
        data_exchange_symbols = response_exchange_symbols.json()
    except JSONDecodeError as error:
        logging.error("Request status '{0}' with status code {1} occurred".format(
            response_exchange_symbols.text, response_exchange_symbols.status_code))
        raise error

    # Creates and formats df
    df_exchange_symbols = pd.DataFrame(data_exchange_symbols)
    if exchange_code == US_EXCHANGE_URL_CODE and time_frame == TimeFrame.DAILY:
        df_exchange_symbols_filtered = df_exchange_symbols[df_exchange_symbols["Exchange"].isin(US_EXCHANGE_CODES_EOD)]
    elif exchange_code == US_EXCHANGE_URL_CODE and time_frame == TimeFrame.MINUTE:
        df_exchange_symbols_filtered = df_exchange_symbols[df_exchange_symbols["Exchange"].isin(US_EXCHANGE_CODES_MINUTE)]
    else:
        df_exchange_symbols_filtered = df_exchange_symbols
    df_exchange_symbols_filtered = df_exchange_symbols_filtered.rename(
        columns={"Code": "symbol_code", "Name": "name", "Country": "country", "Exchange": "exchange_code",
                 "Currency": "currency", "Type": "type", "Isin": "isin"})
    df_exchange_symbols_filtered.insert(1, "time_frame", time_frame.name)
    df_exchange_symbols_filtered.insert(2, "symbol_status", symbol_status.name)

    return df_exchange_symbols_filtered

@catch_download_error
def request_price_data_from_eodhd(symbol_code: str, exchange_url_code: str, exchange_code: str,
                                  time_frame: TimeFrame) -> pd.DataFrame:
    """Requests symbol data"""
    if time_frame == TimeFrame.DAILY:
        url_symbol = "https://eodhd.com/api/eod/{0}.{1}?api_token={2}&fmt=json".format(
            symbol_code, exchange_url_code, API_TOKEN)
    else:
        url_symbol = "https://eodhd.com/api/intraday/{0}.{1}?interval=1m&api_token={2}&fmt=json".format(
            symbol_code, exchange_url_code, API_TOKEN)

    # Requests data
    response_symbol = requests.get(url_symbol)
    if response_symbol.status_code == ApiErrorCode.TICKER_NOT_FOUND:
        # Ticker not found error occurred
        data_symbol = None
    elif response_symbol.status_code == ApiErrorCode.UNAUTHORIZED:
        # Unauthorized error occurred
        raise UnauthorizedError(response_symbol.text, response_symbol.status_code)
    elif response_symbol.status_code == ApiErrorCode.BAD_GATEWAY:
        # Bad gateway error occurred
        raise BadGatewayError(response_symbol.text, response_symbol.status_code)
    elif response_symbol.status_code in ApiErrorCode:
        # Other API error occurred
        raise ApiError(response_symbol.text, response_symbol.status_code)
    else:
        # Reads requested data as json
        try:
            data_symbol = response_symbol.json()
        except JSONDecodeError as error:
            logging.error("Request status '{0}' with status code {1} occurred".format(
                          response_symbol.text, response_symbol.status_code))
            raise error

    # Creates and formats df
    if data_symbol:
        df_symbol = pd.DataFrame(data_symbol)
        df_symbol.insert(0, "exchange_code", exchange_code)
        df_symbol.insert(1, "symbol_code", symbol_code)

        if time_frame == TimeFrame.MINUTE:
            df_symbol = df_symbol.rename(columns={"gmtoffset": "gmt_offset"})
            df_symbol["timestamp"] = pd.to_datetime(df_symbol["timestamp"], unit='s')
            df_symbol = df_symbol.drop("datetime", axis=1)
        else:
            df_symbol["datetime"] = pd.to_datetime(df_symbol["date"])
            df_symbol = df_symbol.drop("date", axis=1)
            df_symbol = df_symbol[df_symbol["datetime"] >= datetime.fromtimestamp(0)]

    else:
        df_symbol = pd.DataFrame()

    return df_symbol

def check_storage_space():
    """Checks if disk offers enough free storage space and if not so, raises error"""
    free_space = shutil.disk_usage("/")[2]
    free_space_in_gb = (free_space // (2**30))
    if free_space_in_gb < MIN_FREE_SPACE_IN_GB:
        raise StorageError("Not enough free disk storage space available (less than {0} GB)".format(
                           MIN_FREE_SPACE_IN_GB))

def request_and_insert_price_data_from_eodhd(time_frame: TimeFrame, symbol_status: SymbolStatus = SymbolStatus.ACTIVE,
                                             exchange_name: str = None, overwrite: bool = False) -> tuple[int, int]:
    """Requests EOD data from EODHD and inserts it into DB"""
    # Requests exchanges meta data
    df_exchanges = request_exchanges_data_from_eodhd(time_frame)
    if not exchange_name:
        num_of_exchanges = df_exchanges.shape[0]
    else:
        num_of_exchanges = 1
    num_of_requested_symbols = 0

    for row_exchange in df_exchanges.iterrows():
        # Requests symbol meta data per exchange
        series_exchange = row_exchange[1]
        exchange_url_code   = series_exchange["Code"]
        if exchange_name and series_exchange["Name"] != exchange_name:
            # if specific exchange is specified by caller, only data for this exchange will be requested
            continue
        df_exchange_symbols = request_exchange_symbols_from_eodhd(exchange_url_code, time_frame, symbol_status)
        num_of_requested_symbols += df_exchange_symbols.shape[0]
        logging.info("")
        logging.info("Number of symbols for exchange {0}: {1}".format(exchange_url_code, df_exchange_symbols.shape[0]))
        for row_exchange_symbol in df_exchange_symbols.iterrows():
            # Checks if enough free disk storage space is available
            check_storage_space()
            # Requests symbol price data
            series_exchange_symbol = row_exchange_symbol[1]
            symbol_code            = series_exchange_symbol["symbol_code"]
            exchange_code          = series_exchange_symbol["exchange_code"]
            symbol_name            = series_exchange_symbol["name"]
            symbols_is_already_in_db = db_access.is_already_in_symbol_meta(symbol_code, exchange_code, time_frame,
                                                                           symbol_status, symbol_name)
            if not overwrite and symbols_is_already_in_db:
                # Price data for symbol already exists and no overwrite is allowed
                logging.info("""Symbol {0} ({1}, {2}, {3}) has already been inserted in DB""".format(
                             symbol_code, time_frame.name, symbol_status.name, exchange_code))
                continue

            # Requests symbol price data
            df_symbol = request_price_data_from_eodhd(symbol_code, exchange_url_code, exchange_code, time_frame)
            if df_symbol.empty:
                # No data available for timeframe and symbol status
                logging.info("No data exists for symbol {0} ({1}, {2}, {3})".format(
                             symbol_code, exchange_code, time_frame.name, symbol_status.name))
                continue

            # Inserts symbol price and meta data
            db_access.insert_ohlcv_data(df_symbol, symbol_code, exchange_code, time_frame, symbol_status)
            if not symbols_is_already_in_db:
                db_access.insert_symbol_meta_data(series_exchange_symbol.to_frame().T, symbol_code, exchange_code,
                                                  time_frame, symbol_status)
    return num_of_exchanges, num_of_requested_symbols

def request_from_eodhd(target_time_frame: TimeFrame = None, target_symbol_status: SymbolStatus = None,
                       target_exchange_name: str = None):
    """Requests data from eodhd.com and inserts it into DB."""
    total_num_of_requested_symbols = 0
    for time_frame in TimeFrame:
        if target_time_frame and time_frame != target_time_frame:
            continue
        for symbol_status in SymbolStatus:
            if target_symbol_status and symbol_status != target_symbol_status:
                continue
            logging.info("")
            logging.info("Requests {0} data of {1} symbols from eodhd.com".format(time_frame.name,
                                                                                  symbol_status.name))
            num_of_exchanges, num_of_requested_symbols = (
                request_and_insert_price_data_from_eodhd(time_frame, symbol_status, target_exchange_name))
            logging.info("Number of exchanges: {0}, Number of requested symbols {1}:".format(
                num_of_exchanges, num_of_requested_symbols))
            total_num_of_requested_symbols += num_of_requested_symbols

    logging.info("")
    logging.info("Total number of requested symbols: {0}".format(total_num_of_requested_symbols))
    return True

def setup_properties():
    """Sets up options and properties for app"""
    # Sets working directory
    os.chdir(WORKING_DIR)
    # Sets up logger
    name_of_this_file = os.path.basename(__file__)
    log_filename = "{0}.log".format(name_of_this_file[:-3])
    logger.setup_logger(LOG_ONLY_TO_TERMINAL, log_filename)
    logging.info("Start {0}".format(name_of_this_file))
    logging.info("Current working directory: {0}".format(os.getcwd()))

if __name__ == "__main__":
    setup_properties()
    try:
        request_from_eodhd()
    except StorageError:
        logging.error("StorageError", exc_info=True)
        exit(1)