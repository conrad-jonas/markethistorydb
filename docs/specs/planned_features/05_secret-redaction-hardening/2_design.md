# secret-redaction-hardening: design

## 1 Overview

| Part | Files (under `src/markethistorydb/` unless named otherwise) |
| ---- | ----- |
| Token in the header | `fetch/eodhd/request_data.py`, `fetch/eodhd/url.py`, the four request classes in `fetch/eodhd/`; `tests/conftest.py` (`scripted_api`, `routed_api`), the request tests, `tests/live/test_eodhd_contract.py` |
| Masking | `utils/redact.py`, `utils/logger.py`, `utils/__init__.py`, `cli.py`; `tests/unit/utils/test_redact.py`, `tests/unit/utils/test_logger.py`, `tests/unit/test_cli.py` |
| Password in database errors | `tests/integration/db/io/test_query.py`, `tests/integration/setup/test_main.py`, `tests/integration/db/io/test_insert.py`; the container fixture of `continuous-integration`; `README.md` (QuestDB server settings) |
| Security lint | `pyproject.toml` |
| hypothesis | `pyproject.toml`, `uv.lock`, `.gitignore`, `README.md` (development section); `tests/unit/fetch/eodhd/test_url.py` |

## 2 Token in the header

- **Auth object:** `RequestData.__init__` builds `_BearerAuth(api_token)`, a
  `requests.auth.AuthBase` that sets `Authorization: Bearer <token>`, and every request passes it
  as `auth=` (section 7), through the session of PROVIDER-S24 or through `requests.get`.
  - On a redirect to another host, requests deletes the header and doesn't call the auth object
    again (`Session.rebuild_auth`, requests 2.34.2), so the redirect clause of PROVIDER-S14 needs
    no code of its own.
- **Parameters:** the four request classes leave the token out of their parameters.
  `Url.Param.API_TOKEN` goes, and with it ruff's one `S105` finding in `src/`.
- **Masking stays:** `_error_detail` and the re-raised request exceptions mask with
  `redact(text, (self._api_token,))`, and the request exceptions stay unchained. With no token in
  the URL, their messages carry none today; the masking guards against a provider page or a
  library message that echoes it.
- **Fakes:** `scripted_api` and `routed_api` record the `auth` of each call. The tests of
  PROVIDER-T01 apply it to a prepared request and assert the header, and that no parameter
  holds the token.
- **Redirect (PROVIDER-T30):** the token must reach eodhd.com and no other host, also when eodhd,
  or a proxy in between, answers with a redirect to another host. The test catches a change on
  either side: in how the package hands the token over, or in requests. It uses a
  `requests.Session` with a transport adapter mounted for `https://` that answers the first
  request with a 302 to another host and records both requests. No socket is opened, so it is a
  unit test.
- **Live (PROVIDER-T31):** in `tests/live/test_eodhd_contract.py`, with the demo token and
  `caplog` at DEBUG level on the root logger. Every live check with the demo token goes through
  the request layer, so a provider that stops taking the header fails the nightly run of
  `continuous-integration`.

## 3 Masking

### 3.1 The rule

`utils/redact.py` offers `redact(text, secrets=()) -> str` in place of `redact_api_token`:

1. **By value, first:** each secret of at least 8 characters (`_MIN_LENGTH_MASKED_BY_VALUE`), in
   three forms, the longest first: as it is, `quote(secret, safe="")` and
   `quote_plus(secret, safe="")`. This is plain `str.replace`, so characters such as `.` or `+`
   in a secret need no escaping. Going first, it also masks a secret with a space in it, where
   the name rule stops at the space.
2. **By name:** one regular expression, case-insensitive except for `Bearer`:

   ```python
   _NAME = r"(?:api_token|password)"
   _QUOTE = r"(?:['\"]|%22|%27)?"
   _SPACE = r"(?:\s|%20|\+)*"
   _SEPARATOR = rf"{_SPACE}(?:[=:]|%3[AD]){_SPACE}"
   _VALUE = r"(?:(?!%26|%22|%27)[^&\s'\",;)}\]])+"
   _PATTERN = re.compile(rf"({_NAME}{_QUOTE}{_SEPARATOR}{_QUOTE}|(?-i:Bearer)\s+){_VALUE}", re.IGNORECASE)
   ```

   Encoded forms appear when a whole URL or a JSON body becomes a parameter of another URL, e.g.
   a redirect's `next=…` or an error page that quotes the request. The parts:

   | Part | Matches | Example |
   | ---- | ------- | ------- |
   | `_NAME` | the name, also inside a longer one | `api_token`, `EODHD_API_TOKEN`, `QUESTDB_PASSWORD` |
   | `_QUOTE` | an optional quote after the name and before the value; `%22` is `"`, `%27` is `'` | `"api_token": "…"`; `%22api_token%22%3A%22…%22`, JSON inside a URL |
   | `_SPACE` | white space around the separator; `%20`, or `+` in a form | `%27api_token%27%3A%20%27…%27`, a printed dict inside a URL |
   | `_SEPARATOR` | `=` or `:`; `%3D` is `=`, `%3A` is `:`, in either case (`%3d`) | `api_token%3D…`, a URL inside another URL |
   | `_VALUE` | the secret, up to `&`, white space, a quote, comma, semicolon or closing bracket, or an encoded `&` (`%26`) or quote | in `api_token%3DSECRET%26fmt%3Djson` only `SECRET` |
   | `Bearer` | the value after it, case-sensitive | `Authorization: Bearer …` |

   `api_token` matches inside `EODHD_API_TOKEN`, and `password` inside `QUESTDB_PASSWORD`.
   `api_token_hint=` doesn't match, since a separator must follow the name. `Bearer` is
   case-sensitive, so that "the bearer of" in prose stays.

- `REDACTED` stays `***`. `utils/__init__.py` exports `redact` instead of `redact_api_token`.
- A short secret with a space, quoted after its name, is masked up to the space
  (`password='x y'` gives `password='*** y'`). This is the length floor at work (LOGGING-S05).

### 3.2 Where it runs

| Place | Secrets masked by value | From |
| ----- | ----------------------- | ---- |
| request layer: `_error_detail`, the re-raised request exceptions | the token of the request class | its construction |
| log formatter (`_RedactingFormatter`) | the token and the password the command line hands over | the call of `mask_secrets` |
| database errors | none: not masked (section 4) | — |

- **Formatter:** `_RedactingFormatter` holds a tuple of secrets, empty when `start_logger` builds
  it. `logger.mask_secrets(*secrets)` sets the tuple on the formatter the installed handlers
  share.
- **Command line:** `_run` calls
  `mask_secrets(client.config.eodhd_api_token, client.config.questdb_password)` right after
  `Client()`. Before that only names are masked, and a `ConfigError` names variables, never
  values.
- **Library callers** attach their own handlers and get no formatter from the package. The
  package's records are clean at the source (RUNS-S12), and with the token in the header, so
  are the records of requests and urllib3.

### 3.3 Tests

- **LOGGING-T06** replaces the parametrised cases of `test_redact.py` with the spellings and
  forms of LOGGING-S05; the four tests there move from LOGGING-T05 to LOGGING-T06.
- **LOGGING-T07** adds two `@given` tests to `test_redact.py`:
  - any secret of at least 8 characters (any character but surrogates and control characters),
    in any of its three forms, between any two texts: the output holds none of the forms, unless
    the surrounding text held one already;
  - any value of URL-safe characters after any name spelling and separator of LOGGING-S05,
    encoded quotes and spaces included, between any two texts: the output holds the name, the
    separator and `***`.
- **PROVIDER-T02:** any `st.text()` as a code; `_path_segment(code)` holds none of `/`, `?`, `#`,
  and `unquote` gives `code` back.
- **hypothesis settings:** the defaults, 100 examples per test, well within the 30 s limit of a
  unit test (QUALITY-S08). A failure prints the shrunk example and a blob that reproduces it.
  `.hypothesis/`, its local example database, goes into `.gitignore`.

## 4 Password in database errors

- **Not masked at the source** (section 7).
- **Tests instead (STORAGE-T39),** with a `Config` holding a wrong password, against the test
  database:
  - `Query.execute` raises `QueryError`: the existing test
    `test_the_error_of_a_rejected_login_does_not_echo_the_password`, extended to the chained
    error, moves from STORAGE-T29 to STORAGE-T39;
  - `setup` raises `DbError`;
  - `Insert.table` with a small frame of daily bars raises `InsertError`, and the log holds no
    retry warning;
  - each asserts that the password is in neither `str(error)` nor `str(error.__cause__)`.
  - If the write succeeds, the instance takes ingestion without a login, and the ingestion test
    is skipped with that reason.
- **Container:** the fixture of CI-S11 sets `QDB_HTTP_USER=admin` and `QDB_HTTP_PASSWORD=quest`
  besides `QDB_LINE_AUTO_CREATE_NEW_COLUMNS=false`; QuestDB reads them as `http.user` and
  `http.password`. The local test service has the same two settings, so the override needs no
  change.
- **Production:** without `http.user` and `http.password`, QuestDB's HTTP port asks no one for a
  login. Anyone who can reach port 9000 (QuestDB binds `0.0.0.0` by default) can write through
  ingestion and run any SQL statement, `DROP TABLE` included, through its REST endpoint and web
  console, and the password the package sends is ignored. The README's section "QuestDB server
  settings" asks for both settings next to `line.auto.create.new.columns`, and for a password
  other than the default `quest` on both interfaces (`pg.password` too). The code doesn't check
  them yet. `SHOW PARAMETERS` shows `http.user` and, for each password, whether it is still the
  default, without revealing it, so `library-contract` can warn about both in its check of the
  server settings (`1_specs.md`, Not done).

## 5 Security lint

On top of the configuration of `code-hygiene`:

```toml
[tool.ruff.lint]
extend-select = ["G", "N", "S"]
ignore = ["DTZ"]

[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["F401"]
# pytest checks with assert; the tests use fake secrets and build SQL from table names
"tests/**" = ["S101", "S105", "S106", "S608"]
# Names from the table constants only; values go in as parameters or quoted literals (STORAGE-S17).
# schema-from-code replaces these modules with its SQL builder, and this line goes.
"src/markethistorydb/db/statements/*.py" = ["S608"]
```

What the ignores mean:

- **`"tests/**"`:** `S101` reports every `assert`, since `python -O` strips asserts; pytest checks
  with `assert`. `S105` and `S106` report a string given to a name containing "password",
  "token" or "secret"; the tests use fake ones, e.g.
  `Config(eodhd_api_token="token", questdb_password="secret")`. `S608` reports SQL text built
  from strings; the tests build it from table names to look at what is stored.
- **`"src/markethistorydb/db/statements/*.py" = ["S608"]`:** `S608` ("possible SQL injection")
  reports every SQL text built with an f-string or `.format`, because a value from outside placed
  in the text could change the statement. The modules in `db/statements/` build every statement
  that way, but only from names the code defines itself, e.g.
  `f"SELECT {_COLUMNS} FROM {_TABLE} WHERE {_EXCHANGE_CODE}=%s"`. The values reach the database
  apart from that text: as parameters (`%s`), or, for the symbol codes of the price reads, as
  literals that psycopg quotes (`{symbol_codes}`, ACCESS-S09). So every finding there is a false
  alarm. The ignore names only these modules: SQL text built from strings anywhere else in
  `src/` is still reported. `schema-from-code` replaces the modules with a SQL builder, and the
  line is deleted then.

- **Findings:** with these ignores, and `Url.Param.API_TOKEN` gone (section 2), ruff reports no
  `S` finding (section 7).
- **Enforced by:** *lint*, required since `code-hygiene`, so the rules block a merge from then
  on.
- **Test:** QUALITY-T11 verifies them; its text stays. The ignores are checked once by hand in
  issue 4: an f-string statement in `db/io/` and `requests.get(..., verify=False)` are both
  reported.

## 6 hypothesis

`uv add --dev hypothesis`: 6.170.11 on 2026-10-26, under the MPL 2.0, a development dependency only
(PACKAGING-S03). The README's development section names it with the other tools, and on merge
`5_test.md` 1 names it with the test tools, for the property tests (LOGGING-T07, PROVIDER-T02).

## 7 Decisions

| Decision | Choice | Options considered | Reason |
| -------- | ------ | ------------------ | ------ |
| How the token travels | `Authorization: Bearer <token>` | query parameter `api_token`, with a known gap for urllib3's DEBUG record; query parameter, with a masking filter on the `urllib3.connectionpool` logger during a fetch | decided on 2026-10-26: no URL holds the token, so neither request exceptions nor urllib3's log nor a redirect carry it. eodhd accepts the header on all five endpoints, with answers identical to the query parameter, and answers a wrong token with 401 (checked on 2026-10-26 with the demo token). Its quick-start documents only `api_token`; the nightly live checks notice a change. A filter would configure a logger the program owns (CLIENT-S02). |
| Header through | an auth object (`auth=`) | a header dict (`headers=`) | a `.netrc` entry for eodhd.com replaces a header set by hand; with an auth object, requests skips `.netrc` (requests 2.34.2) |
| Spellings masked by name | names ending in `api_token` or `password`, any case, separator and quotes plain or percent-encoded; `Bearer` | today's lower-case `api_token` with plain separators | decided on 2026-10-26 |
| Masking by value | each configured secret of at least 8 characters, as it is and percent-encoded | none; any length | decided on 2026-10-26: short values hit ordinary text, e.g. the demo token `demo`, and the default password `quest` in every traceback path `site-packages/questdb/`. Both properties of LOGGING-T07 held over 6,000 generated cases in a scratch prototype (4.8 s). |
| Password in database errors | masked by the log formatter; errors unchanged; tests pin rejected logins | also mask where the three errors are built, cutting the chain to a client error that held it; formatter only | decided on 2026-10-26: neither client puts the password into its errors (18 failure cases checked on 2026-10-26 against the test service: rejected logins, unreachable hosts, malformed settings). A masked message would change nothing in a traceback, which prints the client's chained error too. |
| Login of the CI container over HTTP | required, `admin`/`quest` | QuestDB's default, no login over HTTP | a rejected ingestion login can only be tested against a server that asks for one; the local test service asks too |
| hypothesis | a development dependency, for the masking and for PROVIDER-S02 | the masking only; hand-picked cases | decided on 2026-10-26 |
| ruff's `S` rules | all, with per-file ignores: `S101`, `S105`, `S106`, `S608` in the tests; `S608` in `db/statements/` | `# noqa: S608` on each statement; the statements rewritten with `psycopg.sql` | decided on 2026-10-26: the ignores cover only false alarms, and every other module stays fully checked. 639 findings on 2026-10-26 (ruff 0.16.7, before `code-hygiene`), all false alarms, in four rules. |

## 8 Implementation

| # | Issue | Covers |
| - | ----- | ------ |
| 1 | Masking: `redact` by name and by value, the formatter's secrets, the command line's hand-over; hypothesis as a development dependency; the property tests | LOGGING-S04, S05, T05, T06, T07; PROVIDER-T02; PACKAGING-S03 |
| 2 | The token in the `Authorization` header: the auth object, no token in the parameters, `Url.Param.API_TOKEN` removed, the request layer masking by value; the fakes record `auth`; the redirect and live checks | PROVIDER-S01, S14, T01, T15, T30, T31 |
| 3 | The password in database errors: the container's login over HTTP; the tests of rejected logins; the README's server settings | STORAGE-S18, S23, T29, T39; CI-S11, T14 |
| 4 | The `S` rules and their ignores; the merge into the global files | QUALITY-S11 |

- **Order:** 1, then 2, which masks with `redact`; 3 at any time; 4 last, once issue 2 has
  removed the one finding in `src/`.
- **Earlier features:** all four issues come after `code-hygiene`. Issue 2 builds on its HTTP
  session (PROVIDER-S24), issue 4 on its ruff configuration and the required *lint*, and issue 3
  on the container of `continuous-integration`.

## 9 Open questions

1. **Is the header supported?** eodhd's documentation names only the query parameter. Their
   support could confirm the header as a supported way; until then, the nightly live checks are
   the guard. If they say no, the token goes back into the query, and urllib3's DEBUG record
   becomes a known gap.

## 10 Changes to `4_design.md` on merge

- **1.4 (external dependencies):** the QuestDB server's login over HTTP (`http.user`,
  `http.password`) and a password other than `quest`, recommended and not checked.
- **3.6 (running SQL):** the errors aren't masked: the clients don't put the password into their
  messages, and STORAGE-T39 pins that.
- **4.2 (request flow):** the auth object; the parameters without the token.
- **4.5 (keeping the token out of messages):** rewritten. The token travels in the header, so no
  URL holds it; `_error_detail` and the request exceptions mask by name and by value.
- **11.4 (secrets):** the command line hands the token and the password to the log masking.
- **13 (LOGGING):** the title becomes "log output and masking of secrets", as do those of
  `3_specs.md` 11 and `5_test.md` 12 and the capability tables. 13.1 names `redact` and
  `mask_secrets`. 13.3 becomes "Masking of secrets", with the rule and the places of section 3.
- **14.1 (project files):** hypothesis in the development group; `.hypothesis/` ignored.
- **15 (QUALITY):** the row for lint names the `S` rules and their per-file ignores.
- **Appendix A:**
  - "The API token is masked twice" becomes "Secrets are masked twice", by name and, from 8
    characters, by value.
  - "The API token travels only as a query parameter" becomes "The API token travels only in
    the `Authorization` header", with the reason and the consequence of the first decision.
  - A new row: database errors aren't masked, since the clients don't echo the password; a test
    pins it.
- **Known limitations:** none removed.
