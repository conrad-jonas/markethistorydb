#!/usr/bin/env python12.9

"""Interface to relational DB"""

import logging

import pandas as pd

from markethistorydb.db           import tables, Database
from markethistorydb.errors       import SchemaMismatchError
from markethistorydb.fetch.utils  import (FundamentalType, TABLE_PER_FUNDAMENTAL_TYPE,
                                          convert_df_column_names_from_camel_to_snake_case,
                                          drop_records_before_1970)

logger = logging.getLogger(__name__)

# Fundamental columns the provider sends as dates and that are stored as TIMESTAMP
_DATE_COLUMNS = {tables.EarningsQuarterly.Columns.REPORT_DATE, tables.EarningsQuarterly.Columns.DATE,
                 tables.BalanceSheetQuarterly.Columns.FILING_DATE}
# Fundamental columns stored as text (SYMBOL); every other column is stored as DOUBLE
_TEXT_COLUMNS = {tables.EarningsQuarterly.Columns.SYMBOL_CODE, tables.EarningsQuarterly.Columns.EXCHANGE_CODE,
                 tables.EarningsQuarterly.Columns.BEFORE_AFTER_MARKET, tables.EarningsQuarterly.Columns.CURRENCY,
                 tables.BalanceSheetQuarterly.Columns.CURRENCY_SYMBOL}


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

    @staticmethod
    def _adjust_data_types(df_fundamental: pd.DataFrame, timestamp_column: str) -> pd.DataFrame:
        """
        Converts the provider's values (i.e. amounts as strings (e.g. "383266000000.00") 
        and dates as ISO strings) to the types the fundamental tables store.

        :param df_fundamental: Records with snake case columns, values as the provider sent them
        :param timestamp_column: Designated timestamp column of the target table
        :return: New frame with dates as datetimes, text as strings and everything else as
            floats; a value that cannot be converted becomes null. Records without a designated
            timestamp are dropped, since QuestDB cannot store them.
        """
        converted: dict[str, pd.Series] = {}
        for column in df_fundamental.columns:
            if column in _DATE_COLUMNS:
                converted[column] = pd.to_datetime(df_fundamental[column], errors="coerce")
            elif column in _TEXT_COLUMNS:
                converted[column] = df_fundamental[column].astype("string")
            else:
                converted[column] = pd.to_numeric(df_fundamental[column], errors="coerce").astype("float64")
        df_converted = pd.DataFrame(converted).reset_index(drop=True)
        return df_converted[df_converted[timestamp_column].notna()]

    def _prepare_data_for_db(self, df_fundamental: pd.DataFrame,
                             table: type[tables.FundamentalTable]) -> pd.DataFrame:
        """
        Converts the provider's records to rows of *table*.

        :param df_fundamental: Records as the provider sent them, columns in camel case; the
            frame is not modified
        :param table: Table the records are written to
        :return: New frame with snake case columns, the symbol's codes and the types the table
            stores. Records without a designated timestamp or with one from before 1970 are
            dropped, since QuestDB cannot store them; a warning is logged for the latter.
        """
        df_records = convert_df_column_names_from_camel_to_snake_case(df_fundamental.copy())
        df_records[table.Columns.SYMBOL_CODE] = self._symbol_code
        df_records[table.Columns.EXCHANGE_CODE] = self._exchange_code
        df_records = self._adjust_data_types(df_records, table.TIMESTAMP_COLUMN)
        df_records = drop_records_before_1970(df_records, table.TIMESTAMP_COLUMN, table.NAME,
                                        "{0}.{1}".format(self._symbol_code, self._exchange_code))
        return df_records


    def _check_columns(self, df_records: pd.DataFrame, table: type[tables.FundamentalTable]):
        """
        Checks that *table* has every column of *df_records*.

        Checked before the symbol's records are deleted: the DB would reject the new records
        only after that, leaving the table without the symbol's records.

        :param df_records: Records prepared for *table*
        :param table: Table the records are written to
        :raises SchemaMismatchError: If a column of *df_records* is not a column of *table*,
            most likely a field the provider has started to send
        """
        unknown_columns = [column for column in df_records.columns if column not in table.ALL_COLUMNS]
        if unknown_columns:
            raise SchemaMismatchError("Table {0} has no column(s) {1} the records of {2}.{3} hold".format(
                table.NAME, ", ".join(unknown_columns), self._symbol_code, self._exchange_code))

    def _replace_fundamental_data_in_table(self, df_fundamental: pd.DataFrame,
                                           table: type[tables.FundamentalTable]):
        """
        Replaces the symbol's records in *table* with *df_fundamental*. Converts data types and 
        drops records without a designated timestamp or with one from before 1970, since QuestDB cannot store them.


        :param df_fundamental: Records to write, columns still in camel case
        :param table: Table the records are written to
        :raises SchemaMismatchError: If *df_fundamental* holds a column *table* does not have;
            the table is left untouched
        :raises QueryError: If deleting the symbol's existing records failed
        :raises InsertError: If the ingress write still fails once the retries are used up,
            leaving the table without the symbol's records
        """
        df_records = self._prepare_data_for_db(df_fundamental, table)
        self._check_columns(df_records, table)
        if df_records.empty:
            logger.warning("No {0} records with a {1} from 1970 on for {2}.{3}, keeping the stored ones".format(
                table.NAME, table.TIMESTAMP_COLUMN, self._symbol_code, self._exchange_code))
            return
        self._db.delete.symbol_from_table(self._symbol_code, self._exchange_code,
                                          table.NAME,
                                          table.TIMESTAMP_COLUMN,
                                          table.UNIQUE_KEY_COLUMNS)
        self._db.insert.table(df_records,
                              table.NAME,
                              table.TIMESTAMP_COLUMN)

    def replace_fundamental_data(self, dict_symbol_fundamental: dict[FundamentalType, pd.DataFrame]):
        """
        Replaces the symbol's records in the table of every fundamental type in
        *dict_symbol_fundamental*; the tables of types it leaves out are not touched.

        :param dict_symbol_fundamental: Records per fundamental type
        :raises SchemaMismatchError: If the records of a type hold a column its table does not
            have; that table is left untouched
        :raises QueryError: If deleting the symbol's existing records failed
        :raises InsertError: If the ingress write still fails once the retries are used up
        """
        for fundamental_type, df_fundamental in dict_symbol_fundamental.items():
            self._replace_fundamental_data_in_table(df_fundamental,
                                                    TABLE_PER_FUNDAMENTAL_TYPE[fundamental_type])