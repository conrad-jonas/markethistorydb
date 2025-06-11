DROP TABLE IF EXISTS symbol_meta;

CREATE TABLE symbol_meta (
	code            TEXT,
	time_frame      TEXT,
    symbol_status   TEXT,
    name            TEXT,
    country         TEXT,
    exchange        TEXT,
    currency        TEXT,
    type            TEXT,
    isin            TEXT,
    PRIMARY KEY (code, time_frame, symbol_status, name),
    UNIQUE (code, time_frame, symbol_status, name)
);