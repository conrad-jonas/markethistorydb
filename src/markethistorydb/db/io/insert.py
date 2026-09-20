#!/usr/bin/env python12.9

"""Provides write interface to db"""

from psycopg         import IntegrityError
from questdb.ingress import Sender, ServerTimestamp
import logging
import pandas as pd

import markethistorydb.db.tables as tables
from markethistorydb.config           import Config
from markethistorydb.db.io.error import catch_ingress_error
from markethistorydb.utils import TimeFrame, SymbolStatus

logger = logging.getLogger(__name__)


class Insert:
    def __init__(self, config: Config):
        self._config = config

    @catch_ingress_error
    def table(self, df: pd.DataFrame, table_name: str, timestamp_column: str | None = None):
        """Inserts *df* into *table_name*.

        :param timestamp_column: Name of the df column holding the designated timestamp. If the
            table's designated timestamp is generated server-side (e.g. created_at columns not
            present in df), leave unset so QuestDB assigns it.
        """
        at = timestamp_column if timestamp_column is not None else ServerTimestamp
        with Sender.from_conf(self._config.http_conf) as sender:
            sender.dataframe(df, table_name=table_name, at=at)

    def exchange(self, series_exchange: pd.Series):
        try:
            df_exchange = series_exchange.to_frame().T
            self.table(df_exchange, tables.Exchange.NAME)
        except IntegrityError as error:
            logger.error("""Exchange code {0} already exists in table {1}""".format(
                series_exchange[tables.Exchange.Columns.EXCHANGE_CODE],
                tables.Exchange.NAME))
            raise error

    def symbol(self, series_symbol: pd.Series):
        try:
            df_symbol = series_symbol.to_frame().T
            self.table(df_symbol, tables.Symbol.NAME)
        except IntegrityError as error:
            logger.error("""Symbol code {0} ({1}, {2}, {3}) combo already exists in table {4}""".format(
                series_symbol[tables.Symbol.Columns.SYMBOL_CODE],
                series_symbol[tables.Symbol.Columns.EXCHANGE_CODE],
                series_symbol[tables.Symbol.Columns.TIME_FRAME],
                series_symbol[tables.Symbol.Columns.SYMBOL_STATUS],
                tables.Symbol.NAME))
            raise error

    def sector(self, series_sector: pd.Series):
        try:
            df_sector = series_sector.to_frame().T
            self.table(df_sector, tables.Sector.NAME)
        except IntegrityError as error:
            logger.error("""Symbol and exchange code combo {0} and {1} already exists in table {2}""".format(
                series_sector[tables.Sector.Columns.SYMBOL_CODE],
                series_sector[tables.Sector.Columns.EXCHANGE_CODE],
                tables.Sector.NAME))
            raise error

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