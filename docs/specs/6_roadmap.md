# MarketHistoryDB: roadmap

The milestones and the order of the planned features, the decision gates, and the settled
decisions that no other document records (`1_constitution.md`, section 6.1).

- **Changes:** a new feature enters section 2 as Planned (`1_constitution.md`, section 6.3,
  step 2). Before a milestone is written, the rows of all remaining milestones are reviewed
  (section 6.3). A merged feature gets its merge date, and its decision gates are settled
  (section 6.4, step 5).
- **Trace script:** `scripts/trace.py`, which `traceability` brings, takes the planned features,
  their order and their requirements from the table of section 2, and the decision gates and
  settled decisions from the first cell of the rows of sections 3 and 4. A requirement in a row
  counts as assigned to that row's feature; for one that no specification item satisfies yet,
  the row is its only link.
- **IDs:** milestones `M<n>`, decision gates `DG-<n>`, settled decisions `DEC-<n>`
  (`1_constitution.md`, section 6.5). Numbers missing from sections 3 and 4 are retired: their
  decisions are recorded in another document or were withdrawn. They are not reused.

---

## 1 Milestones

The milestones are written and implemented one at a time, in this order (`1_constitution.md`,
section 6.3).

| Milestone | Name | Goal |
| --------- | ---- | ---- |
| M0 | Safety net | Checks that catch regressions before the code changes further: CI on GitHub, a hardened test suite, checks of data integrity, clean code, no secrets in logs or URLs, and traceability checked in CI. |
| M1 | Library contract and publishing | A public API, a safe setup and packaging that meet the usual standards of a Python library, ready to publish. It comes before the large refactorings, so that CI and the public contract are in place before code moves. |
| M2 | Seams and ingestion quick wins | A pure core with injected collaborators, one database session per run and one settings model, which the target architecture builds on; with them, the cheap gains in ingestion: fewer requests, bulk writes. |
| M3 | Target architecture | The code in the target layout of `1_constitution.md`, section 4: the canonical model, the provider interface with the eodhd adapter, and table definitions in code, on which the read side and the new data build. |
| M4 | Read side | Query functions and a REST API for reading the raw data, with canonical names from the start, so that the backtester reads over REST early and M5 extends the API without breaking it. |
| M5 | Backtest-grade data | What a backtest needs beyond raw bars: survivorship-free universes, adjusted prices and point-in-time fundamentals, with run history, data-quality findings and price corrections; built on the model of M3 and read through M4. |
| M6 | Fetch jobs and ingestion scale | Fetch runs started and watched over REST and carried out by a worker, with concurrent requests, backfills and raw landing; built on the REST API of M4 and the run tracking of M5. |
| M7 | Metrics and screens | Metrics, indicators and screens, computed from the adjusted prices and point-in-time fundamentals of M5. |
| M8 | 1.0 release | Cloud readiness reviewed, the user guide complete, performance targets and a security review; as the very last step, the first release on PyPI. |

**Exit criterion of every milestone:** all its features are Merged, the required checks pass on
`main`, `scripts/trace.py --check` passes, and the README and the user documentation describe
the behaviour as it is.

---

## 2 Planned features

The planned features in roadmap order. `#` is a feature's position and the number of its folder
`planned_features/<nn>_<feature>/` (`1_constitution.md`, sections 6.3 and 6.5); the states are
those of section 6.3.

- **A Planned feature** has a full row. Its requirements are those it works on: those of the
  known gaps of `3_specs.md` naming it, and those assigned to it when it was planned. Writing the
  feature may add or drop some.
- **A written feature** (Draft or later) keeps its position, milestone, name, state and the
  requirements of its header. Its files hold kind, scope and dependencies, so its row shows "—"
  there.

| # | Milestone | Feature | Kind | State | Scope | Requirements | Depends on |
| - | --------- | ------- | ---- | ----- | ----- | ------------ | ---------- |
| 1 | M0 | `continuous-integration` | — | Ready | — | QA-4, QA-7, QA-11 | — |
| 2 | M0 | `test-suite-hardening` | — | Ready | — | COR-5, QA-5, QA-6 | — |
| 3 | M0 | `data-integrity-checks` | — | Ready | — | COR-17, QA-13 | — |
| 4 | M0 | `code-hygiene` | — | Ready | — | COR-4, COR-12, OPS-2, QA-14 | — |
| 5 | M0 | `secret-redaction-hardening` | — | Ready | — | QA-8, QA-11 | — |
| 6 | M0 | `traceability` | — | Ready | — | QA-16 | — |
| 7 | M1 | `library-contract` | change | Planned | `__all__`, `__version__`, `py.typed`; docstrings of the public API, *types* required in CI; rejection of timezone-aware datetimes; safe setup (`ensure_schema`, `setup(force)`, CLI `--force`/`--yes`, a declined setup no longer exits 0); check of the server setting `line.auto.create.new.columns` (OPS-5); a fetch result returned to the caller; `Client` as context manager with `close()`; Ctrl+C on the command line sets the stop function. | CMD-2, CMD-3, COR-3, COR-10, COR-11, ING-3, ING-6, LIB-5, LIB-6, LIB-7, LIB-8, LIB-9, LIB-10, OPS-1, OPS-2, OPS-5, QA-4, QA-11, QA-14, QRY-3, QRY-4 | `continuous-integration` |
| 8 | M1 | `publishing-readiness` | change | Planned | License (MIT) and complete metadata; extras; check that the name is free on PyPI; release workflow prepared but not run; CHANGELOG, CONTRIBUTING (incl. the docstring conventions), SECURITY, non-affiliation statement; docs site (MkDocs Material, mkdocstrings) built in CI; `.env` found from the working directory (test case CLI-T03). Readiness is shown by building and inspecting wheel and sdist, without upload. | DIST-1, DIST-2, DIST-3, DIST-4, DIST-5, DIST-6, DIST-7, OPS-3 | `continuous-integration`, `library-contract` |
| 9 | M2 | `testable-core` | change | Planned | Pure core and injected collaborators; a composition root; repository interfaces with contract-tested fakes replacing today's doubles; the symbol as a method argument, not object state; an injected clock that can also drive timers; seams instead of patched private methods; `load_payload` moved from `tests/fakes.py` to `tests/support/`. | QA-12 | `test-suite-hardening` |
| 10 | M2 | `connection-reuse` | change | Planned | Spike on QuestDB's QWP protocol and the pooled client; one database session per run and per client, and for the lifetime of a long-running process; `Client` lifecycle behind `close()`; TLS options for the database connections. | CLD-8, ING-12, ING-13, ING-14, LIB-8, OPS-2 | `library-contract`, `testable-core` |
| 11 | M2 | `settings-model` | change | Planned | One settings model (pydantic-settings) for every setting, grouped by runtime role; a fetch policy: exchanges, venues, fundamentals scope, thresholds, minute start date and window length; secrets also from files. | CLD-3, CLD-5, ING-15, ING-18, MKT-9, OPS-3, PRV-1, PRV-3, PRV-8 | `testable-core` |
| 12 | M2 | `ingestion-efficiency` | change | Planned | Passes by data kind (reference data and fundamentals once per run, `--data`; test case FUND-T03); bulk reference writes; minute bars written per window (PRICES-T12); a failing pass or exchange list no longer ends the fetch (RUNS-T05); minute history from the listing date or first daily bar; restriction of a fetch to a list of instruments; the nightly end-to-end test (moved here from `continuous-integration`). | ING-4, ING-7, ING-8, ING-9, ING-12, ING-13, ING-14, ING-15, OPS-2 | `testable-core`, `settings-model` |
| 13 | M3 | `target-architecture` | change | Planned | Canonical model, with bars that can carry state, revision, provenance and time of receipt (LIVE-3), and a series of their own per feed (LIVE-4), the target package layout of `1_constitution.md`, section 4, import rules enforced by import-linter; the comparisons and decisions DG-1 (architecture) and DG-2 (storage). | LIVE-3, LIVE-4, PRV-1, PRV-2, QA-4 | `testable-core` |
| 14 | M3 | `provider-interface` | change | Planned | Provider interface and the eodhd adapter; capabilities, including data delivered continuously (LIVE-2); data pushed by the provider as well as fetched on request, through the same parsing (LIVE-1); mappings: exchanges by MIC (one meaning of `exchange_code`), concepts for fundamentals, provider symbols per instrument; the source provider on every record; unmapped provider fields reported. | ING-15, LIVE-1, LIVE-2, PRV-1, PRV-2, PRV-3, PRV-4, PRV-5, PRV-6, PRV-7, PRV-8, PRV-9, PRV-10 | `target-architecture` |
| 15 | M3 | `schema-from-code` | change | Planned | Table definitions in one place, DDL generated from them; a generic SQL builder; a stored schema version checked before processing. | ING-19, ING-20 | `target-architecture` |
| 16 | M4 | `query-layer` | change | Planned | Discovery and coverage; reading fundamentals; raw bars with a defined order; aggregation aligned to sessions, its rules in one implementation that live bars can use too (LIVE-5); trading calendars; input contracts (single instrument identifier, empty selections (test case ACCESS-T10), named columns); command line `list` and `export`. | API-5, API-6, API-7, BT-5, BT-10, BT-11, BT-12, BT-18, CMD-2, CMD-3, CMD-4, COR-11, LIB-5, LIVE-5, MKT-14, QRY-2, QRY-3, QRY-4 | `target-architecture`, `schema-from-code` |
| 17 | M4 | `rest-api` | new (REST) | Planned | Read endpoints; JSON, Arrow IPC and Parquet; pagination and size limits; API keys; error format (RFC 9457); health and readiness; versioning and OpenAPI; the `serve` command. | API-1, API-2, API-3, API-4, API-5, API-6, API-7, API-11, API-12, API-13, API-14, API-15, API-16, QRY-1 | `query-layer` |
| 18 | M5 | `listings-and-universe` | change | Planned | Instruments with listing and delisting dates; listing status history; the universe on a date; aliases for ticker changes; index membership; history of the sector classification; identity beyond code and venue (reused tickers), after checking eodhd's active and delisted lists for reused tickers (moved from `data-integrity-checks`). | BT-1, BT-2, BT-3, BT-4, BT-13, COR-1, PRV-9 | `provider-interface`, `query-layer` |
| 19 | M5 | `corporate-actions` | new (ACTIONS) | Planned | Splits and dividends stored; adjustment factors; adjusted prices on read in three modes. Prices are raw (checked in `data-integrity-checks`; the precondition of DG-4 is met). | BT-5, BT-6, BT-7, BT-10, BT-11, BT-12, COR-12, COR-13 | `provider-interface`, `query-layer` |
| 20 | M5 | `point-in-time-fundamentals` | change | Planned | Bitemporal storage, append-on-change instead of delete-then-write; a concept registry; reads as known on a date; decision DG-3 (table layout). Removes the race of the deletions: FUND-T12 then passes, and its expected-failure mark is removed. | BT-8, BT-9, BT-17, COR-1, COR-2, COR-12, COR-13, PRV-5, PRV-6 | `provider-interface`, `schema-from-code` |
| 21 | M5 | `run-tracking` | change | Planned | Run history stored and queryable; watermarks; resume after an interruption; retry of the failed instruments only; lineage (run, time, provider, parameters, version). | BT-17, COR-5, COR-15, COR-16, ING-7, ING-8, ING-9, ING-10, ING-11, ING-16, PRV-10 | `schema-from-code` |
| 22 | M5 | `data-quality` | new | Planned | Data-quality findings stored and queryable; checks; the pre-1970 drops recorded as findings. | COR-9, COR-14 | `run-tracking` |
| 23 | M5 | `price-corrections` | change | Planned | Reconciliation of past bars with the provider; tombstones for bars the provider no longer delivers. No split overlap check: prices are raw (`data-integrity-checks`). | BT-6, COR-12, COR-13 | `run-tracking`, `corporate-actions` |
| 24 | M6 | `fetch-jobs` | new (JOBS) | Planned | Job queue and worker; lease (one active run per provider account; a mechanism other long-running roles can reuse); job endpoints in the REST API; cancel. | API-8, API-9, API-10, CLD-4 | `rest-api`, `run-tracking` |
| 25 | M6 | `ingestion-scale` | change | Planned | Concurrent requests with a shared rate limiter; the storage guard on the database host; backfill mode; raw landing of provider responses; partitioning measured again. | CLD-2, ING-7, ING-8, ING-9, ING-12, ING-13, ING-14, ING-17, ING-18, ING-21, OPS-2, OPS-3 | `ingestion-efficiency`, `run-tracking` |
| 26 | M7 | `metrics-and-screens` | new (METRICS) | Planned | Metric registry, metrics computed on request, technical indicators, screens, cache where measured; decision DG-5. | BT-13, BT-14, BT-15, BT-16, BT-17 | `point-in-time-fundamentals`, `corporate-actions`, `query-layer` |
| 27 | M8 | `cloud-readiness` | change | Planned | Runtime roles (API server, worker, one-off commands, room for further long-running roles); logging to standard output, structured and in UTC; graceful stop on termination signals; review of the twelve factors. | API-11, API-12, API-13, API-15, CLD-1, CLD-2, CLD-3, CLD-4, CLD-5, CLD-6, CLD-7, CLD-8, COR-10, OPS-3, OPS-4 | `fetch-jobs` |
| 28 | M8 | `release-1-0` | change | Planned | Performance targets; mutation testing; security review; deprecation policy; complete user guide; as the very last step, the act of publishing: TestPyPI rehearsal, the first PyPI release, deployment of the docs site. | API-16, DIST-2, DIST-3, DIST-4, DIST-6, DIST-7, QA-11, QA-13, QA-15 | all others |

---

## 3 Decision gates

A decision gate is a design question that a planned feature decides in its review
(`1_constitution.md`, section 6.3, step 3). The features of the same milestone that wait for it
are written once it is decided (section 6.3).

- **Open:** not decided yet; the deciding feature weighs the options in its review.
- **Decided:** taken in the review of the deciding feature, whose Decisions table holds the
  choice and the reason.
- **Settled** (with the date): the deciding feature is merged, and the decision stands in
  `4_design.md`, Appendix A.

| ID | Question | Decided by | Waiting for it | State |
| -- | -------- | ---------- | -------------- | ----- |
| DG-1 | Code architecture: the target package layout and its dependency rule (`1_constitution.md`, section 4), with room for a long-running live-data role | `target-architecture` | `provider-interface`, `schema-from-code` | Open |
| DG-2 | Storage engine: QuestDB alone, together with another database, or another engine; and what would make the choice be reconsidered; including a second, continuously written bar series (LIVE-4) | `target-architecture` | `schema-from-code` | Open |
| DG-3 | Table layout of the point-in-time fundamentals | `point-in-time-fundamentals` | — | Open |
| DG-4 | Adjustment method: adjustment factors applied to the raw prices on read, or adjusted prices stored; and whether the provider's adjusted close is kept | `corporate-actions` | `price-corrections` | Open |
| DG-5 | Metrics and indicators: computed on request or stored, and what is cached | `metrics-and-screens` | — | Open |
| DG-6 | Formats and paging of large results, and whether QuestDB's export endpoint `/exp` delivers them; with a cursor a client can resume from by time | `query-layer` | `rest-api` | Open |
| DG-7 | Concurrency of the fetch: threads or asyncio, and how concurrent requests share the provider's rate limit, also across processes | `ingestion-scale` | — | Open |
| DG-8 | Partitioning of the minute bars: by day, week or month | `ingestion-scale` | — | Open |
| DG-9 | Lock file and the Python versions tested | `continuous-integration` | — | Decided |
| DG-10 | Database client: QuestDB's pooled client over QWP, or psycopg and the ILP `Sender` as today; for long-running processes as well as runs | `connection-reuse` | — | Open |
| DG-11 | Package name on PyPI | `publishing-readiness` | — | Open |
| DG-12 | Instrument identity: a natural key (symbol and MIC) or a surrogate key with a mapping | `target-architecture` | `provider-interface` | Open |

---

## 4 Settled decisions

Decisions already taken on parts that are not built yet. Each binds planned features before
these are written, which sets it apart from the decisions kept elsewhere: a feature's Decisions
table holds the decisions of that one feature, and `4_design.md`, Appendix A, those in force in
the implemented system. A feature that applies a decision below cites it in its Decisions
table. Once that feature is merged, `4_design.md`, Appendix A, records what is then in force.
The row stays, since the features cite its ID.

| ID | Decision | Applies to | Date |
| -- | -------- | ---------- | ---- |
| DEC-5 | The REST API covers reads and fetch jobs. Schema administration, such as preparing the database, stays in the command line and the library. | `rest-api`, `fetch-jobs` | 2026-10-09 |
| DEC-9 | pydantic is used for the REST API and wherever else records are few and structured: the settings, and provider documents such as the fundamentals and the exchange and instrument lists. Bulk data such as bars is checked with vectorised code instead. | `settings-model`, `provider-interface`, `rest-api` | 2026-10-09 |
| DEC-14 | The README is the landing page of the user documentation. The user guide and the API reference form a MkDocs site, built from a tracked `docs/` folder and published on GitHub Pages. | `publishing-readiness`, `release-1-0` | 2026-10-11 |
