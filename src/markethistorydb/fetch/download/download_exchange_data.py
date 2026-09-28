
from collections.abc import Callable
import pandas as pd

from markethistorydb.db                import Database, tables
from markethistorydb.errors            import NoDataError
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
        """
        Requests the exchange list, stores every exchange kept by the target filter and returns
        their codes.

        :return: Exchange codes of the stored exchanges
        :raises NoDataError: If no exchange is left, either because the provider lists none of
            the exchanges supported for the time frame or because none matches
            target_exchange_name
        :raises FetchError: If the exchange list could not be fetched
        """
        df_exchanges = self._get_exchange_data()
        if df_exchanges.empty:
            message_exchange_not_listed = ("Exchange '{0}' is not listed for {1} data".format(
                self.target_exchange_name, self.time_frame.name))
            message_no_supported_exchanges = ("Provider lists none of the supported {0} exchanges".format(
                self.time_frame.name)) 
            raise NoDataError(message_exchange_not_listed if self.target_exchange_name else message_no_supported_exchanges)
        df_exchanges.apply(self.writeExchangeData.update_exchange_data, axis=1)
        return df_exchanges[tables.Exchange.Columns.EXCHANGE_CODE]