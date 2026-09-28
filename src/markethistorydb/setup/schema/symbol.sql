DROP TABLE IF EXISTS symbol;
DROP TABLE IF EXISTS sector;

-- No designated timestamp and no partitioning, which makes the table non-WAL: a write is immediatly 
-- visible to the next read, which the read-then-insert-or-update in fetch/write relies on. ILP over 
-- HTTP rejects non-WAL tables, so db/io/insert.py writes this table through SQL instead.

CREATE TABLE IF NOT EXISTS symbol (
    symbol_code         VARCHAR,
    exchange_code       SYMBOL,
    time_frame          SYMBOL,  -- Daily, Minute, etc.
    symbol_status       SYMBOL,  -- active or delisted
    name                VARCHAR, -- full company or instrument name
    country             SYMBOL,  -- country of listing
    currency            SYMBOL,  -- currency
    type                SYMBOL,  -- type of asset (e.g. Common Stock, ETF, Fund)
    isin                VARCHAR  -- International Securities Identification Number (if available)
);

CREATE TABLE IF NOT EXISTS sector (
    symbol_code         VARCHAR,
    exchange_code       SYMBOL,
    sector              SYMBOL,
    industry            SYMBOL,
    gic_sector          SYMBOL,
    gic_group           SYMBOL,
    gic_industry        SYMBOL,
    gic_sub_industry    SYMBOL
);
