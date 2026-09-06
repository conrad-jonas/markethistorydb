#!/usr/bin/env python12.9

"""Provides write interface to db"""

from psycopg import sql
import pandas as pd

import markethistorydb.db.statements as statements
from markethistorydb.db.io.query import Query


class Update:
    @staticmethod
    def exchange(series_exchange: pd.Series):
        query = sql.SQL(statements.Exchange.UPDATE_EXCHANGE)
        params = [
            series_exchange["name"],
            series_exchange["operating_mice"],
            series_exchange["country"],
            series_exchange["currency"],
            series_exchange["country_iso_2"],
            series_exchange["country_iso_3"],
            series_exchange["exchange_code"]
        ]
        rows = Query.execute(query, params)
        # One combination of arguments in table expected
        assert len(rows) == 0

    @staticmethod
    def symbol(series_symbol: pd.Series):
        query = sql.SQL(statements.Symbol.UPDATE_SYMBOL)
        params = [
            series_symbol["name"],
            series_symbol["country"],
            series_symbol["currency"],
            series_symbol["type"],
            series_symbol["symbol_code"],
            series_symbol["exchange_code"],
            series_symbol["time_frame"],
            series_symbol["symbol_status"]
        ]
        rows = Query.execute(query, params)
        # One combination of arguments in table expected
        assert len(rows) == 0

    @staticmethod
    def sector(series_symbol: pd.Series):
        query = sql.SQL(statements.Symbol.UPDATE_SECTOR)
        params = [
            series_symbol["sector"],
            series_symbol["industry"],
            series_symbol["gic_sector"],
            series_symbol["gic_group"],
            series_symbol["gic_industry"],
            series_symbol["gic_sub_industry"],
            series_symbol["symbol_code"],
            series_symbol["exchange_code"],
        ]
        rows = Query.execute(query, params)
        # One combination of arguments in table expected
        assert len(rows) == 0