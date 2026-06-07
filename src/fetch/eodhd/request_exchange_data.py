#!/usr/bin/env python12.9

"""Class for requesting exchange data from eodhd.com"""

import pandas as pd

from fetch.eodhd.errors       import CompatibilityError
from fetch.eodhd.config       import API_TOKEN
from fetch.eodhd.request_data import RequestData
from utils.categories         import TimeFrame


# Exchanges to download daily and intraday data from
_EXCHANGE_NAMES_EOD    = ["USA Stocks", "London Exchange", "Toronto Exchange", "XETRA Stock Exchange",
                         "Shanghai Stock Exchange", "FOREX", "Cryptocurrencies",
                         "Government Bonds"]
_EXCHANGE_NAMES_MINUTE = ["USA Stocks", "FOREX", "Cryptocurrencies"]


class RequestExchangeData(RequestData):
    def __init__(self, time_frame: TimeFrame):
        self._time_frame: TimeFrame = time_frame

    @staticmethod
    def _get_url_for_exchanges_data() -> str:
        return "https://eodhd.com/api/exchanges-list/?"

    @staticmethod
    def _get_url_params_for_exchanges_data() -> dict[str, str]:
        return {"api_token": API_TOKEN, "fmt": "json"}

    def _check_exchange_data(self, df_exchanges: pd.DataFrame):
        if not self._has_columns(df_exchanges, ["Name", "Code"]):
            raise CompatibilityError("Exchange data has unexpected structure!")

    def _format_exchanges_data(self, df_exchanges: pd.DataFrame) -> pd.DataFrame:
        if self._time_frame == TimeFrame.DAILY:
            df_exchanges_filtered = df_exchanges[df_exchanges["Name"].isin(_EXCHANGE_NAMES_EOD)]
        else:
            df_exchanges_filtered = df_exchanges[df_exchanges["Name"].isin(_EXCHANGE_NAMES_MINUTE)]
        return df_exchanges_filtered

    def get(self) -> pd.DataFrame:
        """Requests exchanges meta data"""
        url_exchanges = self._get_url_for_exchanges_data()
        params        = self._get_url_params_for_exchanges_data()
        # Requests data
        data_exchanges = self._request_data_from_url(url_exchanges, params)
        # Creates and formats df
        df_exchanges = pd.DataFrame(data_exchanges)
        self._check_exchange_data(df_exchanges)
        df_exchanges_filtered = self._format_exchanges_data(df_exchanges)

        return df_exchanges_filtered