#!/usr/bin/env python12.9

import pandas as pd

from markethistorydb.db               import Database, tables
from markethistorydb.utils import TimeFrame, SymbolStatus


class WriteSymbolData(object):
    def __init__(self, db: Database, time_frame: TimeFrame, symbol_status: SymbolStatus):
        self._db: Database = db
        self._time_frame: TimeFrame = time_frame
        self._symbol_status: SymbolStatus = symbol_status

    def _is_in_table_symbol(self, series_symbol: pd.Series) -> bool:
        symbol_code = series_symbol[tables.Symbol.Columns.SYMBOL_CODE]
        exchange_code = series_symbol[tables.Symbol.Columns.EXCHANGE_CODE]
        record_from_table = self._db.read.symbol(symbol_code, exchange_code, self._time_frame, self._symbol_status)
        return not record_from_table.empty

    def update_symbol_data(self, series_symbol: pd.Series):
        if not self._is_in_table_symbol(series_symbol):
            self._db.insert.symbol(series_symbol)
        else:
            self._db.update.symbol(series_symbol)
