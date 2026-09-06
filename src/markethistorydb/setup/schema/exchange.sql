DROP TABLE IF EXISTS exchange;

CREATE TABLE IF NOT EXISTS exchange (
    name                VARCHAR,    -- Full name of the exchange
    exchange_code       VARCHAR,    -- Exchange code used in EODHD APIs
    operating_mic       VARCHAR,    -- MIC codes for operating venues
    country             VARCHAR,    -- Country where the exchange operates
    currency            VARCHAR,    -- Default trading currencys
    country_iso_2       VARCHAR,    -- ISO2 country code
    country_iso_3       VARCHAR,    -- ISO3 country code
    created_at          TIMESTAMP,  -- Timestamp of creation
) TIMESTAMP(created_at) PARTITION BY YEAR
  DEDUP UPSERT KEYS (exchange_code);