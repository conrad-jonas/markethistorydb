#!/usr/bin/env python12.9

"""Class for requesting price data from eodhd.com"""

from datetime import datetime
import pandas as pd

from fetch.eodhd.errors       import CompatibilityError
from fetch.eodhd.config       import API_TOKEN
from fetch.eodhd.request_data import RequestData
from utils.categories         import TimeFrame

class RequestPriceData(RequestData):
    def __init__(self, time_frame: TimeFrame, series_symbol: pd.Series):
        self._time_frame:  TimeFrame = time_frame
        self._symbol_code:       str = series_symbol["symbol_code"]
        self._exchange_code:     str = series_symbol["exchange_code"]
        self._exchange_url_code: str = series_symbol["exchange_url_code"]

    def _get_url_for_price_data(self) -> str:
        if self._time_frame == TimeFrame.DAILY:
            url_price = "https://eodhd.com/api/eod/{0}.{1}?".format(self._symbol_code, self._exchange_url_code)
        else:
            url_price = "https://eodhd.com/api/intraday/{0}.{1}?".format(self._symbol_code, self._exchange_url_code)
        return url_price

    def _get_url_params_for_price_data(self, start_datetime: datetime, end_datetime: datetime) -> dict[str, str]:
        if self._time_frame == TimeFrame.DAILY:
            if start_datetime:
                url_params = {"api_token": API_TOKEN, "fmt": "json", "from": start_datetime}
            else:
                url_params = {"api_token": API_TOKEN, "fmt": "json"}
        else:
            if not start_datetime or not end_datetime:
                raise ValueError
            url_params = {"api_token": API_TOKEN, "fmt": "json", "from": start_datetime.timestamp(),
                          "to": end_datetime.timestamp(), "interval": "1m"}
        return url_params

    def _check_price_data(self, df_price: pd.DataFrame):
        if (self._time_frame == TimeFrame.MINUTE and
                not self._has_columns(df_price, ["timestamp", "gmtoffset", "datetime",  "open", "high", "low", "close",
                                                 "volume"])):
            raise CompatibilityError("Minute price data has unexpected structure!")
        elif (self._time_frame == TimeFrame.DAILY and
              not self._has_columns(df_price, ["date", "open", "high", "low", "close", "adjusted_close", "volume"])):
            raise CompatibilityError("Daily price data has unexpected structure!")

    def _format_price_data(self, df_price: pd.DataFrame) -> pd.DataFrame:
        df_price.insert(0, "exchange_code", self._exchange_code)
        df_price.insert(1, "symbol_code", self._symbol_code)
        if self._time_frame == TimeFrame.MINUTE:
            df_price = df_price.rename(columns={"gmtoffset": "gmt_offset"})
            df_price["timestamp"] = pd.to_datetime(df_price["timestamp"], unit='s')
            df_price = df_price.drop("datetime", axis=1)
        else:
            df_price["datetime"] = pd.to_datetime(df_price["date"])
            df_price = df_price.drop("date", axis=1)
            df_price = df_price[df_price["datetime"] >= datetime.fromtimestamp(0)]
        return df_price

    def get(self, start_datetime: datetime = None, end_datetime: datetime = None) -> pd.DataFrame:
        """Requests price data for symbol"""
        url_price  = self._get_url_for_price_data(start_datetime, end_datetime)
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