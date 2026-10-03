#!/usr/bin/env python12.9

import markethistorydb.db.tables as tables

_DAILY_TABLE          = tables.DailyOhlcv.NAME
_DAILY_COLUMNS        = ", ".join(tables.DailyOhlcv.ALL_COLUMNS)
_DAILY_TIMESTAMP      = tables.DailyOhlcv.Columns.TIMESTAMP
_DAILY_EXCHANGE_CODE  = tables.DailyOhlcv.Columns.EXCHANGE_CODE
_DAILY_SYMBOL_CODE    = tables.DailyOhlcv.Columns.SYMBOL_CODE
_DAILY_CLOSE          = tables.DailyOhlcv.Columns.CLOSE
_DAILY_UNIQUE_KEYS    = ", ".join(tables.DailyOhlcv.UNIQUE_KEY_COLUMNS)

_MINUTE_TABLE         = tables.MinuteOhlcv.NAME
_MINUTE_COLUMNS       = ", ".join(tables.MinuteOhlcv.ALL_COLUMNS)
_MINUTE_TIMESTAMP     = tables.MinuteOhlcv.Columns.TIMESTAMP
_MINUTE_EXCHANGE_CODE = tables.MinuteOhlcv.Columns.EXCHANGE_CODE
_MINUTE_SYMBOL_CODE   = tables.MinuteOhlcv.Columns.SYMBOL_CODE
_MINUTE_CLOSE         = tables.MinuteOhlcv.Columns.CLOSE
_MINUTE_UNIQUE_KEYS   = ", ".join(tables.MinuteOhlcv.UNIQUE_KEY_COLUMNS)


class StatementsPrice:
    SELECT_CLOSE_FROM_DAILY_OHLCV = f"SELECT {_DAILY_CLOSE} FROM {_DAILY_TABLE} WHERE {_DAILY_TIMESTAMP} = %s"
    SELECT_CLOSE_FROM_MINUTE_OHLCV = f"SELECT {_MINUTE_CLOSE} FROM {_MINUTE_TABLE} WHERE {_MINUTE_TIMESTAMP} = %s"

    SELECT_ALL_FROM_DAILY_OHLCV = (
        f"SELECT {_DAILY_COLUMNS} FROM {_DAILY_TABLE} WHERE {_DAILY_EXCHANGE_CODE} = %s "
        f"AND {_DAILY_SYMBOL_CODE} IN ({{symbol_codes}}) "
        f"AND %s <= {_DAILY_TIMESTAMP} AND {_DAILY_TIMESTAMP} <= %s")
    SELECT_LAST_FROM_DAILY_OHLCV = (
        f"SELECT {_DAILY_COLUMNS} FROM {_DAILY_TABLE} WHERE {_DAILY_EXCHANGE_CODE} = %s "
        f"AND {_DAILY_SYMBOL_CODE} IN ({{symbol_codes}}) "
        f"LATEST ON {_DAILY_TIMESTAMP} PARTITION BY {_DAILY_SYMBOL_CODE}")
    SELECT_ALL_FROM_MINUTE_OHLCV = (
        f"SELECT {_MINUTE_COLUMNS} FROM {_MINUTE_TABLE} WHERE {_MINUTE_EXCHANGE_CODE} = %s "
        f"AND {_MINUTE_SYMBOL_CODE} IN ({{symbol_codes}}) "
        f"AND %s <= {_MINUTE_TIMESTAMP} AND {_MINUTE_TIMESTAMP} <= %s")
    SELECT_LAST_FROM_MINUTE_OHLCV = (
        f"SELECT {_MINUTE_COLUMNS} FROM {_MINUTE_TABLE} WHERE {_MINUTE_EXCHANGE_CODE} = %s "
        f"AND {_MINUTE_SYMBOL_CODE} IN ({{symbol_codes}}) "
        f"LATEST ON {_MINUTE_TIMESTAMP} PARTITION BY {_MINUTE_SYMBOL_CODE}")

    # Each element is a separate statement (QuestDB executes one statement per query). The
    # indexes are added once the copy has taken the original's name, since CREATE TABLE AS does
    # not carry them over and the original is dropped.
    DROP_SYMBOL_FROM_DAILY_OHLCV: tuple[str, ...] = (
        f"CREATE TABLE {_DAILY_TABLE}_copy AS ("
        f"SELECT * FROM {_DAILY_TABLE} WHERE NOT ({_DAILY_SYMBOL_CODE} = %s AND {_DAILY_EXCHANGE_CODE} = %s)"
        f") TIMESTAMP({_DAILY_TIMESTAMP}) PARTITION BY YEAR WAL "
        f"DEDUP UPSERT KEYS({_DAILY_UNIQUE_KEYS});",
        f"DROP TABLE {_DAILY_TABLE};",
        f"RENAME TABLE {_DAILY_TABLE}_copy TO {_DAILY_TABLE};",
        f"ALTER TABLE {_DAILY_TABLE} ALTER COLUMN {_DAILY_EXCHANGE_CODE} ADD INDEX;",
        f"ALTER TABLE {_DAILY_TABLE} ALTER COLUMN {_DAILY_SYMBOL_CODE} ADD INDEX;")
    DROP_SYMBOL_FROM_MINUTE_OHLCV: tuple[str, ...] = (
        f"CREATE TABLE {_MINUTE_TABLE}_copy AS ("
        f"SELECT * FROM {_MINUTE_TABLE} WHERE NOT ({_MINUTE_SYMBOL_CODE} = %s AND {_MINUTE_EXCHANGE_CODE} = %s)"
        f") TIMESTAMP({_MINUTE_TIMESTAMP}) PARTITION BY DAY WAL "
        f"DEDUP UPSERT KEYS({_MINUTE_UNIQUE_KEYS});",
        f"DROP TABLE {_MINUTE_TABLE};",
        f"RENAME TABLE {_MINUTE_TABLE}_copy TO {_MINUTE_TABLE};",
        f"ALTER TABLE {_MINUTE_TABLE} ALTER COLUMN {_MINUTE_EXCHANGE_CODE} ADD INDEX;",
        f"ALTER TABLE {_MINUTE_TABLE} ALTER COLUMN {_MINUTE_SYMBOL_CODE} ADD INDEX;")
