DROP TABLE IF EXISTS symbol_meta;

CREATE TABLE symbol_meta (
	symbol_code     TEXT,
	exchange_code   TEXT,
	time_frame      TEXT,
    symbol_status   TEXT,
    name            TEXT,
    country         TEXT,
    currency        TEXT,
    type            TEXT,
    isin            TEXT,
    PRIMARY KEY (symbol_code, exchange_code, time_frame, symbol_status, name),
    UNIQUE (symbol_code, exchange_code, time_frame, symbol_status, name)
);