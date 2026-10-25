# MarketHistoryDB: specification (status quo)

The behaviour implemented today, one chapter per capability. Planned changes are specified in
`planned_features/<nn>_<feature>/1_specs.md` and enter this file when the feature is merged
(`1_constitution.md`, section 6.4).

- **Specification items** state concrete, observable behaviour, including internal interfaces
  that other capabilities rely on. Each one names the requirements it satisfies
  (`2_requirements.md`).
- **How it is built** is described in `4_design.md`; **how it is tested**, in `5_test.md`.
- **Known gaps:** each chapter ends with the places where today's behaviour falls short of a
  requirement, and the planned feature that closes each gap. A gap is listed once, in the
  chapter of the specification item that its planned feature changes; other chapters don't
  repeat it. Structural shortcomings of the design that no requirement covers (testability,
  coupling, duplication) are listed in `4_design.md` as known limitations, never here.
- **Terms:** code names are used where they help to find the code, e.g. *symbol* for what the
  glossary calls an instrument, and the provider's *exchange code* for an exchange.

## Capabilities

| # | Code | Capability |
| - | ---- | ---------- |
| 1 | STORAGE | QuestDB access and schema: setup, tables, writing, running SQL, deleting an instrument's records |
| 2 | PROVIDER | eodhd request layer: URLs and encoding, parameters, retries and backoff, status → error, payload validation |
| 3 | REFDATA | exchange, symbol and sector ingestion |
| 4 | PRICES | daily and minute price ingestion, incremental runs, 120-day windows |
| 5 | FUND | fundamentals ingestion and replacement |
| 6 | RUNS | fetch orchestration: passes, filters, failure isolation, summary, storage check, stopping |
| 7 | ACCESS | reading: exchanges, symbols, sectors, price bars, newest bars |
| 8 | CLIENT | library facade: `Client`, top-level names, exception hierarchy, logging etiquette |
| 9 | CONFIG | configuration: `Config`, environment variables, connection strings, timeouts |
| 10 | CLI | commands `setup` and `fetch`, confirmation prompt, exit codes, `.env` loading |
| 11 | LOGGING | log file, rotation, token redaction |
| 12 | PACKAGING | installable package, console script, `python -m` |
| 13 | QUALITY | the test suite: levels, coverage gate, protection of the application's database |

---

## 1 STORAGE: QuestDB access and schema

### 1.1 Schema setup

| ID | Specification | Satisfies |
| -- | ------------- | --------- |
| STORAGE-S01 | `setup(config)` creates the 13 tables of the schema from scratch: `exchange`, `symbol`, `sector`, `daily_ohlcv`, `minute_ohlcv` and the eight fundamental tables (section 1.2), with indexes on the exchange and symbol codes of the two price tables. Each table that exists already is dropped first, together with all its data. The library asks for no confirmation. All statements run over one connection. | MKT-3 |
| STORAGE-S02 | The tables `setup` creates match the table definitions the code reads and writes with: table names, columns in order, key columns, designated timestamp, and whether a table is a WAL table. A table definition in the code that lacks its name, its columns, its key columns or its timestamp column is rejected as soon as the code is loaded. | MKT-3 |
| STORAGE-S03 | If a schema file cannot be read, the database rejects a statement, or the database cannot be reached, `setup` raises `DbError`; an unreadable file is named in the message. | MKT-3, LIB-4 |

### 1.2 Stored data

| ID | Specification | Satisfies |
| -- | ------------- | --------- |
| STORAGE-S04 | **Daily bars** (`daily_ohlcv`): one record per timestamp, exchange code and symbol code, holding open, high, low, close and adjusted close as floating-point numbers and the volume as an integer. Writing a record whose key is stored already replaces the stored record. | MKT-5, COR-1, COR-5 |
| STORAGE-S05 | **Minute bars** (`minute_ohlcv`): one record per timestamp, exchange code and symbol code, holding open, high, low, close and volume as floating-point numbers; there is no adjusted close. Writing a record whose key is stored already replaces the stored record. | MKT-6, COR-1, COR-5 |
| STORAGE-S06 | **Fundamentals:** eight tables, one per statement (earnings, balance sheet, cash flow, income statement) and period type (quarterly, annual). A record is keyed by symbol code, exchange code and one date: the report date for quarterly earnings, the period end for annual earnings, the filing date for the other six tables. Its other columns hold the provider's fields under snake_case names. Writing a record whose key is stored already replaces the stored record. | MKT-7, BT-8 |
| STORAGE-S07 | **Reference data:** `exchange` holds one record per exchange code, `symbol` one record per symbol code, exchange code, time frame and listing status, and `sector` one record per symbol code and exchange code. The database does not enforce these keys; the writers keep them unique (REFDATA). A write to these tables is visible to the very next read. | MKT-8 |
| STORAGE-S08 | A record whose designated timestamp lies before 1970-01-01 cannot be stored: a write containing one fails at once with `InsertError`, without retrying. | COR-9 |

### 1.3 Writing

| ID | Specification | Satisfies |
| -- | ------------- | --------- |
| STORAGE-S09 | Price bars and fundamentals are written through QuestDB's HTTP ingestion interface, with the connection settings of the configuration: all records of one call in one batch, on a connection opened for that call. | MKT-2 |
| STORAGE-S10 | Reference records are written through SQL, one record per statement, with a value for every column of the table in definition order. A field missing from the record, or a missing value, is stored as NULL; a field the table does not define is not written; numpy values are stored as plain values. | MKT-8, COR-4 |
| STORAGE-S11 | Updating a reference record overwrites its columns except the key: every other column of an exchange (addressed by its exchange code) and of a sector (addressed by symbol code and exchange code); the name, country, currency and type of a symbol (addressed by its four key columns), whose ISIN keeps the value it was inserted with. Values are written as they are, so a missing value is stored as "not a number" instead of NULL. | MKT-8 |
| STORAGE-S12 | A transient failure of the ingestion interface (address not resolvable, socket error, connect timeout, server failed to take the records, internal server error, failover) is retried: at most 3 attempts, waiting 10 s and then 20 s. If the last attempt fails, `InsertError` is raised, naming the operation. | ING-1 |
| STORAGE-S13 | Records the server rejects because they do not fit the table (a column the table does not have, or a value its column type cannot hold) fail at once with `SchemaMismatchError`; the table's columns stay unchanged. This requires the server setting `line.auto.create.new.columns=false` (`4_design.md`, section 1.4); without it, the server adds the column instead. | COR-6 |
| STORAGE-S14 | Any other rejection, and any other ingestion error (e.g. records that cannot be serialised), fails at once with `InsertError`. Errors that are not ingestion errors pass through unchanged. | LIB-4 |
| STORAGE-S15 | A reference record the database rejects raises `InsertError`, without retrying. | LIB-4 |

### 1.4 Running SQL

| ID | Specification | Satisfies |
| -- | ------------- | --------- |
| STORAGE-S16 | Each SQL statement is sent on its own, since QuestDB runs one statement per query, on a new connection that is closed afterwards: autocommit, client-side parameter binding, a connect timeout of 10 s. A statement that returns no result set (e.g. `UPDATE`, DDL) returns no records. | MKT-2, CLD-8 |
| STORAGE-S17 | Values are always bound as parameters, never formatted into the statement text, and table and column names are quoted as identifiers. | QA-10 |
| STORAGE-S18 | A failed statement, a table that does not exist, an unreachable database and a rejected login all raise `QueryError`. The message never contains the database password. | LIB-4, QA-8 |

### 1.5 Deleting an instrument's records

| ID | Specification | Satisfies |
| -- | ------------- | --------- |
| STORAGE-S19 | When an instrument's fundamentals are replaced (FUND), its records are deleted from a fundamental table by copying every other record into `<table>_copy`, dropping the table and renaming the copy to the table's name. The copy keeps the designated timestamp, the partitioning, WAL and the deduplication keys. The steps are separate statements: if one fails, `QueryError` is raised and the earlier steps stay applied. A deletion request for a table outside the symbol, fundamental and price tables does nothing. (Deleting from the symbol and price tables is implemented as well, but nothing uses it: `4_design.md`, section 3.8.) | MKT-7 |
| STORAGE-S20 | Before deleting, a copy left behind by an interrupted deletion is cleaned up, with a warning in the log. If the table still exists, the copy is dropped, since the table still holds every record. If the table is gone, the copy takes the table's name back. | COR-2 |

### 1.6 Access objects

| ID | Specification | Satisfies |
| -- | ------------- | --------- |
| STORAGE-S21 | Creating the database access objects (`Database(config)`) opens no connection. All of them (query, read, insert, update, delete) share one configuration and one statement runner. | LIB-11 |

### 1.7 Known gaps

| Gap | Requirement | Closed by |
| --- | ----------- | --------- |
| Back-to-back replacements of two instruments' fundamentals may lose a write (suspected WAL race, not reproduced) | COR-1 | `data-integrity-checks` (test), `point-in-time-fundamentals` (no deletes) |
| Two fundamental periods filed on the same day collapse into one record (STORAGE-S06) | COR-1 | `data-integrity-checks` (check, quick fix), `point-in-time-fundamentals` |
| A deletion is not atomic; a table can be missing until the next deletion repairs it (STORAGE-S19, S20) | COR-2 | `point-in-time-fundamentals` (no deletes) |
| `setup` always drops every table; there is no "create what is missing" (STORAGE-S01) | COR-3, OPS-1 | `library-contract` |
| An update stores "not a number" instead of NULL (STORAGE-S11) | COR-4 | `code-hygiene` |
| A deletion request for an unknown table is ignored silently (STORAGE-S19) | COR-3 | `code-hygiene` |
| A new connection for every statement and every ingestion call (STORAGE-S09, S16) | OPS-2 | `connection-reuse` |
| The tables are defined twice, in SQL files and in Python (STORAGE-S02) | ING-20 | `schema-from-code` |
| Writes are not checked against free space on the database host | ING-18 | `ingestion-scale` |
| The server setting `line.auto.create.new.columns=false`, on which STORAGE-S13 depends, is not checked | OPS-5 | `library-contract` |
| `exchange_code` holds eodhd's exchange-list code in `exchange` and the venue in all other tables; exchanges are not identified by MIC | PRV-1, PRV-2 | `provider-interface` |

---

## 2 PROVIDER: eodhd request layer

### 2.1 Requests

| ID | Specification | Satisfies |
| -- | ------------- | --------- |
| PROVIDER-S01 | Data is requested from five endpoints under `https://eodhd.com/api`: `exchanges-list`, `exchange-symbol-list/{exchange}`, `eod/{symbol}.{exchange}`, `intraday/{symbol}.{exchange}` and `fundamentals/{symbol}.{exchange}`, where `{exchange}` is the code of eodhd's exchange list (e.g. `US`). Every request carries the API token and `fmt=json` as query parameters. A successful response is returned as parsed JSON. | MKT-1 |
| PROVIDER-S02 | Symbol and exchange codes are percent-encoded as single path segments: every character that could end the segment, the path or the query (`/`, `?`, `#`, `%`, …) is encoded; ordinary codes stay readable. | COR-8 |
| PROVIDER-S03 | Every request has a connect timeout of 10 s and a read timeout of 120 s. | ING-1 |
| PROVIDER-S04 | The symbol list of an exchange is requested for active symbols, or, with `delisted=1`, for delisted symbols. | MKT-8, BT-2 |
| PROVIDER-S05 | Daily bars are requested from the first day given as `from=YYYY-MM-DD`, without an end; without a first day, the full history is requested. | MKT-5, MKT-10 |
| PROVIDER-S06 | Minute bars are requested with `interval=1m` and both bounds, `from` and `to`, as Unix seconds converted from naive UTC. A request without both bounds is refused with `ValueError` before anything is sent. | MKT-6, COR-10 |
| PROVIDER-S07 | Fundamentals are requested with a `filter` that limits the answer to the sections that are stored: the six sector and industry fields of `General`, `Earnings::History`, `Earnings::Annual`, and the balance sheets, cash-flow statements and income statements of `Financials`. | MKT-7 |

### 2.2 Answers and errors

| ID | Specification | Satisfies |
| -- | ------------- | --------- |
| PROVIDER-S08 | **No data is not an error:** HTTP 404 (no such ticker), an empty array and an empty object all mean "no data", and the request yields an empty result: no symbols, no bars, no fundamentals. The exchange list is the exception: an empty exchange list fails the structure check (PROVIDER-S17). | ING-4 |
| PROVIDER-S09 | **Error statuses** map to errors: 401 → `UnauthorizedError`, 402 → `DataLimitError` and 403 → `AccessRightsError` (all three are `AccountError`s), 429 → `RateLimitError` (carrying the `Retry-After` wait, if any), 500 and above → `BadGatewayError`, any other unsuccessful status → `ApiError`. All of them are `FetchError`s. | LIB-4, ING-5 |
| PROVIDER-S10 | **Retries:** `RateLimitError`, `BadGatewayError` and `NetworkError` (a timeout or a connection that fails) are retried: at most 3 attempts, waiting 10 s and then 20 s, or the provider's `Retry-After` instead. If the last attempt fails, `RequestError` is raised. Account errors, `CompatibilityError` and other `ApiError`s are raised at once, without retry. | ING-1, ING-5 |
| PROVIDER-S11 | A `Retry-After` header is used if it holds a finite, non-negative number of seconds (zero included); a date or any other value falls back to the backoff. | ING-1 |
| PROVIDER-S12 | Every wait between attempts can be interrupted: `should_stop` is polled at least every 0.5 s, and when it returns `True`, `UserInterruptError` is raised. | ING-2 |
| PROVIDER-S13 | A request exception other than a timeout or a failed connection (e.g. an invalid URL) raises `RequestError` at once. | LIB-4 |
| PROVIDER-S14 | **The API token never leaves the request:** error messages hold at most the first 500 characters of the response body, with the token masked, also where it sits at the cut-off point. Errors built from a request exception mask the token and are not chained to that exception, whose message carries the full URL. Retry and give-up log messages name the request by its URL without the query string. | QA-8 |
| PROVIDER-S15 | A response body that is not JSON raises `CompatibilityError`. | COR-7 |
| PROVIDER-S16 | The exchange list, the symbol lists and the price endpoints must answer with a JSON array, the fundamentals endpoint with a JSON object; the other kind raises `CompatibilityError`. | COR-7 |
| PROVIDER-S17 | **Structure check:** each answer must hold every expected field, in any order; further fields are allowed. A missing field, section or value raises `CompatibilityError`, which names the record set for fundamentals. Expected are: <br>• exchanges: `Name`, `Code`, `OperatingMIC`, `Country`, `Currency`, `CountryISO2`, `CountryISO3`; <br>• symbols: `Code`, `Name`, `Country`, `Exchange`, `Currency`, `Type`, `Isin`; <br>• daily bars: `date`, `open`, `high`, `low`, `close`, `adjusted_close`, `volume`; <br>• minute bars: `timestamp`, `datetime`, `open`, `high`, `low`, `close`, `volume` (`gmtoffset` is optional); <br>• fundamentals: the sections of PROVIDER-S07, six sector and industry values, and in each of the eight record sets every column of its table except symbol and exchange code. | COR-7 |

### 2.3 Conversion to records

| ID | Specification | Satisfies |
| -- | ------------- | --------- |
| PROVIDER-S18 | Exchanges and symbols come back with their fields renamed to the table columns (e.g. `Code` → `exchange_code` for exchanges and `symbol_code` for symbols; `OperatingMIC` → `operating_mic`). Symbols also get the time frame and listing status of the request (`DAILY`/`MINUTE`, `ACTIVE`/`DELISTED`). | MKT-8 |
| PROVIDER-S19 | Daily bars come back with `date` renamed to `timestamp`; minute bars keep `timestamp` (Unix seconds) and drop `datetime` and `gmtoffset`. Both get the symbol code and exchange code added. | MKT-5, MKT-6 |
| PROVIDER-S20 | Fundamentals come back as the six sector and industry values and eight record sets (earnings, balance sheet, cash flow, income statement, each quarterly and annual), one row per reporting period, with the field names converted from camelCase to snake_case. `preferredStockRedeemable` (balance sheets) and `preferredStockAndOtherAdjustments` (income statements) are dropped, since the tables have no column for them. A record set without records is left out, so that the stored records of that type are kept (FUND). | MKT-7 |

### 2.4 Retrying with backoff

| ID | Specification | Satisfies |
| -- | ------------- | --------- |
| PROVIDER-S21 | `call_with_backoff` (used by the request layer and by STORAGE) calls a function until it succeeds or the attempts are used up. Only the given error types are retried; others pass through unchanged. The wait after attempt *n* is *base* × *factor*^(*n*−1), or the error's own `retry_after`, both capped at a maximum delay (default 3600 s). Each retry is logged as a warning naming the call, the error type, the attempt and the wait. After the last attempt, the given give-up error is raised, chained from the last error, with a message naming the call, the number of attempts and the last error; this is logged as an error. Fewer than one attempt is refused with `ValueError` before any call. | ING-1, LIB-4 |

### 2.5 Contract checks

| ID | Specification | Satisfies |
| -- | ------------- | --------- |
| PROVIDER-S22 | Live contract checks call eodhd.com and compare every field and JSON type of the current answers of all five endpoints with the stored sample payloads (`tests/data/eodhd`), and run the request layer on the live answers. The public demo token serves end-of-day bars, intraday bars and fundamentals of AAPL.US; the exchange and symbol lists need the account's token and are skipped without it, or when the account is refused. | COR-17 |

### 2.6 Known gaps

| Gap | Requirement | Closed by |
| --- | ----------- | --------- |
| The contract checks cover fields and types, not value semantics (e.g. whether open, high, low and close are split-adjusted), and they don't run on a schedule | COR-17 | `data-integrity-checks`, `continuous-integration` |
| Requests only react to rate limiting (429); there is no planning against the provider's per-minute and daily limits | ING-9 | `ingestion-scale` |
| A new HTTP connection per request (no shared session) | OPS-2 | `code-hygiene` |
| Provider specifics (codes, field names, the virtual exchange `US`) are spread over the request classes and reach the stored data | PRV-1, PRV-3 | `provider-interface` |
| Fields the provider adds pass the structure check and only fail at the write, and only if the server setting is right (STORAGE-S13) | PRV-6 | `provider-interface` |
| Splits and dividends are not requested | BT-7 | `corporate-actions` |

---

## 3 REFDATA: exchange, symbol and sector ingestion

Every fetch pass (one time frame, one listing status, chapter RUNS) starts by obtaining the
exchanges and their symbols. The sector classification is obtained with the fundamentals.

### 3.1 Exchanges

| ID | Specification | Satisfies |
| -- | ------------- | --------- |
| REFDATA-S01 | Each pass requests eodhd's exchange list and keeps the exchanges selected for its time frame, by their name in the list. Daily: `USA Stocks`, `London Exchange`, `Toronto Exchange`, `XETRA Stock Exchange`, `Shanghai Stock Exchange`, `FOREX`, `Cryptocurrencies`, `Government Bonds`. Minute: `USA Stocks`, `FOREX`, `Cryptocurrencies`. The selection is fixed in the code. | MKT-8, MKT-9 |
| REFDATA-S02 | If a target exchange is named (by its name in the list, e.g. `London Exchange`; `--exchange` on the command line), only that exchange is kept. If no exchange is left, `NoDataError` is raised and nothing is written: its message names the target exchange and the time frame, or, without a target, says that the provider lists none of the selected exchanges. | ING-15, ING-5 |
| REFDATA-S03 | Every kept exchange is stored under its exchange-list code: inserted if no record with that code is stored, otherwise all its other columns are overwritten. This happens in every pass, so a full run writes each exchange up to four times. | MKT-8 |

### 3.2 Symbols

| ID | Specification | Satisfies |
| -- | ------------- | --------- |
| REFDATA-S04 | For each kept exchange, the pass requests its symbol list for the pass's listing status. The list of `US` holds every US venue and is cut down to the venues of the time frame: `NASDAQ`, `NYSE` and `NYSE ARCA` for daily bars, `NASDAQ` and `NYSE` for minute bars. The lists of other exchanges are kept whole. | MKT-8, MKT-9, BT-1, BT-2 |
| REFDATA-S05 | The number of symbols of each exchange is logged. An exchange without symbols is skipped. If no exchange yields a symbol, `NoDataError` naming the exchanges is raised and nothing is written. | MKT-8, ING-5 |
| REFDATA-S06 | Every symbol is stored per time frame and listing status: inserted if no record with its symbol code, exchange code (the venue), time frame and status is stored, otherwise its name, country, currency and type are overwritten. A symbol listed for both time frames and both statuses therefore has up to four records. Records are never removed, so a symbol delisted since an earlier run keeps its `ACTIVE` records next to the new `DELISTED` ones. | MKT-8, BT-1, BT-2 |
| REFDATA-S07 | The symbols handed on to the price and fundamentals downloads carry, besides their own exchange code (the venue, e.g. `NASDAQ`), the exchange-list code their requests are built with (`exchange_url_code`, e.g. `US`). This link is held in memory only; it is not stored. | MKT-1 |

### 3.3 Sector and industry

| ID | Specification | Satisfies |
| -- | ------------- | --------- |
| REFDATA-S08 | Sector and industry (sector, industry, GICS sector, group, industry and sub-industry) are stored per symbol code and exchange code, taken from the fundamentals answer (PROVIDER-S20). They are written only for symbols whose fundamentals are fetched (`NASDAQ` and `NYSE`, chapter FUND), and only when the answer holds at least one fundamental record set: inserted if not stored, otherwise overwritten. | MKT-8 |

### 3.4 Known gaps

| Gap | Requirement | Closed by |
| --- | ----------- | --------- |
| The selection of exchanges and US venues is fixed in the code; one target exchange at most, named by its list name | MKT-9, OPS-3, ING-15 | `settings-model` |
| The exchange list is requested in each of the four passes, and the symbol lists of USA Stocks, FOREX and Cryptocurrencies in both the daily and the minute pass of a status: 9 of a full run's 26 list requests repeat an earlier one (`4_design.md` 5.3) | ING-7 | `ingestion-efficiency` |
| Every exchange and symbol is read and then written, one SQL statement each, in every run | ING-12 | `ingestion-efficiency` |
| A changed ISIN is never stored: the symbol update leaves it at its first value (STORAGE-S11) | COR-12 | `code-hygiene` |
| No listing and delisting dates; the listing status is the provider's list at fetch time, so the instruments listed on a past date can't be determined | BT-1 | `listings-and-universe` |
| Ticker changes and index membership are not obtained | BT-3, BT-4 | `listings-and-universe` |
| Sector and industry are overwritten without history, so a screen on a past date sees today's classification | BT-13 | `listings-and-universe` |
| Exchanges are stored under eodhd's list codes, symbols under eodhd's venue names; no MIC identity (STORAGE, section 1.7) | PRV-1, PRV-2, PRV-9 | `provider-interface` |

---

## 4 PRICES: daily and minute price ingestion

For every symbol of a pass (chapter RUNS), the price bars of the pass's time frame are requested
and stored: daily bars in the daily passes, minute bars in the minute passes. The fundamentals
of the symbol follow (chapter FUND).

### 4.1 What is requested

| ID | Specification | Satisfies |
| -- | ------------- | --------- |
| PRICES-S01 | **Start of a daily request:** the newest stored daily bar of the symbol on its venue is looked up, whatever the listing status (the price tables don't hold it). If there is one, the bars are requested from the day after it, without an end; if there is none, the full history is requested. | MKT-5, MKT-10, ING-7, ING-8, ING-10 |
| PRICES-S02 | **Period of a minute request:** from one minute after the newest stored minute bar of the symbol on its venue, or from 2005-01-01 00:00 UTC if there is none, up to 00:00 UTC of the current day, so the current day's bars are never requested. If the start is not before that end, nothing is requested. | MKT-6, MKT-10, ING-7, ING-8, ING-10, COR-10 |
| PRICES-S03 | **Windows:** the minute period is split into windows of at most 120 days, the most the intraday endpoint allows, in chronological order; each window starts where the previous one ended. The windows of a symbol are requested one after the other, collected, and written together at the end. | MKT-6, ING-9 |

### 4.2 What is stored

| ID | Specification | Satisfies |
| -- | ------------- | --------- |
| PRICES-S04 | **Timestamps:** a daily bar's date becomes 00:00 UTC of that date; a minute bar's Unix seconds become the naive UTC datetime of that instant (`4_design.md`, section 2.3). | COR-10 |
| PRICES-S05 | **Bars before 1970** are dropped before writing, with a warning naming their number, the time frame and the symbol, e.g. "Dropped 1520 DAILY price records of IBM.NYSE from before 1970, which QuestDB cannot store". | COR-9 |
| PRICES-S06 | The remaining bars are written to the table of the pass's time frame in one batch (STORAGE-S09). A bar whose timestamp, exchange code and symbol code are stored already replaces the stored bar (STORAGE-S04, S05), so repeating a run stores nothing twice. | MKT-4, MKT-5, MKT-6, COR-5 |
| PRICES-S07 | **No new bars:** if the provider has no bars for the requested period, or the minute data is already up to date, the log says "No data exists for symbol AAPL (NASDAQ, DAILY, ACTIVE)" and nothing is written. If every bar is from before 1970, only the warning of PRICES-S05 is logged and nothing is written. | ING-6 |
| PRICES-S08 | **Errors:** a failed or malformed request (`FetchError`), a failed lookup of the newest bar (`QueryError`) and a failed write (`InsertError`) end the symbol's price download and are handled by the run (chapter RUNS). For minute bars, a failure in any window means that none of the symbol's windows is written. | ING-4 |

### 4.3 Known gaps

| Gap | Requirement | Closed by |
| --- | ----------- | --------- |
| Past bars are never requested again: corrections by the provider, and the adjusted close of earlier bars after a split or dividend, don't reach the stored data | COR-12, BT-6 | `price-corrections`, `corporate-actions` |
| Bars the provider no longer delivers stay stored | COR-13 | `price-corrections` |
| Only the provider's adjusted close is stored, as it was at fetch time; no adjustment on read | BT-5, BT-6 | `corporate-actions` |
| A symbol's minute windows are held in memory and written at the end; a failure in window *k* loses windows 1 to *k*−1, and memory grows with the history | ING-13, ING-14 | `ingestion-efficiency` |
| A new symbol's minute history is requested from 2005 whatever its listing date: about 67 requests per symbol, many of them empty for young symbols | ING-8 | `ingestion-efficiency` |
| The start date 2005-01-01 and the window length are fixed in the code | OPS-3 | `settings-model` |
| Possible: a reused ticker, i.e. a delisted and an active symbol with the same code on the same venue, would share one price series, and the delisted pass would start after the active symbol's newest bar (not verified against eodhd's lists) | COR-1, PRV-9 | `listings-and-universe` (instrument identity) |
| The log says "No data exists" also for a symbol that is merely up to date | ING-6 | `code-hygiene` |
| Not verified: two incremental minute runs leave no gap and no duplicate at the boundary | COR-5 | `test-suite-hardening` |

---

## 5 FUND: fundamentals ingestion and replacement

After its price bars (chapter PRICES), every symbol of a pass gets its fundamentals requested
and stored, if its venue has fundamentals. The sector classification that comes with them is
specified in REFDATA (REFDATA-S08).

### 5.1 What is requested

| ID | Specification | Satisfies |
| -- | ------------- | --------- |
| FUND-S01 | Fundamentals are requested only for symbols on `NASDAQ` and `NYSE`; for every other venue (e.g. `NYSE ARCA`, `LSE`, `FOREX`) nothing is requested. The selection is fixed in the code. They are requested in every pass the symbol takes part in, daily and minute, active and delisted. | MKT-7, MKT-9 |
| FUND-S02 | Each request asks for the symbol's full fundamental history (PROVIDER-S07); there is no incremental request. An answer without any record set (no data, or every record set empty) writes nothing, neither sector nor fundamentals, and leaves the stored records as they are. | MKT-7, ING-8 |

### 5.2 Replacement

| ID | Specification | Satisfies |
| -- | ------------- | --------- |
| FUND-S03 | **Per record set, the stored records are replaced:** for each of the eight record sets in the answer, the symbol's records in its table are deleted (STORAGE-S19) and the new ones written in one batch (STORAGE-S09). The tables are processed in a fixed order: earnings, balance sheet, cash flow, income statement, each quarterly first. A record set missing from the answer leaves its table untouched (PROVIDER-S20). | MKT-7 |
| FUND-S04 | **Conversion:** the fields' camelCase names become snake_case and the symbol code and exchange code (the venue) are added. The dates (`report_date`, `date`, `filing_date`) become datetimes; the text fields (`symbol_code`, `exchange_code`, `before_after_market`, `currency`, `currency_symbol`) stay strings; every other field becomes a floating-point number. The provider sends amounts as strings (e.g. `"383266000000.00"`); a value that is no number or no date (e.g. `"n/a"`, an empty string) is stored as NULL. The caller's records are not modified. | MKT-7, COR-4 |
| FUND-S05 | **Records that can't be stored:** a record without its designated timestamp (STORAGE-S06) is dropped without a message; records whose designated timestamp lies before 1970 are dropped with a warning, e.g. "Dropped 1 balance_sheet_quarterly records of AAPL.NASDAQ from before 1970, which QuestDB cannot store". Other date fields keep dates before 1970. If no record is left, the table is not touched and a warning says that the stored records are kept. | COR-9 |
| FUND-S06 | **Structure check before deleting:** before a table's stored records are deleted, the prepared records are checked against the table's columns. A column the table doesn't have raises `SchemaMismatchError` naming the table, the columns and the symbol, e.g. "Table balance_sheet_quarterly has no column(s) new_field_from_provider the records of AAPL.NASDAQ hold"; that table keeps its stored records, and the tables after it in the order are not processed. Tables processed before it stay replaced. | COR-6 |
| FUND-S07 | **Errors:** a failed deletion raises `QueryError`; a write that still fails after its retries raises `InsertError`, which leaves the table without the symbol's records until a later run succeeds. Both end the symbol's fundamentals download and are handled by the run (chapter RUNS). | ING-4 |
| FUND-S08 | Writing the same answer twice leaves the same records as writing it once. | MKT-7, COR-5 |

### 5.3 Known gaps

| Gap | Requirement | Closed by |
| --- | ----------- | --------- |
| A revised value replaces the earlier one; nothing records when a value became known, so fundamentals can't be read as known on a past date | BT-8, BT-9 | `point-in-time-fundamentals` |
| Replacement is delete-then-write per table: a failed write leaves the table without the symbol's records; a suspected race between the delete and pending writes (STORAGE, section 1.7) | COR-1, COR-2 | `data-integrity-checks`, `point-in-time-fundamentals` |
| The full history is requested in every pass the symbol takes part in, so a NASDAQ or NYSE stock in both the daily and the minute data gets its fundamentals twice per status | ING-7, ING-8 | `ingestion-efficiency` |
| Fundamentals only for `NASDAQ` and `NYSE`, fixed in the code | MKT-9, OPS-3 | `settings-model` |
| Records the provider withdraws stay stored only until the next replacement, without any trace | COR-13, BT-9 | `point-in-time-fundamentals` |
| Fields are stored under eodhd's names in fixed tables; a new field fails the symbol | PRV-5, PRV-6 | `provider-interface`, `point-in-time-fundamentals` |

---

## 6 RUNS: fetch orchestration

A fetch is a sequence of passes, one per time frame and listing status. Each pass obtains the
reference data (REFDATA), then works through its symbols: prices (PRICES), then fundamentals
(FUND).

### 6.1 Passes

| ID | Specification | Satisfies |
| -- | ------------- | --------- |
| RUNS-S01 | A fetch runs one pass per time frame and listing status, in the order daily active, daily delisted, minute active, minute delisted. A given time frame, listing status or both restrict the fetch to the matching passes. | MKT-11, ING-15 |
| RUNS-S02 | The target exchange (REFDATA-S02) and the stop function (RUNS-S08) are handed to every pass. | ING-15, ING-3 |
| RUNS-S03 | A pass obtains the exchanges and symbols, then handles its symbols one after the other, in the order of the symbol lists: per symbol, the stop check and the storage check (RUNS-S08), then the price download, then the fundamentals download. | MKT-1, MKT-11 |
| RUNS-S04 | An error that ends a pass ends the whole fetch: no later pass runs. This applies to every error the pass doesn't isolate (RUNS-S05), including those of the exchange and symbol lists, e.g. `NoDataError` when the target exchange isn't listed for the time frame. | ING-5 |

### 6.2 Failures

| ID | Specification | Satisfies |
| -- | ------------- | --------- |
| RUNS-S05 | **Isolation:** a `FetchError` or `DbError` of a symbol (a failed request, an unexpected payload, a failed read or write, a schema mismatch) is logged with its traceback ("Skipping symbol SYM1 (NASDAQ)"), recorded as a failed symbol (symbol code, venue, error type), and the pass goes on with the next symbol. | ING-4 |
| RUNS-S06 | **Streak:** 20 isolated failures in a row end the pass with `FetchError` ("Aborting run after 20 symbols failed in a row, last one …"), chained from the last error. A symbol that succeeds resets the count. | ING-5 |
| RUNS-S07 | **Account errors** (`UnauthorizedError`, `DataLimitError`, `AccessRightsError`) end the pass at the first symbol that hits them; that symbol is recorded as failed, and the error propagates. | ING-5 |
| RUNS-S08 | **Stop and storage checks** before every symbol: if the stop function returns `True`, `UserInterruptError` is raised; if the file system root (`/`, on Windows the root of the current drive) of the machine running the fetch has less than 50 GB free, `StorageError` is raised. The stop function is also polled while waiting between retries (PROVIDER-S12). Neither error records the symbol as failed. | ING-3, ING-5, ING-18 |

### 6.3 Outcome

| ID | Specification | Satisfies |
| -- | ------------- | --------- |
| RUNS-S09 | **Pass log:** at its start, a pass logs its time frame and status ("Requests DAILY data of ACTIVE symbols from eodhd.com"); once the symbols are known, the number of exchanges and symbols ("Number of exchanges: 2, Number of requested symbols: 3", one exchange with a target exchange). | ING-6 |
| RUNS-S10 | **Pass summary,** logged also when the pass ends early: "Downloaded 2 of 3 symbols, 1 failed", with ", 3 not attempted" when symbols were left; then up to 10 failed symbols ("  failed: B (NASDAQ) - RequestError") and "  ... and 9990 more" for the rest. A symbol counts as downloaded when its downloads raised nothing, whether or not they stored anything. | ING-6 |
| RUNS-S11 | **Fetch total:** after the last pass, the total number of requested symbols is logged and, if symbols were skipped, a warning with their total ("Total number of symbols that were skipped after an error: 2"). `Client.fetch` returns the total number of requested symbols. | ING-6 |
| RUNS-S12 | No log record of a fetch holds the API token, also with retries and failed symbols; the records themselves are clean, not only their formatted output. | QA-8 |
| RUNS-S13 | A fetch keeps no state of its own: nothing is written locally but the log file (chapter LOGGING), and the next fetch works from the stored data alone (`4_design.md` 8.7). | CLD-1, ING-10 |

### 6.4 Known gaps

| Gap | Requirement | Closed by |
| --- | ----------- | --------- |
| An error that ends one pass skips the later passes, even when they could succeed: `fetch --exchange "London Exchange"` runs both daily passes, then fails in the first minute pass with `NoDataError`, since London isn't a minute exchange | ING-15, ING-4 | `ingestion-efficiency` |
| A failed exchange or symbol list (after its retries) ends the fetch, not just that exchange | ING-4 | `ingestion-efficiency` |
| The outcome is a log and a count; failed symbols aren't returned to the caller, and "downloaded" doesn't tell stored from up to date | LIB-9, ING-6 | `library-contract` |
| No run history and no retry of only the failed symbols. An interrupted fetch isn't resumed: the next fetch starts over with every pass and every symbol, and only the prices pick up where they stopped, because each symbol's price request starts after its newest stored bar (`4_design.md` 8.7) | ING-10, ING-11, ING-16 | `run-tracking` |
| The storage check looks at the machine running the fetch, not the database host; 50 GB, 20 failures and 10 summary lines are fixed in the code | ING-18, OPS-3 | `ingestion-scale`, `settings-model` |
| Symbols are handled one at a time | ING-17 | `ingestion-scale` |

---

## 7 ACCESS: reading stored data

`Client.read` is a `Read` object with five read operations. The writers use the same object to
look up stored records (REFDATA, PRICES).

### 7.1 Reference data

| ID | Specification | Satisfies |
| -- | ------------- | --------- |
| ACCESS-S01 | `read.exchange(exchange_code)` returns the stored exchange with that exchange-list code (e.g. `US`), `read.symbol(symbol_code, exchange_code, time_frame, symbol_status)` the stored symbol record with that key, `read.sector(symbol_code, exchange_code)` the stored sector record. | MKT-13 |
| ACCESS-S02 | Each returns a pandas `Series` of the record's values, indexed by position (0, 1, …), not by column name: the exchange's 7 columns and the symbol's 9 columns in table order; for the sector, the symbol code, sector, industry and the four GICS levels, without the exchange code. | MKT-13 |
| ACCESS-S03 | A record that isn't stored yields an empty `Series`. More than one record for the key raises `QueryError` naming the record, e.g. "Expected at most one record for symbol AAPL (NASDAQ, DAILY, ACTIVE), got 2". | MKT-13, LIB-4 |

### 7.2 Price bars

| ID | Specification | Satisfies |
| -- | ------------- | --------- |
| ACCESS-S04 | `read.ohlcv(symbol_codes_per_exchange, time_frame, start_datetime, end_datetime)` returns the bars of the given symbols from the table of the time frame. The symbols are given per venue, e.g. `{"NASDAQ": ["AAPL"], "NYSE": ["IBM"]}`; a symbol code is matched only on the venue it is listed under. Both bounds are inclusive; without them, the whole history is returned. | MKT-12 |
| ACCESS-S05 | The result is a `DataFrame` indexed by symbol code and timestamp, with the other columns of the table: `exchange_code`, `open`, `high`, `low`, `close`, `adjusted_close` (daily only) and `volume`. The bars of all venues are concatenated; their order is the one the database returns, since the query has no `ORDER BY`. Timestamps are naive and mean UTC (`4_design.md` 2.3). | MKT-12, COR-10 |
| ACCESS-S06 | `read.newest_of_ohlcv(symbol_codes_per_exchange, time_frame)` returns the newest bar of each given symbol, in the same form, but with symbol code and timestamp also kept as columns. | MKT-12, BT-12 |
| ACCESS-S07 | A symbol without bars is absent from the result. An empty mapping returns an empty `DataFrame` with the table's columns. A venue with an empty list of symbols raises `QueryError` ("too few arguments for 'in'"). | MKT-12, QRY-4 |
| ACCESS-S08 | Each price read runs one query per venue, however many symbols are given. | MKT-12 |

### 7.3 Safety and errors

| ID | Specification | Satisfies |
| -- | ------------- | --------- |
| ACCESS-S09 | Lookup values, exchange codes and bounds are bound as parameters; symbol codes go into the query as quoted SQL literals, with quotes doubled. Values meant to break out of their literal or parameter find nothing and change nothing. | QA-10 |
| ACCESS-S10 | Every read opens its own connection (STORAGE-S16); a failed read raises `QueryError`. | MKT-12, LIB-4 |

### 7.4 Known gaps

| Gap | Requirement | Closed by |
| --- | ----------- | --------- |
| Fundamentals can't be read | MKT-14 | `query-layer` |
| No discovery: what exchanges, instruments and time ranges are stored can't be asked | QRY-2 | `query-layer` |
| Instruments are given as venue plus code in a mapping, not by a single identifier | QRY-3 | `query-layer` |
| A venue with an empty symbol list raises `QueryError` instead of returning nothing | QRY-4 | `query-layer` |
| Records come back by position, without column names; the sector record lacks the exchange code | LIB-5 | `query-layer` |
| `exchange`, `symbol`, `sector` and `newest_of_ohlcv` have no docstrings | LIB-6 | `library-contract` |
| Timezone-aware bounds aren't rejected, local times are read as UTC | COR-11 | `library-contract` |
| The order of the bars isn't specified | BT-12 | `query-layer` |
| No adjusted prices on read, no aggregation to coarser intervals, no latest *N* bars, no gap handling | BT-5, BT-10, BT-11, BT-12 | `corporate-actions`, `query-layer` |

---

## 8 CLIENT: library facade

### 8.1 Package and client

| ID | Specification | Satisfies |
| -- | ------------- | --------- |
| CLIENT-S01 | The package offers its public names at the top level: `from markethistorydb import Client, Config, MarketHistoryDbError, TimeFrame, SymbolStatus`. The other exception classes are imported from `markethistorydb.errors`. | LIB-5 |
| CLIENT-S02 | Importing the package reads no environment variable, opens no connection and writes nothing. It adds a `NullHandler` to the `markethistorydb` logger and configures nothing else: no handler, level or format. | LIB-1, LIB-2 |
| CLIENT-S03 | `Client(config)` uses the given `Config` as it is; `Client()` reads it from the environment when the client is created (CONFIG-S02), raising `ConfigError` if a required variable is missing. Creating a client opens no connection (STORAGE-S21). | LIB-3, LIB-11 |
| CLIENT-S04 | A client offers `config`, `read` (chapter ACCESS), `setup()` (STORAGE-S01, which drops every table without asking) and `fetch(time_frame, symbol_status, exchange, should_stop)` (chapter RUNS). | MKT-3, MKT-11, MKT-12, MKT-13 |
| CLIENT-S05 | The library emits log records through module loggers below `markethistorydb` (e.g. `markethistorydb.fetch.fetcher`) and never configures logging itself; the command line does (chapter LOGGING). | LIB-2 |
| CLIENT-S09 | The public classes and functions carry type annotations and reStructuredText docstrings with their parameters, return value and the errors they raise, except `Client.__init__` and `Read.exchange`, `Read.symbol`, `Read.sector` and `Read.newest_of_ohlcv`. | LIB-6, LIB-7 |

### 8.2 Errors

| ID | Specification | Satisfies |
| -- | ------------- | --------- |
| CLIENT-S06 | Every error the package raises on purpose derives from `MarketHistoryDbError`, in this tree: <br>• `ConfigError`, `StorageError`, `UserInterruptError`; <br>• `FetchError` → `RequestError`, `NetworkError`, `CompatibilityError`, `NoDataError`, `ApiError`; `ApiError` → `AccountError` (→ `UnauthorizedError`, `DataLimitError`, `AccessRightsError`), `RateLimitError`, `BadGatewayError`; <br>• `DbError` → `InsertError` (→ `SchemaMismatchError`), `QueryError`. | LIB-4 |
| CLIENT-S07 | An error renders as its message, with " (Error Code: N)" appended when it carries a code, e.g. "rejected (Error Code: 401)"; `message` and `error_code` give the two parts on their own. An `ApiError` also offers `http_status` and `retry_after`. | LIB-4 |
| CLIENT-S08 | Failures of the libraries used underneath reach the caller as the package's own errors: request failures as `NetworkError` or `RequestError` (PROVIDER-S09, S13), database failures as `QueryError`, `InsertError` or `DbError` (STORAGE-S03, S12 to S15, S18). | LIB-4 |

### 8.3 Known gaps

| Gap | Requirement | Closed by |
| --- | ----------- | --------- |
| No `__all__`, no `__version__`, no `py.typed` marker | LIB-5, LIB-7, LIB-10 | `library-contract` |
| No `close()` and no context manager; a client holds nothing to release only because every operation opens its own connections | LIB-8, OPS-2 | `library-contract`, `connection-reuse` |
| `fetch` returns a count, not an outcome the caller can act on | LIB-9 | `library-contract` |
| `Client.__init__` has no docstring (the `Read` methods: ACCESS, section 7.4) | LIB-6 | `library-contract` |
| The public API isn't checked by a type checker | LIB-7 | `library-contract` |

---

## 9 CONFIG: configuration

### 9.1 Settings

| ID | Specification | Satisfies |
| -- | ------------- | --------- |
| CONFIG-S01 | `Config` holds the eodhd API token and the QuestDB connection settings: `eodhd_api_token` and `questdb_password` (required), `questdb_host` (default `127.0.0.1`), `questdb_pg_port` (`8812`), `questdb_http_port` (`9000`), `questdb_user` (`admin`) and `questdb_db_name` (`qdb`). A `Config` can't be changed once built. | LIB-3, OPS-3 |
| CONFIG-S02 | `Config.from_env()` reads `EODHD_API_TOKEN` and `QUESTDB_PASSWORD`, which are required, and `QUESTDB_HOST`, `QUESTDB_PG_PORT`, `QUESTDB_HTTP_PORT`, `QUESTDB_USER` and `QUESTDB_DB_NAME`, which fall back to their defaults when unset. A required variable that is unset or empty raises `ConfigError` naming it and pointing to `.env.example`; a port that isn't an integer raises `ConfigError` naming the variable and its value. The library reads the process environment only; loading a `.env` file is left to the command line (chapter CLI). | LIB-3, CLD-3 |
| CONFIG-S03 | The printed form of a `Config` (`repr`) contains neither the API token nor the password. | QA-9 |
| CONFIG-S04 | **SQL connection string:** user, password, host, port, database name and a connect timeout of 10 s, each value quoted, so that a password containing spaces, quotes or backslashes stays one value and can't add settings of its own. | QA-10, CLD-8 |
| CONFIG-S05 | **Ingestion configuration string:** `http::addr=<host>:<port>;username=<user>;password=<password>;`, with every `;` inside a value doubled, so that no value can end early; the QuestDB client accepts the result. | QA-10 |

### 9.2 Known gaps

| Gap | Requirement | Closed by |
| --- | ----------- | --------- |
| Only the token and the connection settings are configurable; fetch scope (exchanges, venues), thresholds, timeouts and paths are fixed in the code | OPS-3, MKT-9 | `settings-model` |
| Secrets come from environment variables only, not from files | CLD-3 | `settings-model` |
| No encrypted database connections (TLS) can be configured | CLD-8 | `connection-reuse`, `cloud-readiness` |
| One provider, named in the field (`eodhd_api_token`) | PRV-3, PRV-8 | `provider-interface`, `settings-model` |

---

## 10 CLI: command line

### 10.1 Commands

| ID | Specification | Satisfies |
| -- | ------------- | --------- |
| CLI-S01 | `markethistorydb fetch [--time-frame daily\|minute] [--symbol-status active\|delisted] [--exchange NAME]` and `markethistorydb setup`. Option values are case-insensitive. An invalid value is a usage error naming the valid choices ("choose from active, delisted"); a missing command is a usage error too; both exit with code 2. | MKT-3, MKT-11 |
| CLI-S02 | Before a command runs, the command line starts the logger (chapter LOGGING), loads a `.env` file into the environment, without overriding variables that are already set, and creates a `Client` from the environment (CONFIG-S02). The `.env` file is searched from the directory of the installed package upwards, not from the working directory. | OPS-3, OPS-4 |
| CLI-S03 | `fetch` calls `Client.fetch` with the given filters, all unset by default, and no stop function (chapter RUNS). | MKT-11, ING-15, CMD-2 |
| CLI-S04 | `setup` logs the question "Do you want to continue? If DB already exist, it will be deleted! (yes/y): " and reads one line from standard input. "yes" or "y", in any case, runs the setup (STORAGE-S01). Any other answer, or a closed standard input, logs that it is exiting, sets up nothing and ends with exit code 0. | COR-3 |

### 10.2 Exit codes and reporting

| ID | Specification | Satisfies |
| -- | ------------- | --------- |
| CLI-S05 | **Exit codes:** <br>• 0: success, including a declined setup; <br>• 2: usage error (from `argparse`; no error of the package uses it); <br>• 3: `RequestError`; <br>• 4: interrupted, by Ctrl+C or `UserInterruptError`; <br>• 5: `InsertError`; <br>• 6: `ConfigError`; <br>• 7: `CompatibilityError`, `SchemaMismatchError`; <br>• 8: `DbError`, including `QueryError`; <br>• 9: any other error; <br>• 10: `StorageError`; <br>• 11: `UnauthorizedError`; <br>• 12: any other `FetchError`, e.g. `NoDataError` or an `ApiError`; <br>• 13: `DataLimitError`; <br>• 14: `AccessRightsError`. <br>The most specific class of the error decides. Every error class of the package has a code other than 9, and every code is produced by some error. The README lists the codes. | CMD-1, CLD-6 |
| CLI-S06 | **Reporting:** a `ConfigError` and an account error are logged as one error line without traceback, e.g. "eodhd.com rejected the account or plan, stopping: …"; an interruption as "Run was interrupted, exiting..."; any other error with its traceback ("Command 'fetch' failed", or "Command 'fetch' failed unexpectedly" for errors outside the package's hierarchy), so that the traceback reaches the log file with the token masked. | CMD-1, OPS-4, QA-8 |

### 10.3 Known gaps

| Gap | Requirement | Closed by |
| --- | ----------- | --------- |
| `setup` can only be confirmed interactively; no `--yes`, and a declined setup ends with code 0, so a script can't tell it from success | CMD-2, COR-3 | `library-contract` |
| Ctrl+C on the command line raises `KeyboardInterrupt` wherever the run is, e.g. between deleting and writing a symbol's fundamentals (FUND-S07), instead of using the stop function; the stop points of RUNS-S08 are used by the library only | ING-3 | `library-contract` |
| `.env` is found only above the installed package's directory: after `pip install .` into an environment outside the project folder, the `.env` in the working directory is not read | OPS-3, DIST-1 | `publishing-readiness` |
| No commands to inspect or export stored data | CMD-3, CMD-4 | `query-layer` |
| `--exchange` takes the exchange's name in eodhd's list (e.g. `"USA Stocks"`), and only one | ING-15, PRV-1 | `settings-model`, `provider-interface` |

---

## 11 LOGGING: log output and token masking

### 11.1 Log output

| ID | Specification | Satisfies |
| -- | ------------- | --------- |
| LOGGING-S01 | `start_logger(log_dir=None, level=INFO)` configures the root logger with two handlers: standard output, and a file `markethistorydb.log` in `log_dir` (the working directory by default), written in UTF-8, rotated at 10 MiB, with 5 backups kept. Calling it again replaces the handlers instead of adding to them. The level applies to the root logger. The module constant `LOG_ONLY_TO_TERMINAL` (`False`) leaves out the file when set. | OPS-4, CLD-5 |
| LOGGING-S02 | Each line reads "{time} - {level} - {message}", with the time as `dd.mm.yyyy-HH:MM:SS` in local time. After the setup, the log says "Logger has been set up" and names the working directory. | OPS-4 |
| LOGGING-S03 | Python warnings, e.g. a pandas `FutureWarning`, are routed into the log. | OPS-4 |
| LOGGING-S04 | Every handler masks the API token in the finished line, so the message, its arguments and the traceback alike: the value after `api_token=` (query strings) and after `'api_token': ` or `"api_token": ` (printed dicts) is replaced by `***`, every occurrence on every line. Text without such a parameter stays unchanged. | QA-8 |

### 11.2 Known gaps

| Gap | Requirement | Closed by |
| --- | ----------- | --------- |
| The masking misses the URL-encoded form (`api_token%3D…`), other spellings of the parameter (`API_TOKEN=`) and the bare token; the database password isn't masked at all | QA-8 | `secret-redaction-hardening` |
| Plain text only, no structured format; log file location and terminal-only mode can't be configured from the command line | CLD-5, OPS-3 | `cloud-readiness`, `settings-model` |
| Log times are local without a time zone, while all data is in UTC | OPS-4 | `cloud-readiness` |

---

## 12 PACKAGING: package and entry points

### 12.1 Package

| ID | Specification | Satisfies |
| -- | ------------- | --------- |
| PACKAGING-S01 | The project is the Python package `markethistorydb`, version 0.1.0, for Python 3.12 and later, built with `uv_build` from `src/`. Its runtime dependencies are pandas, psycopg (binary), python-dotenv, questdb and requests. | DIST-1, DIST-5 |
| PACKAGING-S02 | Installing it provides the command `markethistorydb` (entry point `markethistorydb.cli:main`). `python -m markethistorydb` runs the same command line and exits with its code. | DIST-1 |
| PACKAGING-S03 | `uv sync` installs it for development, together with pytest, pytest-cov and ruff; `pip install .` installs it as a package. The README says so. | DIST-1, DIST-6 |

### 12.2 Known gaps

| Gap | Requirement | Closed by |
| --- | ----------- | --------- |
| No license, no authors, URLs or classifiers in the metadata; not published | DIST-2 | `publishing-readiness`, `release-1-0` (the act of publishing) |
| No changelog, contribution guidelines, security policy or statement of non-affiliation | DIST-4 | `publishing-readiness` |
| No optional parts (extras); every dependency is always installed | DIST-5 | `publishing-readiness` |
| `uv.lock` is ignored by git, so installations aren't reproducible | QA-4, QA-7 | `continuous-integration` |
| No versioning policy, no deprecation policy | DIST-3, DIST-7 | `publishing-readiness`, `release-1-0` |
| No type checker, import rules or security checks in the toolchain | QA-4, QA-11, LIB-7 | `continuous-integration`, `library-contract` |

---

## 13 QUALITY: the test suite

How the suite is organised is described in `5_test.md`, section 1; this chapter specifies what
it guarantees.

### 13.1 Test suite

| ID | Specification | Satisfies |
| -- | ------------- | --------- |
| QUALITY-S01 | The tests are split into three levels by directory: `unit` (provider and database faked), `integration` (a real QuestDB) and `live` (the real eodhd.com). Each directory marks its tests with the level's marker, the markers are registered, and `-m` selects a level. | QA-1 |
| QUALITY-S02 | The unit tests run with branch coverage of `src/`; with `--cov`, the run fails below 100 % line and branch coverage. Excluded are only `if __name__ == "__main__":` blocks and abstract methods. | QA-2 |
| QUALITY-S03 | Integration tests run only against the QuestDB named by `QUESTDB_TEST_HOST`, `QUESTDB_TEST_PG_PORT` and `QUESTDB_TEST_HTTP_PORT`, from the environment or `.env`. Without them, or with that instance unreachable within 2 s, they are skipped. If the instance has the host and a port of the application's QuestDB (`QUESTDB_*`), the whole run stops with exit code 3 before any test, because the tests drop every table. | QA-3 |
| QUALITY-S04 | Every integration test starts on empty tables, which it sets up itself; the test instance has to be started by hand. | QA-7 |

### 13.2 Known gaps

| Gap | Requirement | Closed by |
| --- | ----------- | --------- |
| Nothing checks changes automatically before they are merged; ruff isn't enforced, no type checker or import rules run | QA-4, QA-14 | `continuous-integration`, `code-hygiene`, `library-contract` |
| Unknown markers, new warnings, hanging tests and unit tests that use the network don't fail the run | QA-5 | `test-suite-hardening` |
| Live tests run by default and spend the account's calls | QA-6 | `test-suite-hardening` |
| The integration database is started by hand; no container | QA-7 | `continuous-integration` |
| Test doubles aren't checked against the interfaces they replace | QA-12 | `testable-core` |
| No performance baseline, no mutation testing, no dependency audit | QA-11, QA-13, QA-15 | `continuous-integration`, `data-integrity-checks`, `release-1-0` |
