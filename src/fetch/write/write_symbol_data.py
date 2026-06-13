#!/usr/bin/env python12.9

import pandas as pd

from db               import Read, Insert, Update
from utils.categories import TimeFrame, SymbolStatus


class WriteSymbolData(object):
    def __init__(self, time_frame: TimeFrame, symbol_status: SymbolStatus):
        self._time_frame: TimeFrame = time_frame
        self._symbol_status: SymbolStatus = symbol_status

    def _is_in_table_symbol(self, series_symbol: pd.Series) -> bool:
        symbol_code = series_symbol["symbol_code"]
        exchange_code = series_symbol["exchange_code"]
        record_from_table = Read.symbol(symbol_code, exchange_code, self._time_frame, self._symbol_status)
        return not record_from_table.empty

    def update_symbol_data(self, series_symbol: pd.Series):
        if not self._is_in_table_symbol(series_symbol):
            Insert.symbol(series_symbol)
        else:
            Update.symbol(series_symbol)
