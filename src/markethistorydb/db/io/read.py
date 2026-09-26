#!/usr/bin/env python12.9

"""Provides read interface to db"""

from datetime import datetime
from psycopg  import sql
from typing   import Any
import pandas as pd

import markethistorydb.db.tables as tables
import markethistorydb.db.statements as statements
from markethistorydb.db.io.query      import Query
from markethistorydb.errors import QueryError
from markethistorydb.utils import TimeFrame, SymbolStatus


def _single_record(rows: list[tuple], description: str) -> pd.Series:
    """
    Returns the one expected record in *rows* as a Series.

    :param rows: Records the query returned; at most one is expected
    :param description: What was looked up, used in the error message
    :return: The single record, or an empty Series if there is none. Callers distinguish
        "not found" from "found" by Series.empty, so no record yields an empty Series
        rather than an error.
    :raises QueryError: If *rows* holds more than one record
    """
    # Only one combination of arguments in table allowed -> no more than one record expected
    if len(rows) > 1:
        raise QueryError("Expected at most one record for {0}, got {1}".format(
            description, len(rows)))
    if not rows:
        return pd.Series(dtype=object)
    return pd.Series(rows[0])


class Read:
    def __init__(self, query: Query):
        self._query = query

    def exchange(self, exchange_code: str) -> pd.Series:
        query = sql.SQL(statements.Exchange.SELECT_ALL_FROM_EXCHANGE_BY_EXCHANGE_CODE)
        params = [exchange_code]
        rows = self._query.execute(query, params)
        return _single_record(rows, "exchange {0}".format(exchange_code))

    def symbol(self, symbol_code: str, exchange_code: str, time_frame: TimeFrame,
               symbol_status: SymbolStatus) -> pd.Series:
        query = sql.SQL(statements.Symbol.SELECT_ALL_FROM_SYMBOL_BY_UNIQUE_KEYS)
        params = [symbol_code, exchange_code, time_frame.name, symbol_status.name]
        rows = self._query.execute(query, params)
        return _single_record(rows, "symbol {0} ({1}, {2}, {3})".format(
            symbol_code, exchange_code, time_frame.name, symbol_status.name))

    def sector(self, symbol_code: str, exchange_code: str) -> pd.Series:
        query = sql.SQL(statements.Symbol.SELECT_ALL_FROM_SECTOR_BY_UNIQUE_KEYS)
        params = [symbol_code, exchange_code]
        rows = self._query.execute(query, params)
        return _single_record(rows, "sector of {0} ({1})".format(symbol_code, exchange_code))

    def ohlcv(self, symbol_codes_per_exchange: dict[str, list[str]], time_frame: TimeFrame,
              start_datetime: datetime = datetime.min, end_datetime: datetime = datetime.max) -> pd.DataFrame:
        """
        Selects price data for specific symbols of exchanges, time period and time frame from DB.

        :param symbol_codes_per_exchange: Symbol codes to select, keyed by exchange code
        :param time_frame: Time frame deciding which OHLCV table is read
        :param start_datetime: Start of the time period, inclusive
        :param end_datetime: End of the time period, inclusive
        :return: Price records indexed by symbol code and timestamp
        :raises QueryError: If one of the per-exchange queries failed
        """
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
        df_ohlcv = pd.concat(df_list) if df_list else pd.DataFrame(columns=column_names)
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
        df_ohlcv = pd.concat(df_list) if df_list else pd.DataFrame(columns=column_names)
        df_ohlcv.set_index([column_symbol_code, column_timestamp], inplace=True, drop=False)
        return df_ohlcv