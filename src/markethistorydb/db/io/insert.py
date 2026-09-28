#!/usr/bin/env python12.9

"""Provides write interface to db"""

from psycopg import sql
from questdb import Sender
from typing import Any
import logging
import numpy as np
import pandas as pd

import markethistorydb.db.tables as tables
import markethistorydb.db.statements as statements
from markethistorydb.config           import Config
from markethistorydb.db.io.error import catch_ingress_error
from markethistorydb.db.io.query import Query
from markethistorydb.errors import InsertError, QueryError
from markethistorydb.utils import TimeFrame, SymbolStatus

logger = logging.getLogger(__name__)


class Insert:
    """
    Writes the price and fundamental tables over QuestDB's ILP interface, which acknowledges a
    batch but enforces no constraints; their DEDUP keys keep a re-sent record from being stored
    twice.

    The lookup tables (exchange, symbol, sector) are non-WAL, which ILP over HTTP rejects, so
    they are written through SQL. They have no DEDUP either, so callers that must not duplicate
    (the Write* classes) read first and update instead - see fetch/write. Being non-WAL, a write
    is visible to that read at once.
    """

    def __init__(self, config: Config, query: Query):
        self._config = config
        self._query = query

    @catch_ingress_error
    def table(self, df: pd.DataFrame, table_name: str, timestamp_column: str):
        """
        Inserts *df* into *table_name*.

        :param df: Records to write, one row per record
        :param table_name: Name of the target table, one with a designated timestamp: ILP over
            HTTP only writes WAL tables, and only those have one
        :param timestamp_column: Name of the df column holding the designated timestamp
        :raises SchemaMismatchError: If the DB rejected the records for not fitting the table,
            e.g. a column the table does not have or a value its column's type cannot store
        :raises InsertError: If the ingress write still fails once the retries are used up, or
            fails in another way no retry can fix (e.g. a timestamp before 1970)
        """
        with Sender.from_conf(self._config.http_conf) as sender:
            sender.dataframe(df, table_name=table_name, at=timestamp_column)

    @staticmethod
    def _sql_value(value: Any) -> Any:
        """
        Converts a record's value to one psycopg binds.

        :param value: Value as the record holds it
        :return: None for a missing value (NaN, None), the plain Python value for a numpy scalar,
            *value* itself otherwise
        """
        if pd.isna(value):
            return None
        return value.item() if isinstance(value, np.generic) else value

    def _record(self, statement: str, series_record: pd.Series, table: type[tables.Table]):
        """
        Inserts a single record into one of the lookup tables through SQL.

        :param statement: INSERT statement taking a value for every column of *table*, in
            ALL_COLUMNS order
        :param series_record: Record to write, indexed by column name. A column it lacks is
            written as NULL; a field *table* does not define (e.g. the symbol's exchange_url_code,
            which only routes the requests) is left out.
        :param table: Table the record is written to
        :raises InsertError: If the DB could not be reached or rejected the record
        """
        params = [self._sql_value(series_record.get(column)) for column in table.ALL_COLUMNS]
        try:
            self._query.execute(sql.SQL(statement), params)
        except QueryError as error:
            raise InsertError("Inserting into {0} failed: {1}".format(table.NAME, error)) from error

    def exchange(self, series_exchange: pd.Series):
        """
        Inserts an exchange record.

        :param series_exchange: Record to write, indexed by column name
        :raises InsertError: If the DB could not be reached or rejected the record
        """
        self._record(statements.Exchange.INSERT_EXCHANGE, series_exchange, tables.Exchange)

    def symbol(self, series_symbol: pd.Series):
        """
        Inserts a symbol record.

        :param series_symbol: Record to write, indexed by column name
        :raises InsertError: If the DB could not be reached or rejected the record
        """
        self._record(statements.Symbol.INSERT_SYMBOL, series_symbol, tables.Symbol)

    def sector(self, series_sector: pd.Series):
        """
        Inserts a sector record.

        :param series_sector: Record to write, indexed by column name
        :raises InsertError: If the DB could not be reached or rejected the record
        """
        self._record(statements.Symbol.INSERT_SECTOR, series_sector, tables.Sector)

    def ohlcv(self, df: pd.DataFrame, symbol_code: str, exchange_code: str, time_frame: TimeFrame,
              symbol_status: SymbolStatus):
        if time_frame == TimeFrame.DAILY:
            table_name = tables.DailyOhlcv.NAME
            pd_time_column_name = tables.DailyOhlcv.Columns.TIMESTAMP
        else:
            table_name = tables.MinuteOhlcv.NAME
            pd_time_column_name = tables.MinuteOhlcv.Columns.TIMESTAMP

        logger.info("""Inserts {0} price records for symbol {1} ({2}, {3}, {4}) into table {5}""".format(
            df.shape[0], symbol_code, exchange_code, time_frame.name, symbol_status.name, table_name))
        self.table(df, table_name, pd_time_column_name)
