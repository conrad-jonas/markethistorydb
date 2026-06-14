
"""Class for requesting data from provider and inserting it into DBs"""

from datetime import datetime
import logging
import pandas as pd
import pynput
import shutil

from fetch.download import DownloadExchangeData, DownloadFundamentalData, DownloadPriceData, DownloadSymbolData
from fetch.errors   import StorageError, UserInterruptError
from utils          import TimeFrame, SymbolStatus


# Minimum amount of free storage space on disk that is demanded before proceeding with downloading data
_MIN_FREE_SPACE_IN_GB = 50
# Minute data gets requested from start date to end
_START_DATE_MINUTE_DATA = "01-01-2005"
_END_DATE_MINUTE_DATA = datetime.today().strftime("%d-%m-%Y")
# Minute data gets requested for the following time period in days
_NUM_OF_DAYS_PER_MINUTE_DATA_REQUEST = 120


class Fetcher(object):
    def __init__(self, time_frame: TimeFrame, symbol_status: SymbolStatus, target_exchange_name: str | None = None):
        self.time_frame:            TimeFrame = time_frame
        self.symbol_status:      SymbolStatus = symbol_status
        self.target_exchange_name: str | None = target_exchange_name

        # Flag that set to True on pressing F4 to exit script at specific position
        self._script_must_exit = False
        # Metric on how many symbols data has been downloaded for
        self.num_of_requested_symbols   = 0
        # Download handlers
        self._downloadExchangeData      = DownloadExchangeData(self.time_frame, self.target_exchange_name)
        self._downloadSymbolData        = DownloadSymbolData(self.time_frame, self.symbol_status)
        self._downloadPriceData         = DownloadPriceData(self.time_frame, self.symbol_status)
        self._downloadFundamentalData   = DownloadFundamentalData(self.time_frame, self.symbol_status)

        self._init_keyboard_listener()

    def _init_keyboard_listener(self):
        """Sets up listener to catch key press e.g. for exiting script at specific positions"""
        listener = pynput.keyboard.Listener(on_press=self._handle_on_press)
        listener.start()

    def _handle_on_press(self, key):
        if key == pynput.keyboard.Key.f4:
            self._script_must_exit = True

    def _check_user_interrupt(self):
        if self._script_must_exit:
            # User has entered key to exit script
            raise UserInterruptError("User interrupted process")

    @staticmethod
    def _check_storage_space():
        """Checks if disk offers enough free storage space and if not so, raises error"""
        free_space = shutil.disk_usage("/")[2]
        free_space_in_gb = (free_space // (2**30))
        if free_space_in_gb < _MIN_FREE_SPACE_IN_GB:
            raise StorageError("Not enough free disk storage space available (less than {0} GB)".format(
                               _MIN_FREE_SPACE_IN_GB))

    def _download_historical_data(self, series_symbol: pd.Series):
        self._check_user_interrupt()
        self._check_storage_space()
        # Requests and inserts price data
        self._downloadPriceData.run(series_symbol)
        # Requests and inserts fundamental data
        self._downloadFundamentalData.run(series_symbol)

    def _update_metrics(self, series_exchange_codes: pd.Series, df_symbols: pd.DataFrame):
        num_of_requested_exchanges = series_exchange_codes.shape if not self.target_exchange_name else 1
        self.num_of_requested_symbols = df_symbols.shape[0]

        logging.info("Number of exchanges: {0}, Number of requested symbols {1}:".format(
            num_of_requested_exchanges, self.num_of_requested_symbols))

    def run(self):
        """Requests data from EODHD and inserts it into DB"""
        logging.info("")
        logging.info("Requests {0} data of {1} symbols from eodhd.com".format(self.time_frame.name,
                                                                              self.symbol_status.name))
        # Downloads exchange data
        series_exchange_url_codes = self._downloadExchangeData.run()
        # Downloads symbol data for every exchange
        df_symbols = self._downloadSymbolData.run(series_exchange_url_codes)
        # Downloads price and fundamental data for every symbol
        df_symbols.apply(self._download_historical_data, axis=1)
        # Update metrics
        self._update_metrics(series_exchange_url_codes, df_symbols)
