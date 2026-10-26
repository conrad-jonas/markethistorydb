# test-suite-hardening: test changes

The rules of the suite are test cases of the level *suite*: the configuration carries them out,
and issue 1 checks each once by hand (`2_design.md` 5). The other test cases check behaviour that
exists already: new ones for COR-4 and COR-5, for the four passes and for the command line, and
12 Missing test cases of `5_test.md` filled.

## Test case changes

### Rules of the suite

| Change | ID | Test case | Verifies | Level | Status | Implemented by |
| ------ | -- | --------- | -------- | ----- | ------ | -------------- |
| ADDED | QUALITY-T05 | Given `pytest` without `-m`, then the unit and integration tests run and the live tests are deselected; given `-m live`, only the live tests run; given `tests/live` without `-m live`, no test runs and the exit code is 5. | QUALITY-S05 | suite | Missing | `addopts` in `pyproject.toml` |
| ADDED | QUALITY-T06 | Given a test with an unregistered marker, a misspelt configuration key, or two parameter sets of one test with the same ID, then the run ends with an error before any test; given an `xfail` test that passes, then it fails; the closing report lists every test that did not pass. | QUALITY-S06 | suite | Missing | `strict = true` and `-ra` in `pyproject.toml` |
| ADDED | QUALITY-T07 | Given a test that raises a warning, or whose fixture does, then it fails; given QuestDB's warning "Detected a burst of reconnections", then the test passes; a test that allows its own warning passes. | QUALITY-S07 | suite | Missing | `filterwarnings` in `pyproject.toml`; the mark on `test_warnings_are_routed_into_the_log` |
| ADDED | QUALITY-T08 | Given a unit test running past 30 s, an integration test past 120 s or a live test past 300 s, fixtures included, then it is stopped, with output naming it and showing where it hung. | QUALITY-S08 | suite | Missing | `timeout` in `pyproject.toml`; the collection hooks of `tests/integration/conftest.py` and `tests/live/conftest.py` |
| ADDED | QUALITY-T09 | Given a unit test that creates a socket, then it fails at that point with `SocketBlockedError`; integration tests connect as before. | QUALITY-S09 | suite | Missing | the collection hook of `tests/unit/conftest.py` |
| MODIFIED | QUALITY-T03 | Given `QUESTDB_TEST_*` and `QUESTDB_*` naming the same host and ports, then a run of integration tests stops with exit code 3 before any test; given a test database named by `QUESTDB_TEST_*` that doesn't answer within 2 s, then the integration tests are skipped with a message naming it. Both run as child pytest runs, against ports no database listens on. | QUALITY-S03 | unit | Missing | `unit/integration_support/test_guard.py`: `test_a_test_instance_that_is_the_application_s_stops_the_run_with_exit_code_3`, `test_a_test_database_that_does_not_answer_skips_the_integration_tests` |
| MODIFIED | QUALITY-T04 | Every integration test starts on exactly the tables `setup` creates, all empty; a table `setup` doesn't create, left by an earlier test, is dropped first. | QUALITY-S04 | suite | Missing | fixture `fresh_db` in `tests/integration/conftest.py`, used by the integration tests |

### Data read back and series across runs

| Change | ID | Test case | Verifies | Level | Status | Implemented by |
| ------ | -- | --------- | -------- | ----- | ------ | -------------- |
| ADDED | STORAGE-T36 | Given daily bars of two symbols on two venues over three days with a missing open, and minute bars with a missing price and a missing volume, when each symbol's bars are written and all are read back with `Read.ohlcv`, then the frames read back equal the written ones in values, dtypes and missing values, after indexing and sorting, with the timestamps at microsecond resolution. | STORAGE-S22 | integration | Missing | `integration/db/io/test_round_trip.py`: `test_daily_bars_read_back_equal_the_bars_written`, `test_minute_bars_read_back_equal_the_bars_written` |
| MODIFIED | PRICES-T13 | Given a provider serving a fixed minute series that crosses a window boundary, when a minute pass runs on day *D* and another on *D* + 1 against the test database, then the stored bars equal the provider's series up to 00:00 UTC of *D* + 1, each once: no gap and no duplicate at the boundary between the runs or between windows. | PRICES-S02, PRICES-S03, PRICES-S06, PRICES-S09 | integration | Missing | `integration/fetch/test_series_across_runs.py`: `test_two_incremental_minute_runs_store_the_series_without_gap_or_duplicate` |
| ADDED | PRICES-T14 | Given three symbols and a provider serving fixed daily and minute series, when one run is stopped after the first symbol, the next fails in the third window of the second symbol, and a third completes, then each symbol's stored daily and minute series equals the provider's. | PRICES-S09, RUNS-S05, RUNS-S08 | integration | Missing | `integration/fetch/test_series_across_runs.py`: `test_runs_that_were_stopped_or_failed_leave_no_gap_once_a_run_completes` |

### Runs and command line

| Change | ID | Test case | Verifies | Level | Status | Implemented by |
| ------ | -- | --------- | -------- | ----- | ------ | -------------- |
| ADDED | RUNS-T16 | Given a fetch without filters for `USA Stocks` with the sample payloads against the test database, then each of the four passes stores its symbols under its time frame and status, the daily bars land in the daily table and the minute bars in the minute table, the exchange is stored once, and the fundamentals of the NASDAQ and NYSE symbols are stored. | RUNS-S01, RUNS-S03 | integration | Missing | `integration/test_client.py`: `test_a_fetch_without_filters_stores_what_each_of_the_four_passes_fetched` |
| ADDED | CLI-T08 | Given the test database and the sample payloads, when `setup`, answered with "yes", and `fetch --time-frame daily --exchange "USA Stocks"` run through `cli.main` in-process, then both exit with 0 and the exchange, its symbols and their daily bars are stored; given the exchange list answered with 401, then `fetch` exits with the code of `UnauthorizedError` and logs one line without traceback. | CLI-S01, CLI-S02, CLI-S04, CLI-S05, CLI-S06 | integration | Missing | `integration/test_cli.py`: `test_setup_and_fetch_store_the_exchange_its_symbols_and_their_bars`, `test_a_refused_token_ends_fetch_with_the_auth_error_code` |

## Missing test cases of `5_test.md` filled

Their text stays, except for PRICES-T13 and QUALITY-T03 (MODIFIED above). On merge, each becomes
Implemented with the tests named here.

| Test case | Level | Implemented by (planned) |
| --------- | ----- | ------------------------ |
| STORAGE-T10 | integration | `integration/db/io/test_insert.py`: `test_a_fundamental_record_with_a_stored_key_replaces_it` |
| STORAGE-T32 | unit | `unit/db/io/test_delete.py`: `test_a_failing_statement_ends_the_deletion_and_keeps_the_earlier_ones`, one case per position |
| PROVIDER-T16 | unit | `unit/fetch/eodhd/test_request_data.py`: `test_the_retry_warning_and_the_give_up_error_name_the_url_without_the_token` |
| REFDATA-T04 | unit | `unit/fetch/download/test_download_exchange_data.py`: `test_a_list_without_any_selected_exchange_raises_and_writes_nothing` |
| REFDATA-T12 | integration | `integration/fetch/write/test_write_symbol_data.py`: `test_a_symbol_of_another_time_frame_or_status_gets_a_record_of_its_own` |
| PRICES-T13 | integration | see above |
| FUND-T09 | unit | `unit/fetch/write/test_write_fundamental_data.py`: `test_a_record_set_failing_the_check_keeps_its_records_and_ends_the_replacement` |
| FUND-T10 | integration | `integration/fetch/write/test_write_fundamental_data.py`: `test_a_write_failing_after_the_deletion_leaves_the_symbol_without_records`, with an ingestion port no QuestDB listens on, so that the deletion through SQL works and the write fails |
| CLIENT-T03 | unit | `unit/test_init.py`: `test_importing_the_package_reads_no_variable_connects_nowhere_and_writes_nothing` |
| CLIENT-T08 | unit | `unit/test_errors.py`: `test_each_error_sits_where_the_documented_hierarchy_puts_it`, with one more pair |
| LOGGING-T03 | unit | `unit/utils/test_logger.py`: `test_a_line_has_the_documented_format`, `test_the_setup_logs_the_working_directory` |
| QUALITY-T03 | unit | see above |

The other 9 Missing test cases are left to the features named in `1_specs.md`, Scope.

## Tests changed without a change of their test case

| Test | Test case | Change |
| ---- | --------- | ------ |
| `unit/fetch/write/test_write_fundamental_data.py`: `test_the_symbol_s_records_are_deleted_before_the_new_ones_are_written` | FUND-T04 | asserts the order through `FakeDb.calls`; today it joins two lists and passes with the order swapped too |
| `unit/utils/test_logger.py`: `test_warnings_are_routed_into_the_log` | LOGGING-T04 | allows its `FutureWarning` (QUALITY-S07) |
| `unit/db/io/test_read.py`: `test_a_duplicated_unique_key_is_a_query_error_naming_the_record` | ACCESS-T03 | explicit IDs for its two parameter sets (QUALITY-S06) |
| the tests that build symbols, exchanges, bars or balance sheets themselves (`2_design.md` 3.1) | several | use the builders |

## Changes to `5_test.md` section 1 on merge

- 1.1: `uv run pytest` runs the unit and integration tests, `-m live` the live tests; the time
  limits and the blocked sockets; the new counts. "No end-to-end tests yet" names CLI-T08 and
  RUNS-T16 as the closest; the nightly end-to-end level stays planned, in `ingestion-efficiency`.
- 1.2: rows for `tests/support/builders.py`, `FakeSeriesApi`, `FakeDb.calls` and
  `RecordingQuery(fail_at=…)`.
