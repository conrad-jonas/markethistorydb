# MarketHistoryDB: design (status quo)

How the implemented system is built: its structure, its data model, one chapter per capability,
and the design decisions in force. What the system does is specified in `3_specs.md`; this file
explains how. Planned designs are in `planned_features/<nn>_<feature>/2_design.md` and enter this
file when the feature is merged (`1_constitution.md`, section 6.4).

Each capability chapter ends with its **known limitations**: structural properties of the design
that no requirement covers directly (testability, coupling, duplication, missing seams), each
with the planned feature that changes it. Shortfalls against requirements are listed only as
known gaps in `3_specs.md`; the design text may explain their cause and point to them.

Code state: `main` / `a646f9d`.

## Contents

| # | Chapter |
| - | ------- |
| 1 | Overview |
| 2 | Data model |
| 3 | STORAGE: QuestDB access and schema |
| 4 | PROVIDER: eodhd request layer |
| 5 | REFDATA: exchange, symbol and sector ingestion |
| 6 | PRICES: daily and minute price ingestion |
| 7 | FUND: fundamentals ingestion and replacement |
| 8 | RUNS: fetch orchestration |
| 9 | ACCESS: reading stored data |
| 10 | CLIENT: library facade |
| 11 | CONFIG: configuration |
| 12 | CLI: command line |
| 13 | LOGGING: log output and token masking |
| 14 | PACKAGING: package and entry points |
| 15 | QUALITY: the test suite |
| A | Design decisions in force |

---

## 1 Overview

### 1.1 Context

```
user ───► CLI: markethistorydb setup | fetch ───┐
                                                ├─► Client ─┬─► setup ──────────────────────────────┐
program ─► library ─────────────────────────────┘           ├─► fetch: Fetcher ─► eodhd.com         │
                                                            │          │          (HTTPS, API token)│
                                                            │          └────────────────────────────┤
                                                            └─► read ───────────────────────────────┤
                                                                                                    ▼
                                                                                                 QuestDB
```

- **eodhd.com** is the only provider. It is reached over HTTPS with the owner's API token.
- **QuestDB** is reached on two interfaces: SQL over the PostgreSQL wire protocol (port 8812
  by default) for DDL, reads and the reference tables, and ILP ingestion over HTTP (port 9000)
  for prices and fundamentals.
- Library and CLI run in the same process as the fetch. There is no server process of
  MarketHistoryDB's own.
- What both external systems must provide is listed in section 1.4.

### 1.2 Package layout today

| Module | Capability | Content |
| ------ | ---------- | ------- |
| `__init__.py`, `client.py` | CLIENT | `Client` facade; top-level names `Client`, `Config`, `MarketHistoryDbError`, `TimeFrame`, `SymbolStatus` |
| `errors.py` | CLIENT, CLI | exception hierarchy; `ErrorCode` exit codes; `ApiErrorCode` |
| `config.py` | CONFIG | `Config`: connection settings, connection strings |
| `cli.py`, `__main__.py` | CLI | command line |
| `setup/main.py`, `setup/schema/*.sql` | STORAGE | schema setup |
| `db/database.py`, `db/io/`, `db/statements/`, `db/tables/` | STORAGE, ACCESS | database access, SQL statements, table definitions |
| `fetch/fetcher.py` | RUNS | one fetch pass |
| `fetch/download/` | REFDATA, PRICES, FUND | per data kind: request, then write |
| `fetch/eodhd/` | PROVIDER | requests to eodhd.com |
| `fetch/write/` | REFDATA, PRICES, FUND | preparing records and writing them |
| `fetch/utils.py` | PRICES, FUND | fundamental types, the pre-1970 rule, column renaming, `FailedSymbol` |
| `utils/backoff.py` | PROVIDER, STORAGE | retries with backoff |
| `utils/logger.py`, `utils/redact.py` | LOGGING | log setup, token redaction |
| `utils/categories.py`, `utils/env.py` | CLIENT, CONFIG | `TimeFrame`, `SymbolStatus`; reading required environment variables |

### 1.3 Main flows

- **Setup:** `Client.setup()` or `markethistorydb setup` runs the schema files (chapter 3).
- **Fetch:** `Client.fetch()` runs one pass per time frame (daily, minute) and listing status
  (active, delisted). Each pass requests the exchanges, then their symbols, then per symbol its
  prices and, for NASDAQ and NYSE, its fundamentals; each result is written before the next
  request (chapters RUNS, REFDATA, PRICES, FUND).
- **Read:** `Client.read` is the `Read` object of the database access; each call runs SQL
  (chapter ACCESS).

### 1.4 External dependencies and their required configuration

| Dependency | What MarketHistoryDB needs from it | Checked by the code? |
| ---------- | ---------------------------------- | -------------------- |
| **QuestDB server** | Both interfaces reachable: PostgreSQL wire (default port 8812) and HTTP (default port 9000), with one user allowed to create, drop and write tables. **Server setting `line.auto.create.new.columns=false`** in its `server.conf` (or the environment variable `QDB_LINE_AUTO_CREATE_NEW_COLUMNS=false` for a container). With QuestDB's default (`true`), a field the provider starts to send silently becomes a new column instead of failing with `SchemaMismatchError` (STORAGE-S13, COR-6). No QuestDB version is pinned or checked. | **No.** Neither setup nor a fetch reads the setting; the README asks for it. Only the integration test of STORAGE-S13 checks it, and skips when it is not set. |
| **eodhd.com account** | An API token (`EODHD_API_TOKEN`) whose plan covers the endpoints used: exchanges list, symbol list, end-of-day, intraday, fundamentals. A plan without one of them makes its requests fail with `AccessRightsError` (403), an exhausted daily quota with `DataLimitError` (402) (chapter PROVIDER). | When the requests are made. |
| **Python and packages** | Python 3.12 or later; `pandas`, `psycopg[binary]`, `python-dotenv`, `questdb`, `requests` (`pyproject.toml`). | By the installer. |

---

## 2 Data model

### 2.1 Tables

| Table | Content | Designated timestamp | Partitioned by | WAL | Deduplication keys | Indexes | Columns |
| ----- | ------- | -------------------- | -------------- | --- | ------------------ | ------- | ------- |
| `exchange` | exchanges | — | — | no | — (key `exchange_code`) | — | 7 |
| `symbol` | symbols per time frame and listing status | — | — | no | — (key `symbol_code`, `exchange_code`, `time_frame`, `symbol_status`) | — | 9 |
| `sector` | sector and industry per symbol | — | — | no | — (key `symbol_code`, `exchange_code`) | — | 8 |
| `daily_ohlcv` | daily bars | `timestamp` | year | yes | `timestamp`, `exchange_code`, `symbol_code` | `exchange_code`, `symbol_code` | 9 |
| `minute_ohlcv` | one-minute bars | `timestamp` | day | yes | `timestamp`, `exchange_code`, `symbol_code` | `exchange_code`, `symbol_code` | 8 |
| `earnings_quarterly` | quarterly earnings | `report_date` | year | yes | `symbol_code`, `exchange_code`, `report_date` | — | 10 |
| `earnings_annually` | annual earnings | `date` (period end) | year | yes | `symbol_code`, `exchange_code`, `date` | — | 4 |
| `balance_sheet_quarterly`, `balance_sheet_annually` | balance sheets | `filing_date` | year | yes | `symbol_code`, `exchange_code`, `filing_date` | — | 65 each |
| `cash_flow_quarterly`, `cash_flow_annually` | cash-flow statements | `filing_date` | year | yes | `symbol_code`, `exchange_code`, `filing_date` | — | 34 each |
| `income_statement_quarterly`, `income_statement_annually` | income statements | `filing_date` | year | yes | `symbol_code`, `exchange_code`, `filing_date` | — | 35 each |

### 2.2 Columns

- **`exchange`** (all `VARCHAR`): `name`, `exchange_code`, `operating_mic`, `country`,
  `currency`, `country_iso_2`, `country_iso_3`.
- **`symbol`:** `symbol_code` (`VARCHAR`), `exchange_code`, `time_frame`, `symbol_status`,
  `name` (`VARCHAR`), `country`, `currency`, `type`, `isin` (`VARCHAR`). `time_frame` and
  `symbol_status` hold the enum names (`DAILY`, `MINUTE`; `ACTIVE`, `DELISTED`). A symbol listed
  for both time frames and both statuses has up to four records.
- **`sector`:** `symbol_code` (`VARCHAR`), `exchange_code`, `sector`, `industry`, `gic_sector`,
  `gic_group`, `gic_industry`, `gic_sub_industry`.
- **`daily_ohlcv`:** `timestamp`, `exchange_code`, `symbol_code`, `open`, `high`, `low`, `close`,
  `adjusted_close` (`DOUBLE`), `volume` (`LONG`).
- **`minute_ohlcv`:** `timestamp`, `exchange_code`, `symbol_code`, `open`, `high`, `low`,
  `close`, `volume` (all `DOUBLE`).
- **Fundamental tables:** `symbol_code`, `exchange_code`, the dates (`date` = period end;
  `filing_date` or `report_date`), a currency column, then the provider's fields renamed from
  camelCase to snake_case. The schema files carry the provider's description of each field as a
  comment.
- Columns not marked `VARCHAR`, `DOUBLE`, `LONG` or `TIMESTAMP` are `SYMBOL` (QuestDB's
  dictionary-encoded strings). The price tables size the symbol dictionaries for 13 (daily) and
  6 (minute) exchange codes and 65,000 (daily) and 40,000 (minute) symbol codes.

### 2.3 Conventions

- **Codes are eodhd's, and `exchange_code` has two meanings:**
  - in `exchange` it is the code of eodhd's exchange list, which also appears in request URLs,
    e.g. `US`, `LSE`, `FOREX`. `US` is a virtual exchange covering all US venues;
  - in `symbol`, `sector`, the price tables and the fundamental tables it is the exchange field of
    eodhd's symbol list, e.g. `NASDAQ`, `NYSE` or `NYSE ARCA` for symbols of `US`, `LSE` for
    symbols of `LSE`.

  The link from a symbol to its exchange-list code (needed for its requests) is not stored; it is
  carried in memory during a fetch (chapter REFDATA).

  **Planned:** `provider-interface` replaces both meanings by one canonical exchange per venue,
  identified by its MIC (e.g. `XNAS`, `XNYS`, `ARCX`); eodhd's list codes such as `US` become a
  detail of the eodhd adapter, used only to build requests (PRV-1, PRV-2).
- `symbol_code` is eodhd's ticker without the exchange suffix, e.g. `AAPL`.
- **Timestamps are naive and mean UTC:**
  - *Naive* means that the Python `datetime` values carry no time zone (`tzinfo` is `None`).
    QuestDB's `TIMESTAMP` has none either: it counts microseconds since 1970-01-01 00:00 UTC.
  - *Mean UTC* means that the clock time a value shows is UTC, never local time:
    `2026-10-09 14:30` is 14:30 UTC, which is 10:30 in New York.
  - **Daily bars** are stored at 00:00 UTC of their trading date. The timestamp is a date label,
    not the time of the close: the NYSE session of 2026-10-09 (13:30 to 20:00 UTC) is stored as
    `2026-10-09 00:00`.
  - **Minute bars** carry the provider's bar time, which eodhd sends as Unix seconds and which is
    stored as UTC.
  - **Fundamental dates** (period end, filing date, report date) are stored at 00:00 UTC of the
    date.
  - **Requests:** minute requests convert their bounds from naive UTC to Unix seconds; daily
    requests send plain dates (`YYYY-MM-DD`).
  - **Inputs:** a datetime passed to the library (e.g. the bounds of a read) is read as UTC. A
    local time therefore shifts the result by the machine's UTC offset, and a timezone-aware
    datetime is not rejected (COR-11, planned in `library-contract`). The README shows how to
    convert between local time and UTC.

---

## 3 STORAGE: QuestDB access and schema

### 3.1 Modules

| Module | Content |
| ------ | ------- |
| `setup/main.py` | `setup(config)`: runs the schema files |
| `setup/schema/*.sql` | `exchange.sql`, `fundamental.sql`, `price.sql`, `symbol.sql`: `DROP TABLE IF EXISTS`, then `CREATE TABLE IF NOT EXISTS` (and `ALTER TABLE … ADD INDEX` for the price tables) |
| `db/tables/` | table definitions as Python classes: `Table`, `TimeSeriesTable`, `FundamentalTable`, one class per table |
| `db/statements/` | SQL statement templates per table family (exchange, symbol, price, fundamental, meta) |
| `db/io/query.py` | `Query`: runs one SQL statement |
| `db/io/insert.py`, `update.py`, `delete.py` | writing: ingestion for time series, SQL for reference records; updates; deletes |
| `db/io/error.py` | `catch_ingress_error`: retry and classification of ingestion errors |
| `db/io/read.py` | `Read` (chapter ACCESS) |
| `db/database.py` | `Database`: bundles `query`, `read`, `insert`, `update`, `delete` for one `Config` |

### 3.2 Table definitions

- Each table is a class with the constants `NAME`, `TIMESTAMP_COLUMN` (`None` for the reference
  tables), `UNIQUE_KEY_COLUMNS`, `ALL_COLUMNS` and a nested `Columns` class naming each column.
- `Table.__init_subclass__` rejects a concrete subclass that does not define all four constants
  itself; abstract bases (`TimeSeriesTable`, `FundamentalTable`) pass `abstract=True` and cannot
  be instantiated.
- The groups `TABLE_NAMES_EXCHANGE`, `TABLE_NAMES_SYMBOL`, `TABLE_NAMES_PRICE` and
  `TABLE_NAMES_FUNDAMENTAL` list the tables per family.
- **The schema is defined twice:** in the `.sql` files, which `setup` runs, and in these classes,
  which the readers and writers use. Unit tests parse the `CREATE TABLE` statements of the schema
  files (`tests/unit/db/tables/schema.py`) and compare them with the classes; integration tests
  compare the created tables with them.

### 3.3 Setup

`setup` opens one psycopg connection with autocommit and executes each schema file as one
script, in the order `exchange.sql`, `fundamental.sql`, `price.sql`, `symbol.sql`. Each file
starts with `DROP TABLE IF EXISTS` for its tables. Errors are wrapped in `DbError`.

### 3.4 Writing

- **Prices and fundamentals:** `Insert.table(df, table_name, timestamp_column)` opens a
  `questdb.ingress.Sender` from `Config.http_conf`, sends the whole frame with
  `sender.dataframe(...)` and closes the sender, which flushes. `Insert.ohlcv` picks the table by
  time frame and logs the number of records.
- **Reference records:** `Insert.exchange`, `.symbol` and `.sector` build one `INSERT` with a
  value for every column of `ALL_COLUMNS` and run it through `Query`. `_sql_value` turns a missing
  value into `None` (NULL) and a numpy scalar into its Python value.
- **Updates:** `Update.exchange`, `.symbol` and `.sector` bind the record's values in the order
  the `UPDATE` statement expects, without conversion.
- **Uniqueness of reference records** is the writers' job: they read the record by its key and
  then insert or update (chapter REFDATA). This works because the reference tables are non-WAL,
  so a write is visible to the next read.

### 3.5 Errors and retries of the ingestion

`Insert.table` is decorated with `catch_ingress_error`:

1. A `QuestDBError` whose server answer (JSON after "Could not flush buffer: ") has the code
   `invalid` is a **rejection of the records**. If its message contains "does not exist" or
   "cast error", it becomes `SchemaMismatchError`, otherwise `InsertError`, at once.
2. A `QuestDBError` with a **transient code** (`CouldNotResolveAddr`, `SocketError`,
   `ConnectTimeout`, `ServerFlushError`, `ServerInternalError`, `FailoverRetry`) is retried by
   `call_with_backoff` (at most 3 attempts, 10 s base delay, factor 2), then given up as
   `InsertError`.
3. Every other `QuestDBError` becomes `InsertError` at once; other exceptions pass through.

Reference records go through `Query`, whose `QueryError` `Insert` wraps in `InsertError`
without retrying.

### 3.6 Running SQL

`Query.execute(query, params)` opens a psycopg connection from `Config.psycopg_conninfo`
(connect timeout 10 s, values quoted by `make_conninfo`) with `ClientCursor` and autocommit, runs
the statement with `params` as a tuple, fetches the rows if the statement has a result set, and
closes the connection. Every `psycopg.Error` becomes `QueryError`. Statements are composed with
`psycopg.sql` (`Identifier`, `Literal`), never with string formatting of values.

### 3.7 Deleting an instrument's records

- `Delete.symbol_from_table(symbol_code, exchange_code, table_name, timestamp_column,
  unique_key_columns)` picks the statement sequence by table family:
  - **symbol tables:** `CREATE TABLE <t>_copy AS (SELECT … WHERE NOT (symbol and exchange))`,
    `DROP TABLE <t>`, `RENAME TABLE <t>_copy TO <t>`; without a timestamp, so the copy is non-WAL;
  - **fundamental tables:** the same, with `TIMESTAMP(…) PARTITION BY YEAR WAL DEDUP UPSERT
    KEYS(…)` from the passed timestamp and key columns;
  - **price tables:** the same with the table's own partitioning, then `ADD INDEX` on
    `exchange_code` and `symbol_code`, because `CREATE TABLE AS` does not copy indexes.
- Each statement runs separately through `Query`; QuestDB has no multi-statement transactions.
- **Recovery** (`_recover_interrupted_deletion`): before the sequence, `SELECT table_name FROM
  tables()` looks up the table and its copy. A copy next to the table is dropped; a copy without
  the table is renamed back.
- **Only the fundamentals use it:** `WriteFundamentalData` deletes a symbol's records from each
  fundamental table before writing the new ones (chapter FUND). The symbol and price paths have
  no caller.

### 3.8 Unused code

No caller in the package (removal planned in `code-hygiene`):

- the statements `StatementsMeta.SELECT_SCHEMA` (used by an integration test only),
  `StatementsPrice.SELECT_CLOSE_FROM_DAILY_OHLCV` and `SELECT_CLOSE_FROM_MINUTE_OHLCV`;
- `StatementsFundamental.SELECT_ALL_FROM_*`, eight per-table reads: there is no read of
  fundamentals (MKT-14, planned in `query-layer`);
- the deletion paths for the symbol and price tables (section 3.7);
- `DUMMY_*` constants in `db/tables/fundamental.py` and the aliases `ExchangeTableType`,
  `PriceTableType`, `SymbolTableType`.

### 3.9 Known limitations

None besides the known gaps of `3_specs.md` 1.7.

---

## 4 PROVIDER: eodhd request layer

### 4.1 Modules

| Module | Content |
| ------ | ------- |
| `fetch/eodhd/url.py` | `Url.Address` (base URL and one builder per endpoint), `Url.Param`, `Url.Value`; `_path_segment` percent-encodes a code with `quote(code, safe="")` |
| `fetch/eodhd/request_data.py` | `RequestData`, the base of every request class: sending, status mapping, retries, shape and structure checks |
| `fetch/eodhd/request_exchange_data.py` | `RequestExchangeData`: exchange list, filtered to the exchanges of the time frame (chapter REFDATA) |
| `fetch/eodhd/request_symbol_data.py` | `RequestSymbolData`: symbol list of one exchange, filtered to the US venues of the time frame (chapter REFDATA) |
| `fetch/eodhd/request_price_data.py` | `RequestPriceData`: daily or minute bars of one symbol |
| `fetch/eodhd/request_fundamental_data.py` | `RequestFundamentalData`: fundamentals of one symbol |
| `fetch/eodhd/exchange_codes.py` | `ExchangeCodes`: `NASDAQ`, `NYSE`, `NYSE ARCA` |
| `utils/backoff.py` | `call_with_backoff`, shared with STORAGE |

### 4.2 Request flow

Every request class has a `get(...)` that builds the URL and the query parameters, then calls
`_request_list` (array endpoints) or `_request_object` (fundamentals):

```
get() ─► _request_list / _request_object ─► _request_data_from_url ─► call_with_backoff(_get)
                                                                              │
         _get: requests.get(url, params, timeout=(10, 120))  ◄────────────────┘
               404 → None │ _raise_for_status │ response.json()
```

Back in `get`, the payload is turned into a `pandas.DataFrame`, checked with `_has_columns`
(the expected fields as a subset of the columns, in any order) and formatted: fields renamed to
the table columns, codes, time frame and status added. An empty payload yields an empty frame.

### 4.3 Status codes and errors

| Answer | Error | Retried |
| ------ | ----- | ------- |
| 404 | none: "no data" (`None`) | — |
| 401 | `UnauthorizedError` (`AccountError`) | no |
| 402 | `DataLimitError` (`AccountError`) | no |
| 403 | `AccessRightsError` (`AccountError`) | no |
| 429 | `RateLimitError`, with `retry_after` from the header | yes |
| 500 and above | `BadGatewayError` | yes |
| other unsuccessful status | `ApiError` | no |
| timeout, failed connection | `NetworkError` | yes |
| other `requests` exception | `RequestError` | no |
| body not JSON, wrong shape, missing field | `CompatibilityError` | no |

Once the 3 attempts are used up, `call_with_backoff` raises `RequestError`. Account errors are
never retried, because neither a rejected token nor a used-up plan changes by waiting; the run
ends on them (chapter RUNS).

### 4.4 Backoff

`call_with_backoff(func, retry_on, give_up_error, max_attempts=3, base_delay_in_secs=10,
backoff_factor=2, max_delay_in_secs=3600, should_stop=None, description=None)`:

- **Delay** after attempt *n*: `retry_after` of the error if it has one, else
  `base_delay_in_secs × backoff_factor^(n−1)`; either is capped at `max_delay_in_secs`.
- **Waiting** in slices of 0.5 s on `time.monotonic()`, polling `should_stop` before each slice,
  so that a long `Retry-After` stays interruptible.
- **Values used:** requests 3 attempts from 10 s (10 s, 20 s); ingestion writes 3 attempts from
  10 s (STORAGE).

### 4.5 Keeping the token out of messages

- The token travels only as the query parameter `api_token`, never in the URL path.
- `_error_detail` masks the token in the response body with `redact_api_token` (chapter
  LOGGING) and then cuts it to 500 characters; masking first means a token at the cut-off point
  is masked, not cut in half.
- Exceptions from `requests` carry the full URL with the token. They are re-raised as
  `NetworkError` or `RequestError` with the token masked, `from None`, so that the original never
  appears in a traceback.
- The `description` passed to `call_with_backoff` is the URL without parameters.

### 4.6 Payloads and conversion

| Endpoint | Payload | Conversion |
| -------- | ------- | ---------- |
| `exchanges-list` | array of exchanges | rename to `exchange` columns; keep the exchanges of the time frame (REFDATA) |
| `exchange-symbol-list/{exchange}` | array of symbols | for `US`, keep the venues of the time frame (REFDATA); rename to `symbol` columns; add `time_frame` and `symbol_status`; keep the table's column order |
| `eod/{symbol}.{exchange}` | array of daily bars | `date` → `timestamp`; add codes |
| `intraday/{symbol}.{exchange}` | array of minute bars | keep `timestamp` (Unix seconds; converted to datetimes when written, chapter PRICES); drop `datetime`, `gmtoffset`; add codes |
| `fundamentals/{symbol}.{exchange}` | object with flattened section keys (`General::Sector`, `Earnings::History`, `Financials::Balance_Sheet`, …) | six sector and industry values as a `Series`; each record set (`quarterly`/`yearly` dicts keyed by date) as a transposed `DataFrame`; drop unstored fields; camelCase → snake_case; leave out empty record sets |

### 4.7 Object lifecycle

- `RequestExchangeData` and `RequestSymbolData` are created per pass, `RequestPriceData` and
  `RequestFundamentalData` per symbol: the symbol is constructor state (chapters PRICES, FUND).
  For minute bars, one `RequestPriceData` serves all 120-day windows of the symbol.
- Every request class takes the time frame, including the fundamentals, which don't depend on it.
- `requests.get` is called directly: there is no shared `requests.Session`, so each request opens
  its own connection.

### 4.8 Known limitations

| Limitation | Effect | Planned change |
| ---------- | ------ | -------------- |
| Transport, retries, status mapping, validation and conversion are mixed in the request classes | the pure parts (status mapping, validation, conversion) can only be tested through an HTTP fake | `testable-core`, `provider-interface` |
| The symbol is constructor state of the price and fundamentals request objects | a new object per symbol; one object can't serve several symbols or threads | `testable-core` |

---

## 5 REFDATA: exchange, symbol and sector ingestion

### 5.1 Modules

| Module | Content |
| ------ | ------- |
| `fetch/download/download_exchange_data.py` | `DownloadExchangeData`: requests the exchange list, applies the target exchange, writes the exchanges, returns their list codes |
| `fetch/download/download_symbol_data.py` | `DownloadSymbolData`: requests the symbol list of each exchange, tags each symbol with `exchange_url_code`, writes the symbols, returns them |
| `fetch/write/write_exchange_data.py` | `WriteExchangeData.update_exchange_data`: insert or update one exchange |
| `fetch/write/write_symbol_data.py` | `WriteSymbolData.update_symbol_data`: insert or update one symbol, for the writer's time frame and status |
| `fetch/write/write_fundamental_data.py` | `WriteFundamentalData.update_sector_data`: insert or update the sector record of the current symbol (the rest of the module: chapter FUND) |
| `fetch/eodhd/request_exchange_data.py` | `_EXCHANGE_NAMES_EOD`, `_EXCHANGE_NAMES_MINUTE`: the exchange selection per time frame |
| `fetch/eodhd/request_symbol_data.py` | `_US_EXCHANGE_CODES_EOD`, `_US_EXCHANGE_CODES_MINUTE`: the US venues per time frame |

### 5.2 Flow of one pass

```
Fetcher.run()
  └─► DownloadExchangeData.run()
        RequestExchangeData.get()          1 request: exchanges-list, filtered by name per time frame
        filter by target exchange name     (optional)
        update_exchange_data, per exchange read, then insert or update (2 SQL statements)
        ─► list codes, e.g. ["US", "LSE", ...]
  └─► DownloadSymbolData.run(list codes)
        RequestSymbolData.get(code)        1 request per exchange; US cut down to its venues
        tag with exchange_url_code
        update_symbol_data, per symbol     read, then insert or update (2 SQL statements)
        ─► symbols for the price and fundamentals downloads (chapter RUNS)
```

The sector record is written per symbol in the fundamentals download, after the request and
before the fundamental tables are replaced (chapter FUND).

### 5.3 Selection and requests

| Time frame | Exchanges kept (by list name) | US venues kept |
| ---------- | ----------------------------- | -------------- |
| daily | USA Stocks, London Exchange, Toronto Exchange, XETRA Stock Exchange, Shanghai Stock Exchange, FOREX, Cryptocurrencies, Government Bonds | NASDAQ, NYSE, NYSE ARCA |
| minute | USA Stocks, FOREX, Cryptocurrencies | NASDAQ, NYSE |

The filter by name happens in the request class, the filter by target exchange name in the
download class.

**List requests of a full run** (four passes, no target exchange):

| Pass | Exchange list | Symbol lists | Same answer as |
| ---- | ------------- | ------------ | -------------- |
| daily, active | 1 | 8: the eight daily exchanges | — |
| daily, delisted | 1 | 8: the eight daily exchanges | — |
| minute, active | 1 | 3: USA Stocks, FOREX, Cryptocurrencies | the exchange list and these 3 symbol lists of *daily, active* |
| minute, delisted | 1 | 3: USA Stocks, FOREX, Cryptocurrencies | the exchange list and these 3 symbol lists of *daily, delisted* |
| **total** | **4** | **22** | |

- **Why answers repeat:** the exchange list request carries only the token. A symbol list
  request depends on the exchange and the listing status (`delisted=1`), not on the time frame;
  the cut to the venues of the time frame happens after the answer has arrived. So all four
  passes get the same exchange list, and the daily and minute pass of one status get the same
  lists for USA Stocks, FOREX and Cryptocurrencies.
- **What is needed:** 1 exchange list + 8 active + 8 delisted symbol lists = 17 requests.
  9 of the 26 requests repeat an earlier one.

### 5.4 Writing

- **Read, then insert or update:** the writer reads the record by its key (`Read.exchange`,
  `Read.symbol`, `Read.sector`); an empty result means insert, otherwise update. This needs the
  reference tables to be non-WAL, so that a record written for one symbol is seen by the next
  read (appendix A), and it needs a single writer, since the database enforces no key.
- **Row by row:** `DataFrame.apply(..., axis=1)` calls the writer once per row. Each exchange
  and each symbol therefore costs two SQL statements, a `SELECT` by key, then an `INSERT` or an
  `UPDATE`, and each statement opens its own connection (STORAGE-S16). A pass with *n* exchanges
  and *m* symbols runs 2 (*n* + *m*) statements. An empty frame is checked before, so the writer
  is never called with an empty row.
- **Every run, whether anything changed or not:** a stored record is updated with the values
  just received, even when they equal the stored ones. With, say, 8 exchanges and 10,000 symbols
  in a pass, that pass runs 20,016 statements on as many connections before the first price is
  requested; the next run does the same again. The numbers are an illustration, not a
  measurement (the baseline is planned in `data-integrity-checks`).
- **Per pass, not per symbol:** a US stock in the daily and in the minute pass is read and written
  in both passes, under its two records (REFDATA-S06).
- **What an update keeps:** the symbol update leaves the ISIN unchanged (STORAGE-S11).

### 5.5 The two exchange codes

`DownloadSymbolData` adds the column `exchange_url_code` to each symbol: the list code the symbol
list was requested with. The price and fundamentals requests build their URLs from it, while
all tables store the symbol's own `exchange_code`, the venue (section 2.3). The column is not
part of the `symbol` table, so the insert leaves it out (STORAGE-S10).

### 5.6 Known limitations

| Limitation | Effect | Planned change |
| ---------- | ------ | -------------- |
| The selection is spread over three places: exchange names per time frame in `RequestExchangeData`, US venues in `RequestSymbolData`, the target exchange in `DownloadExchangeData` | selection rules mixed with transport; changing the scope touches three classes | `settings-model`, `provider-interface` |

---

## 6 PRICES: daily and minute price ingestion

### 6.1 Modules

| Module | Content |
| ------ | ------- |
| `fetch/download/download_price_data.py` | `DownloadPriceData.run(series_symbol)`: works out the start, requests the bars (one request for daily bars, one per window for minute bars), hands them to the writer. Constants `_START_DATE_MINUTE_DATA` (2005-01-01) and `_NUM_OF_DAYS_PER_MINUTE_DATA_REQUEST` (120) |
| `fetch/write/write_price_data.py` | `WritePriceData`: `get_last_datetime_of_price_data` (newest stored bar), `insert_price_data` (convert, drop pre-1970, write) |
| `fetch/utils.py` | `drop_records_before_1970`, shared with FUND |
| `fetch/eodhd/request_price_data.py` | the requests (chapter PROVIDER) |

### 6.2 Flow per symbol

```
DownloadPriceData.run(symbol)
  ├─ start = newest stored bar (Read.newest_of_ohlcv, 1 SQL statement) + 1 day | + 1 minute
  ├─ daily:  RequestPriceData.get(start)                      1 request, from = start, no end
  │  minute: windows = split(start or 2005-01-01, today 00:00 UTC, 120 days)
  │          RequestPriceData.get(window) per window          1 request per window
  │          pd.concat(all windows)                           whole history in memory
  ├─ empty?  log "No data exists ...", return False
  └─ WritePriceData.insert_price_data
        convert timestamps, drop_records_before_1970
        Insert.ohlcv ─► ILP over HTTP, 1 batch (STORAGE)
```

`run` returns whether bars were written; the run ignores the value and counts the symbol as
downloaded either way (chapter RUNS).

### 6.3 Incremental start

- `Read.newest_of_ohlcv({venue: [symbol]}, time_frame)` uses `LATEST ON timestamp PARTITION BY
  symbol_code`, filtered by exchange code and symbol code (chapter ACCESS). The price tables have
  no listing status, so the active and the delisted pass of a symbol code on one venue see the
  same newest bar.
- **Daily:** start = newest bar + 1 day, sent as `from=YYYY-MM-DD`; the end is left to the
  provider, so the answer reaches the provider's latest bar.
- **Minute:** start = newest bar + 1 minute. The end is 00:00 UTC of the current day, computed
  from `datetime.now(UTC)`: a run never asks for the day in progress, so minute data lags by up
  to a day. The code records no reason for this end; since the next run starts one minute after
  the newest bar, ending at the current time would work as well, as long as the provider
  delivers only completed bars.

### 6.4 Windows

`_get_time_periods_for_minute_data_requests(start)` returns `(start, end)` pairs: the first
starts at `start` (or 2005-01-01), each ends 120 days later or at the overall end, and the next
starts at the previous end.

- **Boundaries:** a window's end is the next window's start. If the provider includes both
  bounds, the bar at a boundary arrives twice; deduplication stores it once (STORAGE-S05).
- **Number of requests** for a symbol without stored minute bars: ⌈days since 2005-01-01 / 120⌉,
  67 on 2026-10-18. For a symbol already up to date: none.
- **Memory:** all windows are concatenated into one frame before writing, so a symbol's whole
  minute history is in memory at once and written by one ingestion call (STORAGE-T14).

### 6.5 Conversion

- **Timestamps:** `pd.to_datetime(column)` for daily date strings, `pd.to_datetime(column,
  unit="s")` for minute Unix seconds; both give naive datetimes meaning UTC.
- **Before 1970:** `drop_records_before_1970` keeps the rows with a timestamp from 1970-01-01 on,
  renumbers the index and logs the number dropped. QuestDB's designated timestamp starts at the
  Unix epoch, and the ingestion client refuses earlier values (STORAGE-S08).
- The frame received is copied before conversion, so the caller's frame stays unchanged.

### 6.6 Cost per symbol and pass

| | Daily | Minute, new symbol | Minute, incremental |
| - | ----- | ------------------ | ------------------- |
| SQL statements | 1 (newest bar) | 1 | 1 |
| Provider requests | 1 | about 67 | 1 or 2 (one per window since the newest bar) |
| Ingestion calls | 1 | 1 | 1 |

### 6.7 Known limitations

| Limitation | Effect | Planned change |
| ---------- | ------ | -------------- |
| Daily and minute bars share the request, download and write classes, which branch on the time frame | every change touches both paths; another time frame needs edits in every branch | `testable-core` |
| The window planning reads the current date itself (`datetime.now`) | tests replace the module's `datetime` to pin "today"; no injected clock | `testable-core` |

---

## 7 FUND: fundamentals ingestion and replacement

### 7.1 Modules

| Module | Content |
| ------ | ------- |
| `fetch/download/download_fundamental_data.py` | `DownloadFundamentalData.run(series_symbol)`: venue check, request, sector, replacement. Constant `_EXCHANGE_CODES_WITH_FUNDAMENTALS` (`NASDAQ`, `NYSE`) |
| `fetch/write/write_fundamental_data.py` | `WriteFundamentalData`: `update_sector_data` (chapter REFDATA), `replace_fundamental_data` and its helpers (`_prepare_data_for_db`, `_adjust_data_types`, `_check_columns`, `_replace_fundamental_data_in_table`) |
| `fetch/utils.py` | `FundamentalType`, `TABLE_PER_FUNDAMENTAL_TYPE` (record set → table), `convert_df_column_names_from_camel_to_snake_case`, `drop_records_before_1970` |
| `fetch/eodhd/request_fundamental_data.py` | the request (chapter PROVIDER) |

### 7.2 Flow per symbol

```
DownloadFundamentalData.run(symbol)
  ├─ venue not NASDAQ or NYSE?  return False                 no request
  ├─ RequestFundamentalData.get()                            1 request, full history
  ├─ no record set?             return False                 nothing written
  ├─ writer.set_exchange_code / set_symbol_code              the symbol as writer state
  ├─ update_sector_data                                      2 SQL statements (REFDATA)
  └─ replace_fundamental_data: per record set, in table order
        prepare: snake_case, add codes, convert types, drop no-timestamp and pre-1970
        check columns ─► SchemaMismatchError, table untouched
        nothing left? warn, keep stored records
        Delete.symbol_from_table   recovery check + copy, drop, rename (STORAGE: 4 SQL statements,
                                   5 with a leftover copy)
        Insert.table               ILP over HTTP, 1 batch
```

`run` returns whether fundamentals were written; the run ignores the value (chapter RUNS).

### 7.3 Type conversion

| Columns | Conversion | Stored as |
| ------- | ---------- | --------- |
| `report_date`, `date`, `filing_date` | `pd.to_datetime(errors="coerce")` | `TIMESTAMP`; an unreadable date becomes NULL, which for the designated timestamp means the record is dropped |
| `symbol_code`, `exchange_code`, `before_after_market`, `currency`, `currency_symbol` | `astype("string")` | `SYMBOL` |
| every other column | `pd.to_numeric(errors="coerce")`, `float64` | `DOUBLE`; a value that is no number becomes NULL |

The provider sends amounts as decimal strings and dates as ISO strings; without the conversion
the ingestion would send strings, which the `DOUBLE` and `TIMESTAMP` columns reject. The
converted frame gets a fresh index.

### 7.4 Replacement and its order

- **Check, then delete, then write:** `_check_columns` runs before the deletion, because the
  database would reject unknown columns only after the deletion, losing the stored records.
  This check is what turns a new provider field into a `SchemaMismatchError` here even without
  the server setting (STORAGE-S13).
- **Nothing left, nothing deleted:** if preparation drops every record, the table is left as it
  is, so that the stored records aren't replaced by nothing.
- **Not atomic:** the deletion is the copy, drop and rename of STORAGE-S19; the write follows as a
  separate WAL write. Between the two, and if the write fails, the table lacks the symbol's
  records.
- **Cost per symbol:** one request; per non-empty record set, the deletion (rebuilding the whole
  table without the symbol) and one ingestion call. Rebuilding the table means the cost of each
  replacement grows with the size of the table, not with the symbol's records.

### 7.5 Writer state

`WriteFundamentalData` holds the current symbol in `_symbol_code` and `_exchange_code`, set by
`set_symbol_code` and `set_exchange_code` before each symbol. This contradicts testing rule 2 of
the constitution (a symbol is a method argument, not setter state) and is changed in
`testable-core`.

### 7.6 Known limitations

| Limitation | Effect | Planned change |
| ---------- | ------ | -------------- |
| The symbol is writer state, set by `set_symbol_code` and `set_exchange_code` before each symbol | the writer can't be shared across concurrent symbols; contradicts testing rule 2 | `testable-core` |
| Field names are converted to snake_case twice, in the request class and again in the writer | duplicated responsibility | `code-hygiene` |

---

## 8 RUNS: fetch orchestration

### 8.1 Modules

| Module | Content |
| ------ | ------- |
| `client.py` | `Client.fetch(time_frame, symbol_status, exchange, should_stop)`: the pass loop and the fetch total |
| `fetch/fetcher.py` | `Fetcher`: one pass; per-symbol loop, failure handling, counters, summary, storage check. Constants `_MIN_FREE_SPACE_IN_GB` (50), `_MAX_CONSECUTIVE_SYMBOL_FAILURES` (20), `_NUM_OF_FAILURES_IN_SUMMARY` (10) |
| `fetch/utils.py` | `FailedSymbol(symbol_code, exchange_code, error_type_name)`, a frozen dataclass |

### 8.2 Flow

```
Client.fetch(time_frame, symbol_status, exchange, should_stop)
  for tf in (DAILY, MINUTE), status in (ACTIVE, DELISTED), filtered:
    Fetcher(db, token, tf, status, exchange, should_stop).run()      a new Fetcher per pass
      DownloadExchangeData.run()  ─► list codes                      (REFDATA)
      DownloadSymbolData.run()    ─► symbols                         (REFDATA)
      log counts
      try:
        for symbol in symbols:
          should_stop()?        ─► UserInterruptError
          disk_usage("/") < 50 GB ─► StorageError
          DownloadPriceData.run(symbol)                              (PRICES)
          DownloadFundamentalData.run(symbol)                        (FUND)
      finally:
        log summary
    add requested and failed counts
  log total, warn about skipped symbols
  return total requested
```

There is no error handling between passes: whatever leaves `Fetcher.run` leaves
`Client.fetch`.

### 8.3 Error handling

| Error raised for a symbol | Symbol recorded as failed | Pass | Fetch |
| ------------------------- | ------------------------- | ---- | ----- |
| `FetchError`, `DbError` (incl. `RequestError`, `CompatibilityError`, `InsertError`, `SchemaMismatchError`, `QueryError`) | yes | goes on; ends with `FetchError` after 20 in a row | ends if the pass ends |
| `AccountError` | yes | ends at once, error re-raised | ends |
| `UserInterruptError` (stop function) | no | ends | ends |
| `StorageError` | no | ends | ends |
| anything else (e.g. `KeyboardInterrupt`, a bug) | no | ends | ends |

Errors of the exchange and symbol lists aren't caught at all; they end the pass, and with it the
fetch, before any symbol is handled.

### 8.4 Counters and summary

- `num_of_requested_symbols` is set from the symbol list before the loop, so the summary is right
  even when the pass ends early.
- `num_of_downloaded_symbols` counts symbols whose downloads returned, whatever they returned.
- `failed_symbols` lists the failures in order; the summary names the first 10.
- "Not attempted" = requested − downloaded − failed: the symbols after the one the pass ended on,
  plus that one itself if its error wasn't recorded (stop, storage).
- `Client.fetch` adds up requested and failed symbols over the passes, logs the totals and returns
  the requested total. The failed symbols themselves are not returned.

### 8.5 Stop points

| Where | How |
| ----- | --- |
| before every symbol | `Fetcher._check_user_interrupt` calls the stop function |
| while waiting between retries of a request | `call_with_backoff` polls it every 0.5 s (PROVIDER) |
| anywhere else | no check: the list downloads, a running request, the writes |

The command line passes no stop function. Ctrl+C raises `KeyboardInterrupt` at whatever
statement is running, which the command line turns into its exit code (chapter CLI). The stop
points therefore protect library callers only.

### 8.6 Storage check

`shutil.disk_usage("/").free`, in whole GB, must be at least 50, checked before every symbol. It
measures the machine running the fetch; QuestDB on another host, or on another drive of this
machine, isn't covered.

### 8.7 After an interruption

A fetch keeps no state of its own: what it has done is only visible in the stored data. When a
fetch ends early (Ctrl+C, a full disk, an account error, a streak of failures, a crash), the
next fetch starts from the beginning.

| What | In the next fetch |
| ---- | ----------------- |
| Passes already completed | run again in full |
| Exchange and symbol lists | requested again and rewritten (REFDATA) |
| Prices of symbols already done | requested again, but only after the newest stored bar: usually one request per symbol that returns a day or nothing |
| Prices of the symbol the fetch stopped at | daily: requested again from the day after its newest stored bar, so nothing is lost. Minute: none of the windows requested so far was written (PRICES-S03), so they are all requested again; for a new symbol that is its whole history from 2005 |
| Fundamentals of the symbol the fetch stopped at | if it stopped between a table's deletion and its write, that table lacks the symbol's records until the next fetch reaches the symbol |
| Prices of symbols not reached | requested as in a first run |
| Fundamentals of symbols already done | requested again in full and every table rebuilt (FUND) |
| Failed symbols of the interrupted fetch | not known anymore; they get another try only because every symbol does |

**Example:** a first fetch stops after 6,000 of 10,000 symbols of the daily active pass. The
next fetch requests the 26 lists again and rewrites the reference data, makes one price request
for each of the 6,000 done symbols, requests and rebuilds the fundamentals of every NASDAQ and
NYSE symbol among them, and only then continues with the remaining 4,000.

So "the price start" acts as a resume for prices only, as a side effect of fetching after the
newest stored bar. A real resume, which skips the work already done, needs the run's position
and outcome to be stored (ING-10, `run-tracking`).

### 8.8 Known limitations

| Limitation | Effect | Planned change |
| ---------- | ------ | -------------- |
| Every pass builds a new `Fetcher` with new download, request and write objects | nothing can be shared across passes, such as sessions or caches | `testable-core` |
| The `Fetcher` tests replace private methods (`_download_historical_data`, `_check_storage_space`) | contradicts testing rule 6: the collaborators lack a seam | `testable-core` |

---

## 9 ACCESS: reading stored data

### 9.1 Modules

| Module | Content |
| ------ | ------- |
| `db/io/read.py` | `Read`: `exchange`, `symbol`, `sector`, `ohlcv`, `newest_of_ohlcv`; `_single_record` for the lookups |
| `db/statements/exchange.py`, `symbol.py`, `price.py` | the `SELECT` templates |
| `client.py` | `Client.read`, the `Read` of the client's `Database` |

### 9.2 Lookups

```
SELECT <all columns> FROM exchange WHERE exchange_code=%s
SELECT <all columns> FROM symbol   WHERE symbol_code=%s AND exchange_code=%s AND time_frame=%s AND symbol_status=%s
SELECT symbol_code, sector, industry, gic_sector, gic_group, gic_industry, gic_sub_industry
       FROM sector WHERE symbol_code=%s AND exchange_code=%s
```

`_single_record(rows, description)` returns `pd.Series(rows[0])`, so the values are indexed by
position; no rows give an empty `Series`, more than one raise `QueryError`. The writers test
`Series.empty` to choose between insert and update (REFDATA). The time frame and status are
bound as their enum names.

### 9.3 Price reads

```
SELECT <all columns> FROM daily_ohlcv | minute_ohlcv
WHERE exchange_code = %s AND symbol_code IN ('AAPL', 'MSFT', ...) AND %s <= timestamp AND timestamp <= %s

SELECT <all columns> FROM daily_ohlcv | minute_ohlcv
WHERE exchange_code = %s AND symbol_code IN (...) LATEST ON timestamp PARTITION BY symbol_code
```

- **One query per venue:** the symbol codes become `sql.Literal`s joined into the `IN` list; the
  exchange code and the bounds are parameters. A list of 1,000 symbols is still one query.
- **Assembly:** each venue's rows become a `DataFrame` with the table's columns; the frames are
  concatenated and indexed by `symbol_code` and `timestamp`. `newest_of_ohlcv` keeps both as
  columns too (`drop=False`), because `WritePriceData` reads the `timestamp` column.
- **Bounds:** the defaults are `datetime.min` and `datetime.max`, which QuestDB accepts as
  bounds, so "no bounds" is the same query as any other.
- **`LATEST ON`** returns the newest row per symbol code, using the designated timestamp; an
  `ORDER BY … LIMIT 1` would have returned one row for all symbols together.
- **Empty list:** `IN ()` is invalid in QuestDB, hence the `QueryError` of ACCESS-S07.

### 9.4 Results in memory

Every read fetches all rows (`fetchall`) on a new connection and builds the frame in memory.
Reading the minute bars of many symbols over years therefore needs memory for the whole result
at once, plus the copy pandas makes when concatenating.

### 9.5 Known limitations

| Limitation | Effect | Planned change |
| ---------- | ------ | -------------- |
| One object serves the writers' lookups and the public reads | internal lookups are part of the public API; changing one changes the other | `library-contract`, `query-layer` |
| Every read fetches its whole result into memory and returns pandas only | memory grows with the result; no streaming, no Arrow or Polars output | `query-layer`, `rest-api` |

---

## 10 CLIENT: library facade

### 10.1 Modules

| Module | Content |
| ------ | ------- |
| `__init__.py` | imports `Client`, `Config`, `MarketHistoryDbError`, `TimeFrame`, `SymbolStatus`; adds the `NullHandler` |
| `client.py` | `Client` |
| `errors.py` | the exception classes; `ErrorCode` (exit codes, chapter CLI); `ApiErrorCode` (provider statuses, chapter PROVIDER) |
| `utils/categories.py` | `TimeFrame` (`DAILY`, `MINUTE`), `SymbolStatus` (`ACTIVE`, `DELISTED`) |

### 10.2 Client

```
Client(config=None)
  config  = config or Config.from_env()     environment read here, never at import
  _db     = Database(config)                query, read, insert, update, delete; no connection
  read    = _db.read                        the public read interface (chapter ACCESS)
  setup() ─► setup(config)                  (STORAGE)
  fetch() ─► one Fetcher per pass           (RUNS)
```

`Client` keeps no state between calls besides `config` and `_db`; every `fetch` builds new
`Fetcher` objects. `_db` gives internal access to the write interfaces and is not part of the
public API.

### 10.3 Errors

`MarketHistoryDbError(message, error_code=None)` stores both parts and renders them in
`__str__`. `ApiError` adds `retry_after`, which `call_with_backoff` reads (PROVIDER), and
`http_status`, an alias of the code. The hierarchy separates what callers handle differently:

| Branch | Meaning | Typical handling |
| ------ | ------- | ---------------- |
| `ConfigError` | a setting is missing or unusable | fix the configuration |
| `FetchError` | the provider or its data | retry later; `AccountError` means the account or plan needs attention |
| `DbError` | the database | check the database; `SchemaMismatchError` means the provider's data changed shape |
| `StorageError` | free disk space | make room |
| `UserInterruptError` | the stop function asked to stop | none |

The docstrings of `errors.py` describe each class; the README's "Error handling" section shows
the tree.

### 10.4 Logging etiquette

Each module has `logger = logging.getLogger(__name__)`. The package root logger gets a
`NullHandler`, so that a program without logging configuration sees no "no handlers" warning and
no output. Handlers, levels and formats are set only by `start_logger`, which the command line
calls (chapter LOGGING).

### 10.5 Known limitations

| Limitation | Effect | Planned change |
| ---------- | ------ | -------------- |
| The client creates its database access and its `Fetcher`s itself | no composition root; tests replace `Fetcher` and `_setup` in the module | `testable-core`, `target-architecture` |

---

## 11 CONFIG: configuration

### 11.1 Modules

| Module | Content |
| ------ | ------- |
| `config.py` | `Config` (frozen dataclass), `from_env`, `psycopg_conninfo`, `http_conf`; `_CONNECT_TIMEOUT_IN_SECS` (10) |
| `utils/env.py` | `require_env(name)`: a required variable, or `ConfigError` |
| `.env.example` | the variables, with defaults and the test-database variables |

### 11.2 Sources and precedence

| Source | Used by |
| ------ | ------- |
| a `Config` passed to `Client` | library callers |
| the process environment, read by `Config.from_env()` when a `Client` is created without one | library callers, the command line |
| a `.env` file, loaded into the environment by `load_dotenv()` before the client is created; variables already set win | the command line only (chapter CLI) |

### 11.3 Connection strings

- **`psycopg_conninfo`** uses `psycopg.conninfo.make_conninfo`, which quotes each value; it adds
  `connect_timeout=10`, so an unreachable host fails after 10 s instead of psycopg's much longer
  default.
- **`http_conf`** is built by hand for `questdb.ingress.Sender.from_conf`: `_escape_conf_value`
  doubles every `;`, which is how that parser reads a literal semicolon.
- Both are computed on every access; nothing is cached.

### 11.4 Secrets

The token and the password are declared with `field(repr=False)`, so they're missing from
`repr` and from the `dataclass` printing in tracebacks and logs. They are still part of
equality and of the connection strings, which are never logged.

### 11.5 Known limitations

| Limitation | Effect | Planned change |
| ---------- | ------ | -------------- |
| Each environment variable is read and parsed by hand in `from_env` | every new setting needs its own parsing code and tests | `settings-model` |

---

## 12 CLI: command line

### 12.1 Modules

| Module | Content |
| ------ | ------- |
| `cli.py` | `main(argv)`, the parser, `_run`, `_fetch`, `_setup`, the error-to-exit-code map `_ERROR_EXIT_CODES` and `_exit_code_for` |
| `__main__.py` | `python -m markethistorydb` → `sys.exit(main())` |
| `errors.py` | `ErrorCode`, the exit codes |

### 12.2 Flow

```
main(argv)
  args = parser.parse_args(argv)          usage error ─► SystemExit(2)
  start_logger()                          stdout + markethistorydb.log in the working directory
  try:
    _run(args)
      load_dotenv()                       .env above the package's directory; set variables win
      client = Client()                   Config.from_env()
      fetch ─► client.fetch(time_frame, symbol_status, exchange)
      setup ─► prompt via the log, input(); "yes"/"y" ─► client.setup()
    return 0
  except ConfigError                      ─► one error line, code
  except UserInterruptError, KeyboardInterrupt ─► "Run was interrupted", 4
  except AccountError                     ─► one error line, code
  except MarketHistoryDbError             ─► traceback, code
  except Exception                        ─► traceback, 9
```

### 12.3 Exit codes

`_exit_code_for(error)` walks the error's method resolution order and returns the code of the
first class found in `_ERROR_EXIT_CODES`, so the most specific mapping wins, whatever the order
of the map. `AccountError` itself is not mapped and falls back to the code of `FetchError` (12);
its three subclasses have codes of their own. Code 2 stays free for `argparse`.

### 12.4 The `.env` lookup

`load_dotenv()` without arguments calls `find_dotenv()`, which starts in the directory of the
calling module, here `cli.py`, and walks up to the file system root. In the project's
development install, that directory is `src/markethistorydb`, so the project's `.env` is found.
In an installation elsewhere it is `site-packages/markethistorydb`, and the working directory is
never searched. `find_dotenv(usecwd=True)` would start from the working directory instead.

### 12.5 Known limitations

| Limitation | Effect | Planned change |
| ---------- | ------ | -------------- |
| The `setup` question is written through the logger and answered through `input()` | the question lands in the log file; tests replace `builtins.input` | `library-contract` |

---

## 13 LOGGING: log output and token masking

### 13.1 Modules

| Module | Content |
| ------ | ------- |
| `utils/logger.py` | `start_logger`, `_setup_logger`, `_RedactingFormatter`; `LOG_ONLY_TO_TERMINAL` (`False`), `LOG_FILE_NAME`, size and backup constants |
| `utils/redact.py` | `redact_api_token(text)`, `REDACTED` (`***`) |

### 13.2 Setup

`_setup_logger` builds a `StreamHandler(sys.stdout)` and, unless `LOG_ONLY_TO_TERMINAL`, a
`RotatingFileHandler`, then calls `logging.basicConfig(level, handlers, force=True)`: `force`
closes and removes handlers from an earlier call, so the handlers never pile up. Every handler
gets the redacting formatter. `logging.captureWarnings(True)` sends `warnings` to the logger
`py.warnings`, and so into both handlers.

### 13.3 Token masking

Two layers keep the token out of the output:

1. **At the source:** the request layer masks the token in the errors it raises and logs URLs
   without parameters (PROVIDER-S14), so log records are clean even for a program that attaches
   handlers of its own (RUNS-S12).
2. **In the formatter:** `_RedactingFormatter.format` runs `redact_api_token` on the finished
   line, after the arguments, the traceback and the stack information have been added, as a
   second line of defence.

`redact_api_token` uses one regular expression: `api_token`, an optional quote, `=` or `:`, an
optional quote, then the value up to the next `&`, white space, quote, comma or closing bracket,
which is replaced by `***`.

### 13.4 Known limitations

| Limitation | Effect | Planned change |
| ---------- | ------ | -------------- |
| The handlers sit on the root logger | records of third-party libraries share the level, format and file | `cloud-readiness` |

---

## 14 PACKAGING: package and entry points

### 14.1 Project files

| File | Content |
| ---- | ------- |
| `pyproject.toml` | `[project]` name, version, description, readme, `requires-python`, dependencies; `[project.scripts]`; the dev dependency group; pytest markers; coverage settings (branch coverage of `src`, `fail_under = 100`); `[build-system]` `uv_build` |
| `src/markethistorydb/` | the package (src layout) |
| `README.md` | install, QuestDB settings, CLI and library usage, conventions, errors and exit codes, tests |
| `.env.example` | the environment variables (chapter CONFIG) |
| `uv.lock` | resolved versions; ignored by git |

### 14.2 Entry points

| Way to run | Resolves to |
| ---------- | ----------- |
| `markethistorydb …` | console script → `markethistorydb.cli:main` |
| `python -m markethistorydb …` | `markethistorydb/__main__.py` → `cli.main()` |
| `import markethistorydb` | the library (chapter CLIENT) |

### 14.3 Known limitations

None besides the known gaps of `3_specs.md` 12.2.

---

## 15 QUALITY: the test suite

The test approach, the levels, the shared fakes and the commands are described in `5_test.md`,
section 1. Where the guarantees of QUALITY-S01 to S04 are implemented:

| Guarantee | Where |
| --------- | ----- |
| levels and markers | `[tool.pytest.ini_options]` in `pyproject.toml` registers `unit`, `integration`, `live`; `pytest_collection_modifyitems` in `tests/unit/conftest.py`, `tests/integration/conftest.py` and `tests/live/conftest.py` marks every test of its directory |
| coverage gate | `[tool.coverage.run]` (`branch = true`, `source = ["src"]`) and `[tool.coverage.report]` (`fail_under = 100`, `exclude_also`) in `pyproject.toml` |
| protection of the application's database | `questdb_config` in `tests/integration/conftest.py`: compares the resolved addresses of `QUESTDB_TEST_*` and `QUESTDB_*`, calls `pytest.exit(..., returncode=3)` on a match, `pytest.skip` without variables or connection |
| empty tables per test | `fresh_db` in `tests/integration/conftest.py` runs `setup` before each test |

### 15.1 Known limitations

None besides the known gaps of `3_specs.md` 13.2.

---

## Appendix A: Design decisions in force

| Decision | Reason | Consequence |
| -------- | ------ | ----------- |
| The reference tables (`exchange`, `symbol`, `sector`) are non-WAL tables without designated timestamp, written through SQL. | Their writers read a record and then insert or update it; a non-WAL write is visible to the next read at once. ILP over HTTP only writes WAL tables. | No deduplication keys; uniqueness rests on read-then-write by a single writer. |
| Prices and fundamentals are WAL tables with deduplication keys, written through ILP over HTTP. | Fast bulk ingestion; a re-sent record replaces the stored one instead of duplicating it. | Writes become visible shortly after they are acknowledged; a read right after a write may not see it. |
| An instrument's records are deleted by copying the table without them, dropping it and renaming the copy, with recovery of a leftover copy. | QuestDB has no row-level `DELETE`. | Not atomic; cost proportional to the table size. Only the fundamentals replacement uses it. |
| Every error the package raises maps to its own exit code; configuration and account errors are reported without traceback, everything else with it. | Scripts react to exit codes; a user fixing a token needs one clear line, while unexpected errors need the traceback in the log file. | Adding an error class means adding its exit code; a test fails otherwise. |
| The API token is masked twice: where errors and log messages are made, and again in the log formatter. | A program using the library attaches its own handlers, so records must be clean at the source; the formatter catches what slips through. | Two places to extend when another secret or spelling has to be masked. |
| The library reads the environment only when a `Client` is created without a `Config`, and never configures logging. | Importing must be safe in any program, and only the program knows its configuration and logging setup (LIB-1 to LIB-3). | The command line does both itself: it loads `.env` and starts the logger. |
| A failure of one symbol is recorded and the pass goes on; 20 failures in a row, an account error, a full disk or a stop request end the pass. | One bad symbol mustn't cost a run, but a systematic fault mustn't burn through the whole symbol list and the provider quota. | A run can end with many symbols not attempted; the summary counts them. |
| A symbol's fundamentals are replaced as a whole on every fetch: the full history is requested, and per table the stored records are deleted and the new ones written. | The provider revises past periods, and a full replacement picks the revisions up without tracking what changed. | Revisions overwrite the earlier values (BT-9); replacement is not atomic and its cost grows with the table (FUND-S03, S07). |
| A symbol's fundamental records are checked against the table's columns before its stored records are deleted. | Otherwise an unknown column would be rejected only after the deletion, losing the symbol's records. | A new provider field fails the symbol with `SchemaMismatchError`, also without the server setting of STORAGE-S13. |
| Prices are fetched incrementally: only bars after the newest stored bar are requested. | Saves provider requests and write volume on every run. | Past bars are never refreshed, so the provider's corrections and re-adjusted closes don't arrive (COR-12, BT-6). |
| Reference data is stored under the provider's codes: exchanges under eodhd's list codes, symbols under eodhd's venue names, and the link between the two only in memory. | The codes are what the requests need, and nothing else identifies the records yet. | Two meanings of `exchange_code` (section 2.3); replaced by MIC identity in `provider-interface`. |
| Requests are retried only for rate limiting, server errors and network failures; account errors are never retried. | Waiting can help with the first three, but not with a rejected token, a used-up plan or an endpoint outside the plan. | A run ends at once on an account error (chapter RUNS) instead of spending time on retries. |
| HTTP 404 from eodhd means "no data for this ticker", not an error. | eodhd answers 404 for tickers it has no data for; such a symbol is simply skipped. | A wrong URL would be silent too; the URL builders are tested against the documented addresses. |
| The API token travels only as a query parameter and is masked wherever a message could carry it. | Logs and error messages get shared. | Messages name requests by their URL without parameters. |
| QuestDB runs with `line.auto.create.new.columns=false` (section 1.4). | A field the provider starts to send must not silently become a new column. | Such a write fails with `SchemaMismatchError` (STORAGE-S13). The code depends on the setting but does not check it. |
| Records with a designated timestamp before 1970 are dropped before writing and counted in the log. | QuestDB cannot store timestamps before the Unix epoch. | Early history of old instruments (e.g. IBM before 1970) is missing (COR-9). |
| Partitioning: daily bars and fundamentals by year, minute bars by day; indexes on `exchange_code` and `symbol_code` of the price tables. | Partitions sized to the data volume; reads filter by exchange and symbol. | Minute data partitioning is to be measured again (`ingestion-scale`). |
