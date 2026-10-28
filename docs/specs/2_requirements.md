# MarketHistoryDB: requirements

Every requirement of the project, implemented or not.

- **What a requirement is:** a stakeholder need, stated solution-neutrally
  (`1_constitution.md`, section 6.2). How a requirement is met is specified in `3_specs.md`
  (implemented) or in a planned feature's `1_specs.md`; `7_traceability.md` shows which items
  satisfy which requirement.
- **Order:** groups are ordered by importance for the goals: the data first, then the interfaces
  to it, then how data gets in and how the system is run, then quality and distribution, and
  the architectural constraints last. Within a group, requirements are ordered by importance.
- **Priority:** Must, Should, Could, or Arch (an architectural constraint: not built now, but no
  design may block it).
- **Status:**
  - **Done:** all specification items satisfying it are implemented.
  - **Partial:** some are; the cell says what is missing.
  - **Open:** none are.
- **IDs:** stable, never reused.

## Requirement groups

| # | Group | Prefix | What it covers |
| - | ----- | ------ | -------------- |
| 1 | Market data | MKT | The core function: which market data the system obtains from providers, stores and serves. |
| 2 | Data correctness and safety | COR | Stored data is complete, correct, consistent and protected against loss, whatever interface is used. |
| 3 | Data for backtesting | BT | The data a backtester needs beyond the core: survivorship-free universes, adjusted prices, point-in-time fundamentals, resampling, screener metrics. |
| 4 | Querying data | QRY | How queries behave, the same way in the library, REST API and command line. |
| 5 | REST API | API | Reading data and running fetches over HTTP, for clients on other machines or in other languages. |
| 6 | Python library | LIB | What programs using MarketHistoryDB as a library can expect from it. |
| 7 | Command line | CMD | What users can do from the command line. |
| 8 | Ingestion | ING | Fetching data from providers: robust, economical, resumable. |
| 9 | Operation and configuration | OPS | Setting up, configuring and running an instance. |
| 10 | Quality, security and performance | QA | Tests, security and measured performance. |
| 11 | Distribution and open-source project | DIST | How the package is published, versioned and documented. |
| 12 | Provider independence | PRV | Architectural: providers can be replaced, and several can serve disjoint data. |
| 13 | Cloud readiness | CLD | Architectural: the system can run in containers and cloud platforms. |
| 14 | Live data | LIVE | Architectural: live bars can be added later, through the same processing as the history. |

---

## 1 Market data (MKT)

| ID | Requirement | Rationale | Prio | Status |
| -- | ----------- | --------- | ---- | ------ |
| MKT-1 | The system shall obtain historical market data from external market-data providers, through their interfaces and with the user's own provider account. | The purpose of the system. | Must | Done |
| MKT-2 | The system shall store the obtained data in a database it manages, so that the data can be read without contacting the provider again. | Backtests read the same data many times; provider requests are slow and cost quota. | Must | Done |
| MKT-3 | The system shall create the database structure it needs. | Users must not have to set up tables by hand. | Must | Done |
| MKT-4 | The system shall obtain and store price bars (open, high, low, close, volume) of instruments: daily bars, intraday bars, or both. | Prices are the one kind of data every backtest needs; providers differ in which bars they offer. | Must | Done |
| MKT-5 | Where the provider offers them, the system shall obtain and store daily price bars. | The basic input of most backtests. | Must | Done |
| MKT-6 | Where the provider offers them, the system shall obtain and store intraday price bars at the finest resolution the provider offers, down to one minute; finer data (ticks) is out of scope. | Needed for intraday strategies and finer backtests; providers differ in what they offer (e.g. only 5-minute bars). | Must | Done (one-minute bars) |
| MKT-7 | Where the provider offers them, the system shall obtain and store fundamental data of companies: earnings, balance sheets, cash-flow statements and income statements, each quarterly and annual. | Needed for fundamental strategies and screens. | Must | Done |
| MKT-8 | The system shall obtain and store reference data: exchanges and instruments (name, type, currency, country, ISIN), and, where the provider offers it, the sector and industry classification of companies. | Needed to select and describe instruments. | Must | Done |
| MKT-9 | The system shall cover the exchanges and asset classes the user selects among those the provider offers, such as stock exchanges, foreign exchange, cryptocurrencies and government bonds. | Users trade different markets. | Must | Partial: a fixed selection in the code (daily bars for US, London, Toronto, XETRA and Shanghai stocks, FX, crypto and government bonds; minute bars for US stocks, FX and crypto; fundamentals for NASDAQ and NYSE) |
| MKT-10 | The first fetch of an instrument shall obtain its full available history; later fetches shall add what has been published since. | The database must be complete and stay current. | Must | Done |
| MKT-11 | Users shall be able to start fetch runs from the library and the command line. | Fetching is the main operation. | Must | Done |
| MKT-12 | Users shall be able to read the stored prices of selected instruments over a time range. | Price series are the input of every backtest and chart. | Must | Done |
| MKT-13 | Users shall be able to read the stored reference data of exchanges and instruments. | Needed to describe and select instruments. | Must | Done |
| MKT-14 | Users shall be able to read the stored fundamental data of selected instruments. | Fundamental strategies and screens work on the reported figures themselves, not only on metrics derived from them. | Must | Open |

## 2 Data correctness and safety (COR)

| ID | Requirement | Rationale | Prio | Status |
| -- | ----------- | --------- | ---- | ------ |
| COR-1 | The system shall not lose stored records, nor overwrite them with records of another instrument or period, including when writes for several instruments follow each other immediately. | A backtest on silently incomplete data gives wrong results without any sign of it. | Must | Partial: a suspected race between delete and write, and fundamentals of two periods filed on the same day collapsing into one record, are open |
| COR-2 | An interrupted write or delete (crash, kill, lost connection) shall not leave data permanently lost or a table missing. | Long runs do get interrupted. | Must | Partial: an interrupted delete is repaired, but only by the next delete from the same table |
| COR-3 | The system shall not delete or overwrite stored data unless the user explicitly requests it. | One careless call must not wipe years of fetched data. | Must | Partial: the command line asks for confirmation; the library's setup always deletes everything |
| COR-4 | Data read back shall equal the data written, in values, types and missing values. | Readers must be able to trust that storage changes nothing. | Must | Partial: not verified by a test; updates store "not a number" instead of a missing value |
| COR-5 | Time series assembled by several incremental or interrupted runs shall have no gaps and no duplicates compared with the provider's data. | Gaps and duplicates distort indicators and returns. | Must | Partial: incremental fetching exists; not verified across runs |
| COR-6 | The system shall refuse to store data whose structure no longer matches the expected structure, instead of changing the stored structure or storing it partly. | A silent provider change must not corrupt the database. | Must | Done |
| COR-7 | The system shall check every provider response for the expected structure and data types before using it. | Malformed responses must fail loudly, not produce wrong records. | Must | Done |
| COR-8 | Identifiers received from the provider shall not be able to change the meaning of a request built from them. | Provider data is not trusted to be safe in URLs. | Must | Done |
| COR-9 | Records the database cannot store shall be skipped explicitly and reported with their number, instrument and data kind, and shall not cause other records to be lost. | Users must know what is missing and why. | Must | Done (reported in the log only; see COR-14) |
| COR-10 | All points in time shall follow one documented convention (UTC) in storage, requests and interfaces. | Mixed time zones shift data unnoticed. | Must | Partial: log times are local, without a time zone |
| COR-11 | The system shall reject inputs that break its documented conventions, such as points in time in another time zone, instead of silently misreading them. | Silent misreading shifts results unnoticed. | Should | Open: the convention is documented (COR-10), not enforced |
| COR-12 | Corrections the provider makes to past data shall reach the stored data within a configurable time. | Stale history makes backtests disagree with reality. | Must | Open |
| COR-13 | Data the provider no longer delivers shall no longer be served as current. | Removed bars or withdrawn reports must not linger. | Should | Open |
| COR-14 | Data-quality findings shall be stored so that users of every interface can query them. | Logs rotate, and library users never see them. | Should | Open |
| COR-15 | Every stored record shall be traceable to the run and the time it was stored. | Needed to explain and reproduce any value. | Should | Open |
| COR-16 | Every run shall record the providers it used, its parameters and the software version. | Needed to explain and reproduce any run. | Should | Open |
| COR-17 | Changes in a provider's interface or data semantics shall be detected by regular automated checks. | Provider changes must be noticed before they corrupt stored data. | Should | Partial: checks of fields and types exist; value semantics are not checked; not scheduled |

## 3 Data for backtesting (BT)

| ID | Requirement | Rationale | Prio | Status |
| -- | ----------- | --------- | ---- | ------ |
| BT-1 | Users shall be able to determine the instruments listed on any past date, including those delisted since. | A universe of today's survivors makes backtests look too good. | Must | Partial: delisted instruments are stored; no listing dates, no query by date |
| BT-2 | The histories of instruments delisted later shall be kept and served. | Same reason as BT-1. | Must | Done |
| BT-3 | An instrument's history shall remain findable after a ticker change. | Old signal lists use old tickers. | Could | Open |
| BT-4 | Users shall be able to determine the members of an index on any past date. | Index strategies need historical membership. | Could | Open |
| BT-5 | Price queries shall return unadjusted prices, prices adjusted for splits, or prices adjusted for splits and dividends, as chosen by the caller. | Strategies and analyses need different adjustments. | Must | Open |
| BT-6 | Adjusted prices shall reflect every corporate action known to the system at query time. | Stale adjustments distort returns. | Must | Open |
| BT-7 | Splits and dividends shall be queryable. | The backtester needs them, e.g. for dividend income. | Should | Open |
| BT-8 | Fundamental data shall be queryable as known on a given date, without values published later. | Prevents look-ahead bias. | Must | Partial: the publication date is stored; no query by date |
| BT-9 | A revised fundamental value shall not replace the earlier value; both shall remain available. | Needed for point-in-time queries. | Must | Open |
| BT-10 | Users shall be able to request bars aggregated to coarser intervals than stored. | Charting and strategies work on many intervals. | Should | Open |
| BT-11 | Aggregated bars shall be aligned to the trading sessions and time zone of the instrument's exchange. | Bars aligned to UTC hours misrepresent trading. | Should | Open |
| BT-12 | Price queries shall also return the latest N bars per instrument, and let the caller choose how gaps are handled. | Typical charting and backtesting queries. | Should | Partial: the newest bar per instrument can be read |
| BT-13 | Users shall be able to obtain screener-style metrics per instrument and date (valuation, profitability, growth, dividend, performance, liquidity), as known on that date. | Stock-screener data drives the selection of instruments. | Should | Open |
| BT-14 | Users shall be able to obtain common technical indicators for instruments. | Standard inputs of strategies and screens. | Should | Open |
| BT-15 | Users shall be able to select the instruments that meet a set of metric conditions on a given date. | Screening is the start of many strategies. | Should | Open |
| BT-16 | Adding a metric shall not require changing the stored data structure. | The number of useful metrics is open-ended. | Should | Open |
| BT-17 | A query shall be repeatable later with identical results, by pinning the data state it ran against. | Backtest results must be reproducible. | Should | Open |
| BT-18 | Trading calendars (sessions, holidays, early closes) shall be available to clients. | The backtester needs them for scheduling and checks. | Could | Open |

## 4 Querying data (QRY)

| ID | Requirement | Rationale | Prio | Status |
| -- | ----------- | --------- | ---- | ------ |
| QRY-1 | The same query shall return identical results through the library, the REST API and the command line. | One behaviour, whatever the interface. | Must | Open |
| QRY-2 | Users shall be able to find out which exchanges, instruments and time ranges the database holds. | Usually the first thing a user needs. | Should | Open |
| QRY-3 | An instrument shall be identifiable by a single self-contained identifier. | Simpler queries; matches what users write. | Should | Open |
| QRY-4 | A query for an empty selection shall return an empty result. | Callers shouldn't need special cases. | Should | Partial: a price read for no exchanges returns an empty result; one for an exchange with an empty list of symbols fails |

## 5 REST API (API)

| ID | Requirement | Rationale | Prio | Status |
| -- | ----------- | --------- | ---- | ------ |
| API-1 | The system shall offer its read functionality over a REST API. | The backtester runs as a separate process and possibly on another machine. | Must | Open |
| API-2 | The REST API shall cover everything the library can read: exchanges, instruments and universes, prices, fundamentals, corporate actions, coverage and data-quality findings. | The backtester needs all of it. | Must | Open |
| API-3 | Incompatible changes to the REST API shall not break existing clients without a transition period. | Upgrading the server must not break a running backtester. | Must | Open |
| API-4 | The REST API shall be described in a machine-readable form from which documentation and clients can be generated. | Clients may be written in other languages. | Must | Open |
| API-5 | The REST API shall deliver result sets of millions of rows without exhausting the memory of server or client. | Large cross-sections and deep minute histories are the expected load. | Must | Open |
| API-6 | Clients shall be able to receive results in JSON and in a compact columnar binary format that analysis tools read directly. | JSON is universal; large results need an efficient format. | Must | Open |
| API-7 | Requests beyond configurable size limits shall be rejected with an explanation of how to proceed. | Protects the server and tells clients what to do. | Must | Open |
| API-8 | Clients shall be able to start, list, monitor and cancel fetch runs over the REST API. | The owner manages fetches remotely. | Must | Open |
| API-9 | A fetch run started over REST shall continue independently of the request, and its state shall survive restarts of server and worker. | Runs take hours; requests and processes don't last that long. | Must | Open |
| API-10 | At most one fetch run shall be active per provider account at any time. | Provider limits apply per account; parallel runs would compete. | Must | Open |
| API-11 | Only authorised clients shall be able to use the REST API. | The data and the provider quota belong to the owner. | Must | Open |
| API-12 | A fresh installation shall not be reachable from the network until explicitly configured. | Safe default. | Must | Open |
| API-13 | Traffic between clients and the REST API shall be encryptable, and the documentation shall show how. | Keys and data cross networks. | Must | Open |
| API-14 | The REST API shall report errors in one consistent, machine-readable format. | Clients handle every error the same way. | Should | Open |
| API-15 | Operators and orchestrators shall be able to check whether the service is running and ready to serve. | Needed for restarts and load balancing. | Should | Open |
| API-16 | Client libraries for the REST API shall be available or generatable. | Eases writing clients. | Could | Open |

## 6 Python library (LIB)

| ID | Requirement | Rationale | Prio | Status |
| -- | ----------- | --------- | ---- | ------ |
| LIB-1 | Importing the package shall have no side effects: no environment access, no logging configuration, no I/O. | Importing must be safe in any program. | Must | Done |
| LIB-2 | The program using the library shall decide where log output goes; the library shall only emit log records. | Only the program knows its logging setup. | Must | Done |
| LIB-3 | The configuration shall be passable explicitly in code, or taken from the environment when the client is created. | Programs configure libraries in different ways. | Must | Done |
| LIB-4 | All errors the library raises on purpose shall share one documented base class, with distinct subclasses for errors callers handle differently. | Callers need to catch errors selectively. | Must | Done |
| LIB-5 | The public API shall be declared explicitly and be distinguishable from internal modules. | Users must know what they can rely on. | Must | Partial: entry points exist; no explicit declaration |
| LIB-6 | Every public function, class and method shall be documented, including its parameters, return value and the errors it raises. | Users work from the documentation. | Must | Partial: some read methods are undocumented |
| LIB-7 | The public API shall carry type information that static type checkers use. | Users' type checkers need it. | Must | Partial: type annotations exist; not published as typed, not checked |
| LIB-8 | A program shall be able to close a client and release everything it holds (database connections, HTTP sessions) at a moment it chooses, instead of when the program ends. | Long-running programs such as notebooks and servers would otherwise keep connections open. | Must | Open |
| LIB-9 | A fetch shall report its outcome to the calling program as a value: what was requested, stored and failed, and why. | Programs must not have to parse logs to retry failures. | Must | Open |
| LIB-10 | The installed version shall be retrievable at run time. | Needed for bug reports and compatibility checks. | Should | Open |
| LIB-11 | Creating a client shall not connect to the database or a provider; connections shall be opened only when an operation needs them. | Programs can create clients at start-up, even while the database is unreachable. | Should | Done |

## 7 Command line (CMD)

| ID | Requirement | Rationale | Prio | Status |
| -- | ----------- | --------- | ---- | ------ |
| CMD-1 | The command line shall report the outcome of each command through documented exit codes that distinguish the main kinds of failure. | Scripts and schedulers react to exit codes. | Must | Done |
| CMD-2 | Every command-line operation shall be runnable unattended, destructive ones included when confirmed explicitly by a flag. | Scripts, containers and schedulers can't answer prompts. | Should | Partial: setup always asks interactively |
| CMD-3 | The command line shall let users inspect what the database holds. | Quick checks without writing code. | Should | Open |
| CMD-4 | The command line shall export query results to files. | Feeds tools that read files. | Could | Open |

## 8 Ingestion (ING)

| ID | Requirement | Rationale | Prio | Status |
| -- | ----------- | --------- | ---- | ------ |
| ING-1 | Transient failures of the provider, the network or the database shall be retried with growing delays, honouring a waiting time the provider asks for. | Short outages must not fail a run. | Must | Done |
| ING-2 | Waiting between retries shall be interruptible. | Users must be able to stop at any time. | Must | Done |
| ING-3 | A running fetch shall be stoppable by the user at defined points, leaving stored data consistent. | Users must be able to abort a fetch safely. | Must | Partial: the library stops at defined points; Ctrl+C on the command line stops wherever the run is |
| ING-4 | The failure of a single instrument shall not end a run; it shall be recorded and the run continued. | One bad instrument must not cost a whole run. | Must | Partial: a failed pass, or a failed exchange or symbol list, ends the fetch |
| ING-5 | A run shall end early when errors show that continuing cannot succeed: a rejected account, an exhausted quota, full storage, an interruption, or a long series of failures. | Avoids burning the quota on a broken run. | Must | Done |
| ING-6 | Every run shall end with a summary of what was fetched, what failed and what was not attempted. | Users must see the outcome at a glance. | Must | Partial: an up-to-date symbol is logged as having no data and counted as downloaded |
| ING-7 | Each data item shall be requested from the provider at most once per run. | Provider requests cost quota and money. | Must | Partial: fundamentals are requested twice for instruments in both the daily and the minute pass |
| ING-8 | A run shall request only data that is not stored yet or may have changed. | Same reason. | Must | Partial: prices are fetched incrementally; fundamentals are always fetched in full |
| ING-9 | Runs shall stay within the provider's request and quota limits. | Exceeding them blocks the account. | Must | Partial: the run reacts to rate-limit responses; no planning against the quota |
| ING-10 | An interrupted run shall be resumable without repeating the work already done. | Runs are long. | Must | Partial: prices restart from the newest stored bar; nothing else is resumed |
| ING-11 | Users shall be able to repeat a run for its failed instruments only. | Cheap recovery from partial failures. | Must | Open |
| ING-12 | The cost of writing a run's data shall depend on the amount of new data, not on the size of the data already stored. | Write cost must not explode as the database grows. | Must | Open |
| ING-13 | A failure during a long download shall keep the data already received. | Minute histories take many requests per instrument. | Must | Open |
| ING-14 | A run's peak memory shall not grow with the length of an instrument's history. | Long minute histories must fit in memory. | Should | Open |
| ING-15 | Users shall be able to restrict a run by data kind, exchange, instrument list, listing status and time frame. | Targeted runs save time and quota. | Should | Partial: exchange, listing status and time frame filters exist |
| ING-16 | The history of runs shall be stored and queryable. | Operators need to see what ran when, and with what result. | Should | Open |
| ING-17 | Requests to the provider shall run concurrently, within its limits. | Runs are dominated by waiting for responses. | Should | Open |
| ING-18 | Writing shall stop with a clear error before the database host runs out of storage space. | A full disk can damage the database. | Should | Partial: checks the free space of the machine the client runs on, not of the database host |
| ING-19 | A mismatch between the software and the stored data structure shall be detected before any data is processed, with an explanation of how to fix it. | Running on an outdated structure corrupts data. | Should | Open |
| ING-20 | The stored data structure shall be defined in one place in the code. | Two definitions drift apart. | Should | Open |
| ING-21 | Provider responses shall be retainable, so that changed processing can be re-applied without new provider requests. | Re-fetching costs quota and time. | Could | Open |

## 9 Operation and configuration (OPS)

| ID | Requirement | Rationale | Prio | Status |
| -- | ----------- | --------- | ---- | ------ |
| OPS-1 | Preparing the database for use shall be repeatable without side effects, so that it can be done on every start. | Services start often; preparation must be safe each time. | Must | Open |
| OPS-2 | Connections to the database and the providers shall be reused within a client, run or long-running process, not opened per operation. | Per-operation connections cost time and trigger server warnings. | Must | Open |
| OPS-3 | Everything that may differ between installations (connections, providers, fetch scope, thresholds, paths) shall be configurable without code changes. | Other people run their own instance with other needs. | Should | Partial: connections are configurable; fetch scope and thresholds are fixed in the code |
| OPS-4 | Runs started from the command line shall leave a log that outlasts the session, limited in size. | Long runs need a record to look back at, without filling the disk. | Should | Done |
| OPS-5 | Before writing, the system shall check that the database runs with the configuration the system depends on, and stop with an explanation otherwise. | A misconfigured database would silently accept structural changes the system is meant to reject (COR-6). | Should | Open |

## 10 Quality, security and performance (QA)

| ID | Requirement | Rationale | Prio | Status |
| -- | ----------- | --------- | ---- | ------ |
| QA-1 | Behaviour shall be verified on three levels: isolated units without network or database, integration with a real database, and the contract of the real provider. | Each level catches different faults. | Must | Done |
| QA-2 | The unit tests shall execute every line and branch of the code. | Untested code is unknown code. | Must | Done |
| QA-3 | Tests shall never run against a production database. | Integration tests delete data. | Must | Done |
| QA-4 | Every change shall be checked automatically (lint, types, architecture rules, tests, build) before it is merged. | Keeps quality from depending on discipline alone. | Must | Open |
| QA-5 | The test suite shall enforce its own rules automatically: unknown markers, new warnings, hanging tests and unit tests using the network fail the run. | Conventions decay unless enforced. | Must | Open |
| QA-6 | Running the default test suite shall cost nothing: no paid provider requests. | Contributors clone and run the tests. | Must | Open |
| QA-7 | Integration tests shall run reproducibly on any machine and in CI without manual database setup. | A hand-configured test database can't be reproduced. | Must | Partial: the tests set up their tables themselves, but need a hand-started test database |
| QA-8 | Secrets (API tokens, database password) shall never appear in logs, error messages or other output, in any encoding. | Logs and errors get shared. | Must | Partial: the token is masked in its plain form only |
| QA-9 | Secrets shall not appear in the printed form of configuration objects. | Configuration objects end up in logs and tracebacks. | Must | Done |
| QA-10 | Values received from outside shall not be able to change connection settings or requests. | Prevents injection. | Must | Done |
| QA-11 | Dependencies shall be checked for known vulnerabilities, and the code for common security mistakes, automatically. | Expected of a published package. | Must | Open |
| QA-12 | Test doubles shall fail when the real interface they stand in for changes. | Otherwise tests stay green while the code breaks. | Should | Open |
| QA-13 | Performance (run time, provider requests, connections, memory, read throughput, write amplification) shall be measured against a baseline, and regressions detected. | Scalability needs evidence. | Should | Open |
| QA-14 | The code shall pass a configured linter and follow a consistent style: naming, logging, no dead code. | Readability and maintainability. | Should | Open |
| QA-16 | The links between requirements, specifications and tests shall be checked automatically on every change, and a report shall show for each requirement what satisfies and verifies it and what is missing. | Links kept by hand drift apart unnoticed, and a reviewer needs to see what a change does to them. | Should | Open |
| QA-15 | The strength of the unit tests shall be assessed regularly beyond line coverage. | Coverage shows execution, not checking. | Could | Open |

## 11 Distribution and open-source project (DIST)

| ID | Requirement | Rationale | Prio | Status |
| -- | ----------- | --------- | ---- | ------ |
| DIST-1 | The package shall be installable with standard Python tooling and provide a command-line entry point. | Basic usability. | Must | Partial: the installed command finds `.env` only above the package's directory |
| DIST-2 | The package shall be published on PyPI under the MIT license, with complete metadata. | The standard distribution channel for Python packages. | Must | Open |
| DIST-3 | Releases shall follow semantic versioning; before 1.0 the API counts as unstable. | Users need to know which upgrades are safe. | Must | Open |
| DIST-4 | The project shall provide a changelog, contribution guidelines, a security policy, and a statement that it is not affiliated with eodhd.com or QuestDB. | Expected of an open-source project. | Must | Open |
| DIST-5 | Installing the package shall pull in only what its core needs; optional parts shall be installable separately. | Users of the library alone don't want server dependencies. | Should | Partial: lean dependencies; no optional parts yet |
| DIST-6 | Users shall find installation, configuration, the use of every interface, and an API reference in maintained documentation. | Expected of an open-source project. | Should | Partial: the README covers most of today's behaviour |
| DIST-7 | From 1.0 on, a public API element shall be deprecated for at least one minor release before it is removed. | Gives users time to adapt. | Could | Open |

## 12 Provider independence (PRV)

| ID | Requirement | Rationale | Prio | Status |
| -- | ----------- | --------- | ---- | ------ |
| PRV-1 | Stored data, library and REST API shall use provider-independent names and identifiers. | Replacing a provider must not change the interfaces. | Arch | Open |
| PRV-2 | Exchanges shall be identified by their standard market identifier code where one exists. | A provider-independent standard. | Arch | Open |
| PRV-3 | All knowledge specific to a provider shall be confined to one replaceable component per provider. | Makes replacing and adding providers feasible. | Arch | Open |
| PRV-4 | Replacing a provider shall need no changes outside its component, its mapping and the configuration, followed by a refetch. | Same reason. | Arch | Open |
| PRV-5 | Fundamental data shall be mapped to a provider-independent list of concepts. | Providers name the same figures differently. | Arch | Open |
| PRV-6 | Provider fields without a mapping shall be reported, not silently dropped or stored under provider names. | New provider data must be noticed. | Arch | Open |
| PRV-7 | The capabilities of each configured provider (data kinds, time frames, history depth, limits) shall be known to the system. | Planning and the API depend on them. | Arch | Open |
| PRV-8 | Several providers shall be usable in one instance, each serving a disjoint set of data kinds or instruments; a series shall never combine data from several providers. | Best or cheapest source per data kind, wider coverage; merging series would make them inconsistent. | Arch | Open |
| PRV-9 | Instruments shall have a provider-independent identity, mapped to each provider's symbols. | Providers write the same instrument differently (e.g. `BRK.B` and `BRK-B`). | Arch | Open |
| PRV-10 | Every stored record shall carry the provider it came from. | Needed to explain values and to replace or remove a provider's data. | Arch | Open |

## 13 Cloud readiness (CLD)

| ID | Requirement | Rationale | Prio | Status |
| -- | ----------- | --------- | ---- | ------ |
| CLD-1 | Processes shall keep no state on local disk that is needed after a restart. | Containers lose their local disk. | Arch | Done: a run keeps no state of its own, and the next run works from the database alone; only the log file is written locally (RUNS-S13) |
| CLD-2 | File locations shall be configurable as local directories or object storage. | Cloud deployments store files in object storage. | Arch | Open |
| CLD-3 | All settings shall be suppliable through environment variables, secrets also through files, with no hard-coded paths. | Twelve-factor configuration. | Arch | Partial: connections and secrets come from environment variables |
| CLD-4 | API server, ingestion worker, further long-running roles and one-off commands shall be startable and scalable separately, from one package. | Each role scales and restarts on its own. | Arch | Open |
| CLD-5 | Logs shall be writable to standard output, optionally in a structured format. | Platforms collect standard output. | Arch | Partial: the CLI logs to standard output and a file; no structured format |
| CLD-6 | Processes shall stop gracefully on a termination signal, leaving interrupted work resumable. | Platforms stop processes with signals. | Arch | Partial: Ctrl+C is handled; termination signals are not |
| CLD-7 | Basic operational metrics shall be exposed. | Operators need visibility. | Arch | Open |
| CLD-8 | The database shall be usable on another host, with encrypted connections, timeouts and retries; nothing shall assume it runs on the same host. | The database often runs elsewhere. | Arch | Partial: host, timeouts and retries are configurable; no encryption; the storage check assumes the same host |

## 14 Live data (LIVE)

| ID | Requirement | Rationale | Prio | Status |
| -- | ----------- | --------- | ---- | ------ |
| LIVE-1 | Provider data shall be turned into the system's own records by the same implementation, whether it arrives in a fetch run or continuously during a trading session. | Processed differently, live and historical data would make backtests and live trading diverge. | Arch | Open |
| LIVE-2 | A provider's capabilities shall be able to include data it delivers continuously, with its limits, e.g. the number of instruments at once. | Live feeds come with their own limits, which every use of the provider account must respect together. | Arch | Open |
| LIVE-3 | A bar shall be able to carry whether it is provisional (its values may still change, because its interval has not ended) or final, its revision, whether the provider or the system built it, and when it was received. | A live bar changes until its interval has ended; comparing live with historical bars needs their origin and time of receipt. | Arch | Open |
| LIVE-4 | Bars of an instrument and interval from another feed, such as a live feed, shall be storable as a series of their own, never merged with or overwriting the historical series, and readable with the same queries, the series chosen by the caller. | A live feed may differ from the historical data (e.g. one venue instead of all), and a later fetch must not overwrite the record of what was received live. | Arch | Open |
| LIVE-5 | Bars aggregated to coarser intervals shall follow the same rules for historical and for live bars. | Two sets of rules would let the same strategy see different bars in backtests and live. | Arch | Open |
