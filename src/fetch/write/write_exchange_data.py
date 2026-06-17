#!/usr/bin/env python12.9

import pandas as pd

from db import Read, Insert, Update


class WriteExchangeData(object):
    @staticmethod
    def _is_in_table_exchange(series_exchange: pd.Series) -> bool:
        exchange_code = series_exchange["exchange_code"]
        record_from_table = Read.exchange(exchange_code)
        return not record_from_table.empty

    def update_exchange_data(self, series_exchange: pd.Series):
        if not self._is_in_table_exchange(series_exchange):
            Insert.exchange(series_exchange)
        else:
            Update.exchange(series_exchange)
