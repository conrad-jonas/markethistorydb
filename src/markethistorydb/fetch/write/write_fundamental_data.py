#!/usr/bin/env python12.9

"""Interface to relational DB"""

import pandas as pd

from markethistorydb.db           import tables, Database
from markethistorydb.fetch.utils  import FundamentalType, convert_df_column_names_from_camel_to_snake_case


class WriteFundamentalData(object):
    def __init__(self, db: Database):
        self._db: Database = db
        self._symbol_code: str | None = None
        self._exchange_code: str | None = None

    def set_exchange_code(self, exchange_code: str):
        self._exchange_code = exchange_code

    def set_symbol_code(self, symbol_code: str):
        self._symbol_code = symbol_code

    def _format_sector_data(self, series_sector_and_industry: pd.Series) -> pd.Series:
        # Inserts symbol code and exchange code into series.
        series_sector_and_industry = pd.concat([pd.Series([self._symbol_code, self._exchange_code]),
                                                series_sector_and_industry])
        series_sector_and_industry.index = pd.Index(tables.Sector.ALL_COLUMNS)
        return series_sector_and_industry

    def _is_in_table_sector(self) -> bool:
        record_from_table = self._db.read.sector(self._symbol_code, self._exchange_code)
        return not record_from_table.empty

    def update_sector_data(self, series_sector_and_industry: pd.Series):
        series_sector_and_industry = self._format_sector_data(series_sector_and_industry)
        if not self._is_in_table_sector():
            self._db.insert.sector(series_sector_and_industry)
        else:
            self._db.update.sector(series_sector_and_industry)

    def _replace_fundamental_data_in_table(self, df_fundamental: pd.DataFrame,
                                           table: type[tables.FundamentalTable]):
        """
        Replaces historical fundamental table data for symbol into DB.

        :param df_fundamental: Records to write, columns still in camel case
        :param table: Table the records are written to
        :raises QueryError: If deleting the symbol's existing records failed
        :raises InsertError: If the ingress write still fails once the retries are used up,
            leaving the table without the symbol's records
        """
        df_fundamental[tables.EarningsQuarterly.Columns.SYMBOL_CODE] = self._symbol_code
        df_fundamental[tables.EarningsQuarterly.Columns.EXCHANGE_CODE] = self._exchange_code
        df_fundamental = convert_df_column_names_from_camel_to_snake_case(df_fundamental)
        self._db.delete.symbol_from_table(self._symbol_code, self._exchange_code,
                                          table.NAME,
                                          table.TIMESTAMP_COLUMN,
                                          table.UNIQUE_KEY_COLUMNS)
        self._db.insert.table(df_fundamental,
                              table.NAME,
                              table.TIMESTAMP_COLUMN)

    def replace_fundamental_data(self, dict_symbol_fundamental: dict[FundamentalType, pd.DataFrame]):
        self._replace_fundamental_data_in_table(dict_symbol_fundamental[FundamentalType.EARNINGS_QUARTERLY],
                                                tables.EarningsQuarterly)
        self._replace_fundamental_data_in_table(dict_symbol_fundamental[FundamentalType.EARNINGS_ANNUALLY],
                                                tables.EarningsAnnually)
        self._replace_fundamental_data_in_table(dict_symbol_fundamental[FundamentalType.BALANCE_SHEET_QUARTERLY],
                                                tables.BalanceSheetQuarterly)
        self._replace_fundamental_data_in_table(dict_symbol_fundamental[FundamentalType.BALANCE_SHEET_ANNUALLY],
                                                tables.BalanceSheetAnnually)
        self._replace_fundamental_data_in_table(dict_symbol_fundamental[FundamentalType.CASH_FLOW_QUARTERLY],
                                                tables.CashFlowQuarterly)
        self._replace_fundamental_data_in_table(dict_symbol_fundamental[FundamentalType.CASH_FLOW_ANNUALLY],
                                                tables.CashFlowAnnually)
        self._replace_fundamental_data_in_table(dict_symbol_fundamental[FundamentalType.INCOME_STATEMENT_QUARTERLY],
                                                tables.IncomeStatementQuarterly)
        self._replace_fundamental_data_in_table(dict_symbol_fundamental[FundamentalType.INCOME_STATEMENT_ANNUALLY],
                                                tables.IncomeStatementAnnually)