#!/usr/bin/env python12.9


class StatementsPrice:
    SELECT_CLOSE_FROM_DAILY_OHLCV = "SELECT close FROM daily_ohlcv WHERE timestamp = %s"
    SELECT_CLOSE_FROM_MINUTE_OHLCV = "SELECT close FROM minute_ohlcv WHERE timestamp = %s"

    SELECT_ALL_FROM_DAILY_OHLCV = (
        "SELECT timestamp, exchange_code, symbol_code, open, high, low, close, adjusted_close, volume "
        "FROM daily_ohlcv WHERE exchange_code = %s AND symbol_code IN ({symbol_codes}) "
        "AND %s <= timestamp AND timestamp <= %s")
    SELECT_LAST_FROM_DAILY_OHLCV = (
        "SELECT timestamp, exchange_code, symbol_code, open, high, low, close, adjusted_close, volume "
        "FROM daily_ohlcv WHERE exchange_code = %s AND symbol_code IN ({symbol_codes}) "
        "ORDER BY timestamp DESC LIMIT 1")
    SELECT_ALL_FROM_MINUTE_OHLCV = (
        "SELECT timestamp, exchange_code, symbol_code, gmt_offset, open, high, low, close, volume "
        "FROM minute_ohlcv WHERE exchange_code = %s AND symbol_code IN ({symbol_codes}) "
        "AND %s <= timestamp AND timestamp <= %s")
    SELECT_LAST_FROM_MINUTE_OHLCV = (
        "SELECT timestamp, exchange_code, symbol_code, gmt_offset, open, high, low, close, volume "
        "FROM minute_ohlcv WHERE exchange_code = %s AND symbol_code IN ({symbol_codes}) "
        "ORDER BY timestamp DESC LIMIT 1")

    DROP_SYMBOL_FROM_DAILY_OHLCV = (
        "CREATE TABLE daily_ohlcv_copy AS (",
        "SELECT * FROM daily_ohlcv WHERE symbol_code!=%s AND exchange_code!=%s",
        ") TIMESTAMP(timestamp) PARTITION BY YEAR WAL",
        "DEDUP UPSERT KEYS(timestamp, exchange_code, symbol_code);",
        "ALTER TABLE daily_ohlcv  ALTER COLUMN exchange_code  ADD INDEX;",
        "ALTER TABLE daily_ohlcv  ALTER COLUMN symbol_code    ADD INDEX;"
        "DROP TABLE daily_ohlcv;",
        "RENAME TABLE daily_ohlcv_copy TO daily_ohlcv;")
    DROP_SYMBOL_FROM_MINUTE_OHLCV = (
        "CREATE TABLE minute_ohlcv_copy AS (",
        "SELECT * FROM minute_ohlcv WHERE symbol_code!=%s AND exchange_code!=%s",
        ") TIMESTAMP(timestamp) PARTITION BY DAY WAL",
        "DEDUP UPSERT KEYS(timestamp, exchange_code, symbol_code);",
        "ALTER TABLE minute_ohlcv  ALTER COLUMN exchange_code  ADD INDEX;",
        "ALTER TABLE minute_ohlcv  ALTER COLUMN symbol_code    ADD INDEX;"
        "DROP TABLE minute_ohlcv;",
        "RENAME TABLE minute_ohlcv_copy TO minute_ohlcv;")