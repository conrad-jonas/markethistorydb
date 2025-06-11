DROP TABLE IF EXISTS daily_ohlcv;
DROP TABLE IF EXISTS minute_ohlcv;

CREATE TABLE daily_ohlcv (
    timestamp       TIMESTAMP,
	exchange_code   SYMBOL CAPACITY 10,
    symbol_code     SYMBOL CAPACITY 61000,
    open            DOUBLE,
    high            DOUBLE,
    low             DOUBLE,
    close           DOUBLE,
    adjusted_close  DOUBLE,
    volume          LONG
) TIMESTAMP(timestamp) PARTITION BY YEAR WAL
DEDUP UPSERT KEYS(timestamp, exchange_code, symbol_code);

CREATE TABLE minute_ohlcv (
    timestamp       TIMESTAMP,
    exchange_code   SYMBOL CAPACITY 3,
    symbol_code     SYMBOL CAPACITY 36000,
    gmt_offset      BYTE,
    open            DOUBLE,
    high            DOUBLE,
    low             DOUBLE,
    close           DOUBLE,
    volume          LONG
) TIMESTAMP(timestamp) PARTITION BY DAY WAL
DEDUP UPSERT KEYS(timestamp, exchange_code, symbol_code);

ALTER TABLE minute_ohlcv ALTER COLUMN exchange_code  ADD INDEX;
ALTER TABLE minute_ohlcv ALTER COLUMN symbol_code    ADD INDEX;
ALTER TABLE daily_ohlcv  ALTER COLUMN symbol_code    ADD INDEX;
ALTER TABLE daily_ohlcv  ALTER COLUMN symbol_code    ADD INDEX;