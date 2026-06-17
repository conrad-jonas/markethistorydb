
import logging
import pandas as pd

from fetch.eodhd        import RequestSymbolData
from utils.categories   import TimeFrame, SymbolStatus
from fetch.write        import WriteSymbolData

class DownloadSymbolData(object):
    def __init__(self, time_frame: TimeFrame, symbol_status: SymbolStatus):
        self.time_frame:           TimeFrame  = time_frame
        self.symbol_status:      SymbolStatus = symbol_status

        self.writeSymbolData = WriteSymbolData(time_frame, symbol_status)

    @staticmethod
    def _print_symbol_metrics(exchange_url_code: str, number_of_symbols: int):
        logging.info("")
        logging.info("Number of symbols for exchange {0}: {1}".format(exchange_url_code, number_of_symbols))

    def _get_symbol_data(self, series_exchange_url_codes: pd.Series) -> pd.DataFrame:
        dfs_exchange_symbols: list[pd.DataFrame] = []
        symbol_data_requester = RequestSymbolData(self.time_frame, self.symbol_status)
        for exchange_url_code in series_exchange_url_codes:
            df_exchange_symbols = symbol_data_requester.get(exchange_url_code)
            self._print_symbol_metrics(exchange_url_code, df_exchange_symbols.shape[0])

            if not df_exchange_symbols.empty:
                df_exchange_symbols["exchange_url_code"] = exchange_url_code
                dfs_exchange_symbols.append(df_exchange_symbols)
        df_symbols = pd.concat(dfs_exchange_symbols)
        return df_symbols

    def run(self, series_exchange_url_codes: pd.Series) -> pd.DataFrame:
        df_symbols = self._get_symbol_data(series_exchange_url_codes)
        df_symbols.apply(self.writeSymbolData.update_symbol_data, axis=1)
        return df_symbols