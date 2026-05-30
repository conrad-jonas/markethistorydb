#!/usr/bin/env python12.9

"""Provides delete interface to db"""

from psycopg import sql

from db import tables, statements, Query


class Delete:
    @staticmethod
    def _symbol_from_symbol_table(symbol_code: str, exchange_code: str, table_name: str, unique_key_columns: list[str]):
        query_string = statements.Symbol.DROP_SYMBOL_FROM_TABLE
        query = sql.SQL(query_string).format(table_name=sql.Identifier(table_name),
                                             unique_key_column=sql.SQL(', ').join(
                                                 map(sql.Literal, unique_key_columns)))
        params = [symbol_code, exchange_code]
        Query.execute(query, params)

    @staticmethod
    def _symbol_from_fundamental_table(symbol_code: str, exchange_code: str, table_name: str, timestamp_column: str,
                                       unique_key_columns: list[str]):
        query_string = statements.Fundamental.DROP_SYMBOL_FROM_TABLE
        query = sql.SQL(query_string).format(table_name=sql.Identifier(table_name),
                                             timestamp_column=sql.Identifier(timestamp_column),
                                             unique_key_column=sql.SQL(', ').join(map(sql.Literal, unique_key_columns)))
        params = [symbol_code, exchange_code]
        Query.execute(query, params)

    @staticmethod
    def _symbol_from_price_table(symbol_code: str, exchange_code: str, table_name: str):
        if table_name == tables.DailyOhlcv.NAME:
            query_string = statements.Price.DROP_SYMBOL_FROM_DAILY_OHLCV
        else:
            query_string = statements.Price.DROP_SYMBOL_FROM_MINUTE_OHLCV
        query = sql.SQL(query_string)
        params = [symbol_code, exchange_code]
        Query.execute(query, params)

    @staticmethod
    def symbol_from_table(symbol_code: str, exchange_code: str, table_name: str, timestamp_column: str,
                          unique_key_columns: list[str]):
        if table_name in tables.TABLE_NAMES_SYMBOL:
            Delete._symbol_from_symbol_table(symbol_code, exchange_code, table_name, unique_key_columns)
        elif table_name in tables.TABLE_NAMES_FUNDAMENTAL:
            Delete._symbol_from_fundamental_table(symbol_code, exchange_code, table_name, timestamp_column,
                                                unique_key_columns)
        elif table_name in tables.TABLE_NAMES_PRICE:
            Delete._symbol_from_price_table(symbol_code, exchange_code, table_name)