# continuous-integration: design

## 1 Overview

| Part | Files and settings |
| ---- | ------------------ |
| repository | GitHub repository `markethistorydb`, public; a ruleset protecting `main`; the environment `nightly` with the secret `EODHD_API_TOKEN` |
| checks of every change | `.github/workflows/ci.yml` |
| nightly checks | `.github/workflows/nightly.yml`, `.github/scripts/live_summary.py` |
| action updates | `.github/dependabot.yml` |
| integration database | `tests/integration/conftest.py` (container fixture, override) |
| lock file | `uv.lock` tracked; its line removed from `.gitignore` |

### 1.1 GitHub Actions in brief

Everything in this feature runs on GitHub's machines, never on your computer. For public
repositories they are free of charge.

| Term | Meaning here |
| ---- | ------------ |
| **workflow** | a YAML file in `.github/workflows/`; it says when it runs and what it does. This feature has two: `ci.yml` and `nightly.yml` |
| **trigger** (event) | what starts a workflow: `pull_request` (a pull request is opened or gets new commits), `push` (commits arrive on a branch), `schedule` (a time), `workflow_dispatch` (a "Run workflow" button on GitHub) |
| **job** | a part of a workflow that runs on its own fresh virtual machine; the jobs of one workflow run in parallel |
| **runner** | that machine, provided by GitHub: `ubuntu-latest` (Linux) or `windows-latest`; it starts empty and is thrown away after the job |
| **step** | one command of a job (`run: uv run pytest ...`) or one *action* |
| **action** | a reusable step published in a GitHub repository, used as `uses: owner/repo@ref`, e.g. `actions/checkout` (fetches the code) or `astral-sh/setup-uv` (installs uv) |
| **matrix** | one job definition that GitHub expands into several jobs, one per combination of values: `os: [ubuntu, windows]` × `python: [3.12, newest]` gives 4 jobs |
| **check** | the result of a job, shown as a green tick or a red cross on the pull request |
| **required check** | a check that must be green before the pull request can be merged |
| **secret** | a value stored encrypted by GitHub (here the eodhd token), handed to a job as an environment variable and masked as `***` in its logs |
| **environment** | a named set of secrets with rules, e.g. "only for the branch `main`"; a job gets those secrets only if it names the environment |
| **`GITHUB_TOKEN`** | a token GitHub creates for every run, so that steps can talk to the repository (e.g. write annotations); it expires with the run |
| **run summary** | a page of each run; Markdown that a step appends to the file named by `$GITHUB_STEP_SUMMARY` appears there |
| **Dependabot** | a GitHub service that looks for newer versions of what the repository uses and opens pull requests that update them |

## 2 Repository

- **Push:** create the empty repository on GitHub, add it as `origin`, push `main` and the tag
  `v0.1.0`.
- **Ruleset for `main`** (Settings → Rules → Rulesets):
  - changes only through pull requests;
  - required checks: the four *unit* jobs, *integration*, *build* and *audit*;
  - the branch must be up to date with `main` before merging, so the checks have seen the final
    combination;
  - merge commits only (no squash, no rebase), matching the `--no-ff` workflow of
    `1_constitution.md` 5.3;
  - no force pushes and no deletion of `main`.
- **Secret and environment** (Settings → Environments → New environment): the environment
  `nightly` holds the secret `EODHD_API_TOKEN`, and its deployment rule allows the branch `main`
  only. Only the jobs of `nightly.yml` name it (`environment: nightly`); a job of any other
  workflow, or on another branch, gets no token.
- **`pull_request`, not `pull_request_target`:** both triggers react to pull requests.
  - `pull_request` runs the workflow as the pull request's branch defines it, and for a pull
    request from a fork without any secrets: a stranger's code never sees the token.
  - `pull_request_target` runs the workflow as `main` defines it, *with* the repository's secrets
    and a writable token. It exists for tasks such as labelling pull requests; combined with a
    checkout of the pull request's code, it would hand the secrets to that code.

  The workflows use `pull_request` only.
- **Actions settings** (Settings → Actions → General):
  - "Require actions to be pinned to a full-length commit SHA" is on (section 6);
  - workflow permissions "Read repository contents": the `GITHUB_TOKEN` can't push code or change
    settings. A workflow that needs more (e.g. to annotate pull requests) asks for it in a
    `permissions:` block, for itself only.

## 3 Workflow `ci.yml`

### 3.1 What happens on a pull request

1. You push a branch and open a pull request, or push more commits to it.
2. GitHub starts `ci.yml`: ten jobs on fresh machines, in parallel. Each checks out the branch,
   installs uv, installs the locked dependencies and runs its command.
3. The pull request shows one check per job. After a few minutes, all are green, or the red ones
   link to their log.
4. When the required checks are green and the branch is up to date, the merge button is enabled.
   After the merge, `ci.yml` runs once more on `main` (trigger `push`).

### 3.2 Jobs

| Job | Runner | Python | Steps | Required |
| --- | ------ | ------ | ----- | -------- |
| unit | `ubuntu-latest`, `windows-latest` | 3.12, newest stable | `uv sync --locked`; `uv run pytest -m unit --cov` | yes (4 jobs) |
| integration | `ubuntu-latest` | 3.12 | `uv sync --locked`; `uv run pytest -m integration`; the fixture starts the container | yes |
| build | `ubuntu-latest` | 3.12 | `uv build`; check the wheel's file list; install the wheel into a new environment; run `markethistorydb --help` and `python -m markethistorydb --help` | yes |
| audit | `ubuntu-latest` | 3.12 | `uv export --locked --format requirements-txt` piped into `pip-audit` | yes |
| lint | `ubuntu-latest` | 3.12 | `uv run ruff check --output-format github` | no |
| types | `ubuntu-latest` | 3.12 | `uv run pyright`, findings as annotations | no |

- **The matrix:** *unit* is one job definition with `os: [ubuntu-latest, windows-latest]` and
  `python: ["3.12", "<newest>"]`, which GitHub expands into four jobs. Windows matters because
  the code runs on your Windows machine (paths, time zones), Linux because servers and the
  container run it.
- **Newest stable Python release:** one entry of the matrix, written out (e.g. `"3.14"`). It is
  raised by hand, in a pull request of its own, when a new Python version is out *and* has had its
  first bugfix release (x.y.1). New versions come out every October, and the packages this project
  depends on (pandas, psycopg's binary wheels, the QuestDB client) often need weeks to publish
  builds for them. Raising it automatically would turn each release into red checks that say
  nothing about this project. `requires-python` stays `>=3.12`.
  - *Python* means CPython here, the standard implementation from python.org, which uv installs.
    Other implementations, such as PyPy, aren't tested.
- **Cancelling outdated runs:** `concurrency: { group: ci-${{ github.ref }}, cancel-in-progress:
  true }`. `github.ref` names the branch (for a pull request, the pull request), so every branch
  has its own group. When you push again while a run of the same branch is still going, GitHub
  cancels the old run and starts a new one, since the old commit's results no longer matter.
  Different branches don't cancel each other.
- **uv:** `astral-sh/setup-uv` installs uv and keeps a cache of downloaded packages keyed on
  `uv.lock`, so later runs don't download everything again; uv installs the Python version of the
  matrix itself.
- **Reporting jobs:** *lint* and *types* have `continue-on-error: true` and aren't required. Their
  findings appear as annotations next to the lines of the pull request's diff, without blocking
  it. `code-hygiene` makes *lint* required, `library-contract` makes *types* required.
- **pyright:** a dev dependency, configured in `pyproject.toml` (`[tool.pyright]`,
  `typeCheckingMode = "basic"`, `include = ["src"]`).
- **Live tests:** each job selects its level with `-m`, so live tests never run in `ci.yml`,
  whatever the local default is (QA-6, `test-suite-hardening`).

### 3.3 Sketch

```yaml
name: ci
on:
  pull_request:
  push:
    branches: [main]
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true
permissions:
  contents: read
jobs:
  unit:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest]
        python: ["3.12", "3.14"]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@<sha> # v4.2.2
      - uses: astral-sh/setup-uv@<sha> # v6.x
        with:
          python-version: ${{ matrix.python }}
          enable-cache: true
      - run: uv sync --locked
      - run: uv run pytest -m unit --cov
  integration:
    runs-on: ubuntu-latest
    steps:
      # checkout and setup-uv as above
      - run: uv sync --locked
      - run: uv run pytest -m integration
  # build, audit, lint and types alike
```

## 4 Workflow `nightly.yml`

### 4.1 When and where it runs

- **On GitHub, every night:** `schedule: - cron: "17 3 * * *"`. The five fields are minute, hour,
  day of month, month and day of week; `17 3 * * *` means 03:17 every day, always in UTC. GitHub
  starts scheduled runs late when its runners are busy, and full hours are the busiest, hence
  minute 17.
- **On demand:** `workflow_dispatch` adds a "Run workflow" button to the workflow's page (tab
  "Actions"), for a run outside the schedule, e.g. right after setting the secret.
- **From `main` only:** GitHub runs scheduled workflows from the default branch only.
- **Inactivity:** GitHub disables the scheduled workflows of a public repository after 60 days
  without a commit. A long pause therefore stops the nightly runs; they are switched on again on
  the workflow's page.
- **Notifications:** GitHub mails the owner when a scheduled run fails.

### 4.2 Jobs

| Job | Environment | Steps |
| --- | ----------- | ----- |
| live | `nightly` (gets the token) | `uv sync --locked`; `uv run pytest -m live -rs --junitxml=live.xml`; `uv run python .github/scripts/live_summary.py live.xml >> "$GITHUB_STEP_SUMMARY"` |
| integration-latest | none | `QUESTDB_TEST_IMAGE=questdb/questdb:latest uv run pytest -m integration`, with `continue-on-error: true`; a failure becomes a warning in the summary |
| audit | none | as in `ci.yml`, so a new advisory is noticed even without a pull request |

The pytest options of *live*:

- `-m live` selects the live tests;
- `-rs` adds the skipped tests with their reasons to the end of the job's log (`-r` chooses what
  the closing report lists, `s` stands for skipped);
- `--junitxml=live.xml` also writes the results to `live.xml` in JUnit XML, a standard format
  with one entry per test: its name, its outcome, and the message of a failure or skip.

The summary step runs `live_summary.py` on `live.xml`. The script prints Markdown, and
`>> "$GITHUB_STEP_SUMMARY"` appends it to the file that GitHub shows as the run's summary page.
The step runs even when tests failed (`if: always()`), so the summary is there in either case.

### 4.3 The live summary

`live_summary.py` turns `live.xml` into this page:

```
Account checks: not run (DataLimitError)

Passed (13)       test_daily_prices_have_the_sample_s_shape, ...
Failed (0)
Not checked (5)   test_exchanges_have_the_sample_s_shape: account refused: DataLimitError
                  ...
```

- A skip whose reason starts with "eodhd.com refused EODHD_API_TOKEN (" is shown as "account
  refused: <error type>"; other skips keep their reason.
- The first line says whether the account's tests ran. The account is refused most nights, so
  this line tells a quiet night from a checked one.
- A failure among the tests that use the demo token fails the job, and so the run.

The live tests already skip when the account is refused (`_request_with_account_token` in
`tests/live/test_eodhd_contract.py`); the script only makes that readable.

### 4.4 Not done

No memory across nights, such as "account checks last ran 40 days ago": it would need a cache or
an artifact for one number. Each night's summary is enough to see the pattern.

## 5 The container fixture

### 5.1 Choosing the database

A pure function decides where the integration tests run:

`choose_test_database(environment: Mapping[str, str], docker_available: bool) -> Override | Container | Skip`

It reads nothing but its arguments, so its branches are unit-tested with plain values, without
Docker or a database (CI-T13; testing rule 1 of `1_constitution.md` 5.1):

| `QUESTDB_TEST_*` set | Docker reachable | Result |
| -------------------- | ---------------- | ------ |
| yes | either | `Override(host, ports, user, password)` |
| no | yes | `Container(image)`: `QUESTDB_TEST_IMAGE` if set, else `questdb/questdb:10.0.1` |
| no | no | `Skip("No test QuestDB: set QUESTDB_TEST_* or install Docker")` |

### 5.2 Acting on the choice

The session fixture `questdb_config` calls the function, then does the I/O:

1. **Override,** as today: stop the run (exit code 3) if the instance is the application's
   QuestDB; connect within 2 s or skip; build the `Config`.
2. **Container:** start the image as a `testcontainers` `DockerContainer` with
   `QDB_LINE_AUTO_CREATE_NEW_COLUMNS=false`, exposing 8812 (SQL) and 9000 (HTTP); wait until
   `SELECT 1` succeeds, at most 60 s; build the `Config` from the container's host and mapped
   ports (user `admin`, password `quest`); stop and remove the container when the session ends.
3. **Skip:** `pytest.skip` with the message.

`fresh_db` still sets the tables up before each test (QUALITY-S04). Faster resets, truncating
instead of dropping, stay with `test-suite-hardening`.

- **Windows:** GitHub's Windows runners can't run Linux containers, so integration tests run on
  Linux in CI. Locally on Windows, Docker Desktop with Linux containers works; without it, the
  override with your local test service stays.
- **Pinned version:** 10.0.1, the version of the local test service the error-message tests were
  written against (`SELECT build()` on 2026-10-19). Raising it is a deliberate change, prepared
  by the nightly run against `latest` (CI-S10).

## 6 Pinned actions and Dependabot

- **Why pin:** `uses: actions/checkout@v4` names a tag. The owner of the action can move a tag to
  any commit, so a hijacked account can make every workflow that uses `@v4` run new code, with
  that workflow's token and secrets; this happened to the widely used action
  `tj-actions/changed-files` in March 2025. A commit SHA can't be moved: the code behind
  `actions/checkout@<40 hex characters>` stays what it was when it was chosen. The comment
  `# v4.2.2` keeps it readable.
- **Why Dependabot:** pinned versions don't update themselves. `.github/dependabot.yml` has one
  entry, `package-ecosystem: github-actions` with `interval: weekly`. Once a week, Dependabot
  looks for newer versions of each action and opens one pull request per update, replacing SHA
  and comment. CI runs on it; if it's green, you merge it.
- **Python dependencies aren't included.** The lock file is updated deliberately, about once a
  month or for an advisory: `uv lock --upgrade` in one pull request of its own, so that the
  integration tests check the new pandas, psycopg and QuestDB client together, and the history
  shows one update instead of a pull request per package. The *audit* job reports advisories in
  between.

## 7 Decisions

| Decision | Choice | Reason |
| -------- | ------ | ------ |
| Repository visibility | public from the start | unlimited free Actions minutes; the license follows in `publishing-readiness` |
| DG-9 (decision gate of `6_roadmap.md`: lock file and Python versions), lock file | `uv.lock` tracked | reproducible CI; library users still resolve against the ranges of `pyproject.toml` |
| DG-9, Python versions | 3.12 and the newest stable release | covers the supported range at half the cost of every version |
| Integration database | testcontainers, override kept | same behaviour on any machine with Docker and in CI; the override keeps machines without Docker working |
| Live tests | nightly with the token, refusals shown as "not checked" | provider changes are noticed within a day; a refused account must read neither as a failure nor as a pass |
| Audit tool | `pip-audit` on the exported lock | reads a requirements file, uses PyPI's advisory data; no account needed |
| Pinning of the GitHub actions | full commit SHA, Dependabot for updates | a tag can be moved to other code, a SHA can't (section 6) |

## 8 Implementation

Like every planned feature, this one is split into issues, one branch each (`1_constitution.md`
6.3, step 4). Issues 1 to 4 come before the repository exists or create it, so none of them is a
GitHub issue: the branches of 1 to 3 are merged locally with `--no-ff` (`1_constitution.md`
5.3), and 4 is settings on GitHub. From issue 5 on, each issue is a GitHub issue with one pull
request. Proposed issues, in this order:

| # | Issue | Pull request |
| - | ----- | ------------ |
| 1 | Track `uv.lock` | no: merged locally |
| 2 | Container fixture, with the unit tests of `choose_test_database`; testcontainers as dev dependency | no: merged locally |
| 3 | `ci.yml`, `dependabot.yml`, pyright as dev dependency | no: merged locally |
| 4 | Create the repository, push `main` and `v0.1.0`; ruleset; environment `nightly` with the secret | no: settings on GitHub; the first run of `ci.yml` starts with the push |
| 5 | `nightly.yml` and `live_summary.py` with its unit tests; one manual run | yes |
| 6 | Demonstration pull requests for the *ci* test cases (a failing test, coverage below 100 %, an outdated lock, a vulnerable pin), closed without merging | yes, not merged |
| 7 | The merge into the global files (`1_constitution.md` 6.4): this feature's specification, design and test changes, with the *ci* test cases Implemented by the demonstration pull requests of issue 6 and the runs of issues 4 and 5 | yes |

Issues 1 to 3 are done before the repository exists, so its first push already carries CI. The
ruleset chooses required checks by job name, which GitHub knows only after a first run; hence the
ruleset comes after the push.

## 9 Open questions

- **Docker tag:** answered on 2026-11-01: the tag `questdb/questdb:10.0.1` exists on Docker Hub.
- **Account status first?** eodhd has an endpoint for the account's status (calls left,
  subscription). Asking it first would let the summary say why the account is refused before the
  tests run. Whether that request itself counts against the quota is unknown; check in issue 5,
  otherwise the skip reasons are enough.

## 10 Changes to `4_design.md` on merge

- New chapter "CI: continuous integration" with sections 1 to 7 of this file, shortened.
- `4_design.md` 14.1 (PACKAGING): `uv.lock` tracked.
- `4_design.md` 15 (QUALITY): the container fixture in the guarantees table.
- `4_design.md` 1.4 (external dependencies): Docker for local integration tests without the
  override.
- The terms of section 1.1 go to the glossary of `1_constitution.md`.
