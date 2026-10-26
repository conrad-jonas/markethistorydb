# test-suite-hardening: specification changes

State: Ready · Milestone: M0, second feature · Kind: change (QUALITY; test cases of most
chapters) · Requirements: QA-5, QA-6, COR-4, COR-5 · Depends on: `continuous-integration` ·
Decisions: taken on 2026-10-22 and 2026-10-23 (`2_design.md`, section 6)

## Why

The suite enforces none of its own rules. An unknown marker passes silently, a new warning
scrolls by, a hanging test blocks the run, nothing notices a unit test that reaches the network,
and a plain `pytest` spends calls of the account. Two needs that the code meets are verified by
no test: that data read back equals the data written (COR-4), and that runs one after the other
leave no gap and no duplicate (COR-5). And 12 of the 21 Missing test cases of `5_test.md` check
behaviour that stays as it is. M0 is the safety net for the refactorings of M2
(`testable-core`), so these come first.

## Scope

**In:**

- the pytest configuration: live tests opt-in; strict markers, configuration, `xfail` and
  parametrisation IDs; warnings as errors, with named exceptions; a time limit per test; no
  network in unit tests;
- shared test support: builders for test data, a faked provider that serves a price series by
  period, one call log shared by the interfaces of `FakeDb`, a query fake that fails at a chosen
  statement;
- `fresh_db` drops the tables that `setup` doesn't create;
- new test cases: the round trip of bars (COR-4); incremental and interrupted runs (COR-5); a
  fetch of all four passes against the database; the command line in-process against the test
  database;
- the 12 Missing test cases whose behaviour stays (`3_test.md`, "Missing test cases filled");
- the README's section on the tests.

**Out:**

- **Faster resets** of the integration tables (schema once per session, tables truncated before
  each test): dropped on 2026-10-22. `setup` takes 19.8 s of the 35 s integration run (73 tests,
  local test service). In CI the integration job runs alongside the longer unit jobs, so the gain
  would be mostly local, while truncating WAL tables needs waits for the truncation to apply and a
  second path for the tests that change the schema.
- **Missing test cases whose behaviour a later feature changes.** Each becomes a MODIFIED test
  case of that feature, written against the new behaviour: PRICES-T12, FUND-T03, RUNS-T05
  (`ingestion-efficiency`), CLI-T03 (`publishing-readiness`), ACCESS-T10 (`query-layer`). The
  other Missing cases have their feature already: FUND-T12 (`data-integrity-checks`), CLIENT-T11
  (`library-contract`), PACKAGING-T01 and T03 (`continuous-integration`, CI-T05).
- **A local smoke test of the installed console script.** CI-T05 runs the installed command from
  the built wheel on every pull request. A subprocess test in the development environment would
  add little, and once past the argument parsing it would load the repository's `.env` (CLI-S02)
  and reach the application's database.
- **The fix for a daily bar without volume** (found while writing this feature; known gap added
  below): `code-hygiene`, next to the other fix for COR-4 there.
- **The trace script in `scripts/` and `spec` markers on the tests** (`1_constitution.md` 6.6):
  a feature of its own, entered in stage 4.
- **Test doubles checked against their interfaces, seams instead of patched private names**
  (QA-12; testing rules 4 and 6): `testable-core`.

## Specification changes

### Rules of the suite

| Change | ID | Specification | Satisfies |
| ------ | -- | ------------- | --------- |
| ADDED | QUALITY-S05 | **Live tests opt-in:** `pytest` without `-m` runs the unit and integration tests and leaves the live tests out; they run only when `-m` selects them, e.g. `-m live`. A run that names only live test files without such a `-m` runs no test and ends with exit code 5. | QA-6 |
| ADDED | QUALITY-S06 | **Strict collection:** an unknown marker, an unknown configuration key or two parameter sets of one test with the same ID end the run with an error before any test runs; an `xfail` test that passes fails. The closing report lists every test that did not pass, with its reason. | QA-5 |
| ADDED | QUALITY-S07 | **Warnings:** a warning raised during a test, or during the setup or teardown of its fixtures, fails it. The configuration names each exception with the warning's class, a pattern of its message and the feature that removes it. Today it holds one: QuestDB's `UserWarning` "Detected a burst of reconnections", until `connection-reuse`. A test that raises a warning on purpose allows it itself. | QA-5 |
| ADDED | QUALITY-S08 | **Time limit:** a test that runs longer than its level's limit, its fixtures included, is stopped, and the output names the test and shows where it hung. The limits are 30 s for unit tests, 120 s for integration tests (the first one also starts the container of CI-S11) and 300 s for live tests. On Linux the test counts as failed and the run goes on; on Windows, where only the whole process can be ended, the run stops there with a non-zero exit code. A test that needs longer declares its own limit, with the reason. | QA-5 |
| ADDED | QUALITY-S09 | **No network in unit tests:** a unit test that creates a network socket fails at that point, with an error saying so; integration and live tests may connect. Processes a test starts are not covered. | QA-5 |

### Integration database and tools

| Change | ID | Specification | Satisfies |
| ------ | -- | ------------- | --------- |
| MODIFIED | QUALITY-S04 | Every integration test starts on exactly the tables `setup` creates, all empty, which it sets up itself: tables `setup` doesn't create, such as the copy left by an interrupted deletion (STORAGE-S20), are dropped first. The instance is the container of CI-S11 or the one named by the override. (Builds on the text of `continuous-integration`.) | QA-7 |
| MODIFIED | PACKAGING-S03 | `uv sync` installs it for development, together with the development tools: pytest with the plugins pytest-cov, pytest-timeout and pytest-socket, ruff and pyright. `pip install .` installs it as a package. The README says so. (pyright comes with `continuous-integration`.) | DIST-1, DIST-6 |

### Data read back and series across runs

| Change | ID | Specification | Satisfies |
| ------ | -- | ------------- | --------- |
| ADDED | STORAGE-S22 | **Round trip of bars:** bars written to the daily or minute table and read back with `Read.ohlcv` (ACCESS-S04) equal the written frame, once both are indexed by symbol code and timestamp and sorted. They have the same values; the codes come back as strings, prices and the minute volume as `float64`, the daily volume as `int64`, and timestamps as naive datetimes at microsecond resolution (`datetime64[us]`, the resolution QuestDB stores), in UTC (COR-10); a missing price or minute volume comes back as NaN. The order of the rows read back is not specified (`query-layer` defines one). | COR-4 |
| ADDED | PRICES-S09 | **Series across runs:** the bars stored for a symbol by several runs hold each bar of the provider's series up to the end of the period last requested for it, exactly once: no gap and no duplicate at the boundaries between runs or between the windows of a run. This holds for runs that are incremental (PRICES-S01, S02), ended between symbols (RUNS-S07, S08) or failed in one of the symbol's minute windows (PRICES-S08), as long as the provider doesn't change bars it has delivered (COR-12, `price-corrections`). | COR-5 |

## Requirement status after the merge

| Requirement | Before | After |
| ----------- | ------ | ----- |
| QA-5 | Open | Done |
| QA-6 | Open | Done |
| COR-4 | Partial | Partial: verified for bars (STORAGE-S22), reference records and fundamentals; an update stores NaN instead of NULL, and a daily bar without volume can't be stored (`code-hygiene`) |
| COR-5 | Partial | Done |

## Known gaps closed

| `3_specs.md` | Gap |
| ------------ | --- |
| 4.3 PRICES | Not verified: two incremental minute runs leave no gap and no duplicate at the boundary |
| 13.2 QUALITY | Unknown markers, new warnings, hanging tests and unit tests that use the network don't fail the run |
| 13.2 QUALITY | Live tests run by default and spend the account's calls |

## Known gaps added

| `3_specs.md` | Gap | Requirement | Closed by |
| ------------ | --- | ----------- | --------- |
| 4.3 PRICES | A daily bar without volume can't be stored: the frame's volume becomes floating-point, the write fails with `SchemaMismatchError` (FLOAT to LONG), and the symbol's new bars are lost for that run. Found on 2026-10-22 against the test database; whether eodhd sends such bars is not known. | COR-4 | `code-hygiene` |
