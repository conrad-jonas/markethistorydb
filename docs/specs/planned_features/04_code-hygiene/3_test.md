# code-hygiene: test changes

Each fix gets a test of the new behaviour: NULL and the ISIN on update, `InsertError` for a
rejected update, the refused deletion, the daily bar without volume in the round trip, the
up-to-date log line and the shared session. The tests of the removed code go with it. Lint and
format are a test case of the level *static*, carried out by the *lint* job.

A MODIFIED test case whose tests must be added or changed is Missing until they are. STORAGE-T04
only loses the clause and the test of the removed meta statement, so it stays Implemented.

## Test case changes

### Stored data and writing

| Change | ID | Test case | Verifies | Level | Status | Implemented by |
| ------ | -- | --------- | -------- | ----- | ------ | -------------- |
| MODIFIED | STORAGE-T04 | When `setup` has run, then every table exists as its definition in the code describes it (columns, designated timestamp, deduplication keys, WAL). | STORAGE-S02 | integration | Implemented | `integration/setup/test_main.py`: `test_every_table_is_created_as_its_constants_describe_it` (its comparison of the deduplication keys comes with `data-integrity-checks`) |
| MODIFIED | STORAGE-T17 | When a reference record is updated, then the exchange and the symbol `UPDATE` set every column but the key, the symbol's ISIN included; each `UPDATE` addresses its record by the whole key and binds each value to its own column, a missing value as NULL and a numpy value as a plain value; the sector update needs no join. | STORAGE-S11 | unit | Missing | `unit/db/io/test_update.py`: `test_every_value_is_bound_to_its_own_column`, `test_a_missing_value_is_bound_as_null_and_a_numpy_value_as_a_plain_one` <br>`unit/db/statements/test_exchange.py`: `test_the_update_sets_every_column_but_the_key` <br>`unit/db/statements/test_symbol.py`: `test_the_symbol_update_sets_every_column_but_the_key`, `test_the_sector_update_has_no_join`, `test_a_record_is_addressed_by_its_whole_unique_key` |
| ADDED | STORAGE-T38 | Given a stored exchange and a stored symbol, when the exchange is updated with a missing value and the symbol with a new ISIN, then the missing value reads back as NULL and the new ISIN is stored. | STORAGE-S11 | integration | Missing | `integration/db/io/test_update.py`: `test_a_missing_value_is_stored_as_null`, `test_a_changed_isin_is_stored` |
| MODIFIED | STORAGE-T23 | Given a reference record the database rejects, when it is inserted or updated, then `InsertError` is raised without retrying. | STORAGE-S15 | unit | Missing | `unit/db/io/test_insert.py`: `test_a_rejected_lookup_record_is_reported_as_an_insert_error_without_retrying` <br>`unit/db/io/test_update.py`: `test_a_rejected_update_is_reported_as_an_insert_error_without_retrying` |
| MODIFIED | STORAGE-T36 | Given daily bars of two symbols on two venues over three days with a missing open and a missing volume, and minute bars with a missing price and a missing volume, when each symbol's bars are written and all are read back with `Read.ohlcv`, then the frames read back equal the written ones in values, dtypes and missing values, after indexing and sorting, with the timestamps at microsecond resolution. | STORAGE-S22 | integration | Missing | `integration/db/io/test_round_trip.py`: `test_daily_bars_read_back_equal_the_bars_written`, `test_minute_bars_read_back_equal_the_bars_written` (from `test-suite-hardening`) |

### Deleting an instrument's records

| Change | ID | Test case | Verifies | Level | Status | Implemented by |
| ------ | -- | --------- | -------- | ----- | ------ | -------------- |
| MODIFIED | STORAGE-T30 | When a symbol is deleted from a fundamental table, then the statements copy every record except those of that symbol on that exchange, drop the table and rename the copy, in that order, and the copy keeps its timestamp and deduplication keys; a deletion request for any other table, a symbol or a price table included, raises `ValueError` naming the table, and no statement runs. | STORAGE-S19 | unit | Missing | `unit/db/io/test_delete.py`: `test_a_fundamental_table_keeps_its_timestamp_and_dedup_keys`, `test_a_table_other_than_a_fundamental_one_is_refused_before_any_statement` (replaces `test_a_table_outside_the_known_families_is_left_alone`) <br>`unit/db/statements/test_fundamental.py`: `test_the_copy_keeps_every_record_but_those_of_the_one_symbol_on_the_one_exchange`, `test_the_symbol_is_dropped_by_copy_drop_and_rename_in_that_order` |

### Requests

| Change | ID | Test case | Verifies | Level | Status | Implemented by |
| ------ | -- | --------- | -------- | ----- | ------ | -------------- |
| ADDED | PROVIDER-T28 | Given a request class built with a session, then its requests go through that session; built without one, they go through `requests.get`. | PROVIDER-S24 | unit | Missing | `unit/fetch/eodhd/test_request_data.py`: `test_requests_go_through_the_session_given`, `test_without_a_session_each_request_goes_through_requests_get` |
| ADDED | PROVIDER-T29 | Given a fetch of two passes over several symbols, then every request goes through one session, which is closed when the fetch ends; given a fetch that ends with an error, the session is closed as well. | PROVIDER-S24 | unit | Missing | `unit/test_client.py`: `test_a_fetch_sends_every_request_through_one_session`, `test_the_session_is_closed_when_the_fetch_ends_also_after_an_error` |

### Prices and fundamentals

| Change | ID | Test case | Verifies | Level | Status | Implemented by |
| ------ | -- | --------- | -------- | ----- | ------ | -------------- |
| MODIFIED | PRICES-T06 | Given minute data that is up to date, or a start of today, then nothing is requested, nothing is stored, and the symbol is logged as up to date. | PRICES-S02, PRICES-S07 | unit | Missing | `unit/fetch/download/test_download_price_data.py`: `test_minute_prices_that_are_already_up_to_date_are_not_requested` (asserting the log line), `test_a_start_of_today_needs_no_chunk` |
| MODIFIED | PRICES-T11 | Given a symbol without stored daily bars and no bars from the provider, then "No data exists for symbol AAPL (NASDAQ, DAILY, ACTIVE)" is logged and nothing is written; given a newest stored bar of 2024-03-05 and no newer bars, then "Symbol AAPL (NASDAQ, DAILY, ACTIVE) is up to date: newest bar 2024-03-05 00:00:00" is logged instead. | PRICES-S07 | unit | Missing | `unit/fetch/download/test_download_price_data.py`: `test_no_prices_are_logged_and_nothing_is_stored`, `test_a_symbol_without_new_prices_is_logged_as_up_to_date` |
| MODIFIED | FUND-T05 | Every record set maps to its own table; camelCase names become snake_case, snake_case names stay, and the frame is renamed in place. | FUND-S03, PROVIDER-S20 | unit | Implemented | `unit/fetch/test_utils.py`: `test_every_fundamental_type_but_sector_and_industry_has_its_own_table`, `test_camel_case_columns_become_snake_case_and_snake_case_ones_stay`, `test_the_columns_are_renamed_in_place_and_the_frame_returned` |

FUND-T05 keeps its text and tests. It verified FUND-S04, whose conversion of names moves to
PROVIDER-S20 alone.

### Lint and format

| Change | ID | Test case | Verifies | Level | Status | Implemented by |
| ------ | -- | --------- | -------- | ----- | ------ | -------------- |
| ADDED | QUALITY-T11 | Given `src/` and `tests/`, then `ruff check` reports no finding and `ruff format --check` no file to reformat, with the configuration of QUALITY-S11; no file starts with a shebang. | QUALITY-S11 | static | Missing | the *lint* job; `[tool.ruff]` in `pyproject.toml` |
| MODIFIED | CI-T03 | A run of `ci.yml` shows four *unit* jobs (Linux and Windows, each with Python 3.12 and the newest stable Python release), and *integration*, *build*, *audit*, *lint* and *types*; *types* reports findings without failing the run. | CI-S03 | ci | Missing | the first run after issue 6 |
| ADDED | CI-T15 | Given a pull request with a ruff finding, or a file that `ruff format` would change, then *lint* fails and GitHub refuses the merge. | CI-S03, QUALITY-S11 | ci | Missing | demonstration pull request |

## Tests removed

| Test | Why |
| ---- | --- |
| `unit/db/io/test_delete.py`: `test_a_symbol_table_is_copied_without_the_symbol_then_swapped_in`, `test_a_price_table_is_rebuilt_and_gets_its_indexes_back` <br>`unit/db/statements/test_symbol.py`: `test_the_symbol_copy_keeps_every_other_symbol_and_stays_non_wal` <br>`unit/db/statements/test_price.py`: `test_dropping_a_symbol_copies_drops_renames_and_then_restores_the_indexes` <br>`integration/db/io/test_delete.py`: `test_a_symbol_table_loses_the_symbol_only`, `test_a_price_table_loses_the_symbol_only_and_keeps_its_indexes_and_dedup` | the deletion paths of the symbol and price tables are removed (`2_design.md` 3.1) |
| `unit/db/statements/test_fundamental.py`: `test_each_select_reads_its_own_table_by_symbol` | the eight `SELECT_ALL_FROM_*` of the fundamental tables are removed |
| `integration/setup/test_main.py`: `test_every_column_is_found_through_the_meta_statement` | `SELECT_SCHEMA` is removed; the other test of STORAGE-T04 compares every column |
| `unit/db/io/test_delete.py`: `test_a_table_outside_the_known_families_is_left_alone` | replaced by the test of the refusal (STORAGE-T30) |

## Tests changed without a change of their test case

| Test | Test case | Change |
| ---- | --------- | ------ |
| `unit/fetch/write/test_write_fundamental_data.py`: the record-set fixture | FUND-T06 to FUND-T09 | snake_case field names, as the request class delivers them |
| `tests/conftest.py`: `scripted_api`, `routed_api` | several | replace `requests.Session.get` as well as `requests.get` |
| `unit/db/tables/test_exchange.py`: `test_the_table_is_listed_by_name` | STORAGE-T05 | `TABLE_NAMES_EXCHANGE` |
| `unit/fetch/test_fetcher.py` | several of RUNS | the renamed `_download_…` attributes |
| every test module | — | ruff's fixes and the formatter |

## Missing test cases of `5_test.md` filled

None.

## Changes to `5_test.md` section 1 on merge

- 1.1: the commands gain `uv run ruff check` and `uv run ruff format --check`; the new counts.
- 2.7 (tests without a test case) is removed: none is left in STORAGE.
- 14 (QUALITY): QUALITY-T11 is the first test case of the level *static*.
