#!/usr/bin/env python12.9

"""Provides read interface to db"""

from datetime import datetime
from psycopg  import sql
from typing   import Any
import pandas as pd

import markethistorydb.db.tables as tables
import markethistorydb.db.statements as statements
from markethistorydb.db.io.query      import Query
from markethistorydb.utils import TimeFrame, SymbolStatus


class Read:
    def __init__(self, query: Query):
        self._query = query

    def exchange(self, exchange_code: str) -> pd.Series:
        query = sql.SQL(statements.Exchange.SELECT_ALL_FROM_EXCHANGE_BY_EXCHANGE_CODE)
        params = [exchange_code]
        rows = self._query.execute(query, params)
        # Only one combination of arguments in table allowed -> no more than one record expected
        assert len(rows) <= 1
        return pd.Series(rows[0])

    def symbol(self, symbol_code: str, exchange_code: str, time_frame: TimeFrame,
               symbol_status: SymbolStatus) -> pd.Series:
        query = sql.SQL(statements.Symbol.SELECT_ALL_FROM_SYMBOL_BY_UNIQUE_KEYS)
        params = [symbol_code, exchange_code, time_frame.name, symbol_status.name]
        rows = self._query.execute(query, params)
        # Only one combination of arguments in table allowed -> no more than one record expected
        assert len(rows) <= 1
        return pd.Series(rows[0])

    def sector(self, symbol_code: str, exchange_code: str) -> pd.Series:
        query = sql.SQL(statements.Symbol.SELECT_ALL_FROM_SECTOR_BY_UNIQUE_KEYS)
        params = [symbol_code, exchange_code]
        rows = self._query.execute(query, params)
        # Only one combination of arguments in table allowed -> no more than one record expected
        assert len(rows) <= 1
        return pd.Series(rows[0])

    def ohlcv(self, symbol_codes_per_exchange: dict[str, list[str]], time_frame: TimeFrame,
              start_datetime: datetime = datetime.min, end_datetime: datetime = datetime.max) -> pd.DataFrame:
        """Selects price data for specific symbols of exchanges, time period and time frame from DB"""
        if time_frame == TimeFrame.DAILY:
            query_string = statements.Price.SELECT_ALL_FROM_DAILY_OHLCV
            column_names = tables.DailyOhlcv.ALL_COLUMNS
            column_symbol_code = tables.DailyOhlcv.Columns.SYMBOL_CODE
            column_timestamp = tables.DailyOhlcv.Columns.TIMESTAMP
        else:
            query_string = statements.Price.SELECT_ALL_FROM_MINUTE_OHLCV
            column_names = tables.MinuteOhlcv.ALL_COLUMNS
            column_symbol_code = tables.MinuteOhlcv.Columns.SYMBOL_CODE
            column_timestamp = tables.MinuteOhlcv.Columns.TIMESTAMP

        df_list: list[pd.DataFrame] = []
        for exchange_code in symbol_codes_per_exchange:
            symbol_codes = symbol_codes_per_exchange[exchange_code]
            query = sql.SQL(query_string).format(symbol_codes=sql.SQL(', ').join(map(sql.Literal, symbol_codes)))
            params: list[Any] = [exchange_code]
            params.extend([start_datetime, end_datetime])
            rows = self._query.execute(query, params)

            df_list.append(pd.DataFrame(rows, columns=column_names))
        df_ohlcv = pd.concat(df_list)
        df_ohlcv.set_index([column_symbol_code, column_timestamp], inplace=True)
        return df_ohlcv

    def newest_of_ohlcv(self, symbol_codes_per_exchange: dict[str, list[str]], time_frame: TimeFrame) -> pd.DataFrame:
        if time_frame == TimeFrame.DAILY:
            query_string = statements.Price.SELECT_LAST_FROM_DAILY_OHLCV
            column_names = tables.DailyOhlcv.ALL_COLUMNS
            column_symbol_code = tables.DailyOhlcv.Columns.SYMBOL_CODE
            column_timestamp = tables.DailyOhlcv.Columns.TIMESTAMP
        else:
            query_string = statements.Price.SELECT_LAST_FROM_MINUTE_OHLCV
            column_names = tables.MinuteOhlcv.ALL_COLUMNS
            column_symbol_code = tables.MinuteOhlcv.Columns.SYMBOL_CODE
            column_timestamp = tables.MinuteOhlcv.Columns.TIMESTAMP

        df_list: list[pd.DataFrame] = []
        for exchange_code in symbol_codes_per_exchange:
            symbol_codes = symbol_codes_per_exchange[exchange_code]
            query = sql.SQL(query_string).format(symbol_codes=sql.SQL(', ').join(map(sql.Literal, symbol_codes)))
            params: list[Any] = [exchange_code]
            rows = self._query.execute(query, params)

            df_list.append(pd.DataFrame(rows, columns=column_names))
        df_ohlcv = pd.concat(df_list)
        df_ohlcv.set_index([column_symbol_code, column_timestamp], inplace=True, drop=False)
        return df_ohlcv