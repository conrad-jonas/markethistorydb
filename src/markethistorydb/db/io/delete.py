#!/usr/bin/env python12.9

"""Provides delete interface to db"""

from psycopg import sql

import markethistorydb.db.tables as tables
import markethistorydb.db.statements as statements
from markethistorydb.db.io.query import Query


class Delete:
    def __init__(self, query: Query):
        self._query = query

    def _execute_statements(self, statement_templates: tuple[str, ...], format_kwargs: dict,
                            symbol_code: str, exchange_code: str):
        """
        Executes each statement in *statement_templates* sequentially, since QuestDB expects one
        statement per query.

        :param statement_templates: Statement templates to run, in order
        :param format_kwargs: Identifiers substituted into every template
        :param symbol_code: Symbol to delete; only passed to statements containing %s placeholders
        :param exchange_code: Exchange of the symbol; passed alongside *symbol_code*
        :raises QueryError: If one of the statements failed, leaving the earlier ones applied
        """
        for statement_template in statement_templates:
            query = sql.SQL(statement_template).format(**format_kwargs)
            params = [symbol_code, exchange_code] if "%s" in statement_template else []
            self._query.execute(query, params)

    def _symbol_from_symbol_table(self, symbol_code: str, exchange_code: str, table_name: str, unique_key_columns: list[str]):
        format_kwargs = {
            "table_name": sql.Identifier(table_name),
            "table_name_copy": sql.Identifier(f"{table_name}_copy"),
            "unique_key_columns": sql.SQL(', ').join(map(sql.Identifier, unique_key_columns)),
        }
        self._execute_statements(statements.Symbol.DROP_SYMBOL_FROM_TABLE, format_kwargs, symbol_code, exchange_code)

    def _symbol_from_fundamental_table(self, symbol_code: str, exchange_code: str, table_name: str, timestamp_column: str,
                                       unique_key_columns: tuple[str, ...]):
        format_kwargs = {
            "table_name": sql.Identifier(table_name),
            "table_name_copy": sql.Identifier(f"{table_name}_copy"),
            "timestamp_column": sql.Identifier(timestamp_column),
            "unique_key_columns": sql.SQL(', ').join(map(sql.Identifier, unique_key_columns)),
        }
        self._execute_statements(statements.Fundamental.DROP_SYMBOL_FROM_TABLE, format_kwargs,
                                   symbol_code, exchange_code)

    def _symbol_from_price_table(self, symbol_code: str, exchange_code: str, table_name: str):
        if table_name == tables.DailyOhlcv.NAME:
            statement_templates = statements.Price.DROP_SYMBOL_FROM_DAILY_OHLCV
        else:
            statement_templates = statements.Price.DROP_SYMBOL_FROM_MINUTE_OHLCV
        self._execute_statements(statement_templates, {}, symbol_code, exchange_code)

    def symbol_from_table(self, symbol_code: str, exchange_code: str, table_name: str, timestamp_column: str,
                          unique_key_columns: list[str]):
        if table_name in tables.TABLE_NAMES_SYMBOL:
            self._symbol_from_symbol_table(symbol_code, exchange_code, table_name, unique_key_columns)
        elif table_name in tables.TABLE_NAMES_FUNDAMENTAL:
            self._symbol_from_fundamental_table(symbol_code, exchange_code, table_name, timestamp_column,
                                                unique_key_columns)
        elif table_name in tables.TABLE_NAMES_PRICE:
            self._symbol_from_price_table(symbol_code, exchange_code, table_name)
