
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
import logging
import pandas as pd

from markethistorydb.db               import Database, tables
from markethistorydb.fetch.eodhd      import RequestPriceData
from markethistorydb.fetch.write      import WritePriceData
from markethistorydb.utils import TimeFrame, SymbolStatus

logger = logging.getLogger(__name__)

# Minute data gets requested from start date (midnight UTC) to end
_START_DATE_MINUTE_DATA = "01-01-2005"
# Minute data gets requested for the following time period in days
_NUM_OF_DAYS_PER_MINUTE_DATA_REQUEST = 120


class DownloadPriceData(object):
    def __init__(self, db: Database, api_token: str, time_frame: TimeFrame, symbol_status: SymbolStatus,
                 should_stop: Callable[[], bool] | None = None):
        self._api_token:            str       = api_token
        self.time_frame:            TimeFrame = time_frame
        self.symbol_status:      SymbolStatus = symbol_status
        self._should_stop: Callable[[], bool] | None = should_stop

        self.writePriceData = WritePriceData(db, time_frame, symbol_status)

    def _get_start_datetime(self, series_symbol: pd.Series) -> datetime | None:
        start_datetime = None
        last_datetime = self.writePriceData.get_last_datetime_of_price_data(series_symbol)
        if last_datetime:
            if self.time_frame == TimeFrame.DAILY:
                start_datetime = last_datetime + timedelta(days=1)
            else:
                start_datetime = last_datetime + timedelta(minutes=1)

        return start_datetime

    def _get_daily_price_data(self, series_symbol: pd.Series,
                              start_datetime: datetime | None = None) -> pd.DataFrame:
        """
        Requests daily price data from eodhd.com.

        :param series_symbol: Symbol the data is requested for
        :param start_datetime: First day to request (the provider's earliest if unset)
        :return: Daily price records
        :raises FetchError: If the request failed or the payload has an unexpected structure
        :raises UserInterruptError: If should_stop returned True while waiting to retry
        """
        price_data_requester = RequestPriceData(self._api_token, self.time_frame, series_symbol,
                                               self._should_stop)
        return price_data_requester.get(start_datetime)

    @staticmethod
    def _get_time_periods_for_minute_data_requests(
            start_datetime: datetime | None = None) -> list[tuple[datetime, datetime]]:
        """
        Splits the whole time period into the chunks a minute data request is allowed to cover
        (minute data requests are only allowed for a maximum of 120 days).

        :param start_datetime: Start of the whole time period, naive and in UTC like the stored
            timestamps (_START_DATE_MINUTE_DATA if unset)
        :return: Start and end datetime of every request, naive and in UTC, in chronological order
        """
        # Contains the start and end datetime for each minute data request
        minute_data_time_periods: list[tuple[datetime, datetime]] = []
        # End of the whole time period is the start of today in UTC, which the stored timestamps are in
        end_datetime = datetime.combine(datetime.now(UTC).date(), datetime.min.time())
        # Start datetime of request for the chronically first time period
        if start_datetime:
            request_start_datetime = start_datetime
        else:
            request_start_datetime = datetime.strptime(_START_DATE_MINUTE_DATA, "%d-%m-%Y")
        # Loops over whole time period for which minute data should be requested
        while request_start_datetime < end_datetime:
            request_end_datetime = request_start_datetime + timedelta(days=_NUM_OF_DAYS_PER_MINUTE_DATA_REQUEST)
            if request_end_datetime > end_datetime:
                request_end_datetime = end_datetime
            minute_data_time_periods.append((request_start_datetime, request_end_datetime))
            request_start_datetime = request_end_datetime

        return minute_data_time_periods

    def _get_minute_price_data(self, series_symbol: pd.Series,
                               start_datetime: datetime | None = None) -> pd.DataFrame:
        """
        Requests minute price data from eodhd.com by dividing the whole time period, for which the minute price data
        shall be obtained, into smaller time periods (because minute price data from eodhd.com can only be requested for
        max 120 days) and requesting the data for these smaller time periods.

        :param series_symbol: Symbol the data is requested for
        :param start_datetime: Start of the whole time period (_START_DATE_MINUTE_DATA if unset)
        :return: Merged minute price records for the whole time period, empty if the stored data
            is already up to date
        :raises FetchError: If one of the requests failed or a payload has an unexpected structure
        :raises UserInterruptError: If should_stop returned True while waiting to retry
        """
        # Contains the start and end datetime for each minute data request
        minute_data_time_periods: list[tuple[datetime, datetime]] = (
            self._get_time_periods_for_minute_data_requests(start_datetime))
        if not minute_data_time_periods:
            # Stored data reaches today already, so there is nothing to request
            return pd.DataFrame()

        dfs_symbol_for_all_time_periods: list[pd.DataFrame] = []
        price_data_requester = RequestPriceData(self._api_token, self.time_frame, series_symbol,
                                               self._should_stop)
        for start_time_period, end_time_period in minute_data_time_periods:
            dfs_symbol_for_all_time_periods.append(price_data_requester.get(start_time_period, end_time_period))
        df_symbol: pd.DataFrame = pd.concat(dfs_symbol_for_all_time_periods)
        df_symbol.reset_index(drop=True, inplace=True)
        return df_symbol

    def _print_no_data_for_symbol(self, series_symbol: pd.Series):
        symbol_code = series_symbol[tables.Symbol.Columns.SYMBOL_CODE]
        exchange_code = series_symbol[tables.Symbol.Columns.EXCHANGE_CODE]
        logger.info("No data exists for symbol {0} ({1}, {2}, {3})".format(
            symbol_code, exchange_code, self.time_frame.name, self.symbol_status.name))

    def run(self, series_symbol: pd.Series) -> bool:
        """
        Requests price data from eodhd.com and inserts it into QuestDB.

        :param series_symbol: Symbol the data is requested for
        :return: True if price records were stored, False if the provider has none for the
            symbol or all of them are from before 1970, which QuestDB cannot store
        :raises FetchError: If a request failed or a payload has an unexpected structure
        :raises QueryError: If reading the symbol's newest record failed
        :raises InsertError: If the ingress write still fails once the retries are used up
        :raises UserInterruptError: If should_stop returned True while waiting to retry
        """
        # Gets start datetime from which data will be downloaded
        start_datetime = self._get_start_datetime(series_symbol)
        # Requests symbol price data
        if self.time_frame == TimeFrame.DAILY:
            df_price = self._get_daily_price_data(series_symbol, start_datetime)
        else:
            df_price = self._get_minute_price_data(series_symbol, start_datetime)

        if df_price.empty:
            # No data available for timeframe and symbol status
            self._print_no_data_for_symbol(series_symbol)
            successful_download = False
        else:
            # Inserts symbol price data
            successful_download = self.writePriceData.insert_price_data(df_price, series_symbol)
        return successful_download
