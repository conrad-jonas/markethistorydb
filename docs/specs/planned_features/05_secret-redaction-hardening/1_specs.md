# secret-redaction-hardening: specification changes

State: Ready · Milestone: M0 · Kind: change (PROVIDER, STORAGE, LOGGING, PACKAGING, QUALITY, CI) ·
Requirements: QA-8, QA-11 · Depends on: `continuous-integration`, `test-suite-hardening`,
`code-hygiene`

## Why

Secrets can still reach logs and error messages. The masking misses the token in URL-encoded
form (`api_token%3D…`), under another spelling (`EODHD_API_TOKEN=`) and without its name, and the
database password isn't masked at all. One path can't be closed by masking: the token travels as
a query parameter, so urllib3 logs it with the URL of every request at DEBUG level, in records
the package doesn't own. And nothing checks the code for common security mistakes.

## Specification changes

### Requests

| Change | ID | Specification | Satisfies |
| ------ | -- | ------------- | --------- |
| MODIFIED | PROVIDER-S01 | Data is requested from five endpoints under `https://eodhd.com/api`: `exchanges-list`, `exchange-symbol-list/{exchange}`, `eod/{symbol}.{exchange}`, `intraday/{symbol}.{exchange}` and `fundamentals/{symbol}.{exchange}`, where `{exchange}` is the code of eodhd's exchange list (e.g. `US`). Every request carries `fmt=json` as a query parameter and the API token in the header `Authorization: Bearer <token>`, never in the URL. A successful response is returned as parsed JSON. | MKT-1, QA-8 |
| MODIFIED | PROVIDER-S14 | **The API token never leaves the request:** no URL holds it (PROVIDER-S01), so neither the messages of request exceptions nor the log records of the libraries underneath contain it, e.g. urllib3's record of each request at DEBUG level. A redirect to another host doesn't carry the token. Error messages hold at most the first 500 characters of the response body, masked by the rule of LOGGING-S05 with the token as the configured secret, also where a secret sits at the cut-off point. Errors built from a request exception are masked the same way and are not chained to that exception. Retry and give-up log messages name the request by its URL without the query string. | QA-8 |

### Masking

| Change | ID | Specification | Satisfies |
| ------ | -- | ------------- | --------- |
| MODIFIED | LOGGING-S04 | Every handler masks secrets in the finished line, so in the message, its arguments and the traceback alike, by the rule of LOGGING-S05. The secrets masked by value are the API token and the database password of the client the command line runs with, from the moment the client is created (CLI-S02). | QA-8 |
| ADDED | LOGGING-S05 | **Masking rule:** a secret is replaced by `***`, every occurrence on every line: <br>• **after its name:** the value after a name ending in `api_token` or `password`, in any case (e.g. `api_token`, `EODHD_API_TOKEN`, `QUESTDB_PASSWORD`), then `=` or `:`, with or without quotes around name and value and white space around the separator, each plain or percent-encoded (`%3D`, `%3A`, `%22`, `%27`, `%20`, or `+` in a form); and the value after `Bearer `. The value ends at the next `&`, white space, quote, comma, semicolon or closing bracket, or at an encoded `&` or quote. <br>• **by value:** each configured secret of at least 8 characters, wherever it stands, as it is and percent-encoded, as in a URL path and as in a form. A shorter secret is masked only after its name. <br>Text without a secret, or with a name that only begins like one (e.g. `api_token_hint=`, `passwords:`), stays unchanged. | QA-8 |

### Database password

| Change | ID | Specification | Satisfies |
| ------ | -- | ------------- | --------- |
| MODIFIED | STORAGE-S18 | A failed statement, a table that does not exist, an unreachable database and a rejected login all raise `QueryError`. | LIB-4 |
| ADDED | STORAGE-S23 | **The database password stays out of errors:** no error of the database layer contains the database password, neither the `DbError` of `setup`, a `QueryError` nor an `InsertError`, and nor does the error it is chained to. This holds for a rejected login over SQL and over the ingestion interface; the latter raises `InsertError` at once, without retrying (STORAGE-S14). | QA-8 |
| MODIFIED | CI-S11 | Without `QUESTDB_TEST_*`, the integration tests start QuestDB 10.0.1 once per session as a container, with `line.auto.create.new.columns=false` and a login required over HTTP, as over SQL (user `admin`, password `quest`), wait until it answers SQL, and run against its mapped ports; the container is removed after the session. The version is pinned and raised deliberately. | QA-7 |

### Security checks

| Change | ID | Specification | Satisfies |
| ------ | -- | ------------- | --------- |
| MODIFIED | QUALITY-S11 | **Lint and format:** `ruff check` and `ruff format --check` pass on `src/` and `tests/` with the configuration in `pyproject.toml`: Python 3.12 as target, a line length of 120, ruff's default rules plus naming (`N`), logging calls (`G`: values are passed as arguments, formatted only when a record is emitted) and security (`S`, bandit's checks: e.g. `eval`, unpickling, a shell in `subprocess`, requests without a timeout or with `verify=False`, hard-coded passwords, SQL text built from strings). The date and time rules (`DTZ`) are off, since naive datetimes mean UTC (COR-10). Unused imports are allowed in `__init__.py` files until these declare `__all__` (`library-contract`). The tests may use `assert`, fake secrets and SQL text built from strings. The statement modules in `db/statements/` may build SQL text from the table and column constants, since every value goes in as a bound parameter or as a literal that psycopg quotes (STORAGE-S17), until `schema-from-code` replaces them. No file starts with a shebang. | QA-14, QA-4, QA-11 |

### Development tools

| Change | ID | Specification | Satisfies |
| ------ | -- | ------------- | --------- |
| MODIFIED | PACKAGING-S03 | `uv sync` installs it for development, together with the development tools: pytest with the plugins pytest-cov, pytest-timeout and pytest-socket, hypothesis, testcontainers, ruff and pyright. `pip install .` installs it as a package. The README says so. (testcontainers and pyright come with `continuous-integration`.) | DIST-1, DIST-6 |

## Not done

| Item | Where | Why |
| ---- | ----- | --- |
| Dependencies audited for known vulnerabilities, the other half of QA-11 | `continuous-integration` | CI-S05 |
| TLS for the database connections (test architecture plan, Phase 6: "once the DB leaves localhost") | `connection-reuse` | CLD-8: the TLS options belong to the database sessions that feature introduces |
| API keys, TLS and the bind address of the REST API (README ToDo "Check for security issues": API-11 to API-13) | `rest-api` | there is no REST API yet |
| A security review of the whole code beyond the lint rules | `release-1-0` | its scope holds the security review |
| SQL statements composed with quoted identifiers instead of f-strings | `schema-from-code` | its SQL builder replaces `db/statements/`; until then `S608` is ignored there |
| A warning when the QuestDB server asks for no login over HTTP or keeps a default password | `library-contract` | its check of the server settings before writing (OPS-5) reads `SHOW PARAMETERS`, which shows both without revealing a password; a warning, not a stop, since a local QuestDB may well run without a login. No requirement covers it yet. |
