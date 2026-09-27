
from collections.abc import Callable
import logging
import pandas as pd

from markethistorydb.db                 import Database
from markethistorydb.errors             import NoDataError
from markethistorydb.fetch.eodhd        import RequestSymbolData
from markethistorydb.utils   import TimeFrame, SymbolStatus
from markethistorydb.fetch.write        import WriteSymbolData

logger = logging.getLogger(__name__)

class DownloadSymbolData(object):
    def __init__(self, db: Database, api_token: str, time_frame: TimeFrame, symbol_status: SymbolStatus,
                 should_stop: Callable[[], bool] | None = None):
        self._api_token:           str        = api_token
        self.time_frame:           TimeFrame  = time_frame
        self.symbol_status:      SymbolStatus = symbol_status
        self._should_stop: Callable[[], bool] | None = should_stop

        self.writeSymbolData = WriteSymbolData(db, time_frame, symbol_status)

    @staticmethod
    def _print_symbol_metrics(exchange_url_code: str, number_of_symbols: int):
        logger.info("")
        logger.info("Number of symbols for exchange {0}: {1}".format(exchange_url_code, number_of_symbols))

    def _get_symbol_data(self, series_exchange_url_codes: pd.Series) -> pd.DataFrame:
        dfs_exchange_symbols: list[pd.DataFrame] = []
        symbol_data_requester = RequestSymbolData(self._api_token, self.time_frame, self.symbol_status,
                                                  self._should_stop)
        for exchange_url_code in series_exchange_url_codes:
            df_exchange_symbols = symbol_data_requester.get(exchange_url_code)
            self._print_symbol_metrics(exchange_url_code, df_exchange_symbols.shape[0])

            if not df_exchange_symbols.empty:
                df_exchange_symbols["exchange_url_code"] = exchange_url_code
                dfs_exchange_symbols.append(df_exchange_symbols)
        if not dfs_exchange_symbols:
            raise NoDataError("No symbols returned for any of the exchanges {0}".format(
                ", ".join(series_exchange_url_codes)))
        df_symbols = pd.concat(dfs_exchange_symbols)
        return df_symbols

    def run(self, series_exchange_url_codes: pd.Series) -> pd.DataFrame:
        """
        Requests the symbol list of every exchange, stores the symbols and returns them.

        :param series_exchange_url_codes: Exchange codes to request the symbol lists for
        :return: Symbols of all exchanges, each tagged with the exchange_url_code it came from
        :raises NoDataError: If none of the exchanges returned a single symbol
        :raises FetchError: If a symbol list could not be fetched
        """
        df_symbols = self._get_symbol_data(series_exchange_url_codes)
        df_symbols.apply(self.writeSymbolData.update_symbol_data, axis=1)
        return df_symbols