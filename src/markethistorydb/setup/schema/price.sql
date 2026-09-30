DROP TABLE IF EXISTS daily_ohlcv;
DROP TABLE IF EXISTS minute_ohlcv;

CREATE TABLE IF NOT EXISTS daily_ohlcv (
    timestamp       TIMESTAMP,
	exchange_code   SYMBOL CAPACITY 13,
    symbol_code     SYMBOL CAPACITY 65000,
    open            DOUBLE,
    high            DOUBLE,
    low             DOUBLE,
    close           DOUBLE,
    adjusted_close  DOUBLE,
    volume          LONG
) TIMESTAMP(timestamp) PARTITION BY YEAR WAL
DEDUP UPSERT KEYS(timestamp, exchange_code, symbol_code);

CREATE TABLE IF NOT EXISTS minute_ohlcv (
    timestamp       TIMESTAMP,
    exchange_code   SYMBOL CAPACITY 6,
    symbol_code     SYMBOL CAPACITY 40000,
    open            DOUBLE,
    high            DOUBLE,
    low             DOUBLE,
    close           DOUBLE,
    volume          DOUBLE
) TIMESTAMP(timestamp) PARTITION BY DAY WAL
DEDUP UPSERT KEYS(timestamp, exchange_code, symbol_code);

ALTER TABLE daily_ohlcv  ALTER COLUMN exchange_code  ADD INDEX;
ALTER TABLE daily_ohlcv  ALTER COLUMN symbol_code    ADD INDEX;
ALTER TABLE minute_ohlcv ALTER COLUMN exchange_code  ADD INDEX;
ALTER TABLE minute_ohlcv ALTER COLUMN symbol_code    ADD INDEX;