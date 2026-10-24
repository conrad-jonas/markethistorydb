# data-integrity-checks: test changes

The race gets a deterministic test of the intended behaviour, marked as a strict expected
failure, and the key change a test of two periods reported or filed on one day. The value
semantics are checked live every night with the demo token. The baseline is one integration
test whose counts are its assertions.

## Test case changes

### Stored fundamentals

| Change | ID | Test case | Verifies | Level | Status | Implemented by |
| ------ | -- | --------- | -------- | ----- | ------ | -------------- |
| MODIFIED | FUND-T12 | Given symbol A's records written to a fundamental table and not yet applied (the table's WAL apply suspended), when symbol B's records are deleted from that table and B's new records written, then both symbols' records are stored; given A's write applied before the deletion, the same. Today A's records are lost in the first case: its test is marked as a strict expected failure (`xfail(strict=True, raises=AssertionError)`) until `point-in-time-fundamentals` closes the gap. | STORAGE-S19, FUND-S03 | integration | Missing | `integration/db/io/test_delete.py`: `test_a_deletion_keeps_another_symbol_s_write_that_is_not_applied_yet` (expected to fail), `test_a_deletion_keeps_another_symbol_s_write_once_it_is_applied` |
| MODIFIED | STORAGE-T10 | Given a fundamental record, when a record with the same key (STORAGE-S06) is written, then only the new record is stored; in a statement table, the same key means the same filing date and period end. | STORAGE-S06 | integration | Missing | `integration/db/io/test_insert.py`: `test_a_fundamental_record_with_a_stored_key_replaces_it` (from `test-suite-hardening`) |
| ADDED | STORAGE-T37 | Given two records of one symbol for different periods, filed on the same day (as AAPL's two quarters filed on 2006-12-29) or, for quarterly earnings, reported on the same day, when they are written to a balance sheet, cash flow or income statement table, quarterly or annual, or to the quarterly earnings, then both are stored. | STORAGE-S06 | integration | Missing | `integration/db/io/test_insert.py`: `test_two_periods_filed_on_the_same_day_are_two_records`, one case per table |

### Value semantics of prices

| Change | ID | Test case | Verifies | Level | Status | Implemented by |
| ------ | -- | --------- | -------- | ----- | ------ | -------------- |
| ADDED | PROVIDER-T26 | Given AAPL's end-of-day bars from 2020-08-26 to 2020-09-02 with the demo token, then across the split day of 2020-08-31 the close falls by a factor between 3 and 5, the adjusted close changes by less than 20 %, the volume changes by a factor below 2, and every adjusted close has at most 4 decimals. | PROVIDER-S23 | live | Missing | `live/test_eodhd_semantics.py`: `test_end_of_day_prices_are_as_traded_and_only_the_adjusted_close_is_adjusted` |
| ADDED | PROVIDER-T27 | Given AAPL's minute bars from 2020-08-28 19:57 to 2020-08-31 13:32 UTC with the demo token, then the first bar is at 19:57 and the last at 13:32, every bar has `gmtoffset` 0 and a `datetime` equal to its timestamp in UTC, and the close falls by a factor between 3 and 5 across the split. | PROVIDER-S23 | live | Missing | `live/test_eodhd_semantics.py`: `test_minute_prices_are_as_traded_in_utc_with_both_bounds_included` |

### Performance baseline

| Change | ID | Test case | Verifies | Level | Status | Implemented by |
| ------ | -- | --------- | -------- | ----- | ------ | -------------- |
| ADDED | QUALITY-T10 | Given the faked fetch of QUALITY-S10, run twice, then each run's provider requests, SQL statements, connections, ingestion calls, records written and records rewritten equal `baseline.json`; a different count fails with the recorded and the measured value; run time, peak memory and read time are reported at the end of the run without failing it. | QUALITY-S10 | integration | Missing | `integration/performance/test_baseline.py`: `test_a_fetch_costs_what_the_baseline_records` |

## Missing test cases of `5_test.md` filled

| Test case | Level | Implemented by (planned) |
| --------- | ----- | ------------------------ |
| FUND-T12 | integration | see above (MODIFIED: deterministic, and the case with the pending write marked as a strict expected failure) |

## Tests changed without a change of their test case

| Test | Test case | Change |
| ---- | --------- | ------ |
| `integration/setup/test_main.py`: `test_every_table_is_created_as_its_constants_describe_it` | STORAGE-T04 | compares the deduplication keys as well (`upsertKey` of `table_columns()`), as its test case says; today it compares only the columns, the designated timestamp and WAL |

The unit tests of STORAGE-T05 compare the schema files with the table constants, so they
follow the new keys without a change.

## Changes to `5_test.md` section 1 on merge

- 1.1: the new counts of integration and live tests; `tests/integration/performance/` and its
  summary table; the live tests of value semantics use the demo token only.
- 1.2: a row for the spies of `tests/integration/performance/conftest.py`.
- 1.3: a test case whose test is a strict expected failure is *Implemented*. "Implemented
  by" names the test with "(expected to fail until `<feature>`)", and the test case says what
  happens today.
