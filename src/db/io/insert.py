#!/usr/bin/env python12.9

"""Provides write interface to db"""

from psycopg         import IntegrityError
from questdb.ingress import Sender
import logging
import pandas as pd

from db               import tables, QUESTDB_CONF_HTTP
from db.io            import catch_ingress_error
from utils.categories import TimeFrame, SymbolStatus


class Insert:
    @staticmethod
    @catch_ingress_error
    def table(df: pd.DataFrame, table_name: str, timestamp_column: str):
        with Sender.from_conf(QUESTDB_CONF_HTTP) as sender:
            sender.dataframe(df, table_name=table_name, at=timestamp_column)

    @staticmethod
    def exchange(series_exchange: pd.Series):
        try:
            df_exchange = series_exchange.to_frame().T
            Insert.table(df_exchange, tables.Exchange.NAME)
        except IntegrityError as error:
            logging.error("""Exchange code {0} already exists in table {1}""".format(
                series_exchange["exchange_code"],
                tables.Exchange.NAME))
            raise error

    @staticmethod
    def symbol(series_symbol: pd.Series):
        try:
            df_symbol = series_symbol.to_frame().T
            Insert.table(df_symbol, tables.Symbol.NAME)
        except IntegrityError as error:
            logging.error("""Symbol code {0} ({1}, {2}, {3}) combo already exists in table {4}""".format(
                series_symbol["symbol_code"],
                series_symbol["exchange_code"],
                series_symbol["time_frame"],
                series_symbol["symbol_status"],
                tables.Symbol.NAME))
            raise error

    @staticmethod
    def sector(series_sector: pd.Series):
        try:
            df_symbol = series_sector.to_frame().T
            Insert.table(df_symbol, tables.Symbol.NAME)
        except IntegrityError as error:
            logging.error("""Symbol and exchange code combo {0} and {1} already exists in table {2}""".format(
                series_sector["symbol_code"],
                series_sector["exchange_code"],
                tables.Sector.NAME))
            raise error

    @staticmethod
    def ohlcv(df: pd.DataFrame, symbol_code: str, exchange_code: str, time_frame: TimeFrame,
              symbol_status: SymbolStatus):
        if time_frame == TimeFrame.DAILY:
            table_name = tables.DailyOhlcv.NAME
            pd_time_column_name = "datetime"
        else:
            table_name =tables.MinuteOhlcv.NAME
            pd_time_column_name = "timestamp"

        logging.info("""Inserts {0} price records for symbol {1} ({2}, {3}, {4}) into table {5}""".format(
            df.shape[0], symbol_code, exchange_code, time_frame.name, symbol_status.name, table_name))
        Insert.table(df, table_name, pd_time_column_name)