#!/usr/bin/env python12.9

import markethistorydb.db.tables as tables

_SYMBOL_TABLE      = tables.Symbol.NAME
_SYMBOL_COLUMNS    = ", ".join(tables.Symbol.ALL_COLUMNS)
_SYMBOL_CODE       = tables.Symbol.Columns.SYMBOL_CODE
_EXCHANGE_CODE     = tables.Symbol.Columns.EXCHANGE_CODE
_TIME_FRAME        = tables.Symbol.Columns.TIME_FRAME
_SYMBOL_STATUS     = tables.Symbol.Columns.SYMBOL_STATUS
_NAME              = tables.Symbol.Columns.NAME
_COUNTRY           = tables.Symbol.Columns.COUNTRY
_CURRENCY          = tables.Symbol.Columns.CURRENCY
_TYPE              = tables.Symbol.Columns.TYPE

_SECTOR_TABLE      = tables.Sector.NAME
_SECTOR_SYMBOL       = tables.Sector.Columns.SYMBOL_CODE
_SECTOR_EXCHANGE   = tables.Sector.Columns.EXCHANGE_CODE
_SECTOR            = tables.Sector.Columns.SECTOR
_INDUSTRY          = tables.Sector.Columns.INDUSTRY
_GIC_SECTOR        = tables.Sector.Columns.GIC_SECTOR
_GIC_GROUP         = tables.Sector.Columns.GIC_GROUP
_GIC_INDUSTRY      = tables.Sector.Columns.GIC_INDUSTRY
_GIC_SUB_INDUSTRY  = tables.Sector.Columns.GIC_SUB_INDUSTRY
# Sector select excludes exchange_code (caller already has it)
_SECTOR_SELECT_COLUMNS = ", ".join((_SECTOR_SYMBOL, _SECTOR, _INDUSTRY, _GIC_SECTOR, _GIC_GROUP,
                                    _GIC_INDUSTRY, _GIC_SUB_INDUSTRY))
_SECTOR_COLUMNS    = ", ".join(tables.Sector.ALL_COLUMNS)
_SYMBOL_PLACEHOLDERS = ", ".join(["%s"] * len(tables.Symbol.ALL_COLUMNS))
_SECTOR_PLACEHOLDERS = ", ".join(["%s"] * len(tables.Sector.ALL_COLUMNS))


class StatementsSymbol:
    INSERT_SYMBOL = f"INSERT INTO {_SYMBOL_TABLE} ({_SYMBOL_COLUMNS}) VALUES ({_SYMBOL_PLACEHOLDERS})"
    INSERT_SECTOR = f"INSERT INTO {_SECTOR_TABLE} ({_SECTOR_COLUMNS}) VALUES ({_SECTOR_PLACEHOLDERS})"

    UPDATE_SYMBOL = (
        f"UPDATE {_SYMBOL_TABLE} SET {_NAME}=%s, {_COUNTRY}=%s, {_CURRENCY}=%s, {_TYPE}=%s "
        f"WHERE {_SYMBOL_CODE}=%s AND {_EXCHANGE_CODE}=%s AND {_TIME_FRAME}=%s AND {_SYMBOL_STATUS}=%s")
    UPDATE_SECTOR = (
        f"UPDATE {_SECTOR_TABLE} SET {_SECTOR}=%s, {_INDUSTRY}=%s, {_GIC_SECTOR}=%s, {_GIC_GROUP}=%s, "
        f"{_GIC_INDUSTRY}=%s, {_GIC_SUB_INDUSTRY}=%s "
        f"WHERE {_SECTOR_SYMBOL}=%s AND {_SECTOR_EXCHANGE}=%s")

    SELECT_ALL_FROM_SYMBOL_BY_UNIQUE_KEYS = (
        f"SELECT {_SYMBOL_COLUMNS} FROM {_SYMBOL_TABLE} "
        f"WHERE {_SYMBOL_CODE}=%s AND {_EXCHANGE_CODE}=%s AND {_TIME_FRAME}=%s AND {_SYMBOL_STATUS}=%s")
    SELECT_ALL_FROM_SECTOR_BY_UNIQUE_KEYS = (
        f"SELECT {_SECTOR_SELECT_COLUMNS} FROM {_SECTOR_TABLE} WHERE {_SECTOR_SYMBOL}=%s AND {_SECTOR_EXCHANGE}=%s")

    # Each element is a separate statement (QuestDB executes one statement per query); {table_name_copy}
    # is a distinct placeholder from {table_name} so sql.Identifier() quoting isn't glued to literal "_copy" text.
    DROP_SYMBOL_FROM_TABLE = (
        "CREATE TABLE {table_name_copy} AS (SELECT * FROM {table_name} WHERE NOT (symbol_code = %s AND exchange_code = %s));",
        "DROP TABLE {table_name};",
        "RENAME TABLE {table_name_copy} TO {table_name};")
