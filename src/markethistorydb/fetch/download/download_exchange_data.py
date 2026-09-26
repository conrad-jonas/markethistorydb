
from collections.abc import Callable
import pandas as pd

from markethistorydb.db                import Database, tables
from markethistorydb.fetch.eodhd       import RequestExchangeData
from markethistorydb.fetch.write       import WriteExchangeData
from markethistorydb.utils  import TimeFrame

class DownloadExchangeData(object):
    def __init__(self, db: Database, api_token: str, time_frame: TimeFrame, target_exchange_name: str | None,
                 should_stop: Callable[[], bool] | None = None):
        self._api_token:           str       = api_token
        self.time_frame:           TimeFrame = time_frame
        self.target_exchange_name: str       = target_exchange_name
        self._should_stop: Callable[[], bool] | None = should_stop

        self.writeExchangeData = WriteExchangeData(db)

    def _is_valid_exchange(self, exchange_name: str) -> bool:
        if self.target_exchange_name and exchange_name != self.target_exchange_name:
            return False
        return True

    def _get_exchange_data(self) -> pd.DataFrame:
        exchange_data_requester = RequestExchangeData(self._api_token, self.time_frame, self._should_stop)
        df_exchanges = exchange_data_requester.get()
        # Filter out unwanted exchanges
        df_exchanges = df_exchanges[df_exchanges[tables.Exchange.Columns.NAME].map(self._is_valid_exchange)]
        return df_exchanges

    def run(self) -> pd.Series:
        df_exchanges = self._get_exchange_data()
        df_exchanges.apply(self.writeExchangeData.update_exchange_data, axis=1)
        return df_exchanges[tables.Exchange.Columns.EXCHANGE_CODE]