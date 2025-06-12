#!/usr/bin/env python12.9

"""Requests trading data from eodhd.com and inserts it into DB"""

import app.logger as logger

from app.db import DB_PASSWORD

import functools
import logging
import pandas    as pd
import os
import requests
import shutil
import sqlite3

from collections.abc    import Callable
from datetime           import datetime
from enum               import Enum
from os.path            import dirname, abspath
from questdb.ingress    import Sender, IngressError
from typing             import Any

# Bool whether to write only to terminal or also to log file
LOG_ONLY_TO_TERMINAL = False
# Minimum amount of free storage space on disk that is demanded before proceeding with downloading data
MIN_FREE_SPACE_IN_GB = 100
# Working directory
WORKING_DIR = dirname(dirname(abspath(__file__)))

# API token for eodhd.com
API_TOKEN = "YOUR_API_TOKEN"
# Config string http
CONF_HTTP = "http::addr=localhost:9000;username=admin;password={0};".format(DB_PASSWORD)

# Exchanges to download daily and intraday data from
EXCHANGES_EOD    = ["USA Stocks", "London Exchange", "Toronto Exchange", "XETRA Stock Exchange",
                    "Shanghai Stock Exchange", "FOREX", "Cryptocurrencies",
                    "Government Bonds"]
EXCHANGES_MINUTE = ["USA Stocks", "FOREX", "Cryptocurrencies"]
# US exchanges to download daily and intraday data from
US_EXCHANGE_CODE    = "US"
US_EXCHANGES_EOD    = ["NASDAQ", "NYSE", "NYSE ARCA"]
US_EXCHANGES_MINUTE = ["NASDAQ", "NYSE"]

# EOD meta data table name
DB_TABLE_SYMBOL_META = "symbol_meta"
# EOD OHLCV table name
DB_TABLE_EOD_PRICE = "daily_ohlcv"
# Intraday OHLCV table name
DB_TABLE_MINUTE_PRICE = "minute_ohlcv"
# Query to select symbol from table symbol_meta
SQL_SELECT_SYMBOL_FROM_SYMBOL_META = """SELECT code FROM symbol_meta WHERE code=:code AND time_frame=:time_frame AND 
                                        symbol_status=:symbol_status AND name=:name"""

class ApiErrorCode(Enum):
    """Describes error codes from eodhd.com API"""
    DATA_LIMIT_REACHED  = 402
    NO_ACCESS_RIGHTS    = 403

class TimeFrame(Enum):
    """Describes timeframe for trading data"""
    DAILY  = 1
    MINUTE = 2

class SymbolStatus(Enum):
    """Describes status of requested"""
    ACTIVE  = 1
    DELISTED = 2

class StorageError(Exception):
    """Exception raised for API data volume being used up"""

    def __init__(self, message):
        """Inits instance"""
        super().__init__(message)
        self.message = message

    def __str__(self):
        """Returns error message"""
        return f"{self.message}"

class ApiError(Exception):
    """Exception raised for eodhd.com API related error"""

    def __init__(self, message, error_code):
        """Inits instance"""
        super().__init__(message)
        self.message = message
        self.error_code = error_code

    def __str__(self):
        """Returns error message"""
        return f"{self.message} (Error Code: {self.error_code})"

def catch_api_error(func: Callable) -> Callable:
    """Decorator to catch error that data volume for eodhd.com API is used up"""
    @functools.wraps(func)
    def wrapper_catch_api_used_up_error(*args, **kwargs) -> Any:
        """Wrapper function"""
        try:
            value = func(*args, **kwargs)
        except ApiError:
            logging.error("ApiError", exc_info=True)
            exit(1)
        return value
    return wrapper_catch_api_used_up_error

@catch_api_error
def request_exchanges_data_from_eodhd(time_frame: TimeFrame) -> pd.DataFrame:
    """Requests exchanges meta data"""
    url_exchanges = "https://eodhd.com/api/exchanges-list/?api_token={0}&fmt=json".format(API_TOKEN)

    response_exchanges = requests.get(url_exchanges)
    if response_exchanges.status_code in ApiErrorCode:
        # API used up
        raise ApiError(response_exchanges.text, response_exchanges.status_code)

    data_exchanges = response_exchanges.json()
    df_exchanges = pd.DataFrame(data_exchanges)
    if time_frame == TimeFrame.DAILY:
        df_exchanges_filtered = df_exchanges[df_exchanges["Name"].isin(EXCHANGES_EOD)]
    else:
        df_exchanges_filtered = df_exchanges[df_exchanges["Name"].isin(EXCHANGES_MINUTE)]

    return df_exchanges_filtered

@catch_api_error
def request_exchange_symbols_from_eodhd(exchange_code: str, time_frame: TimeFrame,
                                        symbol_status: SymbolStatus) -> pd.DataFrame:
    """Requests exchange symbol meta data"""
    if symbol_status == SymbolStatus.ACTIVE:
        url_exchange_symbols = ("https://eodhd.com/api/exchange-symbol-list/{0}?api_token={1}&fmt=json"
                                .format(exchange_code, API_TOKEN))
    else:
        url_exchange_symbols = ("https://eodhd.com/api/exchange-symbol-list/{0}?delisted=1&api_token={1}&fmt=json"
                                .format(exchange_code, API_TOKEN))
    response_exchange_symbols = requests.get(url_exchange_symbols)
    if response_exchange_symbols.status_code in ApiErrorCode:
        # API used up
        raise ApiError(response_exchange_symbols.text, response_exchange_symbols.status_code)

    data_exchange_symbols = response_exchange_symbols.json()
    df_exchange_symbols = pd.DataFrame(data_exchange_symbols)

    if exchange_code == US_EXCHANGE_CODE and time_frame == TimeFrame.DAILY:
        df_exchange_symbols_filtered = df_exchange_symbols[df_exchange_symbols["Exchange"].isin(US_EXCHANGES_EOD)]
    elif exchange_code == US_EXCHANGE_CODE and time_frame == TimeFrame.MINUTE:
        df_exchange_symbols_filtered = df_exchange_symbols[df_exchange_symbols["Exchange"].isin(US_EXCHANGES_MINUTE)]
    else:
        df_exchange_symbols_filtered = df_exchange_symbols
    df_exchange_symbols_filtered = df_exchange_symbols_filtered.rename(
        columns={"Code": "code", "Name": "name", "Country": "country", "Exchange": "exchange", "Currency": "currency",
                 "Type": "type", "Isin": "isin"})
    df_exchange_symbols_filtered.insert(1, "time_frame", time_frame.name)
    df_exchange_symbols_filtered.insert(2, "symbol_status", symbol_status.name)

    return df_exchange_symbols_filtered

@catch_api_error
def request_price_data_from_eodhd(symbol_code: str, exchange_code: str, exchange_name: str,
                                  time_frame: TimeFrame) -> pd.DataFrame:
    """Requests symbol data"""

    if time_frame == TimeFrame.DAILY:
        url_symbol = "https://eodhd.com/api/eod/{0}.{1}?api_token={2}&fmt=json".format(
            symbol_code, exchange_code, API_TOKEN)
    else:
        url_symbol = "https://eodhd.com/api/intraday/{0}.{1}?interval=1m&api_token={2}&fmt=json".format(
            symbol_code, exchange_code, API_TOKEN)

    response_symbol = requests.get(url_symbol)
    if response_symbol.status_code in ApiErrorCode:
        # API used up
        raise ApiError(response_symbol.text, response_symbol.status_code)
    data_symbol = response_symbol.json()

    # Creates and formats df
    if data_symbol:
        df_symbol = pd.DataFrame(data_symbol)
        df_symbol.insert(0, "exchange_code", exchange_name)
        df_symbol.insert(1, "symbol_code", symbol_code)

        if time_frame == TimeFrame.MINUTE:
            df_symbol = df_symbol.rename(columns={"gmtoffset": "gmt_offset"})
            df_symbol["timestamp"] = pd.to_datetime(df_symbol["timestamp"], unit='s')
            df_symbol = df_symbol.drop("datetime", axis=1)
        else:
            df_symbol["datetime"] = pd.to_datetime(df_symbol["date"])
            df_symbol = df_symbol[df_symbol["datetime"] >= datetime.fromtimestamp(0)]
    else:
        df_symbol = pd.DataFrame()

    return df_symbol

def is_symbol_already_in_db(symbol_code: str, time_frame: TimeFrame, symbol_status: SymbolStatus,
                            symbol_name: str) -> bool:
    """Checks if symbol has been already in SQLite DB"""
    # Connects to SQLite DB
    connection = sqlite3.connect("db/sqlite.db")
    # Queries data
    df_symbol_meta = pd.read_sql(SQL_SELECT_SYMBOL_FROM_SYMBOL_META, con=connection,
                                 params={"code":symbol_code, "time_frame":time_frame.name,
                                         "symbol_status":symbol_status.name, "name":symbol_name})
    connection.close()
    # Checks if symbol exist in DB
    if df_symbol_meta.shape[0] > 0 and df_symbol_meta.at[0, "code"] == symbol_code:
        symbol_already_in_db = True
        logging.info("Symbol {0} exists already in table {1}".format(symbol_code, DB_TABLE_SYMBOL_META))
    else:
        symbol_already_in_db = False

    return symbol_already_in_db

def insert_price_data(df_eod: pd.DataFrame, time_frame: TimeFrame, symbol_code: str):
    """Insert price data into DB"""
    if time_frame == TimeFrame.DAILY:
        table_name = DB_TABLE_EOD_PRICE
        pd_time_column_name = "datetime"
    else:
        table_name = DB_TABLE_MINUTE_PRICE
        pd_time_column_name = "timestamp"

    try:
        with Sender.from_conf(CONF_HTTP) as sender:
            logging.info("Inserts {0} price records for symbol {1} into table {2}".format(
                  df_eod.shape[0], symbol_code, table_name))
            sender.dataframe(df_eod, table_name=table_name, at=pd_time_column_name)
    except IngressError as error:
        # logging.error("IngressError", exc_info=True)
        raise error

def insert_symbol_meta_data(series_exchange_symbol: pd.Series, symbol_code: str):
    """Insert price data into SQLite DB"""
    try:
        # Connects to SQLite DB
        connection = sqlite3.connect("db/sqlite.db")
        # Inserts data
        logging.info("Inserts symbol meta data for symbol {0} into table {1}".format(symbol_code,
                                                                                     DB_TABLE_SYMBOL_META))
        df_exchange_symbol = series_exchange_symbol.to_frame().T
        df_exchange_symbol.to_sql("symbol_meta", connection, if_exists="append", index=False)
        connection.commit()
        connection.close()
    except sqlite3.IntegrityError as error:
        logging.error("Symbol {0} exists already in table {1}".format(symbol_code, DB_TABLE_SYMBOL_META))
        # logging.error("sqlite3.IntegrityError", exc_info=True)
        raise error

def check_storage_space():
    """Checks if disk offers enough free storage space and if not so, raises error"""
    free_space = shutil.disk_usage("/")[2]
    free_space_in_gb = (free_space // (2**30))
    if free_space_in_gb < MIN_FREE_SPACE_IN_GB:
        raise StorageError("Not enough free disk storage space available (less than {0} GB)".format(
                           MIN_FREE_SPACE_IN_GB))

def request_and_insert_price_data_from_eodhd(time_frame: TimeFrame, symbol_status: SymbolStatus = SymbolStatus.ACTIVE,
                                             overwrite: bool = False) -> tuple[int, int]:
    """Requests EOD data from EODHD and inserts it into DB"""
    # Requests exchanges meta data
    df_exchanges = request_exchanges_data_from_eodhd(time_frame)
    num_of_exchanges = df_exchanges.shape[0]
    num_of_requested_symbols = 0

    for row_exchange in df_exchanges.iterrows():
        # Requests symbol meta data per exchange
        series_exchange = row_exchange[1]
        exchange_code   = series_exchange["Code"]

        df_exchange_symbols = request_exchange_symbols_from_eodhd(exchange_code, time_frame, symbol_status)
        num_of_requested_symbols += df_exchange_symbols.shape[0]
        logging.info("Number of symbols for exchange {0}: {1}".format(exchange_code, df_exchange_symbols.shape[0]))

        for row_exchange_symbol in df_exchange_symbols.iterrows():
            # Requests symbol price data
            check_storage_space()

            series_exchange_symbol = row_exchange_symbol[1]
            symbol_code            = series_exchange_symbol["code"]
            exchange_name          = series_exchange_symbol["exchange"]
            symbol_name            = series_exchange_symbol["name"]

            symbols_is_already_in_db = is_symbol_already_in_db(symbol_code, time_frame, symbol_status, symbol_name)
            logging.info("")
            if not overwrite and symbols_is_already_in_db:
                # Price data for symbol already exists and no overwrite is allowed
                logging.info("Symbol {0} of exchange {1} has already been inserted in DB".format(
                             symbol_code, exchange_name))
                continue

            # Requests symbol price data
            df_symbol = request_price_data_from_eodhd(symbol_code, exchange_code, exchange_name, time_frame)
            if df_symbol.empty:
                # No data available for timeframe and symbol status
                logging.info("No data exists for symbol {0}, time frame {1} and symbol status {1}".format(
                             symbol_code, time_frame.name, symbol_status.name))
                continue

            # Inserts symbol price and meta data
            insert_price_data(df_symbol, time_frame, symbol_code)
            if not symbols_is_already_in_db:
                insert_symbol_meta_data(series_exchange_symbol, symbol_code)
    return num_of_exchanges, num_of_requested_symbols

def request_from_eodhd():
    """Requests data from eodhd.com and inserts it into DB."""
    total_num_of_requested_symbols = 0
    for time_frame in TimeFrame:
        for symbol_status in SymbolStatus:
            logging.info("")
            logging.info("Requests {0} data of {1} symbols from eodhd.com".format(time_frame.name,
                                                                                  symbol_status.name))
            num_of_exchanges, num_of_requested_symbols = request_and_insert_price_data_from_eodhd(time_frame,
                                                                                                  symbol_status)
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


"""url_price = f'https://eodhd.com/api/eod/MCD.US?api_token=demo&fmt=json&from=2005-01-05&to=2025-01-05'
data_price = requests.get(url_price).json()
size_price = sys.getsizeof(data_price) * 0.000001

url_fundamental = (f'https://eodhd.com/api/fundamentals/AAPL.US?filter=General::Code,General,Earnings&api_token=demo'
                   f'&fmt=json&from=2005-01-05&to=2025-01-05')
data_fundamental = requests.get(url_fundamental).json()
size_fundamental = sys.getsizeof(data_fundamental) * 0.000001

print(size_price, size_price * 20 * 10000 * 2)
print(size_fundamental, size_fundamental * 20 * 10000 * 2)"""
""" 
# All exchange codes
import requests

url = f'https://eodhd.com/api/exchanges-list/?api_token=YOUR_API_TOKEN&fmt=json'
data = requests.get(url).json()

print(data)

# All XETRA tickers
import requests

url = f'https://eodhd.com/api/exchange-symbol-list/XETRA?api_token=YOUR_API_TOKEN&fmt=json'
data = requests.get(url).json()

print(data)

# All price data for given symbol (stock, etf and mutual funds) and period
import requests

url = f'https://eodhd.com/api/eod/MCD.US?from=2020-01-05&to=2020-02-10&period=d&api_token=demo&fmt=json'
data = requests.get(url).json()

print(data)

# All 1m price data for given symbol and period
import requests

url = f'https://eodhd.com/api/intraday/AAPL.US?from=2020-01-05&to=2020-02-10&interval=1m&api_token=demo&fmt=csv'
data = requests.get(url).content

print(data)

# Get earnings dates
import requests

url = f'https://eodhd.com/api/calendar/earnings?from=2018-12-02&to=2018-12-06&api_token={YOUR_API_TOKEN}&fmt=json'
data = requests.get(url).json()

print(data)

# Get splits dates
import requests

url = f'https://eodhd.com/api/calendar/splits?from=2018-12-02&to=2018-12-06&api_token={YOUR_API_TOKEN}&fmt=json'
data = requests.get(url).json()

print(data)

# Bulk exchange price for day
import requests

url = f'https://eodhd.com/api/eod-bulk-last-day/US?api_token={YOUR_API_TOKEN}&date=2010-09-21&fmt=json'
data = requests.get(url).json()

print(data)

# Bulk exchange splits data for last day
import requests

url = f'https://eodhd.com/api/eod-bulk-last-day/US?api_token={YOUR_API_TOKEN}&type=splits&fmt=json'
data = requests.get(url).json()

print(data)

# Bulk exchange dividends data for last day
import requests

url = f'https://eodhd.com/api/eod-bulk-last-day/US?api_token={YOUR_API_TOKEN}&type=dividends&fmt=json'
data = requests.get(url).json()

print(data)

# Get delisted stocks
import pandas as pd
from eodhd import APIClient
import math
from termcolor import colored as cl
import matplotlib.pyplot as plt

plt.rcParams['figure.figsize'] = (20,10)
plt.style.use('fivethirtyeight')


# API KEY ACTIVATION

api_key = '<YOUR API KEY>'
client = APIClient(api_key)
# GETTING LIST OF DELISTED STOCKS

tickers = client.get_list_of_tickers(delisted = 1, code = 'NASDAQ')
tickers_df = pd.DataFrame(tickers)

tickers_df = tickers_df.fillna('None')
tickers_df = tickers_df[tickers_df.Isin != 'None']

# get delisted price data for given stock
hist_json = client.get_eod_historical_stock_market_data(symbol = 'AVXS.US', period = 'd')
df = pd.DataFrame(hist_json)
df = df.set_index('date')
"""