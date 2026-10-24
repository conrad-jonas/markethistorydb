# data-integrity-checks: design

## 1 Overview

| Part | Files |
| ---- | ----- |
| deduplication keys | `src/markethistorydb/setup/schema/fundamental.sql` (seven `DEDUP UPSERT KEYS` clauses); `UNIQUE_KEY_COLUMNS` of the six statement tables and of quarterly earnings in `src/markethistorydb/db/tables/fundamental.py` |
| the race, tested | `tests/integration/db/io/test_delete.py` |
| value semantics | `tests/live/test_eodhd_semantics.py` (new) |
| performance baseline | `tests/integration/performance/` (new): `conftest.py`, `test_baseline.py`, `baseline.json` |

The key change is the only change under `src/`.

## 2 The race between a deletion and pending writes

### 2.1 Mechanism

The fundamental tables are WAL tables, written through ILP over HTTP (`4_design.md` 3.4).

1. QuestDB answers an ILP write once the transaction is in the table's write-ahead log: the
   table's `sequencerTxn` counts it.
2. A background job applies it to the table a little later; `writerTxn` catches up.
3. A `SELECT`, and so the `CREATE TABLE <t>_copy AS (SELECT …)` of a deletion (STORAGE-S19),
   reads only applied transactions.
4. `DROP TABLE <t>` removes the table together with its write-ahead log.

So when symbol B's records are deleted from a table while symbol A's write to it is still
pending, the copy lacks A's records, and dropping the table discards the pending write. A's
records are gone without any error.

### 2.2 Measurements (2026-10-23, local test service, QuestDB 10.0.1)

Scratch scripts replaced the sample fundamentals of two symbols one after the other, with no
provider request in between. These runs were evidence for the decision of 2.3. They are
recorded here and not repeated; the suite's lasting check is FUND-T12 (2.4).

| Setup | Attempts | A's records lost |
| ----- | -------- | ---------------- |
| one record set (balance sheet, quarterly): B's deletion directly after A's write | 50 | 50 |
| the same, waiting for `wal_tables()` to show nothing pending before B | 20 | 0 |
| all eight record sets per symbol, in the writer's order | 20 | 0 |
| A's write, then B's deletion through `Insert` and `Delete` directly; state before the deletion: `writerTxn` 0, `sequencerTxn` 1 | 3 | 3 |
| the same with the table's WAL apply suspended (`ALTER TABLE … SUSPEND WAL`) | 3 | 3 |

With all eight record sets, each table gets seven other tables' deletions and writes between
A's write and B's deletion, which gave the apply job enough time in these runs.

### 2.3 When a fetch is exposed

Between symbol A's write to a table and symbol B's deletion in the same table, a fetch does:

- A's work on the tables after it;
- B's price download: one request for daily bars, one to about 67 for minute bars;
- B's fundamentals request;
- B's work on the tables before it.

That is usually longer than the apply job needs. A fetch is exposed when applying slows down,
for example:

- the apply job is busy with large transactions, such as the long minute histories written just
  before;
- the disk is slow, or the database is remote;
- a fundamental table's WAL apply is suspended, e.g. after an apply error. Then every write to
  it stays pending, and each next symbol's deletion discards the previous one's records.

**Decision (2026-10-23):** recorded, not fixed. `point-in-time-fundamentals` (M5) replaces the
deletions by appends and so removes the cause; it isn't moved forward. A fix in between would be
cheap: wait before each copy until `wal_tables()` shows nothing pending for the table, with a
limit, else raise `DbError`. It is written down here in case the risk is judged differently
later.

### 2.4 The test (FUND-T12)

**`SUSPEND WAL`:** `ALTER TABLE <t> SUSPEND WAL` is a QuestDB statement that stops the
background job from applying the table's pending writes, until `RESUME WAL`. The project's code
never uses it; only this test does. It holds A's write in the state "acknowledged but not yet
applied", so the race happens on every run, instead of depending on how fast the machine
applies. Without it, a fast CI runner might apply in time and the test would be flaky. QuestDB
puts a table into the same state by itself after an apply error: `wal_tables()` then shows the
table as *suspended*, the worst case of 2.3.

The test asserts the intended behaviour, and is marked as an expected failure until the
loss is fixed:

1. `setup`, then `ALTER TABLE balance_sheet_quarterly SUSPEND WAL`.
2. Write two records of symbol A with `Insert.table`.
3. `Delete.symbol_from_table` for symbol B, then write B's records.
4. Wait until the table has applied everything (the renamed copy is a new table, not
   suspended).
5. Expect: A and B have two records each. Today A has none, so this assertion fails.

The test is marked `pytest.mark.xfail(strict=True, raises=AssertionError, reason="a deletion
loses another symbol's write that isn't applied yet; point-in-time-fundamentals removes the
deletions")`:

- **Today:** the assertion fails, and the run reports the test as *xfailed* with that reason.
  The closing report (`-ra`, QUALITY-S06) lists it on every run, a visible reminder of the gap.
- **Any other error,** e.g. a QuestDB release without `SUSPEND WAL`, isn't an `AssertionError`,
  so it fails the test as usual instead of hiding behind the mark.
- **Once `point-in-time-fundamentals` removes the deletions,** the assertion holds. Strict mode
  turns the unexpected pass into a failure, and that feature removes the mark. The test then
  guards the fixed behaviour without being rewritten.

A second test waits for the apply between steps 2 and 3 and expects both symbols' records. It
passes today, and shows that the loss is down to the pending write alone.

## 3 Deduplication keys

- **The collision**, in AAPL's fundamentals with the demo token on 2026-10-23:

  | Record set | Records | Filing dates shared by two periods |
  | ---------- | ------- | ---------------------------------- |
  | balance sheet, quarterly | 164 | 2006-12-29 |
  | cash flow, quarterly | 147 | 2006-12-29 |
  | income statement, quarterly | 164 | 2006-12-29 |
  | the three, annual | 41, 37, 41 | none |
  | earnings history (key: report date) | 132 | none (report dates) |

  The two quarters filed on 2006-12-29 have the same key `(symbol_code, exchange_code,
  filing_date)`, so the second replaces the first within the same batch.
- **The change**, in `fundamental.sql` and in the `UNIQUE_KEY_COLUMNS` of the table classes:

  | Tables | Key today | Key after the change |
  | ------ | --------- | -------------------- |
  | the six statement tables | `symbol_code, exchange_code, filing_date` | `symbol_code, exchange_code, filing_date, date` |
  | quarterly earnings | `symbol_code, exchange_code, report_date` | `symbol_code, exchange_code, report_date, date` |
  | annual earnings | `symbol_code, exchange_code, date` | unchanged |

  - The designated timestamps stay as they are.
  - Quarterly earnings has no collision in AAPL's history, but two quarters reported on one day,
    e.g. by a late filer, would collapse just like two filed on one day. It has the period end
    (`date`), so it gets the same fix.
  - Annual earnings is already keyed by its period end, one record per year.
- **Nothing else changes:**
  - the deletion creates its copy with the keys of the table constants (STORAGE-S19), so it
    keeps the new keys;
  - the unit tests of STORAGE-T05 compare the schema files with the constants, and the
    integration test of STORAGE-T04 compares the created tables with them;
  - an amended filing with a new filing date stays a record of its own, as today.
- **Existing databases:** none holds data worth keeping (2026-10-23). `setup` creates the tables
  with the new keys; no migration.
  - Checked on 2026-10-23 for completeness: `ALTER TABLE … DEDUP ENABLE UPSERT KEYS(…)` changes
    the keys of an existing table in place once its WAL has applied the change.
  - The first replacement after the update would rebuild each table with the new keys anyway.

## 4 Value semantics of prices

### 4.1 What eodhd delivers (2026-10-23, demo token)

| Endpoint | Request | Result |
| -------- | ------- | ------ |
| `/eod/AAPL.US` | 2020-08-26 to 2020-09-02 | close 499.23 on 08-28, 129.04 on 08-31 (factor 3.87); adjusted close 120.9557 and 125.0575 (3 %); volume 187.6 and 225.7 million (factor 1.2); adjusted close with 4 decimals |
| `/intraday/AAPL.US`, 1m | 2020-08-28 19:57 to 2020-08-31 13:32 UTC | 552 bars, the first at 19:57, the last at 13:32; close 499.76 at 20:00 on 08-28, 127.13 at 13:30 on 08-31; `gmtoffset` 0, `datetime` the UTC form of `timestamp`; pre- and after-market bars included |

So open, high, low, close and volume are as traded, daily and intraday; only the adjusted close
is adjusted, for splits and dividends: 506.09 / 122.6177 = 4.13 before the split, 4 for the
split and about 3 % for the dividends paid since.

### 4.2 The checks

`tests/live/test_eodhd_semantics.py`, two requests per night with the demo token, so they never
read "not checked" (CI-S09):

- **end-of-day:** across the split day, the close falls by a factor between 3 and 5, the adjusted
  close changes by less than 20 %, the volume changes by a factor below 2, and every adjusted
  close has at most 4 decimals. Split-adjusted prices would change by less than 20 %, and a
  split-adjusted volume by a factor of about 3.
- **intraday:** the first bar is at the requested `from`, the last at `to`; every bar has
  `gmtoffset` 0 and a `datetime` equal to its timestamp in UTC; the close falls by a factor
  between 3 and 5 across the split.

The tolerances hold even though eodhd lowers past adjusted closes a little with every new
dividend.

**Why AAPL and not NVDA** (10:1 on 2024-06-10, as the round-2 roadmap proposed): the demo token
serves AAPL.US, but answers 403 for NVDA.US (checked on 2026-10-23). With NVDA, the checks would
need the account's token, which is refused on most nights.

### 4.3 Consequences

- **DG-4:** its precondition is met; the prices are raw. Adjusting on read with raw bars and
  factors stays open for `corporate-actions`, and corporate actions can be fetched
  incrementally.
- **`price-corrections`:** the overlap check that a split would have triggered "only if prices
  turn out split-adjusted" (round-2 roadmap 2.9) isn't needed.
- **Window boundaries** (`4_design.md` 6.4): eodhd includes both bounds, so the bar at a
  boundary arrives in both windows and is stored once (STORAGE-S05). This answers open
  question 1 of `test-suite-hardening`.

## 5 Performance baseline

### 5.1 The measured fetch

- `tests/integration/performance/test_baseline.py` builds a `Client` on the test database with
  `FakeSeriesApi` (`test-suite-hardening`). A route override answers the symbol list of `USA
  Stocks` with 10 symbols on `NASDAQ`. The fake serves each of them fixed daily and minute
  series and the sample fundamentals.
- **Run 1:** `fetch(symbol_status=ACTIVE, exchange="USA Stocks")` with "now" pinned to day *D*.
  It runs the daily and the minute pass. The minute pass requests each symbol's history from
  2005 in windows, mostly empty.
- **Run 2:** the same with "now" on *D* + 1: per symbol, one new daily bar, the minute bars of
  one more day, and the fundamentals replaced again.

### 5.2 What is counted and measured, per run

| Measure | How | Checked |
| ------- | --- | ------- |
| provider requests | the fake counts them | equal to the baseline |
| SQL statements | a spy on `Query.execute` | equal |
| database connections | a spy on `psycopg.connect` | equal |
| ingestion calls | a spy on `Sender.from_conf` | equal |
| records written | rows of the frames passed to `Insert.table`, plus the reference records | equal |
| records rewritten by deletion copies | before each `Delete.symbol_from_table`, the records of other symbols in the table, read through a connection the spies leave out | equal |
| run time | `time.perf_counter` around `fetch` | reported |
| peak memory | `tracemalloc`, started before `fetch` | reported |
| read time | `client.read.ohlcv` for the 10 symbols, daily and minute | reported |

- The spies wrap public names with `monkeypatch` and change no behaviour (testing rule 6).
- The counts are deterministic: the fake provider answers at once, and no retry happens.
- The records rewritten measure the write amplification of the fundamentals replacement, which
  grows with the table (`4_design.md` 7.4).

### 5.3 The baseline file and the report

- `baseline.json` holds both runs' counts, times and memory, plus the date, the machine and the
  QuestDB version they were recorded with.
- **Counts are checked exactly, in both directions.** A count that differs from the file
  fails the test, whether it went up or down. The message names the measure, the run, the
  recorded and the measured value, e.g. "run 1, connections: recorded 412, measured 1"
  (illustrative numbers).
- **What a pull request that changes a count does:** the author checks that the change is
  intended, reruns with `UPDATE_BASELINE=1 uv run pytest tests/integration/performance`, which
  rewrites the file with the measured values, and commits it. The reviewer then sees the cost
  change as a diff of `baseline.json`. Examples:
  - an intended improvement: `connection-reuse` lowers the connections, `ingestion-efficiency`
    the minute requests;
  - an accidental regression: a change that adds one SQL statement per symbol, which then shows
    as 10 more statements per run, and must be fixed or deliberately accepted.
- **Why not fail on increases only:** improvements would then pass without updating the
  file, so the recorded values would drift above the real ones. A later regression could hide in
  that slack, and the file would no longer say what a fetch costs.
- **Which changes touch it:** only changes to the fetch and write paths alter a count, and
  the features that make them (`connection-reuse`, `ingestion-efficiency`, `ingestion-scale`,
  `point-in-time-fundamentals`) exist to change exactly these numbers.
- A `pytest_terminal_summary` hook in the directory's `conftest.py` prints a table at the end
  of any run that includes the test: measure, recorded, measured, change. In CI the table is in
  the log of the *integration* job.
- **Times and memory are never checked.** They depend on the machine and vary between runs
  on the same machine, so any threshold would make the test flaky. They show the trend on one
  machine, and an order of magnitude elsewhere.
- **Run time of the test itself:** about 20 s locally, estimated from the integration tests
  of RUNS (3 symbols in 1 s, two runs in 5 s). It runs in the *integration* job of every pull
  request, whose 73 tests take about 35 s today. The limit of 120 s per integration test
  (QUALITY-S08) applies.

## 6 Not done

| Item | Where | Why |
| ---- | ----- | --- |
| A fix for the race | `point-in-time-fundamentals` (M5), which removes the deletions | decided on 2026-10-23: recorded only (section 2.3) |
| The check for reused tickers in eodhd's lists | `listings-and-universe` | decided on 2026-10-23: that feature gives instruments an identity beyond code and venue anyway |
| A measurement against the real provider | nowhere: dropped on 2026-10-23 | the synthetic baseline is repeatable and checkable; a real run is neither, and spends calls |
| Performance targets | `release-1-0` | QA-13 asks for a baseline and regression checks; targets come with the release |
| Value semantics of fundamentals | nowhere for now; `provider-interface` maps fields to concepts | the code stores them as received and relies on none of them |
| Read throughput at scale | `query-layer`, `ingestion-scale` | the read time of 10 symbols is a trend, not a throughput figure |

## 7 Decisions

| Decision | Choice | Reason |
| -------- | ------ | ------ |
| The race | recorded; not fixed; `point-in-time-fundamentals` not moved forward | decided on 2026-10-23 |
| FUND-T12 | the intended behaviour, marked as a strict expected failure | decided on 2026-10-23: reported on every run, and it needs no rewrite once fixed (section 2.4) |
| Deduplication keys | the period end joins the keys of the six statement tables and of quarterly earnings | the collision is real for the statement tables and possible for quarterly earnings (section 3); the cheap fix the gap row named |
| Existing databases | no migration | decided on 2026-10-23: no data worth keeping |
| Value semantics | live checks with the demo token against AAPL's 4:1 split of 2020-08-31 | run every night regardless of the account; the demo token refuses NVDA |
| DG-4 precondition | met: prices are raw | section 4.1 |
| Baseline | synthetic: a faked fetch against the test database, counts checked, times reported | decided on 2026-10-23: repeatable, free, and a count change shows in the pull request that causes it |
| Reused tickers | left to `listings-and-universe` | decided on 2026-10-23 |

The decisions are recorded in `6_roadmap.md` in stage 4.

## 8 Implementation

| # | Issue | Covers |
| - | ----- | ------ |
| 1 | The keys of the seven tables; the test of two periods reported or filed on one day; STORAGE-T10's test updated | STORAGE-S06, T10, T37 |
| 2 | The race: FUND-T12's two tests, one marked as a strict expected failure | STORAGE-S19, FUND-T12 |
| 3 | The live checks of value semantics | PROVIDER-S23, T26, T27 |
| 4 | The performance baseline: spies, `baseline.json`, the summary hook; the merge into the global files | QUALITY-S10, T10 |

Issue 4 needs `FakeSeriesApi` from `test-suite-hardening`; issues 1 to 3 need only the test
database and the demo token.

## 9 Open questions

1. **`SUSPEND WAL` in later QuestDB releases:** it works on 10.0.1 (checked on 2026-10-23).
   Whether newer releases keep it shows in the nightly run against the newest release (CI-S10).
   Without it, FUND-T12 would fall back to the timing of section 2.2, which lost the record in
   every attempt.
2. **Demo token coverage:** if eodhd stops serving AAPL's 2020 history to the demo token, the
   checks of section 4.2 fail at night, and need another instrument or the account's token.

## 10 Changes to `4_design.md` on merge

- 2.1 (tables): the deduplication keys of the six statement tables and of quarterly earnings.
- 3.7 (deletion): the race of section 2.1, with a pointer to its gap row.
- 4.6 (payloads): the value semantics of section 4.1.
- 6.4 (windows): "If the provider includes both bounds" becomes "The provider includes both
  bounds (PROVIDER-S23)".
- 7.4 (replacement): "Not atomic" gains the race.
- 5.4 (reference writes): the numbers of the baseline replace the illustration.
- 15 (QUALITY): the baseline in the table of guarantees, with the recorded numbers of
  `baseline.json`.
- Appendix A, the decision on deletions: the consequence gains the race.
- No row of "Known limitations" is removed.
