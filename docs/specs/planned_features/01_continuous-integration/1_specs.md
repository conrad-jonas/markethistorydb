# continuous-integration: specification changes

State: In progress · Milestone: M0, first feature · Kind: new (capability CI) · Requirements:
QA-4, QA-7, QA-11 · Depends on: none · Decisions: DG-9 (lock file and Python versions) and the
repository's visibility, decided on 2026-10-19 (`2_design.md`, section 7)

## Why

Nothing checks a change before it reaches `main`: the tests, the coverage gate and the build run
only when someone runs them, and the integration tests need a hand-started database. Every later
feature is safer when CI checks its pull requests from the first one on, so this feature comes
first.

## Scope

**In:**

- the public GitHub repository, with the existing history pushed and `main` protected;
- a workflow for every pull request and every push to `main`: unit tests with the coverage gate
  on Linux and Windows and two Python versions, integration tests against a QuestDB container,
  the build with an installation check, a dependency audit, and ruff and pyright as reporting
  jobs;
- a nightly workflow: the live contract tests with the account's token, presented so that a
  refused account reads as "not checked", and the integration tests against the newest QuestDB
  release;
- a pytest fixture that starts QuestDB through testcontainers, with `QUESTDB_TEST_*` as an
  override;
- the lock file tracked in git;
- action versions pinned, and kept current by Dependabot.

**Out:**

- making ruff and pyright blocking: `code-hygiene` and `library-contract` do that once the code
  passes them;
- making live tests opt-in for local runs, and the other rules of the suite:
  `test-suite-hardening` (CI selects the levels explicitly until then);
- the nightly end-to-end test (real provider, container, setup, fetch, read back). It needs a
  fetch restricted to a few instruments (ING-15), so it moves to `ingestion-efficiency`, which
  brings that restriction;
- publishing to TestPyPI and PyPI, and deploying the docs site: `release-1-0`; building the docs
  in CI: `publishing-readiness`;
- performance and mutation tests: `data-integrity-checks`, `release-1-0`.

## Specification changes

New capability CI (`3_specs.md` gets a chapter "CI: continuous integration" on merge).

### Repository

| Change | ID | Specification | Satisfies |
| ------ | -- | ------------- | --------- |
| ADDED | CI-S01 | The project lives in a public GitHub repository. `main` accepts changes only through pull requests, and only when the required checks of CI-S03 have passed; force pushes and deletion of `main` are refused. A pull request is merged with a merge commit (`1_constitution.md` 5.3). | QA-4 |
| ADDED | CI-S02 | The API token is stored as a secret of the repository, available to the nightly workflow on `main` only. Workflows of pull requests, including those from forks, never get it. | QA-8 |

### Checks of every change

| Change | ID | Specification | Satisfies |
| ------ | -- | ------------- | --------- |
| ADDED | CI-S03 | Every pull request and every push to `main` runs these jobs; a newer push to the same branch cancels the run still going. **Required:** <br>• *unit*: `pytest -m unit --cov` on Linux and on Windows, each with Python 3.12 and the newest stable Python release, with the coverage gate of QUALITY-S02; <br>• *integration*: `pytest -m integration` on Linux with Python 3.12, against a QuestDB container (CI-S11); <br>• *build*: CI-S04; <br>• *audit*: CI-S05. <br>**Reporting only:** *lint* (`ruff check`) and *types* (`pyright`), whose findings appear as annotations of the pull request without failing it. | QA-4, QA-2, QA-7 |
| ADDED | CI-S04 | **Build check:** `uv build` produces a wheel and an sdist. The wheel is installed into a fresh environment, where `markethistorydb --help` and `python -m markethistorydb --help` exit with 0. The wheel holds the schema files of `setup/schema/` and no file of `CLAUDE.md`, `.claude/`, `tests/` or `docs/`. | DIST-1, QA-4 |
| ADDED | CI-S05 | **Dependency audit:** the locked dependencies are checked against a database of known vulnerabilities, on every pull request and nightly; a finding fails the job and names the package, the version and the advisory. | QA-11 |
| ADDED | CI-S06 | Every job installs exactly the locked dependencies (`uv sync --locked`); a lock file that doesn't match `pyproject.toml` fails the job. | QA-4, QA-7 |
| ADDED | CI-S07 | **Pinned actions:** every GitHub action a workflow uses is referenced by its full 40-character commit SHA, with the version as a comment, e.g. `uses: actions/checkout@<40 hex characters> # v4.2.2`, never by a tag such as `@v4` or a branch. The repository setting that refuses unpinned actions is on. **Updates:** Dependabot checks the actions once a week and opens one pull request per new version, with the new SHA; CI checks that pull request like any other, and it is merged by hand. | QA-11 |

### Nightly checks

| Change | ID | Specification | Satisfies |
| ------ | -- | ------------- | --------- |
| ADDED | CI-S08 | A nightly workflow runs on `main` every day at 03:17 UTC, and on demand. It runs the live tests (`pytest -m live`) with the token of CI-S02, and the integration tests against the newest QuestDB release in addition to the pinned one. | COR-17, QA-7 |
| ADDED | CI-S09 | **Presentation of the live results:** the summary of the nightly run lists three groups: *passed*, *failed*, and *not checked*, with the reason for each test not checked. A test the account can't run (the account is rejected, its calls are used up, or its plan doesn't cover the endpoint; PROVIDER-S22) is *not checked*, with the error type as reason, e.g. "account refused: DataLimitError". The run fails only when a test fails; tests not checked don't fail it. The tests that use the public demo token keep checking end-of-day bars, intraday bars and fundamentals however the account stands. | COR-17 |
| ADDED | CI-S10 | The run against the newest QuestDB release reports a failure as a warning in its summary without failing the nightly run; it shows that raising the pinned version (CI-S11) needs work. | QA-7 |
| MODIFIED | QUALITY-S02 | The unit tests run with branch coverage of `src/` and `.github/scripts/`; with `--cov`, the run fails below 100 % line and branch coverage. Excluded are only `if __name__ == "__main__":` blocks and abstract methods. | QA-2 |

### Integration database

| Change | ID | Specification | Satisfies |
| ------ | -- | ------------- | --------- |
| ADDED | CI-S11 | Without `QUESTDB_TEST_*`, the integration tests start QuestDB 10.0.1 once per session as a container, with `line.auto.create.new.columns=false`, wait until it answers SQL, and run against its mapped ports; the container is removed after the session. The version is pinned and raised deliberately. | QA-7 |
| MODIFIED | QUALITY-S03 | Integration tests run against the QuestDB named by `QUESTDB_TEST_HOST`, `QUESTDB_TEST_PG_PORT` and `QUESTDB_TEST_HTTP_PORT` (environment or `.env`) if these are set, and against the container of CI-S11 otherwise. If neither is possible (no variables and no Docker), or the named instance can't be reached within 2 s, they are skipped with a message naming both ways. If the named instance has the host and a port of the application's QuestDB (`QUESTDB_*`), the whole run stops with exit code 3 before any test. | QA-3, QA-7 |
| MODIFIED | QUALITY-S04 | Every integration test starts on empty tables, which it sets up itself; the instance is the container of CI-S11 or the one named by the override. | QA-7 |

### Contract checks and lock file

| Change | ID | Specification | Satisfies |
| ------ | -- | ------------- | --------- |
| MODIFIED | PROVIDER-S22 | Live contract checks call eodhd.com and compare every field and JSON type of the current answers of all five endpoints with the stored sample payloads (`tests/data/eodhd`), and run the request layer on the live answers. The public demo token serves end-of-day bars, intraday bars and fundamentals of AAPL.US; the exchange and symbol lists need the account's token and are skipped without it, or when the account is refused. They run nightly in CI (CI-S08, CI-S09). | COR-17 |
| ADDED | PACKAGING-S04 | `uv.lock` is tracked in git; the version ranges of `pyproject.toml` stay as they are for library users. | QA-4, QA-7 |

## Requirement status after the merge

| Requirement | Before | After |
| ----------- | ------ | ----- |
| QA-4 | Open | Partial: tests, build and audit block a merge; lint, types and architecture rules only report |
| QA-7 | Partial | Done |
| QA-11 | Open | Partial: dependencies are audited; the code isn't checked for security mistakes yet (`secret-redaction-hardening`) |
| COR-17 | Partial | Partial: the checks run nightly; value semantics are still not checked (`data-integrity-checks`) |

## Known gaps closed

| `3_specs.md` | Gap |
| ------------ | --- |
| 2.6 PROVIDER | The contract checks don't run on a schedule |
| 12.2 PACKAGING | `uv.lock` is ignored by git |
| 13.2 QUALITY | The integration database is started by hand; no container |
| 13.2 QUALITY | Nothing checks changes automatically before they are merged: no CI runs the tests or the build |
| 13.2 QUALITY | Dependencies aren't audited for known vulnerabilities |
