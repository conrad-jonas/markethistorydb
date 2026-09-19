
import pandas as pd

from markethistorydb.db          import Database, tables
from markethistorydb.fetch.utils import FundamentalType
from markethistorydb.fetch.eodhd import ExchangeCodes, RequestFundamentalData
from markethistorydb.fetch.write import WriteFundamentalData
from markethistorydb.utils       import TimeFrame, SymbolStatus

# Exchanges for which fundamental data will be downloaded
_EXCHANGE_CODES_WITH_FUNDAMENTALS = [ExchangeCodes.NASDAQ, ExchangeCodes.NYSE]


class DownloadFundamentalData(object):
    def __init__(self, db: Database, api_token: str, time_frame: TimeFrame, symbol_status: SymbolStatus):
        self._api_token:            str       = api_token
        self.time_frame:            TimeFrame = time_frame
        self.symbol_status:      SymbolStatus = symbol_status

        self.writeFundamentalData = WriteFundamentalData(db)

    @staticmethod
    def _exchange_has_fundamental_data(exchange_code: str) -> bool:
        if exchange_code in _EXCHANGE_CODES_WITH_FUNDAMENTALS:
            return True
        return False

    def _get_fundamental_data(
            self, series_symbol: pd.Series) -> tuple[pd.Series, dict[FundamentalType, pd.DataFrame]]:
        fundamental_data_requester = RequestFundamentalData(self._api_token, self.time_frame, series_symbol)
        return fundamental_data_requester.get()

    def run(self, series_symbol: pd.Series) -> bool:
        if not self._exchange_has_fundamental_data(series_symbol[tables.Symbol.Columns.EXCHANGE_CODE]):
            return False

        series_sector_and_industry, dict_fundamental = self._get_fundamental_data(series_symbol)
        if dict_fundamental:
            self.writeFundamentalData.set_exchange_code(series_symbol[tables.Symbol.Columns.EXCHANGE_CODE])
            self.writeFundamentalData.set_symbol_code(series_symbol[tables.Symbol.Columns.SYMBOL_CODE])
            self.writeFundamentalData.update_sector_data(series_sector_and_industry)
            self.writeFundamentalData.replace_fundamental_data(dict_fundamental)
            return True
        return False