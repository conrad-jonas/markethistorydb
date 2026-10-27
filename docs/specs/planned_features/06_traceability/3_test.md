# traceability: test changes

## Test case changes

### Links from the tests

| Change | ID | Test case | Verifies | Level | Status | Implemented by |
| ------ | -- | --------- | -------- | ----- | ------ | -------------- |
| ADDED | QUALITY-T15 | Given test modules with `@pytest.mark.spec` on their functions, naming one ID or several, alone or above other decorators such as `parametrize`, then each function is linked to each test case it names. Given a module-level `pytestmark` with `spec`, a marker whose ID isn't a string literal, or a test function without the marker, then each is an error naming the module and the function. | QUALITY-S12, QUALITY-S15 | unit | Missing | — |
| ADDED | QUALITY-T16 | Given the repository, then `scripts/trace.py --check` reports no error: every test carries a marker, every link resolves, the statuses agree and `7_traceability.md` is current (the job *trace*). | QUALITY-S12, QUALITY-S13, QUALITY-S15 | static | Missing | — |

### Report

| Change | ID | Test case | Verifies | Level | Status | Implemented by |
| ------ | -- | --------- | -------- | ----- | ------ | -------------- |
| ADDED | QUALITY-T12 | Given the sample repository with every link in place, then the written `7_traceability.md` equals the expected file: the matrix, the tests of each test case, the gaps, the next free IDs, and a section per planned feature in roadmap order. A requirement that only a roadmap row assigns is listed as a gap with that row's feature. A second run writes the same text. | QUALITY-S13 | unit | Missing | — |
| ADDED | QUALITY-T13 | Given implemented and planned items and gap rows, then each requirement is Open, Partial or Done by the rule. After a feature's merge, with the features before it merged first: its ADDED and MODIFIED items count with their new Satisfies, its REMOVED items are gone, the gap rows naming it are closed and the rows it changes or adds apply. The items and gap rows of the features after it don't count. | QUALITY-S14 | unit | Missing | — |

### Check

| Change | ID | Test case | Verifies | Level | Status | Implemented by |
| ------ | -- | --------- | -------- | ----- | ------ | -------------- |
| ADDED | QUALITY-T14 | Given the sample repository changed in one place for each error of QUALITY-S15, one case per error, then `--check` prints that error naming its file and the ID, test or feature, ends with exit code 1 and writes nothing. Given the unchanged sample, which has Missing test cases and Open requirements, it ends with 0, also when `7_traceability.md` has CRLF line endings. | QUALITY-S15 | unit | Missing | — |
| MODIFIED | CI-T03 | A run of `ci.yml` shows four *unit* jobs (Linux and Windows, each with Python 3.12 and the newest stable Python release), and *integration*, *build*, *audit*, *lint*, *trace* and *types*; *types* reports findings without failing the run (the first run after issue 3). | CI-S03 | ci | Missing | — |
| ADDED | CI-T16 | Given a pull request that changes a Verifies cell of `5_test.md` without regenerating `7_traceability.md`, then *trace* fails, naming the stale file, and GitHub refuses the merge (demonstrated with a pull request). | CI-S03, QUALITY-S15 | ci | Missing | — |

### Coverage and lint of the script

| Change | ID | Test case | Verifies | Level | Status | Implemented by |
| ------ | -- | --------- | -------- | ----- | ------ | -------------- |
| MODIFIED | QUALITY-T02 | `uv run pytest -m unit --cov` passes only with 100 % line and branch coverage of `src/` and `scripts/` (`[tool.coverage]` in `pyproject.toml`). | QUALITY-S02 | suite | Missing | — |
| MODIFIED | QUALITY-T11 | Given `src/`, `tests/` and `scripts/`, then `ruff check` reports no finding and `ruff format --check` no file to reformat, with the configuration of QUALITY-S11; no file starts with a shebang (the job *lint*; `[tool.ruff]` in `pyproject.toml`). | QUALITY-S11 | static | Missing | — |
