#!/usr/bin/env python12.9

"""Provides write interface to db"""

from psycopg import sql
import pandas as pd

import markethistorydb.db.tables as tables
import markethistorydb.db.statements as statements
from markethistorydb.db.io.query import Query


class Update:
    @staticmethod
    def exchange(series_exchange: pd.Series):
        query = sql.SQL(statements.Exchange.UPDATE_EXCHANGE)
        params = [
            series_exchange[tables.Exchange.Columns.NAME],
            series_exchange[tables.Exchange.Columns.OPERATING_MIC],
            series_exchange[tables.Exchange.Columns.COUNTRY],
            series_exchange[tables.Exchange.Columns.CURRENCY],
            series_exchange[tables.Exchange.Columns.COUNTRY_ISO_2],
            series_exchange[tables.Exchange.Columns.COUNTRY_ISO_3],
            series_exchange[tables.Exchange.Columns.EXCHANGE_CODE]
        ]
        rows = Query.execute(query, params)
        # One combination of arguments in table expected
        assert len(rows) == 0

    @staticmethod
    def symbol(series_symbol: pd.Series):
        query = sql.SQL(statements.Symbol.UPDATE_SYMBOL)
        params = [
            series_symbol[tables.Symbol.Columns.NAME],
            series_symbol[tables.Symbol.Columns.COUNTRY],
            series_symbol[tables.Symbol.Columns.CURRENCY],
            series_symbol[tables.Symbol.Columns.TYPE],
            series_symbol[tables.Symbol.Columns.SYMBOL_CODE],
            series_symbol[tables.Symbol.Columns.EXCHANGE_CODE],
            series_symbol[tables.Symbol.Columns.TIME_FRAME],
            series_symbol[tables.Symbol.Columns.SYMBOL_STATUS]
        ]
        rows = Query.execute(query, params)
        # One combination of arguments in table expected
        assert len(rows) == 0

    @staticmethod
    def sector(series_symbol: pd.Series):
        query = sql.SQL(statements.Symbol.UPDATE_SECTOR)
        params = [
            series_symbol[tables.Sector.Columns.SECTOR],
            series_symbol[tables.Sector.Columns.INDUSTRY],
            series_symbol[tables.Sector.Columns.GIC_SECTOR],
            series_symbol[tables.Sector.Columns.GIC_GROUP],
            series_symbol[tables.Sector.Columns.GIC_INDUSTRY],
            series_symbol[tables.Sector.Columns.GIC_SUB_INDUSTRY],
            series_symbol[tables.Sector.Columns.SYMBOL_CODE],
            series_symbol[tables.Sector.Columns.EXCHANGE_CODE],
        ]
        rows = Query.execute(query, params)
        # One combination of arguments in table expected
        assert len(rows) == 0