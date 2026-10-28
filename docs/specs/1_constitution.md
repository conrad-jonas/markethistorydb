# MarketHistoryDB: constitution

This is the project's constitution: what MarketHistoryDB is for, the rules every change follows,
and how the specification documents in `docs/specs/` work together. It changes rarely. The
glossary is at the end.

---

## 1 Purpose, goals and users

MarketHistoryDB builds and maintains a database of historical market data: prices, fundamentals
and reference data, fetched from market-data providers and stored in QuestDB. Its main use is as
the data source of a trading backtester.

| # | Goal | Status |
| - | ---- | ------ |
| G1 | Serve as the data source for an external trading backtester | primary use case |
| G2 | Be an open-source Python library that meets the usual standards for API, packaging and documentation, published on PyPI under the MIT license | long-term goal |
| G3 | Offer a REST API for reading data and running fetch jobs | long-term goal |
| G4 | Allow the data provider to be replaced, and several providers to serve disjoint data (e.g. prices from one, fundamentals from another) | architectural constraint, not built yet |
| G5 | Be ready to run in the cloud | architectural constraint, not built yet |
| G6 | Allow live bars to be added later: delivered to clients during the trading session, through the same processing as the history | architectural constraint, not built yet |

**Users:**

- the owner, on one machine;
- the owner across machines, with the database and the fetches on a server and backtests
  elsewhere;
- other people running their own instance with their own provider accounts.

**Typical load:** large cross-sections (e.g. daily bars of thousands of instruments over 20
years) and deep histories of a few instruments (e.g. minute bars over years).

## 2 Non-goals

- A hosted multi-tenant service: no tenants, quotas or billing.
- Redistributing provider data. Every instance runs on its owner's provider accounts, and its
  REST API serves that owner's own clients.
- **Merging data from several providers.** A series, e.g. an instrument's daily bars or its
  fundamentals, always comes from exactly one provider: no fallback between providers, no
  stitching, no precedence rules. Several providers serving disjoint data is an architectural
  constraint (G4), not a non-goal. One exception: a read may present an instrument's historical
  series followed by its live series, joined at a boundary the system determines. Each bar keeps
  its series and provider, and nothing joined is stored.
- Deployment artifacts for a specific platform (Helm charts, Terraform, vendor services). Cloud
  readiness stays architectural.
- Order execution. Live market data is an architectural constraint (G6), not a non-goal.
- Data migrations before 1.0. A refetch is acceptable.

## 3 Design principles

1. **One canonical model.** Provider data becomes the project's own records at the edge;
   everything inside uses the project's names and identifiers.
2. **One implementation per capability.** Library, CLI and REST API call the same query and
   ingestion functions, so they behave identically.
3. **Pure core, I/O at the edges.** Decisions are pure functions that can be tested with plain
   values. I/O code only gathers inputs and acts on the results.
4. **Heavy resources are owned once.** Sessions, connection pools and ingestion clients are
   created in one composition root and borrowed everywhere else.
5. **Idempotent, append-friendly writes.** Every load can be repeated without harm; history is
   versioned instead of deleted.
6. **Raw → canonical → derived.** Facts are stored as delivered (in canonical form); adjusted
   prices, metrics and resampled bars are derived from them.
7. **Point-in-time by default.** Every fact that can be revised carries the time it became known.
8. **Safe defaults, explicit danger.** Nothing destructive happens without an explicit flag.

## 4 Architecture rules

The target package layout and its dependency rule are decided in decision gate DG-1
(`6_roadmap.md`) and introduced by the planned feature `target-architecture`. Until then:

- new packages (e.g. `settings.py`, `api/`, `query/`, `domain/`) are created in their target
  place from the start;
- existing code moves with `target-architecture`.

Target layout:

```
src/markethistorydb/
├── domain/        canonical model and pure rules (no I/O, no I/O libraries)
├── providers/
│   ├── interface.py   provider protocol, capabilities, provider errors
│   └── <provider>/    adapter, one per provider (today: eodhd)
├── storage/
│   ├── interface.py   repository protocols
│   ├── questdb/       adapter: QuestDB implementation of the repositories
│   └── files/         adapter: raw landing, staging and exports (local directory or object storage)
├── ingest/        ingestion: plan, extract, parse, validate, load, derive; jobs
├── query/         read side
├── api/           REST API
├── cli/           command line
├── client.py      library facade
├── bootstrap.py   composition root
├── settings.py    settings model
└── errors.py
```

**What `domain/` contains**, for example:

- **Data types of the canonical model,** e.g. `Instrument` (symbol, exchange MIC, name, type,
  currency) and `Bar` (timestamp, open, high, low, close, volume).
- **Rules,** e.g. computing adjustment factors from splits and dividends, or picking the
  point-in-time version of a fundamental value.

**Dependency rule**, enforced by import-linter in CI:

- `api`, `cli` and `client` may import `bootstrap`, `ingest`, `query` and `domain`.
- `ingest` and `query` may import only the two `interface.py` modules and `domain`.
- Adapters (`providers/<provider>`, `storage/questdb`, `storage/files`) may import only the
  interfaces and `domain`.
- No module except `bootstrap.py` imports an adapter.

## 5 Engineering rules

### 5.1 Testing rules

1. Decision logic lives in pure functions that are tested with plain values.
2. Constructors take what stays the same for the object's life. A symbol is always a method
   argument, never constructor or setter state.
3. Heavy resources are created once, in the composition root, and borrowed everywhere else.
4. Test doubles are checked against the real interface: `create_autospec` for stubs and spies,
   and contract tests for hand-written fakes that carry behaviour.
5. Tests assert commands (writes, requests with side effects) and stub queries; they don't
   assert that a read happened.
6. No test patches a private name. If one has to, the production code is missing a seam.

### 5.2 Definition of done for every change

- The unit tests keep 100 % line and branch coverage.
- Every change to the database path has an integration test.
- Docstrings follow the project conventions: reStructuredText field lists, third person
  singular, documented `:raises:`. Today they are written down in `.claude/rules/docstrings.md`;
  they move to `CONTRIBUTING.md` with `publishing-readiness`.
- The README and the user docs are updated in the same change whenever behaviour, CLI or schema
  change.
- The specification documents are updated, and a completed planned feature is merged into the
  global files (section 6.4).
- Breaking changes are noted in the CHANGELOG (once it exists).

### 5.3 Git workflow

- `main` only receives merges: every change is made on a branch named `feature/…`, `fix/…`,
  `test/…`, `refactor/…`, `chore/…` or, for the specification documents, `docs/…`, and merged
  with `git merge --no-ff`.
- Once the repository is on GitHub, every branch is merged through a pull request, and each
  pull request implements one GitHub issue.
- `CLAUDE.md` and `.claude/rules/` are tracked: they hold the instructions for coding agents that
  apply to every contributor. Personal instructions go to `CLAUDE.local.md` and personal settings
  stay in `.claude/`; both are ignored (`.gitignore`).

## 6 Specification process

### 6.1 Documents

| Document | Role |
| -------- | ---- |
| `1_constitution.md` | this constitution: purpose, rules, process, glossary |
| `2_requirements.md` | every requirement: what stakeholders need and why, solution-neutral, with priority and status |
| `3_specs.md` | status quo: the specification of everything implemented, one chapter per capability |
| `4_design.md` | status quo: how the implemented system is built, and the design decisions in force |
| `5_test.md` | status quo: test approach and test cases, each Implemented or Missing |
| `6_roadmap.md` | milestones and the order of the planned features, with a row for each feature not yet written (scope, requirements, dependencies); decision gates, and the settled decisions that no other document records |
| `7_traceability.md` | generated: requirement → specification → test, plus gap lists |
| `planned_features/<nn>_<feature>/1_specs.md` | the specification changes of a planned feature |
| `planned_features/<nn>_<feature>/2_design.md` | the design of that change: target design, options, decision, notes |
| `planned_features/<nn>_<feature>/3_test.md` | its test case changes |
| `archive/<nn>_<feature>/` | planned features after they were merged, with the same three files |

### 6.2 Requirement, specification, design, test

- **A requirement** states what a stakeholder needs and why.
  - It is solution-neutral: no tables, functions, libraries or formats, unless the choice itself
    is the owner's decision (REST, PyPI, MIT, QuestDB).
  - It is atomic and verifiable, and phrased as "The system shall …".
  - Its status follows from `3_specs.md`: **Open** if no specification item there satisfies it;
    **Partial** if one does and a known gap cites it; **Done** if one does and no known gap
    cites it. Planned items don't change the status before they are merged.
- **A specification item** states concrete, observable behaviour: interfaces, inputs and outputs,
  rules, limits, errors, stored data. It names the requirements it satisfies.
- **A known gap** (`3_specs.md`, at the end of each chapter) is a place where the implemented
  behaviour falls short of a requirement. It names the requirements it falls short of and
  exactly one planned feature that closes it. A shortfall that several features close is split
  into one gap per feature, each describing its own part.
- **The design** describes how the specification is realised: structure, data model, algorithms,
  and the options considered with the reasons for the choice.
- **A test case** describes a check in given/when/then form. It names the specification items it
  verifies, its level (unit, integration, live, static, suite or ci) and the tests that implement
  it.

**Completeness.** Every requirement is satisfied by at least one specification item, implemented
or planned, or is assigned to a planned feature not yet written (`6_roadmap.md`). Every
specification item satisfies at least one requirement. Every implemented specification item is
verified by at least one test case.

### 6.3 Workflow

1. **New need:** add or change requirements in `2_requirements.md`.
2. **Plan:** enter the feature in `6_roadmap.md` with its milestone, scope, requirements and
   dependencies. Name it after the capability it introduces (e.g. `rest-api`), or after the change
   if it only changes existing capabilities (e.g. `chunked-minute-writes`). Its number is its
   position in the roadmap order, two digits (e.g. `05`); when the order changes, the numbers
   follow.
3. **Write and review:** the features of one milestone are written together, each as
   `planned_features/<nn>_<feature>/` with `1_specs.md`, `2_design.md` and `3_test.md` (section
   6.7), and reviewed one at a time. The decisions a feature needs are taken in its review and
   recorded in its `2_design.md`.
4. **Issues:** split the feature into GitHub issues (tasks) that reference its specification
   and test IDs.
5. **Implement:** one branch and one pull request per issue (section 5.3).
6. **Complete:** the pull request that completes the feature also merges it into the global
   files (section 6.4).

**One milestone at a time.** The features of a milestone are implemented and merged before the
features of the next milestone are written, so that each milestone is written against the code as
it is. Before a milestone is written, the roadmap rows of all remaining milestones are reviewed:
re-scoped, reordered or dropped. A feature whose design depends on a spike or a decision gate of
another feature in its milestone is written once that outcome is known.

States of a planned feature:

- **Planned:** a row in `6_roadmap.md`, not written yet.
- **Draft:** being written.
- **Ready:** reviewed; may be implemented.
- **In progress:** issues exist and work has started.
- **Merged:** in the global files, folder archived.

### 6.4 Merge checklist (completing a planned feature)

1. **`1_specs.md` into `3_specs.md`:**
   - ADDED items are appended to their capability chapter (a new chapter for a new capability);
   - MODIFIED items replace the text, keeping the ID;
   - REMOVED items are deleted;
   - the rows of "Known gaps" the feature closes are removed, and the rows it changes or adds are
     applied.
2. **`2_design.md` into `4_design.md`:** changed sections are replaced, a new capability gets a
   new chapter, decision outcomes go to "Design decisions in force", and the rows of "Known
   limitations" the feature removes are deleted.
3. **`3_test.md` into `5_test.md`,** in the same way. Status becomes Implemented, with
   "Implemented by" naming the tests.
4. **Archive:** move the folder to `archive/`, keeping its name.
5. **Roadmap:** in `6_roadmap.md`, mark the feature done with its merge date and settle its
   decision gates.
6. **Trace:** regenerate `7_traceability.md`; it must show no new gaps.

### 6.5 IDs and status values

| Kind | Format | Example | Defined in |
| ---- | ------ | ------- | ---------- |
| Requirement | `<TOPIC>-<n>` (COR, LIB, API, BT, ING, QA, PRV, CLD) | `BT-5` | `2_requirements.md` |
| Specification item | `<CAPABILITY>-S<nn>` | `PRICES-S04` | `3_specs.md` or a planned `1_specs.md` |
| Test case | `<CAPABILITY>-T<nn>` | `PRICES-T07` | `5_test.md` or a planned `3_test.md` |
| Milestone | `M<n>` | `M5` | `6_roadmap.md` |
| Settled decision, decision gate | `DEC-<n>`, `DG-<n>` | `DG-3` | `6_roadmap.md` |
| Planned feature | `<nn>_<name>`, *nn* its position in the roadmap order | `05_secret-redaction-hardening` | `6_roadmap.md` |

- A planned feature takes new IDs from the namespace of the capability where the item will land,
  so after a merge every ID matches its chapter.
- IDs are never reused.
- A feature's number changes with the roadmap order, so text cites a feature by its name
  (`code-hygiene`), never by its number or folder.
- The trace script reports duplicate IDs and the next free number per capability.

| Where | Status values |
| ----- | ------------- |
| Requirements | Done, Partial, Open |
| Requirement priority | Must, Should, Could, Arch (an architectural constraint: not built now, but no design may block it) |
| Planned specification and test changes | ADDED, MODIFIED `<ID>`, REMOVED `<ID>` |
| Test cases | Implemented, Missing |
| Planned features | Planned, Draft, Ready, In progress, Merged |

### 6.6 Traceability

Links are maintained in one direction only, where the knowledge arises: specification items list
`Satisfies`, test cases list `Verifies`. `7_traceability.md` is generated from them; nobody edits
it by hand. It shows:

- **the matrix:** requirement → specification items (implemented, planned) → test cases;
- **gaps:**
  - requirements without a specification item;
  - specification items without a requirement;
  - implemented specification items without an implemented test case;
  - MODIFIED or REMOVED items pointing to a non-existent ID;
  - duplicate or dangling IDs;
  - requirements whose status in `2_requirements.md` differs from the one the known gaps give
    (section 6.2);
- **the next free ID** per capability;
- **per planned feature:** the known gaps it closes, and the status of each requirement after its
  merge, with the features before it merged first.

The planned feature `traceability` brings the script as `scripts/trace.py`, which CI runs with
`--check`. Tests then carry `@pytest.mark.spec("<ID>")`, so code and test cases link
automatically.

### 6.7 Files of a planned feature

Each fact is stated once, in the file where it belongs. What the trace script derives (section
6.6) is not written by hand.

**`1_specs.md`:**

- **Header line:** state, milestone, kind (a new capability, or a change to existing ones), the
  requirements whose status the feature changes, and the features it depends on.
- **Why:** the problem the feature solves, in a few lines.
- **Specification changes:** tables `Change | ID | Specification | Satisfies`, grouped by topic.
  ADDED and MODIFIED items carry their full text, REMOVED items their ID.
- **Known gaps changed** and **Known gaps added:** the rows of `3_specs.md` the feature changes
  or adds, if any. The rows it closes are not listed (section 6.6).
- **Not done:** a table `Item | Where | Why` of what the feature leaves out. *Where* is another
  feature, or "nowhere: dropped" with the reason.

**`2_design.md`:**

- **Overview:** the parts of the change and the files each touches.
- **Design per part:** what an implementer can't take from the specification or the code, kept
  short.
- **Decisions:** a table `Decision | Choice | Options considered | Reason`, the only place a
  decision is recorded. A measurement that supports a decision appears there as a one-line
  conclusion.
- **Implementation:** the GitHub issues, one branch and pull request each, with the IDs each
  covers and their order.
- **Open questions.**
- **Changes to `4_design.md` on merge:** the numbers of the sections that change, and the rows of
  "Known limitations" the feature removes.

**`3_test.md`:** tables `Change | ID | Test case | Verifies | Level | Status | Implemented by`,
grouped as in `1_specs.md`. An ADDED test case is Missing. A MODIFIED one is Missing if its tests
must be added or changed, and Implemented if they stay as they are. "Implemented by" names the
tests once they exist, and is "—" before.

**Across features:** a MODIFIED item builds on the text of the features before it in roadmap
order. A feature may correct the files of a Ready feature, in a commit of its own.

---

## 7 Glossary

| Term | Meaning |
| ---- | ------- |
| **Adapter / interface** | An *interface* (a Python `Protocol`) states what the rest of the code needs, e.g. "the daily bars of an instrument". An *adapter* implements it for a concrete technology, e.g. the eodhd provider or QuestDB storage. The rest of the code only knows the interface, so adapters can be swapped. Also called *ports and adapters* or *hexagonal architecture*. |
| **Archive** | `docs/specs/archive/`: planned features that were merged into the global files, kept for their reasoning. |
| **Backfill** | Loading a long stretch of history at once: the first load, or the reload after switching providers. The opposite of an *incremental* run. |
| **Bitemporal** | Storing two kinds of time per fact: when it was true or reported (*valid time*, e.g. the filing date) and when it was stored (*system time*). Needed to answer "what did we know on date T?". |
| **Canonical model** | The project's own data types and names (`Instrument`, `Bar`, `StatementFact`, …), independent of any provider's field names or codes. |
| **Capability** | A coherent area of behaviour, e.g. price ingestion. It is a chapter of `3_specs.md`, `4_design.md` and `5_test.md`, and it gives specification and test IDs their prefix. |
| **Composition root (`bootstrap`)** | The one place that creates the concrete objects (DB session, provider adapter, repositories) and hands them to the code that needs them. |
| **Constitution** | This document (`1_constitution.md`): the project's principles and rules, which every change follows. |
| **Corporate action** | An event that changes a share's price history: a split (e.g. 10:1) or a dividend. |
| **Coverage** | For each instrument and time frame: the first and last stored bar and the row count. |
| **Cursor pagination** | Paging through a large result by remembering where the last page ended, instead of "skip the first N rows". |
| **DDL / generated DDL** | Data Definition Language: the SQL that defines tables (`CREATE TABLE`, `ALTER TABLE`, `DROP TABLE`). *Generated* DDL is produced by code from table definitions in Python, instead of being written by hand in `.sql` files. |
| **DEDUP UPSERT KEYS** | A QuestDB table setting: a row whose key columns equal those of a stored row replaces it. It makes writes repeatable. |
| **Designated timestamp** | The QuestDB column a table is sorted and partitioned by. Time-series features such as resampling and as-of joins need it. |
| **Discovery** | Finding out what the database holds: which exchanges, instruments and time ranges. |
| **Epic** | A planned feature seen as a unit of work; it is split into GitHub issues. |
| **Feed** | The channel through which a provider delivers a series, e.g. eodhd's historical REST endpoint or its live WebSocket stream. One provider can have several feeds, and their data can differ, e.g. one trading venue instead of all. |
| **FILL** | An option of QuestDB's resampling for buckets without data: leave them out (`NONE`), emit nulls (`NULL`), repeat the previous value (`PREV`), interpolate (`LINEAR`) or write a constant. |
| **ILP / QWP** | *ILP* (InfluxDB Line Protocol) is the ingestion protocol the code uses today. *QWP* is QuestDB's newer protocol over WebSocket, used by the current Python client for both ingestion and queries. |
| **Instrument** | A tradable listing, identified as symbol plus exchange, e.g. `AAPL.XNAS`. Today's code calls it a *symbol*. |
| **Lease** | A time-limited claim renewed by a heartbeat, e.g. "worker 7 runs fetches until 12:05:30". If the holder dies, the claim expires on its own. |
| **MIC** | Market Identifier Code (ISO 10383), the standard exchange code, e.g. `XNAS` (NASDAQ), `XNYS` (NYSE), `ARCX` (NYSE Arca). |
| **OpenAPI** | A machine-readable description of a REST API, from which documentation and clients in other languages are generated. |
| **Planned feature** | A change described in `planned_features/<nn>_<feature>/`, or, before it is written, a row in `6_roadmap.md`: a new capability, or changes to existing ones. Usually epic-sized. |
| **Point-in-time (PIT)** | Data as it was known on a given date, without later corrections, to avoid *look-ahead bias* in backtests. |
| **Problem details** | A standard JSON format for HTTP error responses (RFC 9457). |
| **Pure core** | The functions that only compute: values in, values out, with no network, database, clock or file access. The I/O code (the *shell*) gathers inputs, calls them and acts on the results. |
| **Run ledger** | A small pure object that tracks one fetch run: successes, failures, the streak of consecutive failures, whether to abort, and the summary. |
| **Spike** | A short, time-boxed experiment (usually under a day) that answers a technical question before a design is committed to. |
| **Status quo** | The behaviour and design implemented today, described in `3_specs.md`, `4_design.md` and `5_test.md`. |
| **Survivorship bias** | The distortion caused by testing only on instruments that still exist today. The winners survive, so results look too good. |
| **Universe** | The set of instruments a strategy may trade on a given date, e.g. "all active US common stocks on 2010-03-01". A *survivorship-free* universe includes instruments delisted since. |
| **Watermark** | Per instrument and data kind, the point up to which the stored data is known to be complete. The next run starts there. |
