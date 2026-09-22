#!/usr/bin/env python12.9

"""Provides write interface to db"""

from questdb.ingress import Sender, ServerTimestamp
import logging
import pandas as pd

import markethistorydb.db.tables as tables
from markethistorydb.config           import Config
from markethistorydb.db.io.error import catch_ingress_error
from markethistorydb.utils import TimeFrame, SymbolStatus

logger = logging.getLogger(__name__)


class Insert:
    """
    Writes over QuestDB's ILP interface, which acknowledges a batch but enforces no
    constraints: a duplicate is appended, not rejected. Callers that must not duplicate
    (the Write* classes) read first and update instead - see fetch/write.
    """

    def __init__(self, config: Config):
        self._config = config

    @catch_ingress_error
    def table(self, df: pd.DataFrame, table_name: str, timestamp_column: str | None = None):
        """
        Inserts *df* into *table_name*.

        :param df: Records to write, one row per record
        :param table_name: Name of the target table
        :param timestamp_column: Name of the df column holding the designated timestamp. If the
            table's designated timestamp is generated server-side (e.g. created_at columns not
            present in df), leave unset so QuestDB assigns it.
        :raises InsertError: If the ingress write still fails once the retries are used up
        """
        at = timestamp_column if timestamp_column is not None else ServerTimestamp
        with Sender.from_conf(self._config.http_conf) as sender:
            sender.dataframe(df, table_name=table_name, at=at)

    def exchange(self, series_exchange: pd.Series):
        df_exchange = series_exchange.to_frame().T
        self.table(df_exchange, tables.Exchange.NAME)

    def symbol(self, series_symbol: pd.Series):
        df_symbol = series_symbol.to_frame().T
        self.table(df_symbol, tables.Symbol.NAME)

    def sector(self, series_sector: pd.Series):
        df_sector = series_sector.to_frame().T
        self.table(df_sector, tables.Sector.NAME)

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
