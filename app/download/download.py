#!/usr/bin/env python12.9

"""Requests trading data from eodhd.com and inserts it into DB"""
from download.download_objects import ExitCode, WriteMode, FundamentalType, StorageError, CompatibilityError
from misc.data_types           import TimeFrame, SymbolStatus

import download.download_insert  as download_insert
import download.download_request as download_request
import db.db_access as db_access
import db.db_const  as db_const
import misc.const   as const
import misc.logger  as logger

import logging
import pynput
import os
import pandas as pd
import shutil

from datetime import datetime, timedelta


# Global flag that set to True on pressing F4 to exit script at specific position
_global_script_must_exit = False

# Minimum amount of free storage space on disk that is demanded before proceeding with downloading data
_MIN_FREE_SPACE_IN_GB = 50

# Minute data gets requested from start date to end
_START_DATE_MINUTE_DATA = "01-01-2005"
_END_DATE_MINUTE_DATA   = datetime.today().strftime("%d-%m-%Y")
# Minute data gets requested for the following time period in days
_NUM_OF_DAYS_PER_MINUTE_DATA_REQUEST = 120


def _script_must_exit():
    """Checks from global flag if script should exit"""
    return _global_script_must_exit

def _check_storage_space():
    """Checks if disk offers enough free storage space and if not so, raises error"""
    free_space = shutil.disk_usage("/")[2]
    free_space_in_gb = (free_space // (2**30))
    if free_space_in_gb < _MIN_FREE_SPACE_IN_GB:
        raise StorageError("Not enough free disk storage space available (less than {0} GB)".format(
                           _MIN_FREE_SPACE_IN_GB))

def _download_symbol_data_per_exchange(df_exchanges: pd.DataFrame, time_frame: TimeFrame,
                                       symbol_status: SymbolStatus = SymbolStatus.ACTIVE,
                                       exchange_name: str = None) -> dict[str, pd.DataFrame]:
    symbol_data_per_exchange: dict[str, pd.DataFrame] = {}
    for row_exchange in df_exchanges.iterrows():
        # Requests symbol meta data per exchange
        series_exchange = row_exchange[1]
        exchange_url_code = series_exchange["Code"]
        if exchange_name and series_exchange["Name"] != exchange_name:
            # if specific exchange is specified by caller, only data for this exchange will be requested
            continue
        df_exchange_symbols = download_request.request_exchange_symbols_from_eodhd(exchange_url_code, time_frame,
                                                                                   symbol_status)
        logging.info("")
        if not df_exchange_symbols.empty:
            number_of_symbols = df_exchange_symbols.shape[0]
            symbol_data_per_exchange[exchange_url_code] = df_exchange_symbols
        else:
            number_of_symbols = 0
        logging.info("Number of symbols for exchange {0}: {1}".format(exchange_url_code, number_of_symbols))
    return symbol_data_per_exchange

def _download_daily_price_data_from_eodhd(symbol_code: str, exchange_url_code: str, exchange_code: str,
                                          time_frame: TimeFrame, start_datetime: datetime | None = None) -> pd.DataFrame:
    """
    Requests and returns daily price data from eodhd.com
    """
    return download_request.request_price_data_from_eodhd(symbol_code, exchange_url_code, exchange_code, time_frame,
                                                          start_datetime)

def _get_time_periods_for_minute_data_requests(
        start_datetime: datetime | None = None) -> list[tuple[datetime, datetime]]:
    """
    Returns list of time periods (start and end datetime) for every minute data request from eodhd.com
    (minute data request are only allowed for a maximum of 120 days)
    """
    # Contains the start and end datetime for each minute data request
    minute_data_time_periods: list[tuple[datetime, datetime]] = []
    # Start datetime of request for the chronically first time period
    if start_datetime:
        request_start_datetime = start_datetime
    else:
        request_start_datetime = datetime.strptime(_START_DATE_MINUTE_DATA, "%d-%m-%Y")
    # Loops over whole time period for which minute data should be requested
    while request_start_datetime < datetime.strptime(_END_DATE_MINUTE_DATA, "%d-%m-%Y"):
        request_end_datetime = request_start_datetime + timedelta(days=_NUM_OF_DAYS_PER_MINUTE_DATA_REQUEST)
        if request_end_datetime > datetime.strptime(_END_DATE_MINUTE_DATA, "%d-%m-%Y"):
            request_end_datetime = datetime.strptime(_END_DATE_MINUTE_DATA, "%d-%m-%Y")
        minute_data_time_periods.append((request_start_datetime, request_end_datetime))
        request_start_datetime = request_end_datetime

    return minute_data_time_periods

def _download_minute_price_data_from_eodhd(symbol_code: str, exchange_url_code: str, exchange_code: str,
                                           start_datetime: datetime | None = None) -> pd.DataFrame:
    """
    Requests minute price data from eodhd.com by dividing the whole time period, for which the minute price data
    shall be obtained, into smaller time periods (because minute price data from eodhd.com can only be requested for
    max 120 days), requests the data for these smaller time periods and returns the whole merged data for the whole
    time period
    """
    # Contains the start and end datetime for each minute data request
    minute_data_time_periods: list[tuple[datetime, datetime]] = _get_time_periods_for_minute_data_requests(start_datetime)
    dfs_symbol_for_all_time_periods: list[pd.DataFrame] = []
    for start_time_period, end_time_period in minute_data_time_periods:
        dfs_symbol_for_all_time_periods.append(download_request.request_price_data_from_eodhd(
            symbol_code, exchange_url_code, exchange_code, TimeFrame.MINUTE, start_time_period, end_time_period))
    df_symbol: pd.DataFrame = pd.concat(dfs_symbol_for_all_time_periods)
    df_symbol.reset_index(drop=True, inplace=True)
    return df_symbol

def _download_price_data_into_db(symbol_code: str, exchange_url_code: str, exchange_code: str,
                                 time_frame: TimeFrame, symbol_status: SymbolStatus,
                                 start_datetime: datetime | None = None) -> bool:
    """
    Requests price data from eodhd.com and inserts it into QuestDB
    :return: True if successful else False
    """
    # Requests symbol price data
    if time_frame == TimeFrame.DAILY:
        df_symbol = _download_daily_price_data_from_eodhd(symbol_code, exchange_url_code, exchange_code,
                                                          time_frame, start_datetime)
    else:
        df_symbol = _download_minute_price_data_from_eodhd(symbol_code, exchange_url_code, exchange_code,
                                                           start_datetime)

    if df_symbol.empty:
        # No data available for timeframe and symbol status
        logging.info("No data exists for symbol {0} ({1}, {2}, {3})".format(symbol_code, exchange_code, time_frame.name,
                                                                            symbol_status.name))
        return False

    # Inserts symbol price and meta data
    download_insert.insert_price_data(df_symbol, symbol_code, exchange_code, time_frame, symbol_status)
    return True

def _check_exchange_for_fundamental_data(exchange_code: str):
    if exchange_code not in download_request.EXCHANGE_CODES_WITH_FUNDAMENTALS:
        error_msg = "Fundamental data only available for the following exchanges: {0}".format(
            ", ".join(download_request.EXCHANGE_CODES_WITH_FUNDAMENTALS))
        raise CompatibilityError(error_msg)

def _download_fundamental_data_into_db(symbol_code: str, symbol_name: str, exchange_url_code: str,
                                       exchange_code: str, time_frame: TimeFrame,
                                       symbol_status: SymbolStatus) -> bool:
    """
    Requests fundamental data from eodhd.com and inserts it into SQLite db
    """
    _check_exchange_for_fundamental_data(exchange_code)

    dict_symbol_fundamental = download_request.request_fundamental_data_from_eodhd(symbol_code, exchange_url_code)

    if dict_symbol_fundamental:
        # Inserts fundamental data
        symbol_id = db_access.get_id_from_symbol_meta(symbol_code, exchange_code, time_frame, symbol_status, symbol_name)
        download_insert.insert_symbol_sector_data(dict_symbol_fundamental[FundamentalType.SECTOR_AND_INDUSTRY], symbol_id)

        download_insert.insert_historic_fundamental_data(dict_symbol_fundamental[FundamentalType.EARNINGS_QUARTERLY],
                                                         symbol_id, db_const.TABLE_EARNINGS_QUARTERLY)
        download_insert.insert_historic_fundamental_data(dict_symbol_fundamental[FundamentalType.EARNINGS_ANNUALLY],
                                                         symbol_id, db_const.TABLE_EARNINGS_ANNUALLY)
        download_insert.insert_historic_fundamental_data(dict_symbol_fundamental[FundamentalType.BALANCE_SHEET_QUARTERLY],
                                                         symbol_id, db_const.TABLE_BALANCE_SHEET_QUARTERLY)
        download_insert.insert_historic_fundamental_data(dict_symbol_fundamental[FundamentalType.BALANCE_SHEET_ANNUALLY],
                                                         symbol_id, db_const.TABLE_BALANCE_SHEET_ANNUALLY)
        download_insert.insert_historic_fundamental_data(dict_symbol_fundamental[FundamentalType.CASH_FLOW_QUARTERLY],
                                                         symbol_id, db_const.TABLE_CASH_FLOW_QUARTERLY)
        download_insert.insert_historic_fundamental_data(dict_symbol_fundamental[FundamentalType.CASH_FLOW_ANNUALLY],
                                                         symbol_id, db_const.TABLE_CASH_FLOW_ANNUALLY)
        download_insert.insert_historic_fundamental_data(dict_symbol_fundamental[FundamentalType.INCOME_STATEMENT_QUARTERLY],
                                                         symbol_id, db_const.TABLE_INCOME_STATEMENT_QUARTERLY)
        download_insert.insert_historic_fundamental_data(dict_symbol_fundamental[FundamentalType.INCOME_STATEMENT_ANNUALLY],
                                                         symbol_id, db_const.TABLE_INCOME_STATEMENT_ANNUALLY)
        return True
    return False

def _get_start_datetime(write_mode: WriteMode, symbol_is_already_in_db: bool, symbol_code: str, exchange_code: str,
                        time_frame: TimeFrame) -> datetime | None:
    start_datetime = None
    if write_mode == WriteMode.APPEND_IF_EXIST and symbol_is_already_in_db:
        last_datetime = db_access.get_last_datetime(symbol_code, exchange_code, time_frame)
        if last_datetime:
            if time_frame == TimeFrame.DAILY:
                start_datetime = last_datetime + timedelta(days=1)
            else:
                start_datetime = last_datetime + timedelta(minutes=1)

    return start_datetime

def _download_price_and_fundamental_data_for_symbol(series_exchange_symbol: pd.Series, exchange_url_code: str,
                                                    time_frame: TimeFrame, symbol_status: SymbolStatus,
                                                    write_mode: WriteMode):
    if _script_must_exit():
        # User has entered key to exit script here
        exit(ExitCode.USER_INTERRUPT_ERROR)
    # Checks if enough free disk storage space is available
    _check_storage_space()
    # Requests symbol price data

    symbol_code = series_exchange_symbol["symbol_code"]
    exchange_code = series_exchange_symbol["exchange_code"]
    symbol_name = series_exchange_symbol["name"]
    symbol_is_already_in_db = db_access.is_already_in_symbol_meta(symbol_code, exchange_code, time_frame,
                                                                  symbol_status, symbol_name)
    if write_mode == WriteMode.IGNORE_IF_EXIST and symbol_is_already_in_db:
        # Price data for symbol already exists and no overwrite is allowed
        logging.info("""Symbol {0} ({1}, {2}, {3}) has already been inserted in DB""".format(
            symbol_code, time_frame.name, symbol_status.name, exchange_code))
    else:
        start_datetime = _get_start_datetime(write_mode, symbol_is_already_in_db, symbol_code, exchange_code, time_frame)
        if _download_price_data_into_db(symbol_code, exchange_url_code, exchange_code, time_frame,
                                        symbol_status, start_datetime):
            if not symbol_is_already_in_db:
                # Inserts meta data
                download_insert.insert_symbol_meta_data(series_exchange_symbol, symbol_code, exchange_code, time_frame,
                                                        symbol_status)
            if ((not symbol_is_already_in_db or write_mode) and
                    exchange_code in download_request.EXCHANGE_CODES_WITH_FUNDAMENTALS):
                # Requests and inserts fundamental data
                _download_fundamental_data_into_db(symbol_code, symbol_name, exchange_url_code,
                                                   exchange_code, time_frame, symbol_status)

def _download_price_and_fundamental_data(time_frame: TimeFrame, symbol_status: SymbolStatus,
                                         symbol_data_per_exchange: dict[str, pd.DataFrame],
                                         write_mode: WriteMode):
    # Loops over exchanges
    for exchange_url_code in symbol_data_per_exchange:
        df_exchange_symbols = symbol_data_per_exchange[exchange_url_code]
        # Loops over symbols of exchange
        for row_exchange_symbol in df_exchange_symbols.iterrows():
            series_exchange_symbol = row_exchange_symbol[1]
            # Requests symbol specific price and fundamental data and insert it into DBs
            _download_price_and_fundamental_data_for_symbol(series_exchange_symbol, exchange_url_code, time_frame,
                                                            symbol_status, write_mode)

def _get_metrics(df_exchanges: pd.DataFrame, symbol_data_per_exchange: dict[str, pd.DataFrame], exchange_name: str):
    num_of_exchanges = df_exchanges.shape[0] if not exchange_name else 1
    num_of_requested_symbols = sum([df.shape[0] for df in symbol_data_per_exchange.values()])
    return num_of_exchanges, num_of_requested_symbols

def _download_for_time_frame_and_symbol_status(time_frame: TimeFrame, symbol_status: SymbolStatus,
                                               exchange_name: str,
                                               write_mode: WriteMode = WriteMode.APPEND_IF_EXIST) -> tuple[int, int]:
    """Requests EOD data from EODHD and inserts it into DB"""
    # Requests exchanges meta data
    df_exchanges = download_request.request_exchanges_data_from_eodhd(time_frame)
    # Requests symbol data for every exchange
    symbol_data_per_exchange: dict[str, pd.DataFrame] = _download_symbol_data_per_exchange(df_exchanges, time_frame,
                                                                                           symbol_status, exchange_name)
    # Requests price and fundamental data and inserts it into db
    _download_price_and_fundamental_data(time_frame, symbol_status, symbol_data_per_exchange, write_mode)
    # Metrics
    num_of_exchanges, num_of_requested_symbols = _get_metrics(df_exchanges, symbol_data_per_exchange, exchange_name)
    return num_of_exchanges, num_of_requested_symbols

def _download(target_time_frame: TimeFrame = None, target_symbol_status: SymbolStatus = None,
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
                _download_for_time_frame_and_symbol_status(time_frame, symbol_status, target_exchange_name))
            logging.info("Number of exchanges: {0}, Number of requested symbols {1}:".format(
                num_of_exchanges, num_of_requested_symbols))
            total_num_of_requested_symbols += num_of_requested_symbols

    logging.info("")
    logging.info("Total number of requested symbols: {0}".format(total_num_of_requested_symbols))
    return True

def _on_press(key):
    if key == pynput.keyboard.Key.f4:
        global _global_script_must_exit
        _global_script_must_exit = True

def _setup_properties():
    """Sets up options and properties for app"""
    # Sets working directory
    os.chdir(const.WORKING_DIR)
    # Sets up logger
    name_of_this_file = os.path.basename(__file__)
    log_filename = "{0}.log".format(name_of_this_file[:-3])
    logger.setup_logger(const.LOG_ONLY_TO_TERMINAL, log_filename)
    logging.info("Start {0}".format(name_of_this_file))
    logging.info("Current working directory: {0}".format(os.getcwd()))
    # Sets up listener to catch key press e.g. for exiting script at specific positions
    listener = pynput.keyboard.Listener(on_press=_on_press)
    listener.start()

def run():
    _setup_properties()
    try:
        _download()
    except StorageError:
        logging.error("StorageError", exc_info=True)
        exit(ExitCode.STORAGE_ERROR)

if __name__ == "__main__":
    run()