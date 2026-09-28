# MarketHistoryDB

Creates and manages a QuestDB database for historical exchange market data, fed from eodhd.com.

## Install

```
uv sync            # development (includes pytest, ruff)
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

Nothing is read from the environment at import time; `Client()` without a config uses
`Config.from_env()` (`EODHD_API_TOKEN`, `QUESTDB_PASSWORD`, optional `QUESTDB_HOST`, ...).
The library never configures logging; add your own handlers. Pass `should_stop=callable` to
`client.fetch` to abort between symbols.

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

## ToDo

- Implement all missing tests
- Deploy via CI pipeline to github.com
- Make project ready for library usage
- Add read functionality to CLI usage (next to setup and fetch)
- Update the four stale test modules (they import the pre-refactor layout and are skipped
  via `collect_ignore` in `tests/conftest.py`)
- Storage error should trigger if machine on which DB (not the client) runs into limited storage space
- use ruff, pydantic and mypy in the CI workflow
- Move more constants into configuration
- Implement REST API endpoints for fetch and read functionality
- Make app cloud native ready
- Check for performance / scalability issues
- Check for security issues

