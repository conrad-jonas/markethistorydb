# code-hygiene: design

## 1 Overview

| Part | Files (under `src/markethistorydb/` unless named otherwise) |
| ---- | ----- |
| ruff and the formatter | `pyproject.toml` (`[tool.ruff]`); every file of `src/` and `tests/`; `.git-blame-ignore-revs` (new); `.github/workflows/ci.yml` (*lint*); `README.md` (development commands) |
| unused code | `db/io/delete.py`; `db/statements/meta.py`, `price.py`, `symbol.py`, `fundamental.py`; `db/tables/exchange.py`, `price.py`, `symbol.py`, `fundamental.py`, `__init__.py`; their tests |
| reference updates | `db/io/update.py`, `db/io/insert.py`, `db/io/values.py` (new), `db/statements/symbol.py` |
| daily volume | `setup/schema/price.sql` |
| up-to-date log | `fetch/download/download_price_data.py` |
| field names converted once | `fetch/write/write_fundamental_data.py` |
| HTTP session | `client.py`, `fetch/fetcher.py`, `fetch/download/*.py`, `fetch/eodhd/request_data.py` and the four request classes; `tests/conftest.py` |
| smaller deduplications | `db/tables/price.py`, `db/io/read.py`, `db/io/insert.py`, `fetch/write/write_price_data.py`, `fetch/utils.py` |

## 2 ruff and the formatter

### 2.1 Configuration

```toml
[tool.ruff]
line-length = 120
target-version = "py312"

[tool.ruff.lint]
extend-select = ["G", "N"]
# Naive datetimes mean UTC throughout (4_design.md 2.3); library-contract rejects aware ones
ignore = ["DTZ"]

[tool.ruff.lint.per-file-ignores]
# The package's names are re-exported here; library-contract adds __all__ and removes this
"__init__.py" = ["F401"]
```

- **Default rules:** those of ruff 0.16.7, the locked version, about 410 rules. They cover
  pyflakes, isort, pyupgrade, bugbear, comprehensions, simplify, part of pylint, ruff's own rules
  and a few more. A newer ruff may add default rules. It is raised like any dependency, in a pull
  request of its own that fixes the new findings.
- **`G`** flags log messages that are formatted before the call (`G001`, `G004`).
- **`N`** checks the names of classes, functions, arguments and variables (pep8-naming).
- **`DTZ`** would flag every naive datetime, while naive datetimes meaning UTC are the project's
  convention (COR-10).
- **Not chosen** (decided on 2026-10-24):
  - the classic minimal set (`E4`, `E7`, `E9`, `F` plus `I`, `UP`, `G`, `N`): 345 findings,
    without bugbear, simplify and pylint;
  - `ALL` with ignores: 4,908 findings. `D401` asks for docstrings in the imperative mood, against
    the project's third-person convention, and `S101` flags every `assert` of the tests.
- **Later additions:** the security rules `S` come with `secret-redaction-hardening`, which
  modifies QUALITY-S11.

### 2.2 Findings and their fixes

376 findings with this configuration on 2026-10-24: 218 in `src/`, 158 in `tests/`.

| Rule | `src/` | `tests/` | What | Fix |
| ---- | ------ | -------- | ---- | --- |
| `UP030`, `UP032` | 116 | 118 | `"{0}".format(…)` | f-strings; in log calls `%s` arguments instead (`G001`) |
| `I001` | 39 | 34 | import order | `--fix` |
| `G001` | 22 | 0 | log message built with `.format` | by hand: `logger.info("Stored %s rows", n)` |
| `PLR0402` | 13 | 0 | `import markethistorydb.db.tables as tables` | `from markethistorydb.db import tables` (`--fix`) |
| `UP004` | 11 | 0 | `(object)` bases | `--fix` |
| `RUF012` | 2 | 5 | lists as class attributes, e.g. the expected columns | tuples |
| `UP035` | 4 | 0 | `typing.Callable` | `collections.abc.Callable` (`--fix`) |
| `ISC004` | 3 | 0 | implicit string concatenation inside a tuple | parentheses |
| `PLC0206`, `SIM117`, `SIM103`, `PLR1730`, `FLY002`, `RUF007` | 8 | 1 | dict iteration without `.items()`, nested `with`, returned conditions, … | by hand |

- `ruff check --fix` resolves 210 of them. Its diff is reviewed like any other change, not
  accepted wholesale, and `--unsafe-fixes` isn't used.
- The 70 `F401` findings of the `__init__.py` files are covered by the per-file ignore. A blind
  `ruff --fix` would have deleted these re-exports.

### 2.3 By hand, where the rules don't reach

- **Shebangs:** `#!/usr/bin/env python12.9` heads 24 files, though no Python 12.9 exists and no
  module is run directly. They are deleted. Ruff's `EXE001` reports such a shebang only where it
  can read the file mode: on Linux, where CI runs, but not on Windows, so it found none locally.
- **camelCase attributes:** `N` doesn't check attributes assigned on `self`. They keep their
  visibility:

  | Class | Today | After |
  | ----- | ----- | ----- |
  | `DownloadExchangeData`, `DownloadSymbolData`, `DownloadPriceData`, `DownloadFundamentalData` | `writeExchangeData`, `writeSymbolData`, `writePriceData`, `writeFundamentalData` | `write_exchange_data`, `write_symbol_data`, `write_price_data`, `write_fundamental_data` |
  | `Fetcher` | `_downloadExchangeData`, `_downloadSymbolData`, `_downloadPriceData`, `_downloadFundamentalData` | `_download_exchange_data`, `_download_symbol_data`, `_download_price_data`, `_download_fundamental_data` |

  The unit tests of `Fetcher` patch these private attributes. They follow the rename; replacing
  the patches by seams is `testable-core`'s job (testing rule 6).
- **Lazy logging:** every log call passes its values as arguments (`%s`), so that a message is
  formatted only when a handler emits it. Exception messages become f-strings. The records stay
  clean of the token: the values passed are masked where they are made (PROVIDER-S14), and the
  test of RUNS-S12 checks the records.

### 2.4 The formatter

- **`ruff format`** with the configuration above: double quotes, four spaces, line length 120.
  On 2026-10-24 it would reformat 110 of the 138 files. Aligned `=` columns and aligned imports
  are lost, which is intended: one style that no one has to keep up by hand.
- **Line length 120:** only 9 lines are longer today. With ruff's default of 88, about 1,040
  lines would be re-wrapped.
- Long strings and comments that the formatter can't wrap aren't flagged, since `E501` isn't
  selected.
- **One commit:** the reformatting is a commit of its own, with nothing else in it. Its hash
  goes into `.git-blame-ignore-revs`.
  - Without the list, `git blame` would name that commit for nearly every line, and hide the
    change that last touched each line in substance.
  - With it, GitHub's blame view attributes each line to the commit that changed it before the
    reformatting. Local `git blame` does the same after
    `git config blame.ignoreRevsFile .git-blame-ignore-revs`.
  - Lines that the formatter creates anew, e.g. by splitting a long call, may still name it.
- **Authorship stays as it is:** the list affects blame only. The formatting commit keeps its
  author and stays in `git log` like any other commit, so nothing hides who ran the formatter.
- **Common practice:** this is the usual way to handle a mass reformatting. GitHub reads the
  file natively; scikit-learn lists its "black -> ruff format" commit there, and Django keeps
  such a file too (checked on 2026-10-24).

### 2.5 *lint* required

- **In `ci.yml`:** the *lint* job runs `uv run ruff check --output-format github` and
  `uv run ruff format --check`, and loses `continue-on-error`.
- **Branch protection:** *lint* joins the required checks of `main` (CI-S01).
- **Pinned actions:** CI-T08's check of pinned actions runs in *lint*
  (`continuous-integration`), so from then on it blocks a merge as well.
- **README:** its development section names `uv run ruff check` and `uv run ruff format`.

## 3 Unused code

### 3.1 What goes

| Code | Module | Tests removed with it |
| ---- | ------ | --------------------- |
| the deletion paths of the symbol and price tables: `Delete._symbol_from_symbol_table`, `_symbol_from_price_table`, `StatementsSymbol.DROP_SYMBOL_FROM_TABLE`, `StatementsPrice.DROP_SYMBOL_FROM_DAILY_OHLCV` and `…_MINUTE_OHLCV`, and the module constants only they use | `db/io/delete.py`, `db/statements/symbol.py`, `price.py` | the six tests of `5_test.md` 2.7, second row |
| `StatementsMeta.SELECT_SCHEMA` | `db/statements/meta.py` | `integration/setup/test_main.py`: `test_every_column_is_found_through_the_meta_statement`. STORAGE-T04 keeps `test_every_table_is_created_as_its_constants_describe_it`, which compares every column already. |
| `StatementsPrice.SELECT_CLOSE_FROM_DAILY_OHLCV` and `…_MINUTE_OHLCV` | `db/statements/price.py` | none |
| the eight `StatementsFundamental.SELECT_ALL_FROM_*` | `db/statements/fundamental.py` | `unit/db/statements/test_fundamental.py`: `test_each_select_reads_its_own_table_by_symbol` |
| `DUMMY_SYMBOL_CODE`, `DUMMY_EXCHANGE_CODE_A`, `…_B`, `DUMMY_SYMBOL_NAME` | `db/tables/fundamental.py` | none |
| `ExchangeTableType`, `PriceTableType`, `SymbolTableType` | `db/tables/*.py`, `db/tables/__init__.py` | none |

The eight fundamental reads go as well (decided on 2026-10-24). `query-layer` builds its reads of
fundamentals with the generic SQL builder of `schema-from-code`, so these templates would be
rewritten anyway.

**What stays:** `StatementsMeta` with the three statements of the recovery (STORAGE-S20); the
price reads `SELECT_ALL_FROM_*_OHLCV` and `SELECT_LAST_FROM_*_OHLCV`; the deletion statements of
the fundamental tables.

### 3.2 A deletion request for another table

- `Delete.symbol_from_table` first checks that the table is one of `TABLE_NAMES_FUNDAMENTAL`.
  Otherwise it raises `ValueError` naming the table, e.g. "Deleting a symbol's records is
  supported for the fundamental tables only, not daily_ohlcv", before the recovery check, so no
  statement runs.
- **Why `ValueError`** (decided on 2026-10-24): the only caller, the fundamentals writer, passes
  fundamental tables. Any other table is a programming error, not a database failure. It isn't a
  `DbError`, so the run doesn't isolate it per symbol: it ends the fetch, and the command line
  exits with 9 (CLI-S05). The docstring documents it with `:raises ValueError:`, since it is part
  of the method's contract.
- **The parameter `timestamp_column`:**
  - **Today:** the signature is `symbol_from_table(symbol_code, exchange_code, table_name,
    timestamp_column: str | None, unique_key_columns)`. The fundamental path puts the last two
    arguments into its copy statement: `CREATE TABLE <t>_copy AS (…) TIMESTAMP(<timestamp_column>)
    PARTITION BY YEAR WAL DEDUP UPSERT KEYS(<unique_key_columns>)`.
  - **Why `None`:** it was there for the symbol tables (`symbol`, `sector`), which have no
    designated timestamp. Their path ignored both arguments, and so did the price path, whose
    statements name the columns themselves.
  - **After:** only the fundamental path is left, and every fundamental table has a designated
    timestamp. The type becomes `str`, and the docstring loses "None for the lookup tables".
- **The signature stays otherwise:**
  - the fundamentals writer passes `table.NAME`, `table.TIMESTAMP_COLUMN` and
    `table.UNIQUE_KEY_COLUMNS`;
  - the tests of FUND-T12 and the spies of the performance baseline (`data-integrity-checks`)
    call the method by this name;
  - passing the table class instead would be shorter, but `testable-core` turns this interface
    into a repository anyway.

## 4 Reference record updates

- **One conversion:** `to_sql_value(value)` in `db/io/values.py` (new) is today's
  `Insert._sql_value`: a missing value becomes `None` (NULL), and a numpy scalar its plain Python
  value. `Insert` and `Update` both use it.
- **One helper for the updates:** `Update.exchange`, `.symbol` and `.sector` convert every bound
  value and run the statement through one helper. The helper wraps `QueryError` in
  `InsertError` ("Updating symbol failed: …"), as `Insert._record` does ("Inserting into symbol
  failed: …").
- **ISIN:** `StatementsSymbol.UPDATE_SYMBOL` sets `isin` as well, and `Update.symbol` binds it.
  An update writes the provider's current values. If the provider stops sending an ISIN, the
  stored one becomes NULL, as the name, country, currency and type would.
- **Effect of the error class** (decided on 2026-10-24): a failed update is still isolated per
  symbol, since `InsertError` and `QueryError` are both `DbError`s (RUNS-S05). If it ends the
  run, e.g. the update of an exchange at the start of a pass, the command line exits with 5
  (`InsertError`) instead of 8 (`QueryError`, CLI-S05).

## 5 Daily volume

### 5.1 Checks (2026-10-24)

| Check | Result |
| ----- | ------ |
| full daily history of AAPL.US, AMZN.US, MCD.US, TSLA.US, VTI.US, EURUSD.FOREX and BTC-USD.CC (demo token), 63,214 bars | no null and no missing volume; every volume a JSON integer; zero volumes in EURUSD (6,578), BTC-USD (248) and AAPL (1) |
| test service: a float volume with a NaN, into the `LONG` column | refused: "cast error", `SchemaMismatchError` in the code (the gap) |
| a nullable `Int64` volume | refused by the QuestDB client: "pyarrow is required for this DataFrame path" |
| `LONG` column; the rows without volume sent without the field | stored as NULL; read back as `int64` if no NULL is among the rows read, as `float64` with NaN otherwise |
| `DOUBLE` column, a float volume with a NaN | stored as NULL, read back as `float64` NaN |
| `DOUBLE` column, `int64` volumes | accepted and stored as floating-point numbers; exact up to 2^53 (9,007,199,254,740,992) |

### 5.2 The change

- **Schema:** in `price.sql`, `daily_ohlcv.volume` becomes `DOUBLE`, like `minute_ohlcv.volume`
  (decided on 2026-10-24). Nothing else changes in the code. The writer sends the frame as it
  comes: integer volumes, or floating-point ones with NaN once a bar lacks its volume.
- **Read:** both price tables give their volume back as `float64`, a missing one as NaN
  (STORAGE-S22).
- **Precision:** daily volumes stay far below 2^53. `corporate-actions` adjusts volumes for
  splits on read, which yields fractions anyway.
- **Existing databases:** no migration, since there is no data to keep. `setup` creates the
  table with the new type.
- **Why not the alternatives:**
  - `LONG` with the field left out: the read type would depend on the data, so COR-4 (same
    types) would need a conversion on read;
  - a nullable `Int64`: it needs pyarrow, a large dependency, and a conversion on read as well;
  - dropping the fix: eodhd doesn't send null volumes, but COR-4 would stay open for any
    provider that does.

## 6 The up-to-date log line

- **Which line:** `DownloadPriceData.run` looks up the newest stored bar first, as today for the
  start of the request. If no bars come back:
  - without a stored bar, it logs "No data exists for symbol AAPL (NASDAQ, DAILY, ACTIVE)", as
    today;
  - with a stored bar, it logs "Symbol AAPL (NASDAQ, DAILY, ACTIVE) is up to date: newest bar
    2024-03-05 00:00:00".
- **When "up to date" applies:**
  - a daily request answered with no bars;
  - a minute period that starts at or after the current day, so nothing is requested;
  - minute windows that all come back empty.
- **Level and result:** both lines are logged at INFO, and `run` returns `False` in both cases.
  The run counts the symbol as downloaded either way (RUNS-S10). A fetch result that tells a
  stored symbol from an up-to-date one comes with `library-contract` (LIB-9).

## 7 Field names converted once

- **Today:** `RequestFundamentalData` converts the field names from camelCase to snake_case
  (PROVIDER-S20). `WriteFundamentalData._prepare_data_for_db` converts them again, which changes
  nothing on names that are snake_case already.
- **The change:** the writer's call goes. Its docstring says that the names arrive in snake_case.
- `convert_df_column_names_from_camel_to_snake_case` stays in `fetch/utils.py`, used by the
  request class only.
- **Effect:** a frame with camelCase names that reaches the writer now fails the column check
  (FUND-S06) instead of being renamed. Only tests passed such frames, so their fixture changes to
  snake_case names.
- **Test case:** FUND-T05 now verifies PROVIDER-S20, besides the table mapping of FUND-S03.

## 8 One HTTP session per fetch

### 8.1 Ownership

The owner was decided on 2026-10-24: `Client.fetch`.

```
Client.fetch
  with requests.Session() as session:              one per fetch
      per pass: Fetcher(…, session)
          Download{Exchange,Symbol,Price,Fundamental}Data(…, session)
              Request…Data(…, session=session)
                  _get: session.get(url, params, timeout=(10, 120))
  # the with block closes the session, also after an error
```

- **Without a session:** `RequestData.__init__` takes `session: requests.Session | None = None`.
  Without one, `_get` calls `requests.get` as today. The live contract checks and the tests that
  build request classes directly keep working unchanged.
- **Why `Client.fetch`:** it is where the resources of a fetch are created (testing rule 3:
  created once, borrowed everywhere else). Later, `testable-core` moves the session into the
  composition root, and `connection-reuse` may keep it for the client's lifetime behind
  `close()`.
- **No client state:** `Client` holds nothing between fetches, so it needs no `close()` yet.
- **Nothing else changes:** the URL, parameters and timeouts stay the same. A session reads the
  same environment settings, e.g. proxies, as `requests.get`, which uses a session internally.

### 8.2 Measured (2026-10-24, demo token, AAPL end-of-day bars, local machine)

| Request | Time |
| ------- | ---- |
| first request of a session (new connection) | 714 ms |
| right after it, and 5 s later (connection reused) | 173 ms, 188 ms |
| 20 s later (reused) | 413 ms |
| 70 s later | 716 ms: eodhd had closed the idle connection, and the session opened a new one without an error |
| without a session, average of three | 1,174 ms |

- **Gain:** about half a second per request, on this one machine. A new symbol's minute history
  takes about 67 requests (PRICES-S03).
- **Broken connections:** an idle connection the server has closed is replaced without an error.
  A connection that breaks during a request raises `NetworkError` and is retried (PROVIDER-S10),
  as today.

### 8.3 Tests

- **Fakes:** the fixtures `scripted_api` and `routed_api`, and so `FakeSeriesApi`, replace
  `requests.Session.get` as well as `requests.get`, so the tests through `Client` and `Fetcher`
  keep their fakes.
- **PROVIDER-T28:** a request class with a session sends through it; one without a session sends
  through `requests.get`.
- **PROVIDER-T29:** a fetch of two passes sends every request through one session, which is
  closed at the end, also when the fetch ends with an error.
- **Performance baseline:** QUALITY-S10 counts provider requests, which don't change, so
  `baseline.json` stays as it is.

## 9 Smaller deduplications

- **`PRICE_TABLE_BY_TIME_FRAME`**.
  - **Today, four branches pick names by time frame:**
    - `Read.ohlcv` and `Read.newest_of_ohlcv` each start with `if time_frame ==
      TimeFrame.DAILY: … else: …`, which picks four values: the statement, the column names,
      the symbol-code column and the timestamp column;
    - both then run the same loop: one statement per exchange with the symbol codes as
      literals, the rows into a frame, the frames concatenated, the index set to symbol code and
      timestamp;
    - they differ only in the statement (`SELECT_ALL_FROM_*` for a period, `SELECT_LAST_FROM_*`
      with `LATEST ON`), its parameters (start and end, or none), and whether the index columns
      stay columns as well (`drop=False` in `newest_of_ohlcv`);
    - `Insert.ohlcv` branches to pick the table name and the timestamp column;
      `WritePriceData._prepare_data_for_db` branches to pick the timestamp column and the unit of
      the provider's timestamps.
  - **The mapping**, in `db/tables/price.py` (`utils` imports nothing from `db`, so there is no
    import cycle):

    ```python
    PRICE_TABLE_BY_TIME_FRAME: dict[TimeFrame, type[TimeSeriesTable]] = {
        TimeFrame.DAILY: TableDailyOhlcv,
        TimeFrame.MINUTE: TableMinuteOhlcv,
    }
    ```

    The column names, the symbol-code column and the timestamp column come from the table class
    (`ALL_COLUMNS`, `Columns.SYMBOL_CODE`, `TIMESTAMP_COLUMN`), so the branches that only pick
    names go.
  - **`Read`:** two module constants map the time frame to the period read and to the newest
    read, the existing `SELECT_ALL_FROM_*` and `SELECT_LAST_FROM_*` statements. One private
    helper, `_select_ohlcv(statement, time_frame, symbol_codes_per_exchange, params,
    keep_index_columns)`, runs the loop. `ohlcv` calls it with the period and
    `keep_index_columns=False`; `newest_of_ohlcv` without parameters and with `True`. The results
    stay exactly as they are, which the existing tests of ACCESS check.
  - **`Insert.ohlcv`:** `table = PRICE_TABLE_BY_TIME_FRAME[time_frame]`, then
    `self.table(df, table.NAME, table.TIMESTAMP_COLUMN)`.
  - **`WritePriceData._prepare_data_for_db`:** the timestamp column comes from the mapping. The
    unit stays a branch (`None` for date strings, `"s"` for Unix seconds), since it describes the
    provider's payload, not the table.
  - **Effect:** about 25 lines fewer. The database layer names the time frames in one mapping
    and the statement lookups of `Read`, so another time frame, e.g. hourly bars, needs entries
    there instead of edits in four branches. It is a refactoring without a change of behaviour,
    so it needs no new test case.
  - What the request, download and write classes do differently per time frame (one request or
    windows, the timestamp unit) stays as it is: `testable-core` (`4_design.md` 6.7).
- **`EXCHANGE_URL_CODE = "exchange_url_code"`** in `fetch/utils.py`: `DownloadSymbolData`,
  `RequestPriceData` and `RequestFundamentalData` use it instead of the literal.
- **`TABLE_NAMES_EXCHANGE`:** `TABLES_NAMES_EXCHANGE` is renamed, to match the other three groups.

## 10 Not done

| Item | Where | Why |
| ---- | ----- | --- |
| `__all__`, and with it the end of the `F401` ignore | `library-contract` | decided on 2026-10-24: the public names are that feature's decision |
| *types* required (pyright) | `library-contract` | `continuous-integration`, `2_design.md` 3.2 |
| Security rules (`S`) | `secret-redaction-hardening` | QA-11 |
| Docstring rules (`D`) | nowhere: not used | `D401` demands the imperative mood, against the project's third-person convention. `library-contract` documents the public API. |
| A check for unused functions and classes (e.g. vulture) | nowhere: dropped | ruff finds unused imports and variables only. Code kept alive by its own tests, as here, needs a review either way, and such a tool would need a whitelist for the column constants that the code reads through `ALL_COLUMNS`. |
| pre-commit hooks | nowhere: dropped | *lint* checks every pull request; a local hook is each developer's own choice |
| Symbol and exchange as arguments of `WriteFundamentalData` | `testable-core` | `4_design.md` 7.5: testing rule 2 applies to every writer and request class |
| The time-frame branches of the request, download and write classes (beyond the table lookup) | `testable-core` | `4_design.md` 6.7 |
| `ErrorCode` moved to `cli.py`, a real prompt and `--yes` | `library-contract` | part of that feature's safe setup and command line (COR-3, CMD-2) |
| Reusing the database connections | `connection-reuse` | OPS-2, database side |
| Import rules | `target-architecture` | DG-1 settles the package layout first |

## 11 Decisions

| Decision | Choice | Reason |
| -------- | ------ | ------ |
| Ruff rules | the default rules of 0.16 plus `G` and `N`; `DTZ` off; the same for the tests; target Python 3.12 | decided on 2026-10-24: broad, without fighting the project's conventions; 376 findings, 210 fixed automatically |
| Formatter | `ruff format`, line length 120, checked in *lint*; one commit, listed in `.git-blame-ignore-revs` | decided on 2026-10-24: one style without hand alignment; 120 fits today's lines |
| `F401` in `__init__.py` | ignored per file until `library-contract` adds `__all__` | decided on 2026-10-24: no public names decided early, and `ruff --fix` can't delete the re-exports |
| Missing daily volume | `daily_ohlcv.volume` becomes `DOUBLE` | decided on 2026-10-24: NULL without pyarrow, one read type, as for the minute volume |
| HTTP session | one per `Client.fetch`, handed down, closed when the fetch ends | decided on 2026-10-24 |
| Unused code | everything in `4_design.md` 3.8 goes, the eight fundamental reads included | decided on 2026-10-24: `query-layer` builds its reads with the SQL builder of `schema-from-code` |
| Deletion from another table | `ValueError`, before any statement | decided on 2026-10-24: a programming error, not a database failure |
| Failed update | `InsertError`, as for an insert | decided on 2026-10-24: a failed write is an `InsertError`, a failed read a `QueryError` |

The decisions are recorded in `6_roadmap.md` in stage 4.

## 12 Implementation

| # | Issue | Covers |
| - | ----- | ------ |
| 1 | Unused code removed; the deletion refuses other tables; `TABLE_NAMES_EXCHANGE` | STORAGE-S19, T04, T30; the tests of `5_test.md` 2.7 |
| 2 | Reference updates: NULL, ISIN, `InsertError` | STORAGE-S11, S15, T17, T23, T38 |
| 3 | The daily volume as `DOUBLE`; `PRICE_TABLE_BY_TIME_FRAME` | STORAGE-S04, S22, T36 |
| 4 | The up-to-date log line; field names converted once; `EXCHANGE_URL_CODE` | PRICES-S07, T06, T11; FUND-S04, T05 |
| 5 | One HTTP session per fetch | PROVIDER-S24, T28, T29 |
| 6 | ruff configured and its findings fixed; shebangs, names, lazy logging; the formatter; *lint* required; the merge into the global files | QUALITY-S11, T11; CI-S03, T03, T15 |

- **Order:** issues 1 to 5 are independent of each other. Issue 6 comes last, so that the
  reformatting commit runs once all other changes are in.
- **Earlier features:** issue 1 builds on STORAGE-S19 as `data-integrity-checks` leaves it, and
  issue 3 on STORAGE-T36 of `test-suite-hardening`.

## 13 Open questions

1. **Keep-alive over a long fetch:** the measurement of section 8.2 used five requests. Whether
   eodhd keeps connections alive the same way over thousands of requests shows on the first real
   fetch with the account's token.

## 14 Changes to `4_design.md` on merge

- **2.2 (columns):** `daily_ohlcv.volume` is `DOUBLE`. "Columns not marked `VARCHAR`, `DOUBLE`,
  `LONG` or `TIMESTAMP`" loses `LONG`, which no table uses any more.
- **3.2 (table definitions):** `PRICE_TABLE_BY_TIME_FRAME`.
- **3.4 (writing):**
  - updates convert their values through `to_sql_value` (`db/io/values.py`), shared with the
    inserts, and wrap `QueryError` in `InsertError`;
  - `Insert.ohlcv` takes its table from the mapping.
- **3.7 (deletion):** only the fundamental path; a request for another table raises
  `ValueError`. The sentence on the symbol and price paths goes.
- **3.8 (unused code):** removed; 3.9 becomes 3.8.
- **4.2 (request flow):** `_get` sends through the session if it has one, else through
  `requests.get`.
- **4.7 (object lifecycle):** the last bullet becomes the session per fetch (PROVIDER-S24), with
  the measurements of section 8.2.
- **5.4 (reference writes):** "What an update keeps" goes, since the symbol update writes the
  ISIN too.
- **6.2 (flow per symbol):** the empty branch logs "No data exists …" or "… is up to date …".
- **7.1, 7.2 (fundamentals):** the writer no longer converts names ("prepare: add codes,
  convert types, …").
- **7.6 (known limitations):** the row "Field names are converted to snake_case twice" is
  removed.
- **9.3 (price reads):** the shared helper of `Read`.
- **10.2 (client):** `Client.fetch` opens the session.
- **14.1 (project files):** `pyproject.toml` gains `[tool.ruff]`; `.git-blame-ignore-revs` is
  added.
- **15 (QUALITY):** a row for lint and format (QUALITY-S11): `[tool.ruff]` in `pyproject.toml`
  and the *lint* job.
- **Appendix A:** rows for the HTTP session per fetch and the floating-point daily volume.
- **Known limitations:** besides 7.6, no row is removed.
