DROP TABLE IF EXISTS exchange;

-- No designated timestamp and no partitioning, which makes the table non-WAL: a write is immediatly 
-- visible to the next read, which the read-then-insert-or-update in fetch/write relies on. ILP over 
-- HTTP rejects non-WAL tables, so db/io/insert.py writes this table through SQL instead.
CREATE TABLE IF NOT EXISTS exchange (
    name                VARCHAR,    -- Full name of the exchange
    exchange_code       VARCHAR,    -- Exchange code used in EODHD APIs
    operating_mic       VARCHAR,    -- MIC codes for operating venues
    country             VARCHAR,    -- Country where the exchange operates
    currency            VARCHAR,    -- Default trading currencys
    country_iso_2       VARCHAR,    -- ISO2 country code
    country_iso_3       VARCHAR     -- ISO3 country code
);
