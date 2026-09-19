#!/usr/bin/env python12.9

import pandas as pd

from markethistorydb.db import Database, tables


class WriteExchangeData(object):
    def __init__(self, db: Database):
        self._db: Database = db

    def _is_in_table_exchange(self, series_exchange: pd.Series) -> bool:
        exchange_code = series_exchange[tables.Exchange.Columns.EXCHANGE_CODE]
        record_from_table = self._db.read.exchange(exchange_code)
        return not record_from_table.empty

    def update_exchange_data(self, series_exchange: pd.Series):
        if not self._is_in_table_exchange(series_exchange):
            self._db.insert.exchange(series_exchange)
        else:
            self._db.update.exchange(series_exchange)
