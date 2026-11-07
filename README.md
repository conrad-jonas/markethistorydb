# MarketHistoryDB

Creates and manages a QuestDB database for historical exchange market data, fed from eodhd.com.

## Install

```
uv sync            # development (includes pytest, ruff, pyright)
pip install .      # as a package
```

Copy `.env.example` to `.env` and fill in `EODHD_API_TOKEN` and `QUESTDB_PASSWORD`.

### QuestDB server settings

Add to the QuestDB instance's `server.conf` (and restart it):

```
line.auto.create.new.columns=false
```

By default QuestDB adds a column for every field an ILP write carries that the table lacks. A
field eodhd.com starts to send would then quietly become a new column. With the setting off, the
write is rejected instead and the symbol fails with `SchemaMismatchError` (exit code 7). Fundamentals
are checked against their table before the symbol's stored records are replaced, so a rejected
write never leaves them deleted.

## CLI usage

```
markethistorydb setup                      # create tables (asks for confirmation)
markethistorydb fetch [--time-frame daily|minute] [--symbol-status active|delisted] [--exchange NAME]
```

Also available as `python -m markethistorydb ...`.

## Library usage

```python
from markethistorydb import Client, Config, TimeFrame

client = Client(Config(eodhd_api_token="...", questdb_password="..."))  # or Client() to read the environment
client.setup()                                   # drops and recreates the tables
client.fetch(TimeFrame.DAILY, exchange="USA Stocks")
df = client.read.ohlcv({"NASDAQ": ["AAPL"]}, TimeFrame.DAILY)
```

`Client()` without a config uses `Config.from_env()` (`EODHD_API_TOKEN`, `QUESTDB_PASSWORD`, optional `QUESTDB_HOST`, ...).
The library never configures logging; add your own handlers. Pass `should_stop=callable` to
`client.fetch` to abort between symbols.

## Data before 1970

QuestDB cannot store a designated timestamp before 1970-01-01: the server rejects one written
through SQL, and the ingress client refuses to send one. Every record whose designated timestamp
is earlier is therefore dropped before it is written: prices by their `timestamp`, fundamentals
by their table's designated timestamp (`report_date` for quarterly earnings, `date` for annual
earnings, `filing_date` for the balance sheet, cash flow and income statements). Each symbol with dropped records gets a warning naming the table (or
price time frame) and the number of records, e.g.

```
Dropped 1843 DAILY price records of IBM.NYSE from before 1970, which QuestDB cannot store
```

This mostly affects the daily prices of old US stocks, which eodhd.com has back to the 1960s.
If every price eodhd.com sends for a symbol is from before 1970, nothing is stored for it. If
every fundamental record it sends for one of the tables is, the records already stored for the
symbol in that table are left in place: the replacement would otherwise delete them and write
nothing. Date columns that are not the designated timestamp (e.g. a statement's `date`) are
stored as they are, even before 1970.

## Timestamp conventions

All internal datetimes are naive (no timezone info) and hold UTC wall-clock time: the same UTC
that eodhd.com sends in minute data and that QuestDB stores for a designated timestamp. When you
pass a datetime to the library or build one from the stored data, treat it as UTC. This matters
most when requesting minute data programmatically.

- **Minute data**: request bounds are sent as Unix seconds, converted with
  `dt.replace(tzinfo=UTC).timestamp()`. A bare `dt.timestamp()` would read the naive datetime as
  local time and shift the range by the machine's UTC offset.
- **Daily data**: requests use plain trading dates (`YYYY-MM-DD`), and each bar is stored at
  midnight UTC of its trading date.

To convert between local time and the stored naive UTC:

```python
from datetime import UTC
from zoneinfo import ZoneInfo

# Local -> stored
utc_naive = local_dt.astimezone(UTC).replace(tzinfo=None)
# Stored -> local
ny_time = stored_ts.replace(tzinfo=UTC).astimezone(ZoneInfo("America/New_York"))
```

## Error handling

Every error the CLI can end a run with is a subclass of `MarketHistoryDbError`
(`markethistorydb.errors`). `main()` maps the most specific class an error matches to an exit
code; a `MarketHistoryDbError` that matches none of the mapped classes below (directly or
through a mapped parent) exits with `UNKNOWN_ERROR` (9).

| Code | `ErrorCode` member | Exception(s) | Meaning |
| ---- | ------------------- | ------------ | ------- |
| 0 | `SUCCESS` | — | command completed |
| 2 | — | — | reserved: argparse exits with it on a bad command line |
| 3 | `REQUEST_ERROR` | `RequestError` | a request failed after all retries |
| 4 | `USER_INTERRUPT_ERROR` | `UserInterruptError`, `KeyboardInterrupt` | the run was interrupted (Ctrl+C) |
| 5 | `INSERT_ERROR` | `InsertError` | writing to QuestDB failed |
| 6 | `CONFIG_ERROR` | `ConfigError` | configuration problem, e.g. a missing or unusable environment variable |
| 7 | `COMPATIBILITY_ERROR` | `CompatibilityError`, `SchemaMismatchError` | the provider's data no longer has the expected structure, or no longer fits the tables |
| 8 | `DB_ERROR` | `DbError`, `QueryError` | the DB is unreachable or a statement failed |
| 9 | `UNKNOWN_ERROR` | any other `MarketHistoryDbError` | fallback for an error with no more specific mapping |
| 10 | `STORAGE_ERROR` | `StorageError` | not enough free disk space |
| 11 | `AUTH_ERROR` | `UnauthorizedError` | the API token was rejected |
| 12 | `FETCH_ERROR` | `FetchError`, `NetworkError`, `NoDataError`, `ApiError`, `AccountError`, `RateLimitError`, `BadGatewayError` | fetching data from the provider failed |
| 13 | `DATA_LIMIT_ERROR` | `DataLimitError` | the API plan's data limit has been reached |
| 14 | `ACCESS_RIGHTS_ERROR` | `AccessRightsError` | the plan does not cover the requested endpoint |

The exception hierarchy and corresponding exit codes:

```
MarketHistoryDbError
├── ConfigError                    (6)
├── StorageError                   (10)
├── UserInterruptError             (4)
├── FetchError                     (12)
│   ├── RequestError               (3)
│   ├── NetworkError               (12)
│   ├── CompatibilityError         (7)
│   ├── NoDataError                (12)
│   └── ApiError                   (12)
│       ├── AccountError           (12)
│       │   ├── UnauthorizedError  (11)
│       │   ├── DataLimitError     (13)
│       │   └── AccessRightsError  (14)
│       ├── RateLimitError         (12)
│       └── BadGatewayError        (12)
└── DbError                        (8)
    ├── InsertError                (5)
    │   └── SchemaMismatchError    (7)
    └── QueryError                 (8)
```

A `fetch` run does not stop at the first bad symbol: a symbol whose data cannot be
downloaded or stored is logged, counted and skipped, and the run ends with a summary of what
was skipped. Only errors that say nothing about the individual symbol end the run early -
a rejected token, a full disk, an interrupt, or enough symbols failing in a row that the
fault is clearly not with the symbols.

## Tests

```
uv run pytest                    # all tests, without coverage; calls the real eodhd.com API
uv run pytest -m "not live"      # all tests but the live ones: no API calls, no network needed
uv run pytest -m unit --cov      # unit tests only; fails below 100 % line and branch coverage
uv run pytest -m integration     # integration tests only
uv run pytest -m live            # contract tests against the real eodhd.com API only
```

> **API costs:** a plain `uv run pytest` includes the live tests, which spend API calls of the
> account behind `EODHD_API_TOKEN`: one call each to `exchanges-list` and
> `exchange-symbol-list` per run. These count against the plan's daily limit, and on a
> pay-per-use plan they may cost money. Leave `EODHD_API_TOKEN` unset for the test run, or pass
> `-m "not live"`, to avoid them. The other live tests use the free public `demo` token.

Coverage is off unless `--cov` is passed. Its settings (source, branch coverage, the 100 %
threshold, missing lines in the report) come from `[tool.coverage.*]` in `pyproject.toml`.

`tests/unit` mirrors `src/markethistorydb`, one `test_<module>.py` per module. The eodhd.com
API is faked with the sample payloads in `tests/data/eodhd`, so no unit test calls the real API.

`tests/live` checks that eodhd.com still answers the way those samples record: same fields,
same JSON types, and frames from the request layer that hold exactly the columns of their
tables. Run it regularly (e.g. nightly), since the unit tests cannot notice when the provider
changes its API. It runs by default and needs network access; `-m "not live"` leaves it out.
eod, intraday and fundamentals are called with eodhd.com's public `demo` token. The list of
exchanges (`exchanges-list`) and the list of an exchange's symbols (`exchange-symbol-list`) need
`EODHD_API_TOKEN`, one call each per run (see **API costs** above). They are skipped if it is
unset, or if eodhd.com refuses it: rejected (401), out of calls (402), or the plan not covering
the endpoint (403). On a failure, adapt the request layer and tables to the new shape, then
refresh the sample payload.

`tests/integration` runs against a real QuestDB and **drops and recreates every table**, so it
only runs against a throwaway instance:

- **Your own instance,** named by `QUESTDB_TEST_HOST`, `QUESTDB_TEST_PG_PORT` and
  `QUESTDB_TEST_HTTP_PORT` (plus `QUESTDB_TEST_USER`/`QUESTDB_TEST_PASSWORD`, see
  `.env.example`). The tests refuse to run if these point at the instance the `QUESTDB_*`
  variables configure. Start a second QuestDB with its own data directory and ports for it, e.g.
  with a `server.conf` holding `http.bind.to=127.0.0.1:19000`, `pg.net.bind.to=127.0.0.1:18812`,
  `line.tcp.net.bind.to=127.0.0.1:19009` and `http.min.net.bind.to=127.0.0.1:19003`, plus
  `line.auto.create.new.columns=false` as in production (the test for it is skipped otherwise).
- **A container,** when those variables are unset and Docker answers: the tests start QuestDB
  10.0.1 through testcontainers, with `line.auto.create.new.columns=false`, and remove it after
  the run. `QUESTDB_TEST_IMAGE` names another image, e.g. `questdb/questdb:latest`. On Windows,
  Docker Desktop needs Linux containers.

With neither, the integration tests are skipped.
