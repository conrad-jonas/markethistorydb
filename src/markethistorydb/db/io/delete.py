#!/usr/bin/env python12.9

"""Provides delete interface to db"""

import logging

from psycopg import sql

import markethistorydb.db.tables as tables
import markethistorydb.db.statements as statements
from markethistorydb.db.io.query import Query

logger = logging.getLogger(__name__)


class Delete:
    def __init__(self, query: Query):
        self._query = query

    def _recover_interrupted_deletion(self, table_name: str):
        """
        Cleans up the copy an interrupted deletion left behind, which would otherwise make every
        later deletion from *table_name* fail when it creates its own copy. If the table still
        exists, the copy is dropped: the table was never dropped, so it still holds every record.
        If the table is gone, the copy holds the only records, so it takes the table's name back.

        :param table_name: Name of the table a symbol is about to be deleted from
        :raises QueryError: If looking up the tables, dropping the copy or renaming it failed
        """
        table_name_copy = f"{table_name}_copy"
        rows = self._query.execute(sql.SQL(statements.Meta.SELECT_TABLE_AND_COPY), [table_name, table_name_copy])
        existing_table_names = {row[0] for row in rows}
        if table_name_copy not in existing_table_names:
            return
        format_kwargs = {
            "table_name": sql.Identifier(table_name),
            "table_name_copy": sql.Identifier(table_name_copy),
        }
        if table_name in existing_table_names:
            logger.warning("Dropping {0} left over from an interrupted deletion".format(table_name_copy))
            self._query.execute(sql.SQL(statements.Meta.DROP_COPY).format(**format_kwargs), [])
        else:
            logger.warning("Renaming {0}, left over from an interrupted deletion, back to {1}".format(
                table_name_copy, table_name))
            self._query.execute(sql.SQL(statements.Meta.RENAME_COPY_TO_TABLE).format(**format_kwargs), [])

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

    def _symbol_from_symbol_table(self, symbol_code: str, exchange_code: str, table_name: str):
        format_kwargs = {
            "table_name": sql.Identifier(table_name),
            "table_name_copy": sql.Identifier(f"{table_name}_copy"),
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

    def symbol_from_table(self, symbol_code: str, exchange_code: str, table_name: str, timestamp_column: str | None,
                          unique_key_columns: tuple[str, ...]):
        """
        Deletes a symbol's records by copying every other record into a new table that then takes
        the table's place. A copy left over from an interrupted deletion is cleaned up first.
        A table outside the symbol, fundamental and price tables is left alone.

        :param symbol_code: Symbol whose records are deleted
        :param exchange_code: Exchange of the symbol
        :param table_name: Name of the table to delete from
        :param timestamp_column: Designated timestamp column of the table, None for the lookup tables
        :param unique_key_columns: Columns of the table's DEDUP key
        :raises QueryError: If one of the statements failed, leaving the earlier ones applied
        """
        if table_name in tables.TABLE_NAMES_SYMBOL:
            self._recover_interrupted_deletion(table_name)
            self._symbol_from_symbol_table(symbol_code, exchange_code, table_name)
        elif table_name in tables.TABLE_NAMES_FUNDAMENTAL:
            self._recover_interrupted_deletion(table_name)
            self._symbol_from_fundamental_table(symbol_code, exchange_code, table_name, timestamp_column,
                                                unique_key_columns)
        elif table_name in tables.TABLE_NAMES_PRICE:
            self._recover_interrupted_deletion(table_name)
            self._symbol_from_price_table(symbol_code, exchange_code, table_name)
