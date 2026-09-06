
from datetime import datetime, timedelta
import logging
import pandas as pd

from markethistorydb.fetch.eodhd      import RequestPriceData
from markethistorydb.fetch.write      import WritePriceData
from markethistorydb.utils.categories import TimeFrame, SymbolStatus

# Minute data gets requested from start date to end
_START_DATE_MINUTE_DATA = "01-01-2005"
_END_DATE_MINUTE_DATA = datetime.today().strftime("%d-%m-%Y")
# Minute data gets requested for the following time period in days
_NUM_OF_DAYS_PER_MINUTE_DATA_REQUEST = 120


class DownloadPriceData(object):
    def __init__(self, time_frame: TimeFrame, symbol_status: SymbolStatus):
        self.time_frame:            TimeFrame = time_frame
        self.symbol_status:      SymbolStatus = symbol_status

        self.writePriceData = WritePriceData(time_frame, symbol_status)

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
        """Requests and returns daily price data from eodhd.com"""
        price_data_requester = RequestPriceData(self.time_frame, series_symbol)
        return price_data_requester.get(start_datetime)

    @staticmethod
    def _get_time_periods_for_minute_data_requests(
            start_datetime: datetime | None = None) -> list[tuple[datetime, datetime]]:
        """
        Returns list of time periods (start and end datetime) for every minute data request from eodhd.com
        (minute data request are only allowed for a maximum of 120 days)
        """
        # Contains the start and end datetime for each minute data request
        minute_data_time_periods: list[tuple[datetime, datetime]] = []
        # Start datetime of request for the chronically first time period
        if start_datetime:
            request_start_datetime = start_datetime
        else:
            request_start_datetime = datetime.strptime(_START_DATE_MINUTE_DATA, "%d-%m-%Y")
        # Loops over whole time period for which minute data should be requested
        while request_start_datetime < datetime.strptime(_END_DATE_MINUTE_DATA, "%d-%m-%Y"):
            request_end_datetime = request_start_datetime + timedelta(days=_NUM_OF_DAYS_PER_MINUTE_DATA_REQUEST)
            if request_end_datetime > datetime.strptime(_END_DATE_MINUTE_DATA, "%d-%m-%Y"):
                request_end_datetime = datetime.strptime(_END_DATE_MINUTE_DATA, "%d-%m-%Y")
            minute_data_time_periods.append((request_start_datetime, request_end_datetime))
            request_start_datetime = request_end_datetime

        return minute_data_time_periods

    def _get_minute_price_data(self, series_symbol: pd.Series,
                               start_datetime: datetime | None = None) -> pd.DataFrame:
        """
        Requests minute price data from eodhd.com by dividing the whole time period, for which the minute price data
        shall be obtained, into smaller time periods (because minute price data from eodhd.com can only be requested for
        max 120 days), requests the data for these smaller time periods and returns the whole merged data for the whole
        time period
        """
        # Contains the start and end datetime for each minute data request
        minute_data_time_periods: list[tuple[datetime, datetime]] = (
            self._get_time_periods_for_minute_data_requests(start_datetime))

        dfs_symbol_for_all_time_periods: list[pd.DataFrame] = []
        price_data_requester = RequestPriceData(self.time_frame, series_symbol)
        for start_time_period, end_time_period in minute_data_time_periods:
            dfs_symbol_for_all_time_periods.append(price_data_requester.get(start_time_period, end_time_period))
        df_symbol: pd.DataFrame = pd.concat(dfs_symbol_for_all_time_periods)
        df_symbol.reset_index(drop=True, inplace=True)
        return df_symbol

    def _print_no_data_for_symbol(self, series_symbol: pd.Series):
        symbol_code = series_symbol["symbol_code"]
        exchange_code = series_symbol["exchange_code"]
        logging.info("No data exists for symbol {0} ({1}, {2}, {3})".format(
            symbol_code, exchange_code, self.time_frame.name, self.symbol_status.name))

    def run(self, series_symbol: pd.Series) -> bool:
        """
        Requests price data from eodhd.com and inserts it into QuestDB
        :return: True if successful else False
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
            self.writePriceData.insert_price_data(df_price, series_symbol)
            successful_download = True
        return successful_download
