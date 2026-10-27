# test-suite-hardening: design

## 1 Overview

| Part | Files |
| ---- | ----- |
| pytest configuration | `pyproject.toml` (`[tool.pytest.ini_options]`, dev dependencies); `tests/unit/conftest.py`, `tests/integration/conftest.py`, `tests/live/conftest.py` (collection hooks) |
| test support | `tests/support/builders.py` (new); `tests/fakes.py` (`FakeSeriesApi`, `FakeDb.calls`, `RecordingQuery(fail_at=…)`) |
| integration database | `fresh_db` in `tests/integration/conftest.py` |
| new and filled tests | the modules named in `3_test.md` |
| documentation | the README's section on the tests |

No file under `src/` changes.

## 2 pytest configuration

### 2.1 Sketch

```toml
[dependency-groups]
dev = [
    "pytest>=9.1.1",
    "pytest-cov>=7.1.0",
    "pytest-socket>=0.8.1",
    "pytest-timeout>=2.4.0",
    "ruff>=0.16.7",
    # pyright comes with continuous-integration
]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-m 'not live' -ra"
strict = true
timeout = 30
filterwarnings = [
    "error",
    # Insert opens a QuestDB Sender per write, which the client reports as a burst of
    # reconnections; connection-reuse shares one per run and removes this line
    "ignore:.*Detected a burst of reconnections:UserWarning",
]
markers = [
    "unit: tests that fake the eodhd.com API and the database",
    "integration: tests that run against a real QuestDB",
    "live: tests that call the real eodhd.com API, spending calls of EODHD_API_TOKEN's account; left out unless -m selects them, e.g. -m live",
]
```

- **`strict = true`** (pytest 9) turns on four rules at once: unknown markers, unknown
  configuration keys, a passing `xfail`, and parameter sets of one test with the same ID are
  errors. `--strict-markers` and `xfail_strict` aren't needed besides it.
- **`-ra`** adds every test that did not pass to the closing report, with its reason.
- Checked on 2026-10-22: the suite collects under `strict` except for
  `unit/db/io/test_read.py::test_a_duplicated_unique_key_is_a_query_error_naming_the_record`,
  whose two parameter sets get the same ID; they get explicit IDs. No test uses `xfail`.

### 2.2 Live tests opt-in

- pytest puts `addopts` before the arguments of the command line, and a later `-m` replaces an
  earlier one. `pytest` alone therefore leaves the live tests out, while `pytest -m live`, CI's
  `-m unit` and `-m integration`, and `-m "unit or live"` select exactly what they name.
- `pytest tests/live` without `-m live` deselects all 18 tests and ends with exit code 5 ("no
  tests ran"; checked on 2026-10-22). QUALITY-S05 states it; the README and the docstring of
  `tests/live/conftest.py` say to add `-m live`.

### 2.3 Warnings

- `error` applies to the test and to the setup and teardown of its fixtures.
- Checked on 2026-10-22 with `-W error`:
  - unit tests: one failure. `test_warnings_are_routed_into_the_log` raises a `FutureWarning` on
    purpose; it gets `@pytest.mark.filterwarnings("always::FutureWarning")`, so the warning
    reaches the logging module as before.
  - integration tests: one failure, QuestDB's "Detected a burst of reconnections" in
    `test_a_daily_run_stores_every_symbol_of_the_exchange`. The client raises it when senders are
    opened in quick succession, so on another machine other tests may raise it too; the
    exception therefore goes into the configuration, not onto that test.
- **Rule for exceptions:** each names the warning's class and a pattern of its message (a
  regular expression matched from the start of the message), never a whole category or module,
  and carries a comment naming the feature that removes it.

### 2.4 Time limits

- pytest-timeout. `timeout = 30` applies to every test; the collection hooks of
  `tests/integration/conftest.py` and `tests/live/conftest.py` add `pytest.mark.timeout(120)`
  and `pytest.mark.timeout(300)` to their tests. A single test that needs longer gets its own
  mark with a comment.
- The time includes the test's fixtures, so a hanging setup is caught too, e.g. a QuestDB that
  accepts connections but never answers a statement (the SQL connection has a connect timeout,
  but no statement timeout).
- **Why these limits:**
  - unit: the 530 tests take 1.6 s together; 30 s catches e.g. a real backoff wait that a test
    forgot to fake;
  - integration: the slowest test takes 5.1 s locally (the second fetch run), but the first test
    of a session also starts the container (CI-S11): pulling the image and waiting up to 60 s
    for QuestDB to answer SQL;
  - live: a request may wait 10 s to connect and 120 s for an answer, and is retried (PROVIDER-S03,
    S10). 300 s allows one slow answer and a retry, while a provider stuck in rate limiting
    (waits up to 3600 s, PROVIDER-S11) fails the test instead of holding the nightly run for an
    hour.
- **Linux and Windows:** pytest-timeout interrupts the test through a signal on Linux; the test
  fails and the run goes on. Windows has no such signal, so a watchdog thread prints the stacks
  and ends the process. QUALITY-S08 states the difference.

### 2.5 No network in unit tests

- pytest-socket. The collection hook of `tests/unit/conftest.py` adds
  `pytest.mark.disable_socket` to each unit test, next to `pytest.mark.unit`. Creating a socket
  then raises `SocketBlockedError`, at the line that tried.
- Checked on 2026-10-22: the 530 unit tests pass with sockets blocked, and a test that creates a
  socket fails.
- **Not covered:** processes a test starts (the tests of CLIENT-T03 and QUALITY-T03 start Python
  processes, which need no network either), and name lookups such as `socket.getaddrinfo`, which
  no unit test makes.

## 3 Test support

### 3.1 Builders

`tests/support/builders.py`, in the new package `tests/support/`. Each builder returns a fresh
object with typical values and takes keyword arguments for the values a test is about, so a test
names only those.

| Builder | Returns | Replaces |
| ------- | ------- | -------- |
| `symbol(**fields)` | a symbol as `pd.Series`: AAPL on NASDAQ, list code US | the constant `_SYMBOL = pd.Series(...)` of 8 modules; `_symbol(...)` of `integration/fetch/write/test_write_symbol_data.py` and `unit/fetch/download/test_download_fundamental_data.py` |
| `exchange(**fields)` | an exchange: USA Stocks, code US | `_EXCHANGE` of `unit/fetch/write/test_write_exchange_data.py`; `_exchange(...)` of `integration/fetch/write/test_write_exchange_data.py` |
| `daily_bars(symbol_code="AAPL", exchange_code="NASDAQ", days=(2,), **columns)` | daily bars of January 2024 with the table's columns | `_daily_prices(...)` of `integration/db/io/test_insert.py` and `test_read.py` |
| `minute_bars(symbol_code="AAPL", exchange_code="NASDAQ", minutes=(0,), **columns)` | minute bars from 2024-01-02 14:30 UTC on | new; for the round trip and the series tests |
| `balance_sheet(**fields)` | a quarterly balance sheet frame as the provider sends it | `_balance_sheet(...)` of `unit/fetch/write/test_write_fundamental_data.py` |

Helpers that build something else stay in their module, e.g. the row tuples `_daily_row` and
`_minute_row` of `unit/db/io/test_read.py`.

### 3.2 `FakeSeriesApi`

A fake provider for the tests of PRICES-S09, in `tests/fakes.py`, built on `FakeRoutedApi`:

- It holds a fixed series per symbol: a daily bar per weekday, and minute bars around midnight
  UTC of every day (23:58 to 00:02), so that every window boundary, which falls on 00:00 UTC
  (PRICES-S03), has bars on both sides and on the boundary itself.
- It answers `/eod/<symbol>` with the daily bars from the request's `from` on, and
  `/intraday/<symbol>` with the minute bars between `from` and `to`, both inclusive, as
  eodhd's are (PROVIDER-S23); only bars before the pinned "now" exist. The other endpoints
  answer with the sample payloads, as in `FakeRoutedApi`.
- The series start some 130 days before "now", so a symbol's history crosses a window boundary
  while most of the windows from 2005 come back empty.
- A test can make a chosen request fail, e.g. "the third intraday request for MSFT", with a
  payload missing a field, which raises `CompatibilityError` without retries.
- "Now" is pinned by replacing the module's `datetime`, as the unit tests of PRICES do
  (`4_design.md` 6.7; `testable-core` brings an injected clock).

### 3.3 Call log and failing query

- **`FakeDb.calls`:** one list that every `Recorder` of a `FakeDb` appends to as well, as
  `(interface, method, args, kwargs)`. The test of FUND-T04 asserts the order of deletion and
  write through it; today it joins `db.delete.calls + db.insert.calls`, which passes with the
  order swapped too.
- **`RecordingQuery(fail_at=n)`:** the *n*-th statement raises `QueryError`, as the real `Query`
  does for a failing statement. The test of STORAGE-T32 runs a deletion once per position.

### 3.4 Stray tables

Before `setup`, `fresh_db` lists the tables (`SELECT table_name FROM tables()`) and drops each
that `setup` doesn't create, e.g. `earnings_quarterly_copy` left by an interrupted deletion
(STORAGE-S20). QuestDB's own tables (names starting with `sys.` or `telemetry`) are left alone
(open question 3).

## 4 New tests

### 4.1 Round trip of bars (STORAGE-T36)

`tests/integration/db/io/test_round_trip.py`. The builders give daily bars of two symbols on two
venues over three days with a missing `open`, and minute bars with a missing price and a missing
volume, their timestamps converted from Unix seconds as `WritePriceData` does
(`datetime64[s]`). Each symbol's bars go through `insert.ohlcv`; after the WAL has applied them,
`read.ohlcv` reads all back. The frames are compared with `pandas.testing.assert_frame_equal`,
dtypes included, after indexing and sorting both, with the written timestamps cast to
`datetime64[us]` (STORAGE-S22 states the resolution). A daily bar without volume is left out:
it can't be stored (known gap), and its test comes with the fix in `code-hygiene`.

Checked on 2026-10-22 with a script against the test service: values, dtypes and NaN round-trip
as STORAGE-S22 says; the rows of one venue come back in timestamp order, not grouped by symbol.

### 4.2 Series across runs (PRICES-T13, T14)

`tests/integration/fetch/test_series_across_runs.py`, with `FakeSeriesApi` behind a `Client` on
the test database:

- **PRICES-T13:** a minute pass with "now" on day *D*, then one on *D* + 1. The stored bars equal
  the fake's series up to 00:00 UTC of *D* + 1, each once.
- **PRICES-T14:** three symbols, a daily and a minute pass per run. Run 1 is stopped after the
  first symbol (its stop function turns true); in run 2, the third window of the second symbol
  fails; run 3 completes. Each symbol's stored daily and minute series then equals the fake's.
- The comparison covers timestamps and values, so a gap, a duplicate and a shifted bar all fail
  it.

### 4.3 The four passes (RUNS-T16)

In `tests/integration/test_client.py`: `Client.fetch` without filters, restricted to `USA
Stocks`, with `routed_api` (sample payloads). It checks the symbol records of each pass (daily
and minute, active and delisted), the bars in the daily and in the minute table, the one
exchange record and the fundamentals of the NASDAQ and NYSE symbols. Today only a daily active
pass runs against the database (RUNS-T03).

### 4.4 The command line in-process (CLI-T08)

`tests/integration/test_cli.py` calls `cli.main(["setup"])` and `cli.main(["fetch", "--time-frame",
"daily", "--exchange", "USA Stocks"])` in-process, with `routed_api` as the provider. The test
must not reach the application's database, since `setup` drops every table:

- every variable that `Config.from_env` reads is set to the test instance with `monkeypatch`:
  `QUESTDB_HOST`, `QUESTDB_PG_PORT`, `QUESTDB_HTTP_PORT`, `QUESTDB_USER`, `QUESTDB_PASSWORD`,
  `QUESTDB_DB_NAME`, and a fake `EODHD_API_TOKEN`;
- `cli.load_dotenv` is replaced by a function that does nothing and returns `False`, what
  `load_dotenv` returns when it finds no file. The unit tests of the CLI replace it the same
  way. The real `load_dotenv` searches for `.env` from the directory of `cli.py` upwards
  (CLI-S02), so it would find the repository's `.env`, which points to the application's
  database. It doesn't override variables that are already set, but it would add every
  variable the test forgot to set;
- the session's guard (QUALITY-S03) has made sure before any test that the test instance isn't
  the application's.

`setup`'s question is answered by replacing `sys.stdin` with `io.StringIO("yes\n")`, the way a
user answers it, without replacing `input`. The working directory is a temporary one (the log
file lands there), and `reset_logging` restores the logging setup. A second case answers the
exchange list with 401 and expects the exit code of `UnauthorizedError` and one log line
without traceback.

### 4.5 The guard (QUALITY-T03)

The guard is the check in the session fixture `questdb_config` (QUALITY-S03). Before any
integration test, it compares the test database named by `QUESTDB_TEST_*` with the
application's database named by `QUESTDB_*`, and stops the run if they are the same, because
every integration test drops all tables. Then it tries to connect to the test database, and
skips the integration tests if that fails within 2 s.

`tests/unit/integration_support/test_guard.py`, next to the test of `choose_test_database`
(CI-T13), runs the guard in a child pytest run: `python -m pytest -m integration
tests/integration/setup/test_main.py`. The child gets the test process's environment without
any `QUESTDB_*` or `EODHD_*` variable, plus the variables of the case. Each case sets every host
and port that the guard compares. The guard reads a variable that isn't set from `.env`, and the
repository's `.env` names the real databases. Only the user and password still come from there,
and they don't matter against a port that nothing listens on.

| Case | Test database (`QUESTDB_TEST_*`) | Application's database (`QUESTDB_*`) | What the guard does | Expected |
| ---- | -------------------------------- | ------------------------------------ | ------------------- | -------- |
| the test database is the application's | 127.0.0.1, ports 1 and 2 | 127.0.0.1, ports 1 and 2 | finds the same address in both and stops before connecting | exit code 3, output with "Refusing to run", no test run |
| the test database doesn't answer | 127.0.0.1, ports 1 and 2 | 127.0.0.1, ports 3 and 4 | finds different addresses, tries to connect to port 1 and gets no connection within 2 s | every test skipped with "is not reachable", exit code 0 |

Nothing listens on ports 1 to 4 on an ordinary machine or runner, so a broken guard still
finds no database whose tables it could drop. The third case, no `QUESTDB_TEST_*` and no
Docker, is covered by CI-T13.

### 4.6 Import in a fresh interpreter (CLIENT-T03)

In `tests/unit/test_init.py`: a child interpreter (`sys.executable -c …`) runs in an empty
temporary directory, with the environment minus every `QUESTDB_*` and `EODHD_*` variable. Before
importing `markethistorydb`, its script installs an audit hook (`sys.addaudithook`) that records
`socket.connect` and every `open` for writing, and replaces `os.environ` with a mapping that
records which variables are read and from which module. It prints what it recorded as JSON. The
test expects no read from a module of the package and no read of an `EODHD_*` or `QUESTDB_*`
variable from anywhere, no connection, no file opened for writing, and the directory still
empty.

## 5 Not done

What this feature leaves undone, and where it goes:

| Item | Where | Why |
| ---- | ----- | --- |
| Faster resets of the integration tables | nowhere: dropped on 2026-10-22 | `1_specs.md`, Scope |
| Tests of the rules of the suite themselves (QUALITY-S05 to S09), e.g. with `pytester` | nowhere: dropped on 2026-10-23 | Each rule is one setting of pytest or of a maintained plugin. Issue 1 checks each rule once by hand: a test with an unknown marker, one raising a warning, one sleeping past its limit, a unit test creating a socket. After that, a change to a setting shows in the `pyproject.toml` diff of its pull request. The configuration implements QUALITY-T01, T02 and T04 in the same way. |
| Splitting `assert a and b` (44 such asserts) | nowhere: dropped | pytest's assertion rewriting reports the failing operand with its values (checked on 2026-10-22), so such a failure is not ambiguous |
| Moving `load_payload` from `tests/fakes.py` to `tests/support/` | `testable-core` (M2) | that feature reorganises the doubles of `tests/fakes.py`; moving it now would move it twice |

## 6 Decisions

| Decision | Choice | Reason |
| -------- | ------ | ------ |
| Live tests | opt-in through `-m 'not live'` in `addopts` | opt-in is what QA-6 asks for; a later `-m` replaces it, so CI's explicit selections keep working; a flag such as `--live` would need a hook of its own |
| Strictness | pytest's `strict = true` | one setting for the four rules; rules that later pytest versions add come with it, and pytest is only raised deliberately through the lock file |
| No network in unit tests | pytest-socket, applied by the unit conftest | blocks the creation of sockets, which every connection needs; the unit tests pass with it |
| Time limits | pytest-timeout: 30 s, 120 s, 300 s per level | section 2.4 |
| Warnings | errors; each exception named, with the feature that removes it | a new warning shows in the change that causes it |
| Faster resets | dropped | decided on 2026-10-22: gain mostly local, against apply-waits and a second reset path |
| Missing test cases whose behaviour a later feature changes | left to that feature | decided on 2026-10-22: written now, they would be rewritten soon after |
| Daily bar without volume | fixed in `code-hygiene` | decided on 2026-10-22: this feature changes no file under `src/` |
| Trace script and `spec` markers | a feature of its own, entered in stage 4 | decided on 2026-10-22: it changes how "Implemented by" is maintained |
| Local smoke test of the console script | none; CI-T05 covers the installed command | past the argument parsing it would reach the application's database through `.env` (`1_specs.md`, Scope) |
| Checking the rules of the suite | once by hand, in issue 1; no test | decided on 2026-10-23: the configuration implements them, as it does QUALITY-T01, T02 and T04; a change shows in the diff of `pyproject.toml` (section 5) |

The decisions are recorded in `6_roadmap.md` in stage 4.

## 7 Implementation

GitHub issues, one branch and one pull request each (`1_constitution.md` 6.3, step 4), in this
order:

| # | Issue | Covers |
| - | ----- | ------ |
| 1 | pytest configuration: pytest-socket and pytest-timeout as dev dependencies (`uv add --dev`); `strict`, `addopts`, `filterwarnings`, the time limits, sockets blocked in unit tests; the logger test allows its warning; explicit IDs for the duplicated parameter sets; README and conftest docstrings; each rule checked once by hand | QUALITY-S05 to S09, T05 to T09; PACKAGING-S03 |
| 2 | Test support: `tests/support/builders.py` and the switch of the copies; `FakeDb.calls`; `RecordingQuery(fail_at=…)`; the cleanup of stray tables in `fresh_db` | QUALITY-S04, T04; the test of FUND-T04 |
| 3 | The Missing unit test cases | STORAGE-T32, PROVIDER-T16, REFDATA-T04, FUND-T09, CLIENT-T03, CLIENT-T08, LOGGING-T03, QUALITY-T03 |
| 4 | The Missing integration test cases | STORAGE-T10, REFDATA-T12, FUND-T10 |
| 5 | The round trip of bars; the gap row of the daily volume | STORAGE-S22, T36 |
| 6 | `FakeSeriesApi`; series across runs; the four passes | PRICES-S09, T13, T14; RUNS-T16 |
| 7 | The command line in-process; the merge into the global files | CLI-T08 |

Issues 3 to 7 use the builders of issue 2. The pull request of issue 7 completes the feature and
merges it into the global files (`1_constitution.md` 6.4).

## 8 Open questions

1. **Bounds of the intraday endpoint:** answered on 2026-10-23: eodhd includes both bounds, so
   neighbouring windows share their boundary bar, which is stored once (PRICES-S06).
   `data-integrity-checks` checks it every night (PROVIDER-S23, PROVIDER-T27).
2. **Warnings of the container fixture:** whether testcontainers or the Docker client raises
   warnings (e.g. `DeprecationWarning`) while the container of CI-S11 starts. Each becomes an
   exception of QUALITY-S07 or is avoided; checked in issue 1.
3. **QuestDB's own tables:** the local test service lists only the project's 13 tables in
   `tables()`. Whether the container lists tables of its own, and under which names, is checked
   in issue 2.

## 9 Changes to `4_design.md` on merge

- 15 QUALITY: rows for QUALITY-S05 to S09 in the table of guarantees (where each is configured);
  the row "empty tables per test" names the cleanup of stray tables.
- 14.1 PACKAGING: the development tools of PACKAGING-S03.
- No row of "Known limitations" is removed.
