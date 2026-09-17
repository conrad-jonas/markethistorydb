#!/usr/bin/env python12.9

"""Class for requesting price data from eodhd.com"""

from datetime import datetime
import pandas as pd

from markethistorydb.db                       import tables
from markethistorydb.fetch.eodhd.errors       import CompatibilityError
from markethistorydb.fetch.eodhd.config       import API_TOKEN
from markethistorydb.fetch.eodhd.request_data import RequestData
from markethistorydb.utils.categories         import TimeFrame

class RequestPriceData(RequestData):
    def __init__(self, time_frame: TimeFrame, series_symbol: pd.Series):
        self._time_frame:  TimeFrame = time_frame
        self._symbol_code:       str = series_symbol[tables.Symbol.Columns.SYMBOL_CODE]
        self._exchange_code:     str = series_symbol[tables.Symbol.Columns.EXCHANGE_CODE]
        self._exchange_url_code: str = series_symbol["exchange_url_code"]

    def _get_url_for_price_data(self) -> str:
        if self._time_frame == TimeFrame.DAILY:
            url_price = RequestData.Url.eod(self._symbol_code, self._exchange_url_code)
        else:
            url_price = RequestData.Url.intraday(self._symbol_code, self._exchange_url_code)
        return url_price

    def _get_url_params_for_price_data(self, start_datetime: datetime | None, end_datetime: datetime | None) -> dict[str, str]:
        url_params = {
            RequestData.Params.API_TOKEN: API_TOKEN,
            RequestData.Params.FMT: RequestData.Values.JSON,
        }
        if self._time_frame == TimeFrame.DAILY:
            if start_datetime:
                url_params[RequestData.Params.FROM] = start_datetime.strftime("%Y-%m-%d")
        else:
            if not start_datetime or not end_datetime:
                raise ValueError
            url_params[RequestData.Params.FROM] = str(int(start_datetime.timestamp()))
            url_params[RequestData.Params.TO] = str(int(end_datetime.timestamp()))
            url_params[RequestData.Params.INTERVAL] = RequestData.Values.INTERVAL_1M
        return url_params

    # Raw column names as returned by the eodhd.com API, before renaming to match the DB schema
    class _ApiColumns:
        TIMESTAMP      = "timestamp"
        GMT_OFFSET     = "gmtoffset"
        DATETIME       = "datetime"
        DATE           = "date"
        OPEN           = "open"
        HIGH           = "high"
        LOW            = "low"
        CLOSE          = "close"
        ADJUSTED_CLOSE = "adjusted_close"
        VOLUME         = "volume"

    def _check_price_data(self, df_price: pd.DataFrame):
        if (self._time_frame == TimeFrame.MINUTE and
                not self._has_columns(df_price, [self._ApiColumns.TIMESTAMP, self._ApiColumns.GMT_OFFSET,
                                                 self._ApiColumns.DATETIME, self._ApiColumns.OPEN,
                                                 self._ApiColumns.HIGH, self._ApiColumns.LOW,
                                                 self._ApiColumns.CLOSE, self._ApiColumns.VOLUME])):
            raise CompatibilityError("Minute price data has unexpected structure!")
        elif (self._time_frame == TimeFrame.DAILY and
              not self._has_columns(df_price, [self._ApiColumns.DATE, self._ApiColumns.OPEN, self._ApiColumns.HIGH,
                                               self._ApiColumns.LOW, self._ApiColumns.CLOSE,
                                               self._ApiColumns.ADJUSTED_CLOSE, self._ApiColumns.VOLUME])):
            raise CompatibilityError("Daily price data has unexpected structure!")

    def _format_price_data(self, df_price: pd.DataFrame) -> pd.DataFrame:
        df_price.insert(0, tables.DailyOhlcv.Columns.EXCHANGE_CODE, self._exchange_code)
        df_price.insert(1, tables.DailyOhlcv.Columns.SYMBOL_CODE, self._symbol_code)
        if self._time_frame == TimeFrame.MINUTE:
            df_price = df_price.rename(columns={self._ApiColumns.GMT_OFFSET: tables.MinuteOhlcv.Columns.GMT_OFFSET})
            df_price[tables.MinuteOhlcv.Columns.TIMESTAMP] = pd.to_datetime(
                df_price[self._ApiColumns.TIMESTAMP], unit='s')
            df_price = df_price.drop(self._ApiColumns.DATETIME, axis=1)
        else:
            df_price[tables.DailyOhlcv.Columns.TIMESTAMP] = pd.to_datetime(df_price[self._ApiColumns.DATE])
            df_price = df_price.drop(self._ApiColumns.DATE, axis=1)
            df_price = df_price[df_price[tables.DailyOhlcv.Columns.TIMESTAMP] >= datetime.fromtimestamp(0)]
        return df_price

    def get(self, start_datetime: datetime | None = None, end_datetime: datetime | None = None) -> pd.DataFrame:
        """Requests price data for symbol"""
        url_price  = self._get_url_for_price_data()
        url_params = self._get_url_params_for_price_data(start_datetime, end_datetime)
        # Requests data
        data_price = self._request_data_from_url(url_price, url_params)
        # Creates and formats df
        if data_price:
            df_price = pd.DataFrame(data_price)
            self._check_price_data(df_price)
            df_price = self._format_price_data(df_price)
        else:
            df_price = pd.DataFrame()
        return df_price