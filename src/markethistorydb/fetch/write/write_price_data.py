#!/usr/bin/env python12.9

"""Interface to time series DB"""

from datetime import datetime
import pandas as pd

from markethistorydb.db                import Database, tables
from markethistorydb.fetch.utils       import drop_records_before_1970
from markethistorydb.utils  import TimeFrame, SymbolStatus


class WritePriceData(object):
    def __init__(self, db: Database, time_frame: TimeFrame, symbol_status: SymbolStatus):
        self._db: Database = db
        self._time_frame: TimeFrame = time_frame
        self._symbol_status: SymbolStatus = symbol_status

    def get_last_datetime_of_price_data(self, series_symbol: pd.Series) -> datetime | None:
        symbol_code = series_symbol[tables.Symbol.Columns.SYMBOL_CODE]
        exchange_code = series_symbol[tables.Symbol.Columns.EXCHANGE_CODE]
        df_existing_ohlcv = self._db.read.newest_of_ohlcv({exchange_code: [symbol_code]}, self._time_frame)
        try:
            last_datetime = df_existing_ohlcv.iloc[0]["timestamp"].to_pydatetime()
        except IndexError:
            last_datetime = None
        return last_datetime

    def _prepare_data_for_db(self, df_price: pd.DataFrame, symbol_name: str) -> pd.DataFrame:
        """
        Converts the provider's timestamps to the datetimes the price tables store.

        The provider sends a daily price's date as an ISO string and a minute price's timestamp
        as Unix seconds, and the ingress writes either as it is, which a TIMESTAMP column rejects.

        :param df_price: Price records, timestamps as the provider sent them; the frame is not
            modified
        :param symbol_name: Symbol the records belong to, for the log
        :return: New frame with the timestamps as datetimes. Records from before 1970 are
            dropped, since QuestDB cannot store them, and a warning is logged.
        """
        if self._time_frame == TimeFrame.DAILY:
            timestamp_column, unit = tables.DailyOhlcv.TIMESTAMP_COLUMN, None
        else:
            timestamp_column, unit = tables.MinuteOhlcv.TIMESTAMP_COLUMN, "s"
        df_converted = df_price.copy()
        df_converted[timestamp_column] = pd.to_datetime(df_converted[timestamp_column], unit=unit)
        df_converted = drop_records_before_1970(df_converted, timestamp_column,
                                                "{0} price".format(self._time_frame.name), symbol_name)
        return df_converted

    def insert_price_data(self, df_price: pd.DataFrame, series_symbol: pd.Series) -> bool:
        """
        Inserts the symbol's price records into the table of the writer's time frame. Records
        from before 1970 are dropped, since QuestDB cannot store them, and a warning is logged.

        :param df_price: Price records with the table's columns, timestamps as the provider sent
            them
        :param series_symbol: Symbol the records belong to
        :return: True if records were inserted, False if every record was from before 1970
        :raises InsertError: If the ingress write still fails once the retries are used up
        """
        symbol_code = series_symbol[tables.Symbol.Columns.SYMBOL_CODE]
        exchange_code = series_symbol[tables.Symbol.Columns.EXCHANGE_CODE]
        df_records = self._prepare_data_for_db(df_price, "{0}.{1}".format(symbol_code, exchange_code))
        if df_records.empty:
            return False
        self._db.insert.ohlcv(df_records, symbol_code, exchange_code, self._time_frame, self._symbol_status)
        return True
