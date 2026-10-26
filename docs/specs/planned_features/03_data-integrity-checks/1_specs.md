# data-integrity-checks: specification changes

State: Ready · Milestone: M0, third feature · Kind: change (STORAGE, PROVIDER, QUALITY) ·
Requirements: COR-1, COR-17, QA-13 · Depends on: `continuous-integration`,
`test-suite-hardening` · Decisions: taken on 2026-10-23 (`2_design.md`, section 7)

## Why

Three suspicions about the stored data were never checked, and the plan depends on their
answers. Could back-to-back replacements of fundamentals lose records? Do two periods filed on
one day collapse into one record? Are eodhd's prices raw or split-adjusted? The adjustment
method of `corporate-actions` (DG-4) depends on the last answer. Later features also promise
fewer requests, statements and connections, and without a baseline nobody could tell whether
they deliver.

The checks were run on 2026-10-23 while this feature was written (`2_design.md`, sections 2 to
4):

- **The race is real.** A deletion loses another instrument's write to the same table that
  QuestDB has acknowledged but not yet applied. It happened in 50 of 50 attempts when the
  deletion followed the write directly, and in 0 of 20 with a wait in between.
- **The collision is real.** AAPL has two quarters filed on 2006-12-29 in the balance sheet,
  cash flow and income statement, so one of them is lost in each table.
- **eodhd's prices are raw.** Open, high, low, close and volume are as traded, daily and
  intraday; only the adjusted close is adjusted.

This feature pins these answers in the specification and in tests. It fixes the collision,
records the race without fixing it (decided on 2026-10-23), and adds the baseline.

## Scope

**In:**

- the period end in the deduplication keys of the six financial statement tables and of
  quarterly earnings;
- the race, stated in the specification and tested deterministically, as an expected failure;
- live checks of the value semantics of prices, nightly with the public demo token;
- a performance baseline: a faked fetch against the test database whose counts are checked
  for regressions, and whose times and memory are reported.

**Out:**

- **A fix for the race:** decided on 2026-10-23 to record it only and accept the risk until
  `point-in-time-fundamentals` (M5) removes the deletions. That feature isn't moved forward.
  `2_design.md` 2.3 describes when a fetch is exposed.
- **The check of eodhd's lists for reused tickers:** decided on 2026-10-23 to leave it to
  `listings-and-universe`, which gives instruments an identity beyond code and venue anyway.
- **A measurement against the real provider:** decided on 2026-10-23, the baseline is synthetic
  only (`2_design.md` 5).
- **Performance targets:** `release-1-0`.
- **Value semantics of fundamentals** (units, currencies, restatements): the code stores them as
  received and relies on none of them. No feature takes them up until `provider-interface` maps
  fields to concepts.
- **The dependency audit and mutation testing,** which the shared gap row of `3_specs.md` 13.2
  also names: `continuous-integration` (QA-11) and `release-1-0` (QA-15). The backlog's
  requirement list for this feature named QA-11, QA-15 and COR-2. COR-2, the failed write after
  the deletion, stays with `point-in-time-fundamentals`.
- **Existing databases:** none holds data worth keeping (2026-10-23), so the key change needs no
  migration. `setup` creates the tables with the new keys.

## Specification changes

### Stored fundamentals

| Change | ID | Specification | Satisfies |
| ------ | -- | ------------- | --------- |
| MODIFIED | STORAGE-S06 | **Fundamentals:** eight tables, one per statement (earnings, balance sheet, cash flow, income statement) and period type (quarterly, annual). A record is keyed by symbol code, exchange code and its dates: the report date together with the period end (`date`) for quarterly earnings, the period end for annual earnings, and the filing date together with the period end for the other six tables, so that two periods reported or filed on the same day are two records. Its other columns hold the provider's fields under snake_case names. Writing a record whose key is stored already replaces the stored record. | MKT-7, BT-8, COR-1 |
| MODIFIED | STORAGE-S19 | When an instrument's fundamentals are replaced (FUND), its records are deleted from a fundamental table by copying every other record into `<table>_copy`, dropping the table and renaming the copy to the table's name. The copy keeps the designated timestamp, the partitioning, WAL and the deduplication keys. **The copy holds only the writes QuestDB has applied to the table.** Records of another instrument that QuestDB has acknowledged but not yet applied are not copied, and are lost when the table is dropped. The steps are separate statements: if one fails, `QueryError` is raised and the earlier steps stay applied. A deletion request for a table outside the symbol, fundamental and price tables does nothing. (Deleting from the symbol and price tables is implemented as well, but nothing uses it: `4_design.md`, section 3.8.) | MKT-7 |

### Value semantics of prices

| Change | ID | Specification | Satisfies |
| ------ | -- | ------------- | --------- |
| ADDED | PROVIDER-S23 | **Value semantics:** live contract checks use the public demo token against AAPL.US around its 4:1 split of 2020-08-31. They verify what the code and the planned features rely on:<br>• end-of-day open, high, low, close and volume are as traded, not adjusted for splits;<br>• the adjusted close is adjusted for splits and dividends, with at most 4 decimals;<br>• intraday bars are as traded, with timestamps in Unix seconds UTC and `gmtoffset` 0;<br>• an intraday request returns the bars at both of its bounds.<br>They run nightly (CI-S08), whatever the state of the account. | COR-17 |

### Performance baseline

| Change | ID | Specification | Satisfies |
| ------ | -- | ------------- | --------- |
| ADDED | QUALITY-S10 | **Performance baseline:** an integration test runs the daily and the minute pass of active symbols for 10 faked symbols of one exchange against the test database, twice: a first run, then an incremental one a day later. Per run it counts the provider requests, SQL statements, database connections, ingestion calls, records written and records rewritten by deletion copies. It also measures the run time, the peak memory of the Python process and the time to read the stored bars back. The counts must equal those in `tests/integration/performance/baseline.json`. A difference fails the test and shows both values, so a change that alters a count updates the file in the same pull request. Times and memory are reported next to their recorded values at the end of the test run, without failing it. | QA-13 |

## Requirement status after the merge

| Requirement | Before | After |
| ----------- | ------ | ----- |
| COR-1 | Partial | Partial: a deletion loses another instrument's write that isn't applied yet (reproduced; `point-in-time-fundamentals`); periods reported or filed on the same day are kept apart |
| COR-17 | Partial | Done, with the nightly runs of `continuous-integration`: fields, types and the value semantics of prices are checked every night |
| QA-13 | Open | Partial: counts are checked for regressions; run time, memory and read time are measured but not checked; no targets (`release-1-0`) |

## Known gaps closed

| `3_specs.md` | Gap |
| ------------ | --- |
| 1.7 STORAGE | Two fundamental periods filed on the same day collapse into one record (STORAGE-S06) |
| 2.6 PROVIDER | The contract checks cover fields and types, not value semantics (e.g. whether open, high, low and close are split-adjusted) |
| 13.2 QUALITY | No performance baseline: a regression in requests, statements or run time goes unnoticed |

## Known gaps changed

| `3_specs.md` | Today | After the merge | Requirement | Closed by |
| ------------ | ----- | --------------- | ----------- | --------- |
| 1.7 STORAGE | Back-to-back replacements of two instruments' fundamentals may lose a write (suspected WAL race, not reproduced) | A deletion loses another instrument's write to the same table that QuestDB has acknowledged but not yet applied (STORAGE-S19). A replacement right after another instrument's write to that table loses it. Reproduced on 2026-10-23: always when the deletion followed the write directly, never with a wait in between | COR-1 | `point-in-time-fundamentals` (no deletes) |
