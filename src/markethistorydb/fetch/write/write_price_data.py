#!/usr/bin/env python12.9

"""Interface to time series DB"""

from datetime import datetime
from questdb.ingress import IngressError
import pandas as pd

from markethistorydb.db                import Database, tables
from markethistorydb.fetch.errors      import InsertError
from markethistorydb.utils  import TimeFrame, SymbolStatus


class WritePriceData(object):
    def __init__(self, db: Database, time_frame: TimeFrame, symbol_status: SymbolStatus):
        self._db: Database = db
        self._time_frame: TimeFrame = time_frame
        self._symbol_status: SymbolStatus = symbol_status

    def get_last_datetime_of_price_data(self, series_symbol: pd.Series) -> datetime | None:
        symbol_code = series_symbol[tables.Symbol.Columns.SYMBOL_CODE]
        exchange_code = series_symbol[tables.Symbol.Columns.EXCHANGE_CODE]
        df_existing_ohlcv = self._db.read.newest_of_ohlcv({exchange_code: [symbol_code]}, self._time_frame)
        try:
            last_datetime = df_existing_ohlcv.iloc[0]["timestamp"].to_pydatetime()
        except IndexError:
            last_datetime = None
        return last_datetime

    def insert_price_data(self, df_price: pd.DataFrame, series_symbol: pd.Series):
        symbol_code = series_symbol[tables.Symbol.Columns.SYMBOL_CODE]
        exchange_code = series_symbol[tables.Symbol.Columns.EXCHANGE_CODE]
        try:
            self._db.insert.ohlcv(df_price, symbol_code, exchange_code, self._time_frame, self._symbol_status)
        except IngressError:
            raise InsertError