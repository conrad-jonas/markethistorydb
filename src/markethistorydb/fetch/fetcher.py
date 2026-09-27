
"""Class for requesting data from provider and inserting it into DBs"""

from typing import Callable
import logging
import pandas as pd
import shutil

from markethistorydb.db             import Database, tables
from markethistorydb.errors         import (AccountError, DbError, FetchError, StorageError,
                                            UserInterruptError)
from markethistorydb.fetch.download import DownloadExchangeData, DownloadFundamentalData, DownloadPriceData, DownloadSymbolData
from markethistorydb.fetch.utils    import FailedSymbol
from markethistorydb.utils          import TimeFrame, SymbolStatus

logger = logging.getLogger(__name__)


# Minimum amount of free storage space on disk that is demanded before proceeding with downloading data
_MIN_FREE_SPACE_IN_GB = 50
# Number of bytes in a gigabyte, used to convert disk_usage()'s byte count
_BYTES_PER_GB = 2**30
# Number of symbols that may fail in a row before the run is treated as broken rather than
# unlucky; without it a systemic fault burns through the whole symbol list and the API quota
_MAX_CONSECUTIVE_SYMBOL_FAILURES = 20
# Number of failed symbols named in the summary at the end of a run
_NUM_OF_FAILURES_IN_SUMMARY = 10


class Fetcher(object):
    def __init__(self, db: Database, api_token: str, time_frame: TimeFrame, symbol_status: SymbolStatus,
                 target_exchange_name: str | None = None, should_stop: Callable[[], bool] | None = None):
        self.time_frame:            TimeFrame = time_frame
        self.symbol_status:      SymbolStatus = symbol_status
        self.target_exchange_name: str | None = target_exchange_name

        # Polled at specific positions; returning True aborts the run with UserInterruptError
        self._should_stop: Callable[[], bool] = should_stop or (lambda: False)
        # Metrics on how many symbols data has been requested and downloaded for
        self.num_of_requested_symbols   = 0
        self.num_of_downloaded_symbols  = 0
        # Symbols whose download failed
        self.failed_symbols: list[FailedSymbol] = []
        # Download handlers
        self._downloadExchangeData      = DownloadExchangeData(db, api_token, self.time_frame, self.target_exchange_name,
                                                               self._should_stop)
        self._downloadSymbolData        = DownloadSymbolData(db, api_token, self.time_frame, self.symbol_status,
                                                             self._should_stop)
        self._downloadPriceData         = DownloadPriceData(db, api_token, self.time_frame, self.symbol_status,
                                                            self._should_stop)
        self._downloadFundamentalData   = DownloadFundamentalData(db, api_token, self.time_frame, self.symbol_status,
                                                                  self._should_stop)

    def _check_user_interrupt(self):
        if self._should_stop():
            # Caller requested to exit
            raise UserInterruptError("User interrupted process")

    @staticmethod
    def _check_storage_space():
        """
        Checks if disk offers enough free storage space.

        :raises StorageError: If less than _MIN_FREE_SPACE_IN_GB of free space is left
        """
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

    @staticmethod
    def _symbol_description(series_symbol: pd.Series) -> tuple[str, str]:
        return (series_symbol[tables.Symbol.Columns.SYMBOL_CODE],
                series_symbol[tables.Symbol.Columns.EXCHANGE_CODE])

    def _download_all_symbols(self, df_symbols: pd.DataFrame):
        """
        Downloads every symbol's data

        A symbol that fails is logged and recorded in failed_symbols; errors that say nothing
        about the symbol itself (interrupt, disk full, anything wrong with the account) are not
        caught here and end the run. So does a long enough streak of failures, which means the
        fault is not with the individual symbols.

        :param df_symbols: Symbols to download, one row per symbol
        :raises AccountError: If the token, the plan's data limit or its access rights are what
            failed, so that every remaining symbol would fail the same way
        :raises FetchError: If _MAX_CONSECUTIVE_SYMBOL_FAILURES symbols failed in a row
        :raises DbError: If reading from or writing to the DB failed on that many symbols
        :raises StorageError: If free disk space has run out
        :raises UserInterruptError: If should_stop returned True
        """
        consecutive_failures = 0
        for _, series_symbol in df_symbols.iterrows():
            try:
                self._download_historical_data(series_symbol)
                self.num_of_downloaded_symbols += 1
                consecutive_failures = 0
            except AccountError as error:
                # Every remaining symbol would fail the same way, so ending the run beats
                # burning the rest of the list. Not logged here: the summary names the symbol
                # and main logs the error itself.
                symbol_code, exchange_code = self._symbol_description(series_symbol)
                self.failed_symbols.append(FailedSymbol(symbol_code, exchange_code, type(error).__name__))
                raise
            except (FetchError, DbError) as error:
                symbol_code, exchange_code = self._symbol_description(series_symbol)
                # exception() already logs the error itself, so the message only names the symbol
                logger.exception("Skipping symbol {0} ({1})".format(symbol_code, exchange_code))
                self.failed_symbols.append(FailedSymbol(symbol_code, exchange_code, type(error).__name__))
                consecutive_failures += 1
                if consecutive_failures >= _MAX_CONSECUTIVE_SYMBOL_FAILURES:
                    raise FetchError(
                        "Aborting run after {0} symbols failed in a row, last one {1} ({2}): {3}".format(
                            consecutive_failures, symbol_code, exchange_code, error)) from error

    def _update_metrics(self, series_exchange_codes: pd.Series, df_symbols: pd.DataFrame):
        num_of_requested_exchanges = series_exchange_codes.shape[0] if not self.target_exchange_name else 1
        self.num_of_requested_symbols = df_symbols.shape[0]

        logger.info("Number of exchanges: {0}, Number of requested symbols: {1}".format(
            num_of_requested_exchanges, self.num_of_requested_symbols))

    def _log_summary(self):
        """Logs how the run went, so a long one leaves a record of what was skipped"""
        num_of_failures = len(self.failed_symbols)
        # Symbols the run never got to because it ended early
        num_of_not_attempted = self.num_of_requested_symbols - self.num_of_downloaded_symbols - num_of_failures
        summary = "Downloaded {0} of {1} symbols, {2} failed".format(
            self.num_of_downloaded_symbols, self.num_of_requested_symbols, num_of_failures)
        if num_of_not_attempted:
            summary += ", {0} not attempted".format(num_of_not_attempted)
        logger.info(summary)
        for failed_symbol in self.failed_symbols[:_NUM_OF_FAILURES_IN_SUMMARY]:
            logger.info("  failed: {0} ({1}) - {2}".format(
                failed_symbol.symbol_code, failed_symbol.exchange_code, failed_symbol.error_type_name))
        if num_of_failures > _NUM_OF_FAILURES_IN_SUMMARY:
            logger.info("  ... and {0} more".format(num_of_failures - _NUM_OF_FAILURES_IN_SUMMARY))

    def run(self):
        """
        Requests data from EODHD and inserts it into DB.

        A single symbol's failure only gets recorded in failed_symbols. FetchError and DbError
        from an individual symbol end the run only once _MAX_CONSECUTIVE_SYMBOL_FAILURES have
        happened in a row; the other errors below end the run as soon as they occur.

        :raises AccountError: If the token, the plan's data limit or its access rights are what
            failed
        :raises FetchError: If the exchange or symbol list could not be fetched or came back
            empty, or too many symbols failed in a row
        :raises DbError: If reading from or writing to the DB failed
        :raises StorageError: If free disk space has run out
        :raises UserInterruptError: If should_stop returned True
        """
        logger.info("")
        logger.info("Requests {0} data of {1} symbols from eodhd.com".format(self.time_frame.name,
                                                                              self.symbol_status.name))
        # Downloads exchange data
        series_exchange_url_codes = self._downloadExchangeData.run()
        # Downloads symbol data for every exchange
        df_symbols = self._downloadSymbolData.run(series_exchange_url_codes)
        # Update metrics before downloading, so that the summary is right even if the run aborts
        self._update_metrics(series_exchange_url_codes, df_symbols)
        try:
            # Downloads price and fundamental data for every symbol
            self._download_all_symbols(df_symbols)
        finally:
            self._log_summary()
