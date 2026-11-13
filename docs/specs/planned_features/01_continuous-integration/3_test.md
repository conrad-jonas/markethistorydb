# continuous-integration: test changes

Most of this feature is configuration of GitHub. Its test cases are therefore of a new level,
*ci*: checked by a run of the workflows, often on a demonstration pull request that is closed
without merging (`2_design.md` 8, issue 6). The level is added to `5_test.md` 1.3 on merge. The
container fixture's choice of database gets unit tests.

## Test case changes

### Repository and checks

| Change | ID | Test case | Verifies | Level | Status | Implemented by |
| ------ | -- | --------- | -------- | ----- | ------ | -------------- |
| ADDED | CI-T01 | Given a pull request whose branch adds a failing unit test, then the *unit* checks fail and GitHub refuses the merge; a direct push to `main` is refused. | CI-S01, CI-S03 | ci | Missing | demonstration pull request |
| ADDED | CI-T02 | Given a pull request that lowers the coverage below 100 %, then the *unit* checks fail. | CI-S03 | ci | Missing | demonstration pull request |
| ADDED | CI-T03 | A run of `ci.yml` shows four *unit* jobs (Linux and Windows, each with Python 3.12 and the newest stable Python release), and *integration*, *build*, *audit*, *lint* and *types*; *lint* and *types* report findings without failing the run. | CI-S03 | ci | Missing | first run after the push |
| ADDED | CI-T04 | A second push to a branch while its run is going cancels the older run. | CI-S03 | ci | Missing | demonstration pull request |
| ADDED | CI-T05 | The *build* job builds a wheel and an sdist; the installed wheel answers `markethistorydb --help` and `python -m markethistorydb --help` with exit code 0; the wheel holds the schema files and none of `CLAUDE.md`, `.claude/`, `tests/`, `docs/`. | CI-S04 | ci | Missing | *build* job |
| ADDED | CI-T06 | Given a branch that pins a dependency version with a known advisory, then the *audit* job fails, naming package, version and advisory. | CI-S05 | ci | Missing | demonstration pull request |
| ADDED | CI-T07 | Given a branch that changes a dependency in `pyproject.toml` without updating `uv.lock`, then every job fails at `uv sync --locked`. | CI-S06, PACKAGING-S04 | ci | Missing | demonstration pull request |
| ADDED | CI-T08 | Every `uses:` line of the workflows names an action by a full 40-character commit SHA, e.g. `actions/checkout@<40 hex characters> # v4.2.2`; a tag (`@v4`), a branch (`@main`) or a short SHA fails the check. | CI-S07 | static | Missing | `.github/scripts/check_workflows.sh`, run by the *lint* job |
| ADDED | CI-T09 | No workflow triggered by `pull_request` names the environment `nightly` or the secret, and no workflow uses `pull_request_target`. | CI-S02 | static | Missing | the same script |

### Nightly checks

| Change | ID | Test case | Verifies | Level | Status | Implemented by |
| ------ | -- | --------- | -------- | ----- | ------ | -------------- |
| ADDED | CI-T10 | Given JUnit XML with passed tests, a failed test and tests skipped with "eodhd.com refused EODHD_API_TOKEN (DataLimitError): …", then `live_summary.py` writes the three sections, the failure's first line, "account refused: DataLimitError" for the skipped ones, and "Account checks: not run (DataLimitError)" at the top. | CI-S09 | unit | Missing | `tests/unit/github/test_live_summary.py` |
| ADDED | CI-T11 | A manual run of `nightly.yml` with the account refused passes and shows the account tests as not checked; with the account usable, they show as passed. | CI-S08, CI-S09 | ci | Missing | manual runs of the workflow |
| ADDED | CI-T12 | Given a failure against the newest QuestDB release, then the nightly run shows a warning in its summary and does not fail. | CI-S10 | ci | Missing | demonstration run with a failing test on a branch |

### Integration database

| Change | ID | Test case | Verifies | Level | Status | Implemented by |
| ------ | -- | --------- | -------- | ----- | ------ | -------------- |
| ADDED | CI-T13 | The choice of database: with `QUESTDB_TEST_*` set, the override is used and no container started; without them and with Docker, the container; without both, a skip whose message names both ways. | CI-S11, QUALITY-S03 | unit | Missing | `unit/integration_support/test_database_choice.py`: `test_the_named_instance_is_used_whether_or_not_docker_answers`, `test_the_named_instance_takes_user_and_password_from_the_variables`, `test_without_the_variables_a_container_of_the_pinned_release_is_started`, `test_the_container_image_can_be_replaced`, `test_a_partial_set_of_variables_counts_as_unset`, `test_an_empty_variable_counts_as_unset`, `test_without_the_variables_and_docker_the_tests_are_skipped_with_both_ways_named` |
| ADDED | CI-T14 | Without `QUESTDB_TEST_*` and with Docker, the integration tests run against a container of the pinned version with `line.auto.create.new.columns=false`, and the container is gone after the session. | CI-S11, QUALITY-S04 | integration | Missing | the *integration* job, with its step "Check that no QuestDB container is left" |
| MODIFIED | STORAGE-T21 | Given a bar with a value of the wrong type, or a column the table does not have, when it is written, then `SchemaMismatchError` is raised at once and the table's columns are unchanged. With the container, both checks always run; the second is skipped only with an override instance whose server lacks `line.auto.create.new.columns=false`. | STORAGE-S13 | integration | Implemented | unchanged |

## Missing test cases of `5_test.md` this feature fills

| Test case | Filled by |
| --------- | --------- |
| PACKAGING-T01 (wheel and sdist with the declared metadata) | CI-T05 |
| PACKAGING-T03 (installed command in a fresh environment) | CI-T05 |
