# traceability: specification changes

State: Ready · Milestone: M0 · Kind: change (QUALITY, CI) · Requirements: QA-16 ·
Depends on: `continuous-integration`, `test-suite-hardening`, `code-hygiene`,
`secret-redaction-hardening`

## Why

The links between requirements, specification items and test cases are written by hand, and
nothing checks them. A typo in a Satisfies or Verifies cell goes unnoticed. So does a test that
no test case names, or a requirement status that a merge has made wrong. Each test is named
twice: in its module and in "Implemented by" in `5_test.md`. The status cells of
`2_requirements.md` repeat in words what the known gaps say. And the facts about a planned
feature that `1_constitution.md` 6.7 leaves to the trace script (the gaps it closes, the
statuses after its merge) have no script to derive them yet.

## Specification changes

### Links from the tests

| Change | ID | Specification | Satisfies |
| ------ | -- | ------------- | --------- |
| ADDED | QUALITY-S12 | **`spec` markers:** every test function carries the marker `spec` as a decorator, `@pytest.mark.spec("<ID>", …)`, with the IDs of the test cases it carries out as string literals: one or more `<CAPABILITY>-T<nn>` defined in `5_test.md` or added by a planned feature's `3_test.md`. A parametrised test carries it once, for all its parameter sets. The marker is registered, so a misspelt marker name fails the run (QUALITY-S06). | QA-16 |

### Report

| Change | ID | Specification | Satisfies |
| ------ | -- | ------------- | --------- |
| ADDED | QUALITY-S13 | **Trace report:** `scripts/trace.py`, run without options, writes `docs/specs/7_traceability.md` from `2_requirements.md`, `3_specs.md`, the known limitations of `4_design.md`, `5_test.md`, `6_roadmap.md`, the files in `planned_features/` and the `spec` markers of the tests, and from no other file. It holds: <br>• **the matrix:** for each requirement, its status (QUALITY-S14), the specification items satisfying it, implemented or planned with the feature's name, and the test cases verifying each item, with their status; <br>• **the tests of each test case:** the test functions whose markers name it, by module; <br>• **the gaps:** requirements without an implemented specification item, each with the planned feature it is assigned to; implemented specification items without an Implemented test case; <br>• **the next free ID** of specification items and of test cases per capability, over the global files and every planned feature; <br>• **per planned feature,** in the order of `6_roadmap.md`: the known gaps it closes, and each requirement whose status its merge changes, before and after, with the features before it merged first. <br>The same documents and tests give the same text: no date, a fixed order. | QA-16 |
| ADDED | QUALITY-S14 | **Requirement status:** a requirement is Open when no implemented specification item satisfies it, Partial when one does and a known gap of `3_specs.md` cites it, and Done when one does and no known gap cites it (`1_constitution.md` 6.2). **After the merge of a planned feature,** with the features before it in the order of `6_roadmap.md` merged first: the items the merged features add or modify count as implemented, with their new Satisfies, and the items they remove are gone; the known gaps naming a merged feature are closed; and the rows that the merged features list under "Known gaps changed" and "Known gaps added" apply. Items and gap rows of features not merged don't count. | QA-16 |

### Check

| Change | ID | Specification | Satisfies |
| ------ | -- | ------------- | --------- |
| ADDED | QUALITY-S15 | **Check:** `scripts/trace.py --check` writes nothing. It prints each error on a line of its own, naming the file and the ID, test or feature concerned, and ends with exit code 1 if it found one, and 0 otherwise. The errors: <br>• **IDs:** an ID defined twice; a requirement, specification item, test case, settled decision or decision gate cited in a file the script reads, outside a code block, but defined nowhere; a MODIFIED or REMOVED ID that neither the global files nor a feature before it define; <br>• **completeness** (`1_constitution.md` 6.2): a specification item without a requirement; an implemented specification item that no test case verifies; a requirement that no specification item, implemented or planned, satisfies and that neither a known gap nor a row of `6_roadmap.md` assigns to a planned feature; <br>• **statuses:** a Status cell of `2_requirements.md` holding anything but the status of QUALITY-S14; in `5_test.md`, a test case of level unit, integration or live that is Implemented with no test carrying its ID, or Missing with one; <br>• **markers:** a test function without a `spec` marker; the marker in any other form, e.g. a module-level `pytestmark` or an ID that isn't a string literal; <br>• **features:** a known gap naming no planned feature or more than one; a known gap or known limitation naming a feature that `6_roadmap.md` doesn't list; a folder of `planned_features/` whose feature `6_roadmap.md` doesn't list, or whose number isn't the feature's position there; a planned feature whose header names other requirements than those whose status its merge changes (QUALITY-S14); <br>• **report:** a `7_traceability.md` whose text differs from what the script would write, line endings aside. <br>The gaps the report lists (QUALITY-S13) are not errors. | QA-16 |
| MODIFIED | CI-S03 | Every pull request and every push to `main` runs these jobs; a newer push to the same branch cancels the run still going. **Required:** <br>• *unit*: `pytest -m unit --cov` on Linux and on Windows, each with Python 3.12 and the newest stable Python release, with the coverage gate of QUALITY-S02; <br>• *integration*: `pytest -m integration` on Linux with Python 3.12, against a QuestDB container (CI-S11); <br>• *build*: CI-S04; <br>• *audit*: CI-S05; <br>• *lint*: `ruff check` and `ruff format --check` (QUALITY-S11), with the findings also shown as annotations of the pull request; <br>• *trace*: `scripts/trace.py --check` (QUALITY-S15). <br>**Reporting only:** *types* (`pyright`), whose findings appear as annotations of the pull request without failing it. | QA-4, QA-2, QA-7, QA-14, QA-16 |

### Coverage and lint of the script

| Change | ID | Specification | Satisfies |
| ------ | -- | ------------- | --------- |
| MODIFIED | QUALITY-S02 | The unit tests run with branch coverage of `src/` and `scripts/`; with `--cov`, the run fails below 100 % line and branch coverage. Excluded are only `if __name__ == "__main__":` blocks and abstract methods. | QA-2 |
| MODIFIED | QUALITY-S11 | **Lint and format:** `ruff check` and `ruff format --check` pass on `src/`, `tests/` and `scripts/` with the configuration in `pyproject.toml`: Python 3.12 as target, a line length of 120, ruff's default rules plus naming (`N`), logging calls (`G`: values are passed as arguments, formatted only when a record is emitted) and security (`S`, bandit's checks: e.g. `eval`, unpickling, a shell in `subprocess`, requests without a timeout or with `verify=False`, hard-coded passwords, SQL text built from strings). The date and time rules (`DTZ`) are off, since naive datetimes mean UTC (COR-10). Unused imports are allowed in `__init__.py` files until these declare `__all__` (`library-contract`). The tests may use `assert`, fake secrets and SQL text built from strings. The statement modules in `db/statements/` may build SQL text from the table and column constants, since every value goes in as a bound parameter or as a literal that psycopg quotes (STORAGE-S17), until `schema-from-code` replaces them. No file starts with a shebang. | QA-14, QA-4, QA-11 |

## Not done

| Item | Where | Why |
| ---- | ----- | --- |
| A check that a MODIFIED item builds on the newest text of the features before it | nowhere: dropped | it needs a comparison of prose; the review does it, and the check of IDs catches a MODIFIED item whose ID is defined nowhere |
| The status of a test case derived from the markers instead of written | nowhere: dropped | a planned feature's Status says whether tests must be added or changed (`1_constitution.md` 6.7), which no marker shows; in `5_test.md`, `--check` compares the written status with the markers |
| Links from the code to specification items, e.g. a marker on the functions of `src/` | nowhere: dropped | the tests link the code to test cases, and these to the items; a second link would be kept by hand |
| A hook that regenerates `7_traceability.md` before each commit | nowhere: dropped | `code-hygiene` dropped pre-commit hooks; the CI job *trace* (CI-S03) fails on a stale file and names the command that regenerates it |
