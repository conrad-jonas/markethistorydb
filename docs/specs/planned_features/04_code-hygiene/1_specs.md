# code-hygiene: specification changes

State: Ready · Milestone: M0, fourth feature · Kind: change (STORAGE, PROVIDER, PRICES, FUND,
QUALITY, CI) · Requirements: COR-4, COR-12, OPS-2, QA-14 · Depends on:
`continuous-integration`; builds on the text of `test-suite-hardening` (STORAGE-S22, T36) and
`data-integrity-checks` (STORAGE-S19) · Decisions: taken on 2026-10-24 (`2_design.md`, section 11)

## Why

The code carries leftovers that make it harder to read and to trust:

- 24 files start with a shebang naming a Python that doesn't exist (`python12.9`);
- attributes are camelCase, and log calls format their messages even when nothing is logged;
- deletion paths and statements that nothing calls are kept alive by their own tests;
- ruff runs with no configuration and reports 474 findings with its defaults.

Six small defects are known as well:

- an update stores "not a number" instead of NULL;
- a changed ISIN is never stored;
- a daily bar without volume can't be stored;
- a deletion request for an unknown table is ignored;
- an up-to-date symbol is logged as having no data;
- every request to eodhd opens a new connection.

The refactorings of M2 are easier on clean code, and `continuous-integration` waits for this
feature to make *lint* required.

Checked on 2026-10-24 while this feature was written (`2_design.md`, sections 5 and 8):

- **eodhd sends 0, not null, for a missing volume:** none of 63,214 daily bars of 7 instruments
  (demo token) had a null volume, while EURUSD had 6,578 zero volumes. The fix for a bar without
  volume is defensive.
- **A `DOUBLE` column takes the integer volumes as they come** and stores a missing one as NULL.
  A nullable integer would need pyarrow, which the QuestDB client requires for such columns.
- **eodhd keeps connections alive:** a request on a reused connection took 170 to 410 ms, one on
  a new connection 700 to 1,170 ms.

## Scope

**In:**

- ruff configured (rules, target version, line length 120) and its findings fixed in `src/` and
  `tests/`; the code formatted with `ruff format`; *lint* required in CI;
- by hand, where the rules don't reach: shebangs removed, camelCase attributes renamed to
  snake_case, log calls with lazy arguments;
- unused code removed: the deletion paths of the symbol and price tables with their tests, the
  unused statements (`SELECT_SCHEMA`, `SELECT_CLOSE_FROM_*`, the eight `SELECT_ALL_FROM_*` of the
  fundamental tables), the `DUMMY_*` constants and the `*TableType` aliases;
  `TABLES_NAMES_EXCHANGE` renamed to `TABLE_NAMES_EXCHANGE`;
- small fixes:
  - updates convert values as inserts do (NULL instead of NaN) and report a failure as
    `InsertError`;
  - the symbol update stores the ISIN;
  - the daily volume is floating-point, so a bar without volume is stored;
  - a deletion request for a table other than a fundamental one raises;
  - an up-to-date symbol is logged as such;
  - field names of fundamentals are converted once;
  - the requests of one fetch share one HTTP session;
- two small deduplications: one mapping from time frame to price table for `Read` and `Insert`,
  and one constant for `exchange_url_code`.

**Out:**

- **`__all__`** and the type checker made required: `library-contract`. Until `__all__` exists,
  unused imports are allowed in `__init__.py` files, which re-export the package's names
  (decided on 2026-10-24).
- **The security rules (`S`):** `secret-redaction-hardening` (QA-11).
- **Reusing database connections**, and `Client.close()`: `connection-reuse`, `library-contract`.
  The HTTP session lives within one fetch, so the client holds nothing between fetches.
- **The symbol as an argument of the fundamentals writer** (`set_symbol_code`), and the
  time-frame branches of the request, download and write classes: `testable-core`
  (`4_design.md` 6.7, 7.5).
- **`ErrorCode` moved to `cli.py`, a real setup prompt, `--yes`:** `library-contract`.
- **Import rules:** `target-architecture`.
- **Existing databases:** none holds data worth keeping, so the changed volume column needs no
  migration. `setup` creates the table with the new type.

## Specification changes

### Stored data and writing

| Change | ID | Specification | Satisfies |
| ------ | -- | ------------- | --------- |
| MODIFIED | STORAGE-S04 | **Daily bars** (`daily_ohlcv`): one record per timestamp, exchange code and symbol code, holding open, high, low, close, adjusted close and volume as floating-point numbers; a missing value, e.g. a bar without volume, is stored as NULL. Writing a record whose key is stored already replaces the stored record. | MKT-5, COR-1, COR-4, COR-5 |
| MODIFIED | STORAGE-S11 | Updating a reference record overwrites its columns except the key: every other column of an exchange (addressed by its exchange code), of a symbol (name, country, currency, type and ISIN; addressed by its four key columns) and of a sector (addressed by symbol code and exchange code). Values are converted as for an insert (STORAGE-S10): a missing value is stored as NULL, numpy values as plain values. | MKT-8, COR-4, COR-12 |
| MODIFIED | STORAGE-S15 | A reference record the database rejects, when it is inserted or updated, raises `InsertError`, without retrying. | LIB-4 |
| MODIFIED | STORAGE-S22 | **Round trip of bars:** bars written to the daily or minute table and read back with `Read.ohlcv` (ACCESS-S04) equal the written frame, once both are indexed by symbol code and timestamp and sorted. They have the same values; the codes come back as strings, prices and volumes as `float64`, and timestamps as naive datetimes at microsecond resolution (`datetime64[us]`, the resolution QuestDB stores), in UTC (COR-10); a missing price or volume comes back as NaN. The order of the rows read back is not specified (`query-layer` defines one). | COR-4 |

### Deleting an instrument's records

| Change | ID | Specification | Satisfies |
| ------ | -- | ------------- | --------- |
| MODIFIED | STORAGE-S19 | When an instrument's fundamentals are replaced (FUND), its records are deleted from a fundamental table by copying every other record into `<table>_copy`, dropping the table and renaming the copy to the table's name. The copy keeps the designated timestamp, the partitioning, WAL and the deduplication keys. **The copy holds only the writes QuestDB has applied to the table.** Records of another instrument that QuestDB has acknowledged but not yet applied are not copied, and are lost when the table is dropped. The steps are separate statements: if one fails, `QueryError` is raised and the earlier steps stay applied. A deletion request for any other table raises `ValueError` naming the table, before any statement runs. | MKT-7, COR-3 |

### Requests

| Change | ID | Specification | Satisfies |
| ------ | -- | ------------- | --------- |
| ADDED | PROVIDER-S24 | **One HTTP session per fetch:** all requests of one `Client.fetch` go through one HTTP session, which keeps its connections to eodhd.com open between requests and across the passes. The session is closed when the fetch ends, also when it ends with an error. A request class used without a session, e.g. by the live contract checks, opens a connection per request. | OPS-2 |

### Prices and fundamentals

| Change | ID | Specification | Satisfies |
| ------ | -- | ------------- | --------- |
| MODIFIED | PRICES-S07 | **No new bars:** if a symbol has no stored bars of the time frame and the provider has none for the requested period, the log says "No data exists for symbol AAPL (NASDAQ, DAILY, ACTIVE)". If it has stored bars and the provider has no newer ones, or the minute data already reaches the current day, the log says "Symbol AAPL (NASDAQ, DAILY, ACTIVE) is up to date: newest bar 2024-03-05 00:00:00". In both cases nothing is written. If every bar is from before 1970, only the warning of PRICES-S05 is logged and nothing is written. | ING-6 |
| MODIFIED | FUND-S04 | **Conversion:** the symbol code and exchange code (the venue) are added to the records, whose field names arrive in snake_case (PROVIDER-S20). The dates (`report_date`, `date`, `filing_date`) become datetimes; the text fields (`symbol_code`, `exchange_code`, `before_after_market`, `currency`, `currency_symbol`) stay strings; every other field becomes a floating-point number. The provider sends amounts as strings (e.g. `"383266000000.00"`); a value that is no number or no date (e.g. `"n/a"`, an empty string) is stored as NULL. The caller's records are not modified. | MKT-7, COR-4 |

### Lint and format

| Change | ID | Specification | Satisfies |
| ------ | -- | ------------- | --------- |
| ADDED | QUALITY-S11 | **Lint and format:** `ruff check` and `ruff format --check` pass on `src/` and `tests/` with the configuration in `pyproject.toml`: Python 3.12 as target, a line length of 120, ruff's default rules plus naming (`N`) and logging calls (`G`: values are passed as arguments, formatted only when a record is emitted). The date and time rules (`DTZ`) are off, since naive datetimes mean UTC (COR-10). Unused imports are allowed in `__init__.py` files until these declare `__all__` (`library-contract`). No file starts with a shebang. | QA-14, QA-4 |
| MODIFIED | CI-S03 | Every pull request and every push to `main` runs these jobs; a newer push to the same branch cancels the run still going. **Required:** <br>• *unit*: `pytest -m unit --cov` on Linux and on Windows, each with Python 3.12 and the newest stable Python release, with the coverage gate of QUALITY-S02; <br>• *integration*: `pytest -m integration` on Linux with Python 3.12, against a QuestDB container (CI-S11); <br>• *build*: CI-S04; <br>• *audit*: CI-S05; <br>• *lint*: `ruff check` and `ruff format --check` (QUALITY-S11), with the findings also shown as annotations of the pull request. <br>**Reporting only:** *types* (`pyright`), whose findings appear as annotations of the pull request without failing it. | QA-4, QA-2, QA-7, QA-14 |

## Requirement status after the merge

| Requirement | Before | After |
| ----------- | ------ | ----- |
| COR-3 | Partial | Partial: the command line asks for confirmation; the library's setup always deletes everything (`library-contract`); a deletion request for a table other than a fundamental one is refused |
| COR-4 | Partial | Done: verified for bars (STORAGE-S22), reference records and fundamentals; updates store NULL, and a daily bar without volume is stored |
| COR-12 | Open | Partial: corrections to reference data, the ISIN now included, and to fundamentals reach the stored data on every run; past bars are never requested again (`price-corrections`); no configurable time |
| ING-6 | Partial | Partial: the log tells a symbol without data from an up-to-date one; the run summary still counts an up-to-date symbol as downloaded (`library-contract`) |
| OPS-2 | Open | Partial: the provider connections are reused within a fetch; the database connections are still opened per statement and per ingestion call (`connection-reuse`) |
| QA-4 | Partial | Partial: tests, build, audit and lint block a merge; types only report (`library-contract`); architecture rules aren't checked (`target-architecture`) |
| QA-14 | Open | Done: ruff configured and enforced, naming and logging rules included; the known unused code removed |

## Known gaps closed

| `3_specs.md` | Gap |
| ------------ | --- |
| 1.7 STORAGE | An update stores "not a number" instead of NULL (STORAGE-S11) |
| 1.7 STORAGE | A deletion request for an unknown table is ignored silently (STORAGE-S19) |
| 2.6 PROVIDER | A new HTTP connection per request (no shared session) |
| 3.4 REFDATA | A changed ISIN is never stored: the symbol update leaves it at its first value (STORAGE-S11) |
| 4.3 PRICES | The log says "No data exists" also for a symbol that is merely up to date |
| 4.3 PRICES | A daily bar without volume can't be stored … (added by `test-suite-hardening`) |
| 13.2 QUALITY | ruff isn't configured or enforced |
