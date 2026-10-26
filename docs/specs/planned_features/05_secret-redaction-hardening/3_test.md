# secret-redaction-hardening: test changes

## Test case changes

### Requests

| Change | ID | Test case | Verifies | Level | Status | Implemented by |
| ------ | -- | --------- | -------- | ----- | ------ | -------------- |
| MODIFIED | PROVIDER-T01 | Each endpoint has its documented address, and each request class asks its endpoint with `fmt=json` and with the token in the `Authorization` header, in no query parameter; a successful answer is returned as parsed JSON. | PROVIDER-S01 | unit | Missing | — |
| MODIFIED | PROVIDER-T02 | Ordinary codes stay readable; any symbol or exchange code that hypothesis generates, `/`, `?`, `#` and `%` included, stays within its path segment, and `unquote` gives it back unchanged. | PROVIDER-S02 | unit | Missing | — |
| MODIFIED | PROVIDER-T15 | The error message is limited in length however long the body; an error page echoing the token after its name or on its own, plain or percent-encoded, a token at the cut-off point, and a request exception carrying the token never put the token into the raised error. | PROVIDER-S14 | unit | Missing | — |
| ADDED | PROVIDER-T30 | Given a session whose transport answers a request to eodhd.com with a redirect to another host, then the request to eodhd.com carries the token in the `Authorization` header, and the redirected request carries no `Authorization` header. | PROVIDER-S14 | unit | Missing | — |
| ADDED | PROVIDER-T31 | Given the demo token and every logger at DEBUG level, when AAPL's end-of-day bars are requested through the request layer, then bars arrive, and no log record of any logger, urllib3's included, holds `api_token` or the token. | PROVIDER-S01, PROVIDER-S14 | live | Missing | — |

### Masking

| Change | ID | Test case | Verifies | Level | Status | Implemented by |
| ------ | -- | --------- | -------- | ----- | ------ | -------------- |
| MODIFIED | LOGGING-T05 | The secrets are masked in a record's message, its arguments and its traceback, by every handler, in the file too. Once the command line has created its client, an error message holding the client's token or password is logged masked by value. | LOGGING-S04 | unit | Missing | — |
| ADDED | LOGGING-T06 | Case by case: each name (`api_token`, `EODHD_API_TOKEN`, `password`, `QUESTDB_PASSWORD`) in lower and in upper case, after `=` or `:`, quoted or not, plain and percent-encoded, at the start, in the middle and at the end of a query; a printed dict, plain and percent-encoded (`%27api_token%27%3A%20%27…%27`); the token after `Bearer `; every occurrence on a line and on every line; a configured secret of 8 characters masked by value as it is, percent-encoded and form-encoded, one of 7 characters only after its name. Text without a secret, `api_token_hint=keep`, `passwords: 3` and "the bearer of" stay unchanged. | LOGGING-S05 | unit | Missing | — |
| ADDED | LOGGING-T07 | Properties, with hypothesis: for any secret of at least 8 characters, in any of its three forms, and any text around it, the masked text holds none of the forms; for any value of URL-safe characters after any name and separator of LOGGING-S05, the masked text holds the name and the separator followed by `***`. | LOGGING-S05 | unit | Missing | — |

### Database password

| Change | ID | Test case | Verifies | Level | Status | Implemented by |
| ------ | -- | --------- | -------- | ----- | ------ | -------------- |
| MODIFIED | STORAGE-T29 | Given invalid SQL, a table that does not exist, or a wrong password, then `QueryError` is raised. | STORAGE-S18 | integration | Implemented | `integration/db/io/test_query.py`: `test_invalid_sql_is_a_query_error`, `test_a_table_that_does_not_exist_is_a_query_error`, `test_a_wrong_password_is_rejected` |
| ADDED | STORAGE-T39 | Given a wrong password, then the errors of a statement (`QueryError`), of `setup` (`DbError`) and of a write through the ingestion interface (`InsertError`, without a retry) hold the password neither in their messages nor in the errors they are chained to. Against a test database that takes ingestion without a login, the ingestion part is skipped. | STORAGE-S23 | integration | Missing | — |
| MODIFIED | CI-T14 | Without `QUESTDB_TEST_*` and with Docker, the integration tests run against a container of the pinned version with `line.auto.create.new.columns=false` and a login required over HTTP, and the container is gone after the session. | CI-S11, QUALITY-S04 | integration | Missing | — |
