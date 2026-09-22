
"""Class for requesting data from provider and inserting it into DBs"""

from typing import Callable
import logging
import pandas as pd
import shutil

from markethistorydb.db                import Database
from markethistorydb.fetch.download import DownloadExchangeData, DownloadFundamentalData, DownloadPriceData, DownloadSymbolData
from markethistorydb.errors         import StorageError, UserInterruptError
from markethistorydb.utils          import TimeFrame, SymbolStatus

logger = logging.getLogger(__name__)


# Minimum amount of free storage space on disk that is demanded before proceeding with downloading data
_MIN_FREE_SPACE_IN_GB = 50
# Number of bytes in a gigabyte, used to convert disk_usage()'s byte count
_BYTES_PER_GB = 2**30


class Fetcher(object):
    def __init__(self, db: Database, api_token: str, time_frame: TimeFrame, symbol_status: SymbolStatus,
                 target_exchange_name: str | None = None, should_stop: Callable[[], bool] | None = None):
        self.time_frame:            TimeFrame = time_frame
        self.symbol_status:      SymbolStatus = symbol_status
        self.target_exchange_name: str | None = target_exchange_name

        # Polled at specific positions; returning True aborts the run with UserInterruptError
        self._should_stop: Callable[[], bool] = should_stop or (lambda: False)
        # Metric on how many symbols data has been downloaded for
        self.num_of_requested_symbols   = 0
        # Download handlers
        self._downloadExchangeData      = DownloadExchangeData(db, api_token, self.time_frame, self.target_exchange_name)
        self._downloadSymbolData        = DownloadSymbolData(db, api_token, self.time_frame, self.symbol_status)
        self._downloadPriceData         = DownloadPriceData(db, api_token, self.time_frame, self.symbol_status)
        self._downloadFundamentalData   = DownloadFundamentalData(db, api_token, self.time_frame, self.symbol_status)

    def _check_user_interrupt(self):
        if self._should_stop():
            # Caller requested to exit
            raise UserInterruptError("User interrupted process")

    @staticmethod
    def _check_storage_space():
        """Checks if disk offers enough free storage space and if not so, raises error"""
        free_space = shutil.disk_usage("/").free
        free_space_in_gb = (free_space // _BYTES_PER_GB)
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

        logger.info("Number of exchanges: {0}, Number of requested symbols {1}:".format(
            num_of_requested_exchanges, self.num_of_requested_symbols))

    def run(self):
        """Requests data from EODHD and inserts it into DB"""
        logger.info("")
        logger.info("Requests {0} data of {1} symbols from eodhd.com".format(self.time_frame.name,
                                                                              self.symbol_status.name))
        # Downloads exchange data
        series_exchange_url_codes = self._downloadExchangeData.run()
        # Downloads symbol data for every exchange
        df_symbols = self._downloadSymbolData.run(series_exchange_url_codes)
        # Downloads price and fundamental data for every symbol
        df_symbols.apply(self._download_historical_data, axis=1)
        # Update metrics
        self._update_metrics(series_exchange_url_codes, df_symbols)
