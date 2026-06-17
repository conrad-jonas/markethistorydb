
import pandas as pd

from fetch.eodhd import RequestExchangeData
from fetch.write import WriteExchangeData
from utils.categories import TimeFrame

class DownloadExchangeData(object):
    def __init__(self, time_frame: TimeFrame, target_exchange_name: str):
        self.time_frame:           TimeFrame = time_frame
        self.target_exchange_name: str       = target_exchange_name

        self.writeExchangeData = WriteExchangeData()

    def _is_valid_exchange(self, exchange_name: str) -> bool:
        if self.target_exchange_name and exchange_name != self.target_exchange_name:
            return False
        return True

    def _get_exchange_data(self) -> pd.DataFrame:
        exchange_data_requester = RequestExchangeData(self.time_frame)
        df_exchanges = exchange_data_requester.get()
        # Filter out unwanted exchanges
        df_exchanges = df_exchanges[df_exchanges["Name"].map(self._is_valid_exchange)]
        return df_exchanges

    def run(self) -> pd.Series:
        df_exchanges = self._get_exchange_data()
        df_exchanges.apply(self.writeExchangeData.update_exchange_data, axis=1)
        return df_exchanges["Code"]