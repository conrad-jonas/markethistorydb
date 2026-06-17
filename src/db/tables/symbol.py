#!/usr/bin/env python12.9

from db.tables import Table


class TableSymbol(Table):
    """Constants for the 'symbol' table."""
    NAME = "symbol"

    class Columns:
        SYMBOL_CODE     = "symbol_code"
        EXCHANGE_CODE   = "exchange_code"
        TIME_FRAME      = "time_frame"
        SYMBOL_STATUS   = "symbol_status"
        NAME            = "name"
        COUNTRY         = "country"
        CURRENCY        = "currency"
        TYPE            = "type"
        ISIN            = "isin"
        CREATED_AT      = "created_at"

    # Designated timestamp column
    TIMESTAMP_COLUMN = Columns.CREATED_AT

    # Columns that form the unique key
    UNIQUE_KEY_COLUMNS = (
        Columns.SYMBOL_CODE,
        Columns.EXCHANGE_CODE,
        Columns.TIME_FRAME,
        Columns.SYMBOL_STATUS
    )

    # All columns in definition order
    ALL_COLUMNS = (
        Columns.SYMBOL_CODE,
        Columns.EXCHANGE_CODE,
        Columns.TIME_FRAME,
        Columns.SYMBOL_STATUS,
        Columns.NAME,
        Columns.COUNTRY,
        Columns.CURRENCY,
        Columns.TYPE,
        Columns.ISIN,
        Columns.CREATED_AT,
    )


class TableSector(Table):
    """Constants for the 'sector' table."""
    NAME = "sector"

    class Columns:
        SYMBOL_CODE         = "symbol_code"
        EXCHANGE_CODE       = "exchange_code"
        SECTOR              = "sector"
        INDUSTRY            = "industry"
        GIC_SECTOR          = "gic_sector"
        GIC_GROUP           = "gic_group"
        GIC_INDUSTRY        = "gic_industry"
        GIC_SUB_INDUSTRY    = "gic_sub_industry"
        CREATED_AT          = "created_at"

    # Designated timestamp column
    TIMESTAMP_COLUMN = Columns.CREATED_AT

    # Columns that form the unique/dedup key
    UNIQUE_KEY_COLUMNS = (
        Columns.SYMBOL_CODE,
        Columns.EXCHANGE_CODE
    )

    # All columns in definition order
    ALL_COLUMNS = (
        Columns.SYMBOL_CODE,
        Columns.EXCHANGE_CODE,
        Columns.SECTOR,
        Columns.INDUSTRY,
        Columns.GIC_SECTOR,
        Columns.GIC_GROUP,
        Columns.GIC_INDUSTRY,
        Columns.GIC_SUB_INDUSTRY,
        Columns.CREATED_AT,
    )


# Type Hint for tables in this class
SymbolTableType = TableSymbol | TableSector
# Table names
TABLE_NAMES_SYMBOL = [TableSymbol.NAME, TableSector.NAME]