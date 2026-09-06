#!/usr/bin/env python12.9

"""Interface to time series DB"""

from datetime import datetime
from questdb.ingress import IngressError
import pandas as pd

from markethistorydb.db                import Read, Insert
from markethistorydb.fetch.errors      import InsertError
from markethistorydb.utils.categories  import TimeFrame, SymbolStatus


class WritePriceData(object):
    def __init__(self, time_frame: TimeFrame, symbol_status: SymbolStatus):
        self._time_frame: TimeFrame = time_frame
        self._symbol_status: SymbolStatus = symbol_status

    def get_last_datetime_of_price_data(self, series_symbol: pd.Series) -> datetime | None:
        symbol_code = series_symbol["symbol_code"]
        exchange_code = series_symbol["exchange_code"]
        df_existing_ohlcv = Read.newest_of_ohlcv({exchange_code: [symbol_code]}, self._time_frame)
        try:
            last_datetime = df_existing_ohlcv.iloc[0]["timestamp"].to_pydatetime()
        except IndexError:
            last_datetime = None
        return last_datetime

    def insert_price_data(self, df_price: pd.DataFrame, series_symbol: pd.Series):
        symbol_code = series_symbol["symbol_code"]
        exchange_code = series_symbol["exchange_code"]
        try:
            Insert.ohlcv(df_price, symbol_code, exchange_code, self._time_frame, self._symbol_status)
        except IngressError:
            raise InsertError