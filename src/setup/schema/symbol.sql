DROP TABLE IF EXISTS symbol;
DROP TABLE IF EXISTS sector;

CREATE TABLE IF NOT EXISTS symbol (
    symbol_code         VARCHAR,
    exchange_code       SYMBOL,
    time_frame          SYMBOL,  -- Daily, Minute, etc.
    symbol_status       SYMBOL,  -- active or delisted
    name                VARCHAR, -- full company or instrument name
    country             SYMBOL,  -- country of listing
    currency            SYMBOL,  -- currency
    type                SYMBOL,  -- type of asset (e.g. Common Stock, ETF, Fund)
    isin                VARCHAR, -- International Securities Identification Number (if available)
    created_at          TIMESTAMP,
) TIMESTAMP(created_at) PARTITION BY DAY
  DEDUP UPSERT KEYS (symbol_code, exchange_code, time_frame, symbol_status);

CREATE TABLE IF NOT EXISTS sector (
    symbol_code         VARCHAR,
    exchange_code       SYMBOL,
    sector              SYMBOL,
    industry            SYMBOL,
    gic_sector          SYMBOL,
    gic_group           SYMBOL,
    gic_industry        SYMBOL,
    gic_sub_industry    SYMBOL
    created_at          TIMESTAMP,
) TIMESTAMP(created_at) PARTITION BY DAY
  DEDUP UPSERT KEYS (symbol_code, exchange_code);
