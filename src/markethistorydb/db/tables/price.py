#!/usr/bin/env python12.9

from markethistorydb.db.tables.table import TimeSeriesTable


class TableDailyOhlcv(TimeSeriesTable):
    """Constants for the 'daily_ohlcv' table."""
    NAME = "daily_ohlcv"

    class Columns(TimeSeriesTable.Columns):
        TIMESTAMP      = "timestamp"
        EXCHANGE_CODE  = "exchange_code"
        SYMBOL_CODE    = "symbol_code"
        OPEN           = "open"
        HIGH           = "high"
        LOW            = "low"
        CLOSE          = "close"
        ADJUSTED_CLOSE = "adjusted_close"
        VOLUME         = "volume"

    # Designated timestamp column
    TIMESTAMP_COLUMN = Columns.TIMESTAMP

    # Columns that form the unique/dedup key
    UNIQUE_KEY_COLUMNS = (
        Columns.TIMESTAMP,
        Columns.EXCHANGE_CODE,
        Columns.SYMBOL_CODE,
    )

    # All columns in definition order
    ALL_COLUMNS = (
        Columns.TIMESTAMP,
        Columns.EXCHANGE_CODE,
        Columns.SYMBOL_CODE,
        Columns.OPEN,
        Columns.HIGH,
        Columns.LOW,
        Columns.CLOSE,
        Columns.ADJUSTED_CLOSE,
        Columns.VOLUME,
    )


class TableMinuteOhlcv(TimeSeriesTable):
    """Constants for the 'minute_ohlcv' table."""
    NAME = "minute_ohlcv"

    class Columns(TimeSeriesTable.Columns):
        TIMESTAMP     = "timestamp"
        EXCHANGE_CODE = "exchange_code"
        SYMBOL_CODE   = "symbol_code"
        GMT_OFFSET    = "gmt_offset"
        OPEN          = "open"
        HIGH          = "high"
        LOW           = "low"
        CLOSE         = "close"
        VOLUME        = "volume"

    # Designated timestamp column
    TIMESTAMP_COLUMN = Columns.TIMESTAMP

    # Columns that form the unique/dedup key
    UNIQUE_KEY_COLUMNS = (
        Columns.TIMESTAMP,
        Columns.EXCHANGE_CODE,
        Columns.SYMBOL_CODE,
    )

    # All columns in definition order
    ALL_COLUMNS = (
        Columns.TIMESTAMP,
        Columns.EXCHANGE_CODE,
        Columns.SYMBOL_CODE,
        Columns.GMT_OFFSET,
        Columns.OPEN,
        Columns.HIGH,
        Columns.LOW,
        Columns.CLOSE,
        Columns.VOLUME,
    )


# Type Hint for tables in this class
PriceTableType = TableDailyOhlcv | TableMinuteOhlcv
# Table names
TABLE_NAMES_PRICE = [TableDailyOhlcv.NAME, TableMinuteOhlcv.NAME]