# MarketHistoryDB: tests (status quo)

How the implemented behaviour is tested: the test approach, then one chapter of test cases per
capability, in the order of `3_specs.md`. Planned test changes are in
`planned_features/<nn>_<feature>/3_test.md` and enter this file when the feature is merged
(`1_constitution.md`, section 6.4).

---

## 1 Approach

### 1.1 Test levels

| Level | Directory | Tests | What it needs | What it checks |
| ----- | --------- | ----- | ------------- | -------------- |
| unit | `tests/unit/` | 530 | nothing: the provider API and the database are faked | logic, error handling, the SQL and requests that are sent |
| integration | `tests/integration/` | 73 | a throwaway QuestDB | behaviour against a real database |
| live | `tests/live/` | 18 | network access; for some endpoints an `EODHD_API_TOKEN` | the contract of the real eodhd.com API |

Counts as collected on 2026-10-17 (621 in total, parametrised cases counted one by one).

- **Markers:** `unit`, `integration` and `live` are registered in `pyproject.toml`. Each
  directory's `conftest.py` marks its tests, so `-m` selects a level.
- **Commands:**
  - `uv run pytest -m unit --cov` runs the unit tests with the coverage gate: 100 % line and
    branch coverage of `src/` (`fail_under = 100`).
  - `uv run pytest -m "not live"` runs unit and integration tests.
  - `uv run pytest` runs all three levels. Live tests run by default (QA-6 is Open).
- **Integration tests** run against the QuestDB named by `QUESTDB_TEST_HOST`,
  `QUESTDB_TEST_PG_PORT` and `QUESTDB_TEST_HTTP_PORT` (optionally `QUESTDB_TEST_USER`,
  `QUESTDB_TEST_PASSWORD`), from the environment or `.env`.
  - They are skipped when the variables are unset or the instance cannot be reached within 2 s.
  - They stop the whole run (exit code 3) if the test instance is the one the `QUESTDB_*`
    variables point the application to, because every test drops all tables (QA-3).
  - Each test starts on empty tables (`fresh_db` runs `setup`). Helpers wait up to 15 s for a WAL
    table to apply a write.
  - Locally, the test instance is a separate QuestDB service (ports 19000 and 18812).
- **Live tests** call eodhd.com. Endpoints the public demo token serves use it; the others need
  `EODHD_API_TOKEN` and spend that account's calls, and are skipped without it or when eodhd.com
  refuses it.
- **No end-to-end tests yet.** No test runs the whole chain: command line or `Client`, the real
  provider, a real database, and reading the result back. The closest are integration tests that
  run `Client` and `Fetcher` against the test QuestDB with a faked provider (chapters RUNS and
  CLIENT). Planned: an in-process test of the command line against the test QuestDB with a faked
  provider, a smoke test of the installed console script (`test-suite-hardening`), and a nightly
  end-to-end level against the real provider (`continuous-integration`).

### 1.2 Shared test support

| Where | What |
| ----- | ---- |
| `tests/fakes.py` | `FakeScriptedApi`, `FakeRoutedApi`, `FakeResponse` (provider API); `FakeQuery`, `FakeCursor`, `FakeConnection`, `RecordingQuery`, `Recorder`, `FakeDb` (database); `FakeClock`, `FakeConfig`; `load_payload` |
| `tests/conftest.py` | fixtures `slept` (records waits instead of sleeping), `scripted_api`, `routed_api`, `clock`, `reset_logging` |
| `tests/unit/conftest.py` | fixture `local_time_off_utc` (runs a test with the local time zone set away from UTC) |
| `tests/data/eodhd/*.json` | sample payloads of the five endpoints: `exchanges-list`, `exchange-symbol-list`, `eod`, `intraday`, `fundamentals` |
| `tests/unit/db/tables/schema.py` | parses the `CREATE TABLE` statements of the schema files, for comparison with the table definitions |
| `tests/unit/db/statements/checks.py` | checks that a statement template is one complete statement |

### 1.3 Conventions of this file

- **Test case:** a check described as given / when / then, with an ID `<CAPABILITY>-T<nn>`, the
  specification items it verifies, its level and its status.
- **Levels** besides the three of section 1.1: *static* for a check of the code itself (a linter,
  a type checker), *suite* for a guarantee carried out by the suite's own configuration.
- **Status:**
  - **Implemented:** the tests in "Implemented by" carry it out.
  - **Missing:** the behaviour exists, but no test checks it yet.
- **"Implemented by"** names test functions, grouped by module; paths are relative to `tests/`.
  A parametrised test counts as one function.
- **Tests without a test case:** each chapter ends with the tests that check code without a
  specification item (unused code), so that every test of the suite is accounted for.

---

## 2 STORAGE: QuestDB access and schema

### 2.1 Schema setup

| ID | Test case | Verifies | Level | Status | Implemented by |
| -- | --------- | -------- | ----- | ------ | -------------- |
| STORAGE-T01 | Given tables holding records, when `setup` runs again, then all tables exist and are empty. | STORAGE-S01 | integration | Implemented | `integration/setup/test_main.py`: `test_running_setup_again_starts_from_empty_tables` |
| STORAGE-T02 | When `setup` runs, then every schema file is executed, in dependency order, over one connection. | STORAGE-S01 | unit | Implemented | `unit/setup/test_main.py`: `test_every_schema_file_runs_in_dependency_order_over_one_connection` |
| STORAGE-T03 | When `setup` has run, then the price tables index exactly `exchange_code` and `symbol_code`. | STORAGE-S01 | integration | Implemented | `integration/setup/test_main.py`: `test_the_price_tables_index_the_columns_they_are_filtered_by` |
| STORAGE-T04 | When `setup` has run, then every table exists as its definition in the code describes it (columns, designated timestamp, deduplication keys, WAL), and each defined column is found in the database's schema information. | STORAGE-S02 | integration | Implemented | `integration/setup/test_main.py`: `test_every_table_is_created_as_its_constants_describe_it`, `test_every_column_is_found_through_the_meta_statement` |
| STORAGE-T05 | Given the schema files and the table definitions, then each schema file creates its tables as the definitions describe them: key columns are columns of the table, the reference tables are non-WAL, fundamental tables start with symbol and exchange code and share the fundamental base columns, and every table is listed once in its family. | STORAGE-S02, STORAGE-S07 | unit | Implemented | `unit/db/tables/test_exchange.py`: `test_the_key_columns_are_columns_of_the_table`, `test_the_schema_creates_the_table_as_the_constants_describe_it`, `test_the_table_is_not_wal_so_a_write_is_visible_to_the_next_read`, `test_the_table_is_listed_by_name` <br>`unit/db/tables/test_symbol.py`: `test_the_key_columns_are_columns_of_the_table`, `test_the_schema_creates_the_table_as_the_constants_describe_it`, `test_the_table_is_not_wal_so_a_write_is_visible_to_the_next_read`, `test_both_tables_are_listed_by_name` <br>`unit/db/tables/test_price.py`: `test_the_key_columns_are_columns_of_the_table`, `test_the_schema_creates_the_table_as_the_constants_describe_it`, `test_both_tables_are_listed_by_name` <br>`unit/db/tables/test_fundamental.py`: `test_the_key_columns_are_columns_of_the_table`, `test_every_table_starts_with_the_symbol_and_exchange_code`, `test_every_table_shares_the_fundamental_base_and_its_columns`, `test_the_schema_creates_the_table_as_the_constants_describe_it`, `test_every_table_is_listed_by_name_once` |
| STORAGE-T06 | Given a table definition that lacks one of its constants, when the class is defined, then it is rejected; abstract bases cannot be instantiated, need not define the constants, and inherited constants do not count as defined. | STORAGE-S02 | unit | Implemented | `unit/db/tables/test_table.py`: `test_an_abstract_base_cannot_be_instantiated`, `test_an_abstract_base_need_not_define_the_constants`, `test_a_table_derived_from_an_abstract_base_must_define_the_constants`, `test_a_complete_subclass_can_be_instantiated`, `test_a_subclass_missing_constants_is_rejected_when_defined`, `test_inherited_constants_do_not_count_as_defined` |
| STORAGE-T07 | Given an unreadable schema file, a statement the database rejects, or an unreachable database, when `setup` runs, then it raises `DbError`, naming the unreadable file. | STORAGE-S03 | unit | Implemented | `unit/setup/test_main.py`: `test_a_schema_file_that_cannot_be_read_is_a_db_error_naming_it`, `test_a_statement_the_db_rejects_is_a_db_error`, `test_an_unreachable_db_is_a_db_error` |

### 2.2 Stored data

| ID | Test case | Verifies | Level | Status | Implemented by |
| -- | --------- | -------- | ----- | ------ | -------------- |
| STORAGE-T08 | Given a daily bar, when it is written, then it reads back unchanged and the table's columns stay the same; when the same bars are written twice, then each is stored once. | STORAGE-S04 | integration | Implemented | `integration/db/io/test_insert.py`: `test_a_record_round_trips_without_changing_the_table_s_columns`, `test_prices_sent_twice_are_stored_once` |
| STORAGE-T09 | Given minute bars, when they are written, then they read back unchanged. | STORAGE-S05 | integration | Implemented | `integration/db/io/test_insert.py`: `test_minute_prices_round_trip` |
| STORAGE-T10 | Given a fundamental record, when a record with the same symbol code, exchange code and key date is written, then only the new record is stored. | STORAGE-S06 | integration | Missing | — |
| STORAGE-T11 | Given a reference record, when it is written through SQL, then the very next read finds it; the ingestion interface cannot write a reference table. | STORAGE-S07, STORAGE-S10 | integration | Implemented | `integration/db/io/test_insert.py`: `test_a_lookup_record_is_visible_to_the_very_next_read`, `test_the_ingress_cannot_write_a_lookup_table` |
| STORAGE-T12 | Given a daily bar dated 1969-12-31, when it is written, then `InsertError` is raised at once, without waiting for a retry. | STORAGE-S08 | integration | Implemented | `integration/db/io/test_insert.py`: `test_a_value_the_table_cannot_store_fails_at_once_instead_of_being_retried` |

### 2.3 Writing

| ID | Test case | Verifies | Level | Status | Implemented by |
| -- | --------- | -------- | ----- | ------ | -------------- |
| STORAGE-T13 | When prices are written, then the frame goes to the table of its time frame, through the ingestion interface with the configuration's settings, in one batch rather than row by row. | STORAGE-S09 | unit | Implemented | `unit/db/io/test_insert.py`: `test_a_frame_is_written_with_the_config_s_ingress_settings`, `test_prices_go_to_the_table_of_their_time_frame`, `test_a_symbol_s_prices_are_written_in_one_batch_not_row_by_row` |
| STORAGE-T14 | Given a long minute history, when it is written, then all bars are stored by one call. | STORAGE-S09 | integration | Implemented | `integration/db/io/test_insert.py`: `test_a_long_minute_history_is_written_in_one_batch` |
| STORAGE-T15 | When a reference record is written, then one SQL `INSERT` takes every column in definition order; a missing field or value is bound as NULL, a field the table does not define is left out, and numpy values are bound as plain values. | STORAGE-S10 | unit | Implemented | `unit/db/io/test_insert.py`: `test_a_lookup_record_is_written_through_sql_not_the_ingress`, `test_fields_the_table_does_not_define_are_not_written`, `test_a_missing_field_or_value_is_written_as_null`, `test_numpy_scalars_are_written_as_plain_python_values` <br>`unit/db/statements/test_exchange.py`: `test_the_insert_takes_every_column_in_definition_order` <br>`unit/db/statements/test_symbol.py`: `test_an_insert_takes_every_column_in_definition_order` |
| STORAGE-T16 | Given a reference record lacking a field, when it is written, then the field is stored as NULL. | STORAGE-S10 | integration | Implemented | `integration/db/io/test_insert.py`: `test_a_missing_field_is_stored_as_null` |
| STORAGE-T17 | When a reference record is updated, then the exchange `UPDATE` sets every column but the key, each `UPDATE` addresses its record by the whole key and binds each value to its own column, and the sector update needs no join. | STORAGE-S11 | unit | Implemented | `unit/db/io/test_update.py`: `test_every_value_is_bound_to_its_own_column` <br>`unit/db/statements/test_exchange.py`: `test_the_update_sets_every_column_but_the_key` <br>`unit/db/statements/test_symbol.py`: `test_the_sector_update_has_no_join`, `test_a_record_is_addressed_by_its_whole_unique_key` |
| STORAGE-T18 | Given stored reference records, when one is updated, then only that record changes: an exchange by its code, a symbol by symbol, exchange, time frame and status, a sector by symbol and exchange. | STORAGE-S11 | integration | Implemented | `integration/db/io/test_update.py`: `test_an_exchange_update_changes_only_that_exchange`, `test_a_symbol_update_is_keyed_by_time_frame_and_status_too`, `test_a_sector_update_takes_effect` |
| STORAGE-T19 | Given an ingestion write that fails transiently (unreachable or busy host, a flush error that is no rejection), then it is retried until it passes, or ends in `InsertError` naming the operation once the attempts are used up; a passing write returns its result, and the wrapped function keeps its name. | STORAGE-S12 | unit | Implemented | `unit/db/io/test_error.py`: `test_a_passing_write_returns_its_result_with_the_arguments_passed_through`, `test_a_failing_write_is_retried_until_it_passes`, `test_a_write_that_keeps_failing_ends_in_an_insert_error_naming_the_method`, `test_an_error_of_an_unreachable_or_busy_host_is_retried`, `test_a_flush_error_that_is_no_rejection_of_the_records_is_retried`, `test_the_decorated_function_keeps_its_name` <br>`unit/db/io/test_insert.py`: `test_an_ingress_error_is_retried_then_reported_as_an_insert_error` |
| STORAGE-T20 | Given a server rejection saying the records do not fit the table, then `SchemaMismatchError` is raised at once. | STORAGE-S13 | unit | Implemented | `unit/db/io/test_error.py`: `test_records_that_do_not_fit_the_table_are_a_schema_mismatch_at_once` |
| STORAGE-T21 | Given a bar with a value of the wrong type, or a column the table does not have, when it is written, then `SchemaMismatchError` is raised at once and the table's columns are unchanged. The second check is skipped unless the test server runs with `line.auto.create.new.columns=false`. | STORAGE-S13 | integration | Implemented | `integration/db/io/test_insert.py`: `test_a_value_of_the_wrong_type_is_a_schema_mismatch_at_once`, `test_a_column_the_table_does_not_have_is_a_schema_mismatch_instead_of_a_new_column` |
| STORAGE-T22 | Given a rejection for another reason, a rejection without a message, or an ingestion error no retry can fix, then `InsertError` is raised at once; an error that is no ingestion error passes through without retry. | STORAGE-S14 | unit | Implemented | `unit/db/io/test_error.py`: `test_records_rejected_for_another_reason_are_an_insert_error_at_once`, `test_a_rejection_without_a_message_is_an_insert_error_all_the_same`, `test_an_error_no_retry_can_fix_is_an_insert_error_at_once`, `test_other_errors_pass_through_unretried` |
| STORAGE-T23 | Given a reference record the database rejects, when it is written, then `InsertError` is raised without retrying. | STORAGE-S15 | unit | Implemented | `unit/db/io/test_insert.py`: `test_a_rejected_lookup_record_is_reported_as_an_insert_error_without_retrying` |

### 2.4 Running SQL

| ID | Test case | Verifies | Level | Status | Implemented by |
| -- | --------- | -------- | ----- | ------ | -------------- |
| STORAGE-T24 | When a statement runs, then it connects with autocommit and client-side binding; a `SELECT` returns its records, a statement without a result set returns none. | STORAGE-S16 | unit | Implemented | `unit/db/io/test_query.py`: `test_every_statement_connects_with_autocommit_and_client_side_binding`, `test_a_select_returns_its_records`, `test_a_statement_without_a_result_set_returns_no_records` |
| STORAGE-T25 | Against the database: a `SELECT` returns its records, a statement without a result set returns none. | STORAGE-S16 | integration | Implemented | `integration/db/io/test_query.py`: `test_a_select_returns_its_records`, `test_a_statement_without_a_result_set_returns_no_records` |
| STORAGE-T26 | Every statement template of the code is one complete statement: it starts with an SQL keyword and closes every parenthesis it opens. | STORAGE-S16 | unit | Implemented | `unit/db/statements/test_exchange.py`, `test_fundamental.py`, `test_price.py`, `test_symbol.py`: `test_every_statement_is_complete` |
| STORAGE-T27 | When a statement runs, then its values are bound as a tuple and never formatted into the statement; the deletion statements quote table names as identifiers. | STORAGE-S17 | unit | Implemented | `unit/db/io/test_query.py`: `test_the_params_are_bound_as_a_tuple_and_never_formatted_into_the_statement` <br>`unit/db/io/test_delete.py`: `test_table_names_are_quoted_as_identifiers` |
| STORAGE-T28 | Given a statement that fails, then `QueryError` (a `DbError`) is raised. | STORAGE-S18 | unit | Implemented | `unit/db/io/test_query.py`: `test_a_failing_statement_is_reported_as_a_db_error` |
| STORAGE-T29 | Given invalid SQL, a table that does not exist, or a wrong password, then `QueryError` is raised; the error of a rejected login does not contain the password. | STORAGE-S18 | integration | Implemented | `integration/db/io/test_query.py`: `test_invalid_sql_is_a_query_error`, `test_a_table_that_does_not_exist_is_a_query_error`, `test_a_wrong_password_is_rejected`, `test_the_error_of_a_rejected_login_does_not_echo_the_password` |

### 2.5 Deleting an instrument's records

| ID | Test case | Verifies | Level | Status | Implemented by |
| -- | --------- | -------- | ----- | ------ | -------------- |
| STORAGE-T30 | When a symbol is deleted from a fundamental table, then the statements copy every record except those of that symbol on that exchange, drop the table and rename the copy, in that order, and the copy keeps its timestamp and deduplication keys; a deletion request for a table outside the three families is left alone. | STORAGE-S19 | unit | Implemented | `unit/db/io/test_delete.py`: `test_a_fundamental_table_keeps_its_timestamp_and_dedup_keys`, `test_a_table_outside_the_known_families_is_left_alone` <br>`unit/db/statements/test_fundamental.py`: `test_the_copy_keeps_every_record_but_those_of_the_one_symbol_on_the_one_exchange`, `test_the_symbol_is_dropped_by_copy_drop_and_rename_in_that_order` |
| STORAGE-T31 | Given a fundamental table holding several symbols, when one symbol is deleted, then only its records are gone. | STORAGE-S19 | integration | Implemented | `integration/db/io/test_delete.py`: `test_a_fundamental_table_loses_the_symbol_only` |
| STORAGE-T32 | Given a deletion whose statement *n* fails, then `QueryError` is raised and statements 1 to *n*−1 stay applied; one test per position in the sequence. | STORAGE-S19 | unit | Missing | — |
| STORAGE-T33 | Before a deletion, the table and its copy are looked up; a copy left next to the table is dropped; a copy left without the table takes the table's name back. | STORAGE-S20 | unit | Implemented | `unit/db/io/test_delete.py`: `test_the_table_and_its_copy_are_looked_up_before_the_copy_is_made`, `test_a_leftover_copy_is_dropped_while_the_table_still_exists`, `test_a_leftover_copy_takes_the_table_s_name_back_once_the_table_is_gone` |
| STORAGE-T34 | Given a copy left next to the table, the deletion succeeds; given a copy left without the table, it takes the table's place with every record. | STORAGE-S20 | integration | Implemented | `integration/db/io/test_delete.py`: `test_a_copy_left_next_to_the_table_does_not_block_the_deletion`, `test_a_copy_left_without_the_table_takes_its_place_with_every_record` |

### 2.6 Access objects

| ID | Test case | Verifies | Level | Status | Implemented by |
| -- | --------- | -------- | ----- | ------ | -------------- |
| STORAGE-T35 | When the database access objects are created, then no connection is opened, and all interfaces share one statement runner and the configuration. | STORAGE-S21 | unit | Implemented | `unit/db/test_database.py`: `test_building_a_database_does_not_connect`, `test_the_interfaces_share_one_query_and_the_config` |

### 2.7 Tests without a test case

| Test | Checks | Why no test case |
| ---- | ------ | ---------------- |
| `unit/db/statements/test_fundamental.py`: `test_each_select_reads_its_own_table_by_symbol` | the eight `SELECT_ALL_FROM_*` statements of the fundamental tables | the statements have no caller (`4_design.md`, section 3.8); reading fundamentals is planned (MKT-14, `query-layer`) |
| `unit/db/io/test_delete.py`: `test_a_symbol_table_is_copied_without_the_symbol_then_swapped_in`, `test_a_price_table_is_rebuilt_and_gets_its_indexes_back` <br>`unit/db/statements/test_symbol.py`: `test_the_symbol_copy_keeps_every_other_symbol_and_stays_non_wal` <br>`unit/db/statements/test_price.py`: `test_dropping_a_symbol_copies_drops_renames_and_then_restores_the_indexes` <br>`integration/db/io/test_delete.py`: `test_a_symbol_table_loses_the_symbol_only`, `test_a_price_table_loses_the_symbol_only_and_keeps_its_indexes_and_dedup` | deleting a symbol from the symbol and price tables | nothing deletes from these tables (`4_design.md`, sections 3.7 and 3.8); `code-hygiene` removes the paths with their tests |

---

## 3 PROVIDER: eodhd request layer

Unit tests fake the API with `scripted_api` (answers in a given order) or `routed_api` (answers
by endpoint, from the sample payloads), and record waits with `slept`. Two tests of the
provider's test modules check the selection of exchanges and venues; they belong to REFDATA.

### 3.1 Requests

| ID | Test case | Verifies | Level | Status | Implemented by |
| -- | --------- | -------- | ----- | ------ | -------------- |
| PROVIDER-T01 | Each endpoint has its documented address, and each request class asks its endpoint with the token and `fmt=json`; a successful answer is returned as parsed JSON. | PROVIDER-S01 | unit | Implemented | `unit/fetch/eodhd/test_url.py`: `test_each_endpoint_has_its_documented_address` <br>`unit/fetch/eodhd/test_request_data.py`: `test_successful_response_is_returned_as_parsed_json` <br>`unit/fetch/eodhd/test_request_exchange_data.py`: `test_the_exchange_list_is_requested_with_the_token_as_json` <br>`unit/fetch/eodhd/test_request_symbol_data.py`: `test_the_symbol_list_of_the_exchange_is_requested` <br>`unit/fetch/eodhd/test_request_price_data.py`: `test_daily_prices_are_requested_from_the_eod_endpoint` |
| PROVIDER-T02 | Ordinary codes stay readable; a symbol code or an exchange code holding `/`, `?`, `#` or `%` stays within its path segment. | PROVIDER-S02 | unit | Implemented | `unit/fetch/eodhd/test_url.py`: `test_ordinary_codes_are_left_readable`, `test_a_symbol_code_stays_within_its_path_segment`, `test_an_exchange_code_stays_within_its_path_segment` |
| PROVIDER-T03 | Every request is sent with both a connect and a read timeout. | PROVIDER-S03 | unit | Implemented | `unit/fetch/eodhd/test_request_data.py`: `test_every_request_is_sent_with_both_a_connect_and_a_read_timeout` |
| PROVIDER-T04 | Delisted symbols are asked for with `delisted=1`. | PROVIDER-S04 | unit | Implemented | `unit/fetch/eodhd/test_request_symbol_data.py`: `test_delisted_symbols_are_asked_for_explicitly` |
| PROVIDER-T05 | Daily bars are requested from the given start day on. | PROVIDER-S05 | unit | Implemented | `unit/fetch/eodhd/test_request_price_data.py`: `test_daily_prices_are_requested_from_the_start_day_on` |
| PROVIDER-T06 | With the local time zone set away from UTC, minute bars are requested from the intraday endpoint with the period's bounds as UTC Unix seconds; a request missing either bound raises `ValueError`. | PROVIDER-S06 | unit | Implemented | `unit/fetch/eodhd/test_request_price_data.py`: `test_minute_prices_are_requested_from_the_intraday_endpoint_for_the_period`, `test_minute_prices_need_both_ends_of_the_period` |
| PROVIDER-T07 | Fundamentals are requested with the filter of the stored sections. | PROVIDER-S07 | unit | Implemented | `unit/fetch/eodhd/test_request_fundamental_data.py`: `test_the_fundamentals_are_requested_filtered_to_the_sections_that_are_stored` |

### 3.2 Answers and errors

| ID | Test case | Verifies | Level | Status | Implemented by |
| -- | --------- | -------- | ----- | ------ | -------------- |
| PROVIDER-T08 | Given a 404 or an empty answer, then the request yields no data of the expected shape: no symbols, an empty frame of bars, no fundamentals. | PROVIDER-S08 | unit | Implemented | `unit/fetch/eodhd/test_request_data.py`: `test_ticker_not_found_yields_no_data_instead_of_an_error`, `test_no_data_yields_an_empty_value_of_the_expected_shape` <br>`unit/fetch/eodhd/test_request_symbol_data.py`: `test_an_exchange_without_symbols_yields_an_empty_frame` <br>`unit/fetch/eodhd/test_request_price_data.py`: `test_a_symbol_without_prices_yields_an_empty_frame` <br>`unit/fetch/eodhd/test_request_fundamental_data.py`: `test_a_symbol_without_fundamentals_yields_nothing` |
| PROVIDER-T09 | Given an empty exchange list, then `CompatibilityError` is raised. | PROVIDER-S08, PROVIDER-S17 | unit | Implemented | `unit/fetch/eodhd/test_request_exchange_data.py`: `test_no_exchange_list_at_all_is_a_compatibility_error` |
| PROVIDER-T10 | Given 401, 402 or 403, then the matching account error is raised without retry, and 403 is told apart from 401; an unknown client error status raises `ApiError`. | PROVIDER-S09, PROVIDER-S10 | unit | Implemented | `unit/fetch/eodhd/test_request_data.py`: `test_unauthorized_is_not_retried_because_a_bad_token_cannot_fix_itself`, `test_the_plan_being_used_up_is_not_retried_because_waiting_cannot_refill_it`, `test_an_endpoint_outside_the_plan_is_told_apart_from_a_rejected_token`, `test_unknown_client_error_is_reported_as_an_api_error` |
| PROVIDER-T11 | Given a rate limit, a server error (also of an unknown 5xx status), or a timeout, then the request is retried and succeeds once the provider recovers; given a host that stays unreachable, then `RequestError` is raised once the attempts are used up. | PROVIDER-S10 | unit | Implemented | `unit/fetch/eodhd/test_request_data.py`: `test_rate_limit_is_retried_and_honours_retry_after`, `test_server_error_is_retried_although_its_status_is_not_a_known_one`, `test_a_retried_request_succeeds_once_the_provider_recovers`, `test_a_timeout_is_retried_and_the_request_succeeds_once_the_host_answers`, `test_a_host_that_stays_unreachable_ends_in_a_request_error` |
| PROVIDER-T12 | A `Retry-After` in seconds replaces the backoff, zero included, and is cut down to the maximum delay; a date, `nan`, `inf` or a negative value falls back to the backoff. | PROVIDER-S11 | unit | Implemented | `unit/fetch/eodhd/test_request_data.py`: `test_rate_limit_falls_back_to_the_backoff_when_retry_after_is_a_date`, `test_a_retry_after_that_is_no_usable_wait_falls_back_to_the_backoff`, `test_a_retry_after_beyond_the_cap_is_cut_down_to_it` <br>`unit/utils/test_backoff.py`: `test_a_zero_retry_after_is_honoured_instead_of_the_backoff` |
| PROVIDER-T13 | A wait is slept in short slices that add up to the delay, ends early once `should_stop` turns true (raising `UserInterruptError`), and a zero wait returns after a single poll. | PROVIDER-S12 | unit | Implemented | `unit/fetch/eodhd/test_request_data.py`: `test_waiting_for_a_retry_is_interruptible` <br>`unit/utils/test_backoff.py`: `test_a_wait_is_slept_in_short_slices_that_add_up_to_the_delay`, `test_a_wait_ends_early_once_should_stop_turns_true`, `test_a_zero_wait_returns_after_a_single_poll` |
| PROVIDER-T14 | Given a request exception no retry can fix, then `RequestError` is raised at once. | PROVIDER-S13 | unit | Implemented | `unit/fetch/eodhd/test_request_data.py`: `test_a_request_exception_no_retry_can_fix_is_a_request_error_at_once` |
| PROVIDER-T15 | The error message is limited in length however long the body; an error page echoing the token, a token at the cut-off point, and a request exception carrying the token in its URL never put the token into the raised error. | PROVIDER-S14 | unit | Implemented | `unit/fetch/eodhd/test_request_data.py`: `test_error_message_does_not_grow_with_the_response_body`, `test_an_error_page_echoing_the_token_does_not_carry_it_into_the_error`, `test_a_token_at_the_cut_off_point_is_masked_rather_than_cut_in_half`, `test_the_error_raised_for_a_request_exception_does_not_carry_the_api_token` |
| PROVIDER-T16 | Given a request that is retried and then given up, then the warning and the error logged name the URL but do not contain the token. | PROVIDER-S14 | unit | Missing | — |
| PROVIDER-T17 | Given a body that is not JSON, then `CompatibilityError` is raised. | PROVIDER-S15 | unit | Implemented | `unit/fetch/eodhd/test_request_data.py`: `test_a_body_that_is_not_json_is_a_compatibility_error` |
| PROVIDER-T18 | An array endpoint hands back the array and an object endpoint the object; the other kind raises `CompatibilityError`. | PROVIDER-S16 | unit | Implemented | `unit/fetch/eodhd/test_request_data.py`: `test_an_array_endpoint_hands_back_the_array`, `test_an_object_endpoint_hands_back_the_object`, `test_an_object_where_an_array_is_expected_is_a_compatibility_error`, `test_an_array_where_an_object_is_expected_is_a_compatibility_error` |
| PROVIDER-T19 | The structure check asks for every expected field in any order: a missing field of an exchange, a symbol, a daily bar (`adjusted_close`) or a minute bar raises `CompatibilityError`, while a minute bar without `gmtoffset` passes; for fundamentals, a real payload passes, and a missing or misshapen section, a record set missing a column (naming the type) or the wrong number of sector values raises `CompatibilityError`; the order of fields doesn't matter. | PROVIDER-S17 | unit | Implemented | `unit/fetch/eodhd/test_request_data.py`: `test_the_structure_check_asks_for_every_expected_column_in_any_order` <br>`unit/fetch/eodhd/test_request_exchange_data.py`: `test_the_order_of_the_fields_does_not_matter`, `test_a_missing_field_is_a_compatibility_error` <br>`unit/fetch/eodhd/test_request_symbol_data.py`: `test_a_missing_field_is_a_compatibility_error` <br>`unit/fetch/eodhd/test_request_price_data.py`: `test_a_daily_payload_without_adjusted_close_is_a_compatibility_error`, `test_a_minute_payload_without_gmtoffset_is_accepted`, `test_a_minute_payload_without_a_required_field_is_a_compatibility_error` <br>`unit/fetch/eodhd/test_request_fundamental_data.py`: `test_a_real_payload_passes_the_checks`, `test_a_missing_or_misshapen_section_is_a_compatibility_error`, `test_a_record_set_missing_a_column_is_a_compatibility_error_naming_the_type`, `test_the_order_of_the_fields_does_not_matter`, `test_sector_and_industry_must_have_one_value_per_sector_column` |

### 3.3 Conversion to records

| ID | Test case | Verifies | Level | Status | Implemented by |
| -- | --------- | -------- | ----- | ------ | -------------- |
| PROVIDER-T20 | Exchanges come back with the exchange table's columns; symbols with the symbol table's columns, time frame and status. | PROVIDER-S18 | unit | Implemented | `unit/fetch/eodhd/test_request_exchange_data.py`: `test_the_columns_are_renamed_to_the_db_columns` <br>`unit/fetch/eodhd/test_request_symbol_data.py`: `test_the_symbols_come_with_the_db_columns_time_frame_and_status` |
| PROVIDER-T21 | Daily and minute bars come back with the columns of their table. | PROVIDER-S19 | unit | Implemented | `unit/fetch/eodhd/test_request_price_data.py`: `test_daily_prices_come_with_the_db_columns`, `test_minute_prices_come_with_the_db_columns` |
| PROVIDER-T22 | Every fundamental record set holds its table's columns in snake_case; the unstored fields are dropped, and a payload without them passes as well; a record set without records is left out. | PROVIDER-S20 | unit | Implemented | `unit/fetch/eodhd/test_request_fundamental_data.py`: `test_every_record_set_holds_its_table_s_columns_in_snake_case`, `test_the_columns_that_are_not_stored_are_dropped`, `test_a_payload_without_the_unstored_columns_passes_as_well`, `test_a_section_without_records_is_left_out_so_the_stored_ones_are_kept` |

### 3.4 Retrying with backoff

| ID | Test case | Verifies | Level | Status | Implemented by |
| -- | --------- | -------- | ----- | ------ | -------------- |
| PROVIDER-T23 | `call_with_backoff` returns as soon as the call succeeds; lets an error it was not asked to retry pass; gives up after a single attempt without waiting; refuses fewer than one attempt before calling; caps the plain backoff at the maximum delay; on giving up, keeps the last error as the cause and names the call (by its name, its `repr`, or an explicit description), the attempts and the last error. | PROVIDER-S21 | unit | Implemented | `unit/utils/test_backoff.py`: `test_call_with_backoff_returns_as_soon_as_the_call_succeeds`, `test_call_with_backoff_does_not_swallow_an_error_it_was_not_asked_to_retry`, `test_a_single_attempt_gives_up_without_waiting`, `test_fewer_than_one_attempt_is_rejected_before_calling`, `test_the_plain_backoff_is_capped_at_the_maximum_delay`, `test_call_with_backoff_keeps_the_original_error_as_the_cause`, `test_the_give_up_message_names_the_call_the_attempts_and_the_last_error`, `test_a_callable_without_a_name_is_described_by_its_repr`, `test_an_explicit_description_replaces_the_function_name` |

### 3.5 Contract checks

| ID | Test case | Verifies | Level | Status | Implemented by |
| -- | --------- | -------- | ----- | ------ | -------------- |
| PROVIDER-T24 | The current answers of the five endpoints have every field and JSON type of the stored samples, in every fundamental record set. | PROVIDER-S22 | live | Implemented | `live/test_eodhd_contract.py`: `test_daily_prices_have_the_sample_s_shape`, `test_minute_prices_have_the_sample_s_shape`, `test_the_fundamentals_have_the_sample_s_sections`, `test_every_fundamental_record_set_has_the_sample_s_shape`, `test_exchanges_have_the_sample_s_shape`, `test_exchange_symbols_have_the_sample_s_shape` |
| PROVIDER-T25 | The request layer turns the current live answers into frames with the columns of their tables. | PROVIDER-S22 | live | Implemented | `live/test_eodhd_contract.py`: `test_live_daily_prices_yield_the_columns_of_their_table`, `test_live_minute_prices_yield_the_columns_of_their_table`, `test_live_fundamentals_yield_the_columns_of_their_tables`, `test_live_exchanges_yield_the_columns_of_their_table`, `test_live_exchange_symbols_yield_the_columns_of_their_table` |

---

## 4 REFDATA: exchange, symbol and sector ingestion

Unit tests run the download and write classes against `routed_api` (sample payloads) and
`FakeDb`, which records reads and writes and answers reads with a given record. The sample
exchange list holds `USA Stocks`, `London Exchange`, `FOREX` and `Vienna Exchange`; the sample
symbol list holds four symbols, three of them on US venues.

### 4.1 Exchanges

| ID | Test case | Verifies | Level | Status | Implemented by |
| -- | --------- | -------- | ----- | ------ | -------------- |
| REFDATA-T01 | Given the sample exchange list, then a daily pass keeps `USA Stocks`, `London Exchange` and `FOREX`, a minute pass `USA Stocks` and `FOREX`. | REFDATA-S01 | unit | Implemented | `unit/fetch/eodhd/test_request_exchange_data.py`: `test_only_the_exchanges_of_the_time_frame_are_kept` |
| REFDATA-T02 | When a daily pass runs, then every kept exchange is stored and its list code returned. | REFDATA-S01, REFDATA-S03 | unit | Implemented | `unit/fetch/download/test_download_exchange_data.py`: `test_every_exchange_of_the_time_frame_is_stored_and_its_code_returned` |
| REFDATA-T03 | Given a target exchange, then only it is kept; given a target that is not listed, then `NoDataError` naming it is raised and nothing is read or written. | REFDATA-S02 | unit | Implemented | `unit/fetch/download/test_download_exchange_data.py`: `test_only_the_target_exchange_is_kept_when_one_is_named`, `test_a_target_exchange_that_is_not_listed_raises_and_writes_nothing` |
| REFDATA-T04 | Given an exchange list without any of the selected exchanges and no target, then `NoDataError` saying so is raised and nothing is written. | REFDATA-S02 | unit | Missing | — |
| REFDATA-T05 | Given an exchange that is not stored, then it is inserted; given one that is, then it is updated, not inserted again. | REFDATA-S03 | unit | Implemented | `unit/fetch/write/test_write_exchange_data.py`: `test_a_new_exchange_is_inserted`, `test_a_stored_exchange_is_updated_so_it_is_not_duplicated` <br>`unit/fetch/download/test_download_exchange_data.py`: `test_an_exchange_already_stored_is_updated_rather_than_inserted_again` |
| REFDATA-T06 | Given an exchange written twice with different values, then one record with the newer values is stored. | REFDATA-S03 | integration | Implemented | `integration/fetch/write/test_write_exchange_data.py`: `test_writing_an_exchange_twice_keeps_one_record_with_the_newer_values` |

### 4.2 Symbols

| ID | Test case | Verifies | Level | Status | Implemented by |
| -- | --------- | -------- | ----- | ------ | -------------- |
| REFDATA-T07 | Given the sample `US` list, then a daily pass keeps the symbols on `NASDAQ`, `NYSE` and `NYSE ARCA`, a minute pass those on `NASDAQ` and `NYSE`; the `LSE` list is kept whole. | REFDATA-S04 | unit | Implemented | `unit/fetch/eodhd/test_request_symbol_data.py`: `test_the_us_list_is_cut_down_to_the_venues_of_the_time_frame` |
| REFDATA-T08 | Given two exchanges, then each symbol list is requested once, and every kept symbol is stored and returned. | REFDATA-S04, REFDATA-S06 | unit | Implemented | `unit/fetch/download/test_download_symbol_data.py`: `test_the_symbols_of_every_exchange_are_stored_and_returned` |
| REFDATA-T09 | Given an exchange without symbols, then it is skipped; given no symbols for any exchange, then `NoDataError` naming the exchanges is raised and nothing is read or written. | REFDATA-S05 | unit | Implemented | `unit/fetch/download/test_download_symbol_data.py`: `test_an_exchange_without_symbols_is_skipped`, `test_no_symbols_anywhere_raises_naming_the_exchanges_and_writes_nothing` |
| REFDATA-T10 | A symbol is looked up under the writer's time frame and status; a new one is inserted; a stored one is updated, not inserted again. | REFDATA-S06 | unit | Implemented | `unit/fetch/write/test_write_symbol_data.py`: `test_the_symbol_is_looked_up_under_the_writer_s_time_frame_and_status`, `test_a_new_symbol_is_inserted`, `test_a_stored_symbol_is_updated_so_it_is_not_duplicated` <br>`unit/fetch/download/test_download_symbol_data.py`: `test_a_stored_symbol_is_updated_rather_than_inserted_again` |
| REFDATA-T11 | Given a symbol written twice with different values, then one record with the newer values is stored. | REFDATA-S06 | integration | Implemented | `integration/fetch/write/test_write_symbol_data.py`: `test_writing_a_symbol_twice_keeps_one_record_with_the_newer_values` |
| REFDATA-T12 | Given the same symbol in a daily and a minute pass, or as active and then as delisted, then a record for each is stored and the earlier one is kept. | REFDATA-S06 | integration | Missing | — |
| REFDATA-T13 | The returned symbols carry the list code their requests are built with, while their own exchange code stays the venue. | REFDATA-S07 | unit | Implemented | `unit/fetch/download/test_download_symbol_data.py`: `test_every_symbol_remembers_the_exchange_code_its_urls_are_built_with` |

### 4.3 Sector and industry

| ID | Test case | Verifies | Level | Status | Implemented by |
| -- | --------- | -------- | ----- | ------ | -------------- |
| REFDATA-T14 | Given a symbol without a sector record, then one is inserted with every sector column, symbol and exchange code first; given one with a sector record, then it is updated, not inserted again. | REFDATA-S08 | unit | Implemented | `unit/fetch/write/test_write_fundamental_data.py`: `test_a_new_sector_record_is_inserted_with_every_sector_column`, `test_a_stored_sector_record_is_updated_so_it_is_not_duplicated` |
| REFDATA-T15 | Given a `NASDAQ` or `NYSE` symbol with fundamentals, then its sector record is stored; given a symbol of another venue, or one without fundamentals, then no sector record is written. | REFDATA-S08 | unit | Implemented | `unit/fetch/download/test_download_fundamental_data.py`: `test_the_fundamentals_of_a_us_stock_are_stored`, `test_exchanges_without_fundamentals_are_not_requested`, `test_a_symbol_without_fundamentals_stores_nothing` |
| REFDATA-T16 | Given the sample fundamentals payload, when it is written, then the `sector` table holds one record for the symbol. | REFDATA-S08 | integration | Implemented | `integration/fetch/write/test_write_fundamental_data.py`: `test_the_payload_fills_the_sector_and_every_fundamental_table` |

---

## 5 PRICES: daily and minute price ingestion

Unit tests run `DownloadPriceData` and `WritePriceData` against `routed_api` and a `FakeDb` that
answers the newest-bar lookup with a given timestamp. The tests of
`test_download_price_data.py` pin "today" to 2025-09-25 15:30 UTC, so the windows are fixed.

### 5.1 What is requested

| ID | Test case | Verifies | Level | Status | Implemented by |
| -- | --------- | -------- | ----- | ------ | -------------- |
| PRICES-T01 | Given a symbol without stored daily bars, then its full history is requested (no `from`) and stored under the pass's time frame and status. | PRICES-S01, PRICES-S06 | unit | Implemented | `unit/fetch/download/test_download_price_data.py`: `test_a_new_symbol_s_daily_history_is_requested_in_full_and_stored` |
| PRICES-T02 | Given a newest stored daily bar of 2024-03-05, then the bars are requested from 2024-03-06. | PRICES-S01 | unit | Implemented | `unit/fetch/download/test_download_price_data.py`: `test_a_stored_symbol_is_only_requested_from_the_day_after_its_newest_price` |
| PRICES-T03 | The newest bar is looked up for the symbol on its venue in the table of the time frame, and comes back as a datetime, or as nothing for a symbol without bars; against the database, it is the newest bar written. | PRICES-S01, PRICES-S02 | unit, integration | Implemented | `unit/fetch/download/test_download_price_data.py`: `test_the_newest_price_is_looked_up_for_the_symbol_on_its_exchange` <br>`unit/fetch/write/test_write_price_data.py`: `test_the_newest_stored_timestamp_is_returned_as_a_datetime`, `test_a_symbol_without_stored_prices_has_no_newest_timestamp` <br>`integration/fetch/write/test_write_price_data.py`: `test_the_newest_stored_timestamp_is_read_back_after_an_insert` |
| PRICES-T04 | Given a completed daily run, when the same run follows, then only the days after the newest stored bar are requested and no table gains a record. | PRICES-S01, PRICES-S06 | integration | Implemented | `integration/fetch/test_fetcher.py`: `test_a_second_run_asks_only_for_the_new_days_and_duplicates_nothing` |
| PRICES-T05 | With the local time zone set away from UTC, given a newest minute bar of 2025-09-20 15:59, then minute bars are requested from 16:00 UTC that day up to 00:00 UTC of "today". | PRICES-S02 | unit | Implemented | `unit/fetch/download/test_download_price_data.py`: `test_minute_prices_are_requested_from_one_minute_after_the_newest_one` |
| PRICES-T06 | Given minute data that is up to date, or a start of today, then nothing is requested and nothing is stored. | PRICES-S02, PRICES-S07 | unit | Implemented | `unit/fetch/download/test_download_price_data.py`: `test_minute_prices_that_are_already_up_to_date_are_not_requested`, `test_a_start_of_today_needs_no_chunk` |
| PRICES-T07 | Without a stored minute bar, the period from 2005-01-01 to today is split into ⌈days / 120⌉ contiguous windows of at most 120 days; a recent start needs a single window. | PRICES-S02, PRICES-S03 | unit | Implemented | `unit/fetch/download/test_download_price_data.py`: `test_the_whole_minute_history_is_split_into_contiguous_chunks_of_at_most_120_days`, `test_a_recent_start_needs_a_single_chunk` |
| PRICES-T08 | The windows' bars are merged into one frame with a fresh index and written once. | PRICES-S03, PRICES-S06 | unit | Implemented | `unit/fetch/download/test_download_price_data.py`: `test_the_minute_chunks_are_merged_into_one_frame_with_a_fresh_index` |

### 5.2 What is stored

| ID | Test case | Verifies | Level | Status | Implemented by |
| -- | --------- | -------- | ----- | ------ | -------------- |
| PRICES-T09 | Daily date strings and minute Unix seconds are written as datetimes, the caller's frame unchanged; the bars are written under the writer's time frame and status. | PRICES-S04, PRICES-S06 | unit | Implemented | `unit/fetch/write/test_write_price_data.py`: `test_daily_dates_are_inserted_as_datetimes`, `test_minute_unix_seconds_are_inserted_as_datetimes`, `test_prices_are_inserted_under_the_writer_s_time_frame_and_status` |
| PRICES-T10 | Bars before 1970 are dropped with a warning naming their number and the symbol, the rest keep a fresh index and the caller's frame stays unfiltered; nothing is logged when none is dropped; if all are dropped, nothing is written. | PRICES-S05, PRICES-S07 | unit | Implemented | `unit/fetch/write/test_write_price_data.py`: `test_prices_from_before_1970_are_dropped_with_a_warning`, `test_nothing_is_inserted_if_every_price_is_from_before_1970` <br>`unit/fetch/download/test_download_price_data.py`: `test_a_symbol_whose_prices_are_all_from_before_1970_is_not_stored` <br>`unit/fetch/test_utils.py`: `test_records_from_before_1970_are_dropped_and_the_rest_get_a_fresh_index`, `test_dropping_records_is_logged_with_the_symbol_and_their_number`, `test_nothing_is_logged_when_no_record_is_from_before_1970`, `test_the_caller_s_records_are_not_filtered` |
| PRICES-T11 | Given no bars from the provider, then "No data exists for symbol AAPL (NASDAQ, DAILY, ACTIVE)" is logged and nothing is written. | PRICES-S07 | unit | Implemented | `unit/fetch/download/test_download_price_data.py`: `test_no_prices_are_logged_and_nothing_is_stored` |
| PRICES-T12 | Given a minute history whose third of five windows fails, then the error reaches the caller and none of the windows is written. | PRICES-S03, PRICES-S08 | unit | Missing | — |
| PRICES-T13 | Given two incremental minute runs against the test database, then the stored series has no gap and no duplicate at the boundary between them. | PRICES-S02, PRICES-S06 | integration | Missing | — |

---

## 6 FUND: fundamentals ingestion and replacement

Unit tests run `DownloadFundamentalData` against `routed_api` and `WriteFundamentalData` against
`FakeDb` with small balance-sheet frames; the integration tests write the sample fundamentals
payload of AAPL, which holds two records per record set.

### 6.1 What is requested

| ID | Test case | Verifies | Level | Status | Implemented by |
| -- | --------- | -------- | ----- | ------ | -------------- |
| FUND-T01 | Given a symbol on `NYSE ARCA`, `LSE` or `FOREX`, then no request is made; given one on `NASDAQ` or `NYSE`, then its fundamentals are requested, and each of the eight tables is cleared of the symbol and written. | FUND-S01, FUND-S03 | unit | Implemented | `unit/fetch/download/test_download_fundamental_data.py`: `test_exchanges_without_fundamentals_are_not_requested`, `test_the_fundamentals_of_a_us_stock_are_stored` |
| FUND-T02 | Given an empty answer, then nothing is deleted or written. | FUND-S02 | unit | Implemented | `unit/fetch/download/test_download_fundamental_data.py`: `test_a_symbol_without_fundamentals_stores_nothing` |
| FUND-T03 | Given a NASDAQ symbol in a daily and a minute pass, then its fundamentals are requested in both. | FUND-S01 | unit | Missing | — |

### 6.2 Replacement

| ID | Test case | Verifies | Level | Status | Implemented by |
| -- | --------- | -------- | ----- | ------ | -------------- |
| FUND-T04 | The symbol's records in a table are deleted before the new ones are written, with the table's timestamp and key columns; only the tables of the record sets given are touched, in their order. | FUND-S03 | unit | Implemented | `unit/fetch/write/test_write_fundamental_data.py`: `test_the_symbol_s_records_are_deleted_before_the_new_ones_are_written`, `test_only_the_tables_of_the_given_types_are_touched` |
| FUND-T05 | Every record set maps to its own table; camelCase names become snake_case, snake_case names stay, and the frame is renamed in place. | FUND-S04 | unit | Implemented | `unit/fetch/test_utils.py`: `test_every_fundamental_type_but_sector_and_industry_has_its_own_table`, `test_camel_case_columns_become_snake_case_and_snake_case_ones_stay`, `test_the_columns_are_renamed_in_place_and_the_frame_returned` |
| FUND-T06 | Amounts sent as strings are written as floats and dates as datetimes, with the codes added and a fresh index; `"n/a"`, an empty string or no value is written as NULL; the caller's records are unchanged. | FUND-S04 | unit | Implemented | `unit/fetch/write/test_write_fundamental_data.py`: `test_the_records_are_written_in_the_types_their_columns_store`, `test_an_amount_that_is_no_number_is_stored_as_null`, `test_the_caller_s_records_are_not_modified` |
| FUND-T07 | A record without its designated timestamp is dropped; records with a designated timestamp before 1970 are dropped with a warning, while another date field keeps a date before 1970; if no record is left, the stored records are kept (nothing deleted or written). | FUND-S05 | unit | Implemented | `unit/fetch/write/test_write_fundamental_data.py`: `test_a_record_without_its_designated_timestamp_is_dropped`, `test_the_stored_records_are_kept_when_no_record_has_its_designated_timestamp`, `test_records_from_before_1970_are_dropped_with_a_warning`, `test_the_stored_records_are_kept_when_every_record_is_from_before_1970`, `test_a_date_column_other_than_the_designated_timestamp_keeps_a_date_from_before_1970` |
| FUND-T08 | Given a record set with a field the table doesn't have, then `SchemaMismatchError` with the documented message is raised before anything is deleted or written. | FUND-S06 | unit | Implemented | `unit/fetch/write/test_write_fundamental_data.py`: `test_a_column_the_table_does_not_have_fails_before_the_stored_records_are_deleted` |
| FUND-T09 | Given two record sets of which the second fails the structure check, then the first table is replaced, the second keeps its records, and the third is not processed. | FUND-S06 | unit | Missing | — |
| FUND-T10 | Given a write that fails after the deletion, then `InsertError` is raised and the table holds no records of the symbol. | FUND-S07 | integration | Missing | — |
| FUND-T11 | Given the sample payload, then every fundamental table holds its two records, with the table's columns unchanged and amounts stored as floating-point numbers; written twice, the tables hold the same records. | FUND-S03, FUND-S04, FUND-S08 | integration | Implemented | `integration/fetch/write/test_write_fundamental_data.py`: `test_the_payload_fills_the_sector_and_every_fundamental_table`, `test_writing_the_fundamentals_again_replaces_them_rather_than_adding_to_them` |
| FUND-T12 | Given the fundamentals of two symbols replaced right after each other, then both symbols' records are stored completely (the suspected WAL race, STORAGE section 1.7). | FUND-S03 | integration | Missing | — |

---

## 7 RUNS: fetch orchestration

Unit tests replace a `Fetcher`'s download objects (or its per-symbol step) with functions that
succeed or raise as told, and disable the storage check unless it is under test. The tests of
`Client.fetch` replace `Fetcher` with a `FakeFetcher` that records the passes. The integration
test runs a daily pass for `USA Stocks` against the test database with the sample payloads.

### 7.1 Passes

| ID | Test case | Verifies | Level | Status | Implemented by |
| -- | --------- | -------- | ----- | ------ | -------------- |
| RUNS-T01 | Without filters, the passes run in the order daily active, daily delisted, minute active, minute delisted; a time frame, a status or both select the matching passes. | RUNS-S01 | unit | Implemented | `unit/test_client.py`: `test_fetch_without_filters_runs_every_time_frame_and_status`, `test_fetch_runs_only_the_passes_the_filters_select` |
| RUNS-T02 | Every pass gets the token, the target exchange and the stop function. | RUNS-S02 | unit | Implemented | `unit/test_client.py`: `test_fetch_hands_token_exchange_and_should_stop_to_every_pass` |
| RUNS-T03 | Given a daily pass for `USA Stocks` with the sample payloads, then its three symbols are requested and downloaded without failure, and the exchange, symbol, sector, price and fundamental tables hold the expected records. | RUNS-S03 | integration | Implemented | `integration/fetch/test_fetcher.py`: `test_a_daily_run_stores_every_symbol_of_the_exchange` |
| RUNS-T04 | Given an account error in the first pass, then no later pass runs. | RUNS-S04, RUNS-S07 | unit | Implemented | `unit/test_client.py`: `test_an_account_error_ends_the_fetch_before_the_next_pass` |
| RUNS-T05 | Given a `NoDataError` from the exchange list of a pass (a target exchange not listed for the time frame), then the fetch ends and no later pass runs. | RUNS-S04 | unit | Missing | — |

### 7.2 Failures

| ID | Test case | Verifies | Level | Status | Implemented by |
| -- | --------- | -------- | ----- | ------ | -------------- |
| RUNS-T06 | Given a symbol whose download raises a `CompatibilityError` or an `InsertError`, then it is recorded as failed with its code, venue and error type, and the other symbols are downloaded; a failed symbol is an immutable record. | RUNS-S05 | unit | Implemented | `unit/fetch/test_fetcher.py`: `test_a_symbol_that_fails_is_recorded_and_the_run_carries_on`, `test_a_failing_insert_only_costs_its_own_symbol` <br>`unit/fetch/test_utils.py`: `test_a_failed_symbol_is_an_immutable_record` |
| RUNS-T07 | Given every symbol failing with a `RequestError` or an `InsertError`, then the pass ends with `FetchError` after 20 failures, chained from the last error; given one success among them, the streak resets and the pass goes on. | RUNS-S06 | unit | Implemented | `unit/fetch/test_fetcher.py`: `test_enough_failures_in_a_row_abort_the_run`, `test_the_failure_streak_resets_after_a_symbol_succeeds` |
| RUNS-T08 | Given a `DataLimitError`, `UnauthorizedError` or `AccessRightsError` at the first symbol, then the pass ends there with that error, and the symbol is recorded as failed. | RUNS-S07 | unit | Implemented | `unit/fetch/test_fetcher.py`: `test_an_account_level_error_ends_the_run_at_the_first_symbol`, `test_the_symbol_the_run_ends_on_is_recorded_as_a_failure` |
| RUNS-T09 | Given a stop request after the first symbol, then the pass ends with `UserInterruptError` before the second; a `UserInterruptError` from a download isn't recorded as a failure; a `StorageError` ends the pass. | RUNS-S08 | unit | Implemented | `unit/fetch/test_fetcher.py`: `test_should_stop_ends_the_run_before_the_next_symbol`, `test_a_user_interrupt_is_never_treated_as_a_symbol_failure`, `test_running_out_of_disk_space_ends_the_run` |
| RUNS-T10 | Free space of 49 GB is a `StorageError`, 50 GB is enough, and the check runs before a symbol is downloaded. | RUNS-S08 | unit | Implemented | `unit/fetch/test_fetcher.py`: `test_less_free_disk_space_than_the_minimum_is_a_storage_error`, `test_exactly_the_minimum_free_disk_space_is_enough`, `test_the_disk_is_checked_before_every_symbol` |

### 7.3 Outcome

| ID | Test case | Verifies | Level | Status | Implemented by |
| -- | --------- | -------- | ----- | ------ | -------------- |
| RUNS-T11 | Given three symbols of which one fails, then the counts, the log of exchanges and symbols, the summary and the failed symbol's line are as specified; with a target exchange, one exchange is reported. | RUNS-S09, RUNS-S10 | unit | Implemented | `unit/fetch/test_fetcher.py`: `test_a_run_counts_the_requested_downloaded_and_failed_symbols`, `test_a_run_restricted_to_one_exchange_reports_one_exchange` |
| RUNS-T12 | Given a pass that ends early on a `StorageError`, then the summary is still logged and counts the remaining symbols as not attempted; given 10,000 failures, the summary names 10 and adds "... and 9990 more". | RUNS-S10 | unit | Implemented | `unit/fetch/test_fetcher.py`: `test_the_summary_is_logged_even_when_the_run_ends_early`, `test_the_summary_names_at_most_ten_failures_however_many_there_were` |
| RUNS-T13 | The fetch total adds up the requested symbols of every pass; a warning names the total of skipped symbols, and there is none when nothing was skipped. | RUNS-S11 | unit | Implemented | `unit/test_client.py`: `test_fetch_without_filters_runs_every_time_frame_and_status`, `test_fetch_warns_about_the_symbols_that_were_skipped`, `test_fetch_does_not_warn_when_nothing_was_skipped` |
| RUNS-T14 | Given a pass with a connection error carrying the token in its URL and a 503 answer echoing it, then both symbols fail after retries, and no log record, neither its message nor its arguments, holds the token. | RUNS-S12 | unit | Implemented | `unit/fetch/test_fetcher.py`: `test_no_log_record_of_a_run_with_retries_and_failures_holds_the_token` |
| RUNS-T15 | Given a completed run, when a new run starts, then it works from the stored data alone: it asks only for the days after the newest stored bar and stores nothing twice. | RUNS-S13 | integration | Implemented | `integration/fetch/test_fetcher.py`: `test_a_second_run_asks_only_for_the_new_days_and_duplicates_nothing` |

---

## 8 ACCESS: reading stored data

Unit tests run `Read` on `FakeQuery` or `RecordingQuery`, which answer with given rows and record
the statements and parameters. Integration tests store daily bars in the test database and read
them back.

### 8.1 Reference data

| ID | Test case | Verifies | Level | Status | Implemented by |
| -- | --------- | -------- | ----- | ------ | -------------- |
| ACCESS-T01 | A stored record comes back as its values; a symbol is looked up by its whole key, a sector by symbol and exchange code; the exchange lookup reads every column by exchange code, the symbol lookup the columns in table order. | ACCESS-S01, ACCESS-S02 | unit | Implemented | `unit/db/io/test_read.py`: `test_reading_an_existing_record_yields_its_values`, `test_a_symbol_is_looked_up_by_its_whole_unique_key`, `test_a_sector_is_looked_up_by_symbol_and_exchange` <br>`unit/db/statements/test_exchange.py`: `test_the_select_reads_every_column_by_exchange_code` <br>`unit/db/statements/test_symbol.py`: `test_the_symbol_select_reads_the_columns_the_record_is_built_from` |
| ACCESS-T02 | A record that isn't stored reads as an empty `Series`, in unit tests and against the database, for exchange, symbol and sector, and so do the price reads. | ACCESS-S03, ACCESS-S07 | unit, integration | Implemented | `unit/db/io/test_read.py`: `test_reading_a_missing_record_yields_an_empty_series_not_an_index_error` <br>`integration/db/io/test_read.py`: `test_records_that_are_not_stored_read_as_empty` |
| ACCESS-T03 | Given two records for one key, then `QueryError` is raised, naming the record for symbols and sectors. | ACCESS-S03 | unit | Implemented | `unit/db/io/test_read.py`: `test_more_records_than_the_unique_key_allows_is_a_query_error`, `test_a_duplicated_unique_key_is_a_query_error_naming_the_record` |

### 8.2 Price bars

| ID | Test case | Verifies | Level | Status | Implemented by |
| -- | --------- | -------- | ----- | ------ | -------------- |
| ACCESS-T04 | Daily bars are read from the daily table, indexed by symbol code and timestamp, with its other columns and the bounds as parameters; minute bars from the minute table with its columns; without bounds, `datetime.min` and `datetime.max` are sent. | ACCESS-S04, ACCESS-S05 | unit | Implemented | `unit/db/io/test_read.py`: `test_daily_prices_are_indexed_by_symbol_and_timestamp`, `test_minute_prices_are_read_from_the_minute_table_with_its_columns` |
| ACCESS-T05 | The range query takes the exchange code and both bounds as parameters and the symbol codes as an `IN` list. | ACCESS-S04, ACCESS-S09 | unit | Implemented | `unit/db/statements/test_price.py`: `test_the_range_select_takes_the_exchange_and_both_bounds_as_params` |
| ACCESS-T06 | Against the database, both bounds are inclusive, no bounds read the whole history, and only the requested symbols of each venue are read. | ACCESS-S04 | integration | Implemented | `integration/db/io/test_read.py`: `test_the_date_bounds_are_inclusive`, `test_without_bounds_the_whole_history_is_read`, `test_only_the_requested_symbols_of_each_exchange_are_read` |
| ACCESS-T07 | The bars of several venues are concatenated into one frame. | ACCESS-S05 | unit | Implemented | `unit/db/io/test_read.py`: `test_prices_of_several_exchanges_are_concatenated` |
| ACCESS-T08 | The newest bars are selected per symbol with `LATEST ON`, keep symbol code and timestamp as columns, and against the database are the newest bar of each symbol. | ACCESS-S06 | unit, integration | Implemented | `unit/db/io/test_read.py`: `test_the_newest_prices_keep_symbol_and_timestamp_as_columns_too` <br>`unit/db/statements/test_price.py`: `test_the_newest_record_is_selected_per_symbol` <br>`integration/db/io/test_read.py`: `test_the_newest_record_is_read_for_every_symbol` |
| ACCESS-T09 | An empty mapping returns an empty frame, for bars and for newest bars. | ACCESS-S07 | unit | Implemented | `unit/db/io/test_read.py`: `test_reading_prices_for_no_symbols_yields_an_empty_frame`, `test_the_newest_prices_for_no_symbols_are_an_empty_frame` |
| ACCESS-T10 | Given a venue with an empty symbol list, then `QueryError` is raised (today's behaviour, verified by hand on 2026-10-19; `query-layer` changes it). | ACCESS-S07 | integration | Missing | — |
| ACCESS-T11 | Three venues of 1,000 symbols each are read with three queries, each listing its 1,000 codes. | ACCESS-S08 | unit | Implemented | `unit/db/io/test_read.py`: `test_prices_are_read_with_one_query_per_exchange_however_many_symbols` |

### 8.3 Safety and errors

| ID | Test case | Verifies | Level | Status | Implemented by |
| -- | --------- | -------- | ----- | ------ | -------------- |
| ACCESS-T12 | A symbol code with a quote stays one literal; lookup values are bound as parameters; against the database, injection attempts in lookups and price reads find nothing and leave the stored bars unchanged. | ACCESS-S09 | unit, integration | Implemented | `unit/db/io/test_read.py`: `test_a_symbol_code_cannot_break_out_of_its_literal`, `test_lookups_bind_their_values_as_params` <br>`integration/db/io/test_read.py`: `test_injection_attempts_in_lookups_find_nothing_and_change_nothing` |
| ACCESS-T13 | A read whose statement fails raises `QueryError` (through the statement runner, STORAGE-T28). | ACCESS-S10 | unit | Implemented | `unit/db/io/test_query.py`: `test_a_failing_statement_is_reported_as_a_db_error` |

---

## 9 CLIENT: library facade

### 9.1 Package and client

| ID | Test case | Verifies | Level | Status | Implemented by |
| -- | --------- | -------- | ----- | ------ | -------------- |
| CLIENT-T01 | `Client`, `Config`, `MarketHistoryDbError`, `SymbolStatus` and `TimeFrame` import from the package. | CLIENT-S01 | unit | Implemented | `unit/test_init.py`: `test_the_public_api_is_importable_from_the_package` |
| CLIENT-T02 | After import, the package logger has exactly one handler, a `NullHandler`. | CLIENT-S02, CLIENT-S05 | unit | Implemented | `unit/test_init.py`: `test_the_package_only_adds_a_null_handler_and_leaves_the_rest_to_the_application` |
| CLIENT-T03 | Importing the package in a fresh interpreter with no environment variables set reads none, opens no connection and creates no file. | CLIENT-S02 | unit | Missing | — |
| CLIENT-T04 | A given `Config` is used as it is, without reading the environment, and `read` is the database's own read interface; without a `Config`, the environment is read, and a missing variable raises `ConfigError`. | CLIENT-S03, CLIENT-S04 | unit | Implemented | `unit/test_client.py`: `test_an_explicit_config_is_used_as_is_and_the_environment_is_not_read`, `test_without_a_config_the_environment_is_read`, `test_without_a_config_a_missing_variable_is_a_config_error` |
| CLIENT-T05 | `setup()` sets up the database the client's `Config` points to. | CLIENT-S04 | unit | Implemented | `unit/test_client.py`: `test_setup_sets_up_the_db_the_config_points_to` |
| CLIENT-T06 | Through the public API only: set up, fetch a daily pass of `USA Stocks` from the sample payloads (3 symbols), read the bars of two symbols back, and read the newest bar. | CLIENT-S01, CLIENT-S04 | integration | Implemented | `integration/test_client.py`: `test_setup_fetch_and_read_through_the_public_api` |

### 9.2 Errors

| ID | Test case | Verifies | Level | Status | Implemented by |
| -- | --------- | -------- | ----- | ------ | -------------- |
| CLIENT-T07 | Each error class has the parent the documented tree gives it. | CLIENT-S06 | unit | Implemented | `unit/test_errors.py`: `test_each_error_sits_where_the_documented_hierarchy_puts_it` |
| CLIENT-T08 | `SchemaMismatchError` derives from `InsertError` (missing from the hierarchy test). | CLIENT-S06 | unit | Missing | — |
| CLIENT-T09 | An error without a code renders as its message; with a code, " (Error Code: N)" is appended to the rendered text only; an `ApiError` offers its HTTP status and `retry_after`. | CLIENT-S07 | unit | Implemented | `unit/test_errors.py`: `test_an_error_without_a_code_renders_as_its_message`, `test_an_error_with_a_code_appends_it_to_the_rendered_message_only`, `test_an_api_error_exposes_the_http_status_and_the_retry_after` |
| CLIENT-T10 | Failures of `requests` and of the database drivers reach the caller as the package's errors (covered per layer by PROVIDER-T11, T14 and STORAGE-T07, T19, T22, T28). | CLIENT-S08 | unit | Implemented | `unit/fetch/eodhd/test_request_data.py`: `test_a_host_that_stays_unreachable_ends_in_a_request_error`, `test_a_request_exception_no_retry_can_fix_is_a_request_error_at_once` <br>`unit/db/io/test_query.py`: `test_a_failing_statement_is_reported_as_a_db_error` <br>`unit/db/io/test_error.py`: `test_an_error_no_retry_can_fix_is_an_insert_error_at_once` |
| CLIENT-T11 | A docstring and type check of the public API passes (e.g. ruff's docstring rules and a type checker). | CLIENT-S09 | static | Missing | — |

`unit/test_errors.py` also holds `test_exit_code_2_stays_reserved_for_argparse`, which checks the
exit codes; it is mapped in the CLI chapter.

---

## 10 CONFIG: configuration

| ID | Test case | Verifies | Level | Status | Implemented by |
| -- | --------- | -------- | ----- | ------ | -------------- |
| CONFIG-T01 | A `Config` can't be changed once built. | CONFIG-S01 | unit | Implemented | `unit/test_config.py`: `test_a_config_cannot_be_changed_once_built` |
| CONFIG-T02 | Unset optional variables fall back to their defaults; each one, when set, overrides its default. | CONFIG-S01, CONFIG-S02 | unit | Implemented | `unit/test_config.py`: `test_unset_optional_variables_fall_back_to_the_defaults`, `test_every_optional_variable_overrides_its_default` |
| CONFIG-T03 | A missing token raises `ConfigError` naming the variable; a set variable is returned as it is; an unset or empty one raises `ConfigError` naming it; a port that isn't a number raises `ConfigError` naming the variable. | CONFIG-S02 | unit | Implemented | `unit/test_config.py`: `test_a_missing_token_is_a_config_error_naming_the_variable`, `test_a_port_that_is_not_a_number_is_a_config_error` <br>`unit/utils/test_env.py`: `test_a_set_variable_is_returned_as_is`, `test_an_unset_or_empty_variable_is_a_config_error_naming_it` |
| CONFIG-T04 | The printed form of a `Config` shows neither the token nor the password. | CONFIG-S03 | unit | Implemented | `unit/test_config.py`: `test_neither_secret_shows_up_in_the_repr` |
| CONFIG-T05 | The SQL connection string carries every setting and a connect timeout; a password with a space, a quote, a backslash or an injected `hostaddr=` stays one value. | CONFIG-S04 | unit | Implemented | `unit/test_config.py`: `test_the_psycopg_connection_string_carries_every_setting`, `test_the_db_connection_gives_up_rather_than_hanging_on_an_unreachable_host`, `test_the_password_cannot_break_out_of_the_db_connection_string` |
| CONFIG-T06 | The ingestion string carries every setting; semicolons in the password are doubled, and the QuestDB client parses the result. | CONFIG-S05 | unit | Implemented | `unit/test_config.py`: `test_the_ingress_config_string_carries_every_setting`, `test_a_semicolon_in_the_password_cannot_end_the_ingress_config_early` |

---

## 11 CLI: command line

Unit tests call `cli.main([...])` in-process with the logger, the `.env` loading and the `Client`
replaced: by a client whose `fetch` raises a given error, or by one that records its calls. No
test runs the installed command (`5_test.md` 1.1, end-to-end tests).

### 11.1 Commands

| ID | Test case | Verifies | Level | Status | Implemented by |
| -- | --------- | -------- | ----- | ------ | -------------- |
| CLI-T01 | `fetch --time-frame minute --symbol-status DELISTED --exchange "USA Stocks"` reaches the client as enum members and the name; `fetch` without options leaves every filter unset. | CLI-S01, CLI-S03 | unit | Implemented | `unit/test_cli.py`: `test_fetch_options_reach_the_client_as_enum_members`, `test_fetch_without_options_leaves_every_filter_unset` |
| CLI-T02 | An invalid choice names the valid ones; an invalid value and a missing command exit with code 2, which no error of the package uses. | CLI-S01, CLI-S05 | unit | Implemented | `unit/test_cli.py`: `test_an_invalid_choice_names_the_valid_ones`, `test_a_missing_command_is_a_usage_error`, `test_argparse_usage_errors_keep_an_exit_code_of_their_own` <br>`unit/test_errors.py`: `test_exit_code_2_stays_reserved_for_argparse` |
| CLI-T03 | Given a `.env` file in the working directory of an installed copy, then its variables are (today: are not) loaded; variables already set are kept. | CLI-S02 | integration | Missing | — |
| CLI-T04 | `setup` runs once the answer is "yes" or "Y"; an empty answer, "no", "n", "yess" or a closed standard input set up nothing; `markethistorydb setup` confirmed with "yes" exits with 0. | CLI-S04 | unit | Implemented | `unit/test_cli.py`: `test_setup_runs_once_the_user_confirms`, `test_setup_drops_nothing_unless_the_user_confirms`, `test_setup_command_runs_the_setup_once_confirmed` |

### 11.2 Exit codes and reporting

| ID | Test case | Verifies | Level | Status | Implemented by |
| -- | --------- | -------- | ----- | ------ | -------------- |
| CLI-T05 | Each error, and success, ends with its exit code, including Ctrl+C, a `ConfigError` while the client is built, and an error outside the hierarchy. | CLI-S05 | unit | Implemented | `unit/test_cli.py`: `test_cli_maps_each_error_to_its_exit_code`, `test_a_config_error_while_building_the_client_is_a_config_error_code` |
| CLI-T06 | The most specific mapped class wins; `AccountError` falls back to the `FetchError` code; an unmapped package error is unknown; every exit code is produced by some error, and every error class of the package has a code. | CLI-S05 | unit | Implemented | `unit/test_cli.py`: `test_a_subclass_wins_over_the_parent_whatever_the_entries_are_ordered_like`, `test_an_error_outside_every_mapped_class_is_an_unknown_error`, `test_every_exit_code_can_actually_be_produced_by_some_error`, `test_every_error_the_package_raises_maps_to_an_exit_code` |
| CLI-T07 | An account error and a `ConfigError` are logged without traceback; a `RequestError` and an error outside the hierarchy are logged with it. | CLI-S06 | unit | Implemented | `unit/test_cli.py`: `test_an_account_error_is_reported_without_a_traceback`, `test_a_config_error_is_reported_without_a_traceback`, `test_any_other_failure_is_logged_with_its_traceback` |

---

## 12 LOGGING: log output and token masking

Tests that start the logger use the `reset_logging` fixture, which restores the logging setup
afterwards, and write the log file to a temporary directory.

| ID | Test case | Verifies | Level | Status | Implemented by |
| -- | --------- | -------- | ----- | ------ | -------------- |
| LOGGING-T01 | The logger writes to standard output and to `markethistorydb.log` in the given directory, in UTF-8, or in the working directory by default; terminal-only mode writes no file; starting it twice leaves two handlers; the level is set on the root logger. | LOGGING-S01 | unit | Implemented | `unit/utils/test_logger.py`: `test_start_logger_writes_to_stdout_and_to_a_log_file_in_the_given_dir`, `test_the_log_dir_defaults_to_the_working_directory`, `test_only_the_terminal_is_written_to_when_so_configured`, `test_starting_the_logger_twice_does_not_duplicate_handlers`, `test_the_level_is_applied_to_the_root_logger` |
| LOGGING-T02 | The file rotates at 10 MiB with 5 backups; with small limits, no more than the configured backups are kept. | LOGGING-S01 | unit | Implemented | `unit/utils/test_logger.py`: `test_the_log_file_is_rotated_so_its_disk_use_is_capped`, `test_rotation_keeps_no_more_than_the_configured_backups` |
| LOGGING-T03 | A line has the documented format, and the setup logs the working directory. | LOGGING-S02 | unit | Missing | — |
| LOGGING-T04 | A `FutureWarning` ends up in the log file. | LOGGING-S03 | unit | Implemented | `unit/utils/test_logger.py`: `test_warnings_are_routed_into_the_log` |
| LOGGING-T05 | The token is masked in a record's message, its arguments and its traceback, by every handler, in the file too; in query strings and printed dicts, at the start or end of a query, every occurrence on a line and on every line; text without a token, or with a similar parameter name, stays unchanged. | LOGGING-S04 | unit | Implemented | `unit/utils/test_logger.py`: `test_the_api_token_is_masked_in_the_message_its_args_and_the_traceback`, `test_every_handler_masks_the_token` <br>`unit/utils/test_redact.py`: `test_the_token_is_masked_wherever_it_appears`, `test_every_occurrence_on_a_line_is_masked`, `test_every_line_of_a_multi_line_text_is_masked`, `test_text_without_a_token_is_left_unchanged` |

---

## 13 PACKAGING: package and entry points

| ID | Test case | Verifies | Level | Status | Implemented by |
| -- | --------- | -------- | ----- | ------ | -------------- |
| PACKAGING-T01 | Building the package gives a wheel and an sdist with the declared metadata, dependencies and console script. | PACKAGING-S01 | unit | Missing | — |
| PACKAGING-T02 | `python -m markethistorydb` exits with the code `cli.main` returns. | PACKAGING-S02 | unit | Implemented | `unit/test_main.py`: `test_running_the_package_exits_with_the_code_main_returns` |
| PACKAGING-T03 | In a fresh environment, the installed `markethistorydb --help` exits with 0. | PACKAGING-S02, PACKAGING-S03 | integration | Missing | — |

---

## 14 QUALITY: the test suite

These test cases are carried out by the suite's own configuration rather than by test
functions; "Implemented by" names the configuration.

| ID | Test case | Verifies | Level | Status | Implemented by |
| -- | --------- | -------- | ----- | ------ | -------------- |
| QUALITY-T01 | `pytest -m unit`, `-m integration` and `-m live` each select exactly the tests of their directory. | QUALITY-S01 | suite | Implemented | `pytest_collection_modifyitems` in `tests/unit/conftest.py`, `tests/integration/conftest.py`, `tests/live/conftest.py`; markers in `pyproject.toml` |
| QUALITY-T02 | `uv run pytest -m unit --cov` passes only with 100 % line and branch coverage of `src/`. | QUALITY-S02 | suite | Implemented | `[tool.coverage.report] fail_under = 100` in `pyproject.toml` |
| QUALITY-T03 | Given `QUESTDB_TEST_*` pointing at the application's QuestDB, then the run stops with exit code 3 before any test; without the variables, or with the instance unreachable, the integration tests are skipped. | QUALITY-S03 | suite | Missing | — |
| QUALITY-T04 | Every integration test starts on empty tables. | QUALITY-S04 | suite | Implemented | fixture `fresh_db` in `tests/integration/conftest.py`, used by the integration tests |
