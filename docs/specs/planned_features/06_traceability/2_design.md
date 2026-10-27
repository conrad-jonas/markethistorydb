# traceability: design

## 1 Overview

| Part | Files |
| ---- | ----- |
| Trace script | `scripts/trace.py` (new); `tests/unit/scripts/test_trace.py`, `tests/data/trace/` (new); `pyproject.toml` (coverage source) |
| Markers | every `tests/**/test_*.py`; `pyproject.toml` (the marker registered); `README.md` (section "Tests") |
| Documents | `docs/specs/7_traceability.md` (new, generated); `docs/specs/2_requirements.md` (intro, Status cells); `docs/specs/5_test.md` (section 1.3, every table); `docs/specs/1_constitution.md` (sections 6.1, 6.2, 6.4, 6.6, 6.7) |
| CI | `.github/workflows/ci.yml` (job *trace*); the protection of `main` (one more required check) |

## 2 Trace script

- **Place:** `scripts/trace.py`, in a new folder `scripts/` at the repository root, next to
  `src/`, `tests/` and `docs/`. It is a development tool, not part of the package: the wheel is
  built from `src/` only, so the script is neither published nor installed with the package. It
  is the folder's only file.
- **Shape:** one file using the standard library only (`argparse`, `ast`, `pathlib`, `re`). Pure
  functions read the texts into a model (requirements, items, test cases, gap rows, features,
  markers), compute statuses and errors, and render the report; `main` reads and writes the
  files.
- **Command:** two modes, run from the repository root.
  - `uv run python scripts/trace.py` regenerates `docs/specs/7_traceability.md`. It is run by
    hand after a change to the documents or the tests, and the file is committed with the
    change. It also prints the errors of QUALITY-S15, all but the stale file, and ends with exit
    code 1 if it found one.
  - `uv run python scripts/trace.py --check` writes nothing. It prints every error of
    QUALITY-S15, a `7_traceability.md` that differs from what the first mode would write included,
    and ends with exit code 1 if it found one. The CI job *trace* runs it (section 6); anyone can
    run it before a push.
  - `--root` names another repository root, for the tests. A wrong argument ends with exit code 2
    (`argparse`).
- **Tables:** a row defines the ID in its first cell: requirements in `2_requirements.md`, items
  in `3_specs.md`, test cases in `5_test.md`; in a planned feature, the ID after `ADDED`,
  `MODIFIED` or `REMOVED`. Columns are found by their header (`Satisfies`, `Verifies`, `Level`,
  `Status`), not by position. Gap rows are the rows under a heading holding "Known gaps", and
  limitation rows those under "Known limitations"; the feature they name is the name in
  backticks in their last cell.
- **IDs:** a token of a form of `1_constitution.md` 6.5 whose prefix is a requirement group of
  `2_requirements.md` or a capability: one of the capability table of `3_specs.md`, or one that a
  planned feature adds IDs to. So `UTF-8` is no ID. Settled decisions and decision gates are
  defined by the first cell of a row in `6_roadmap.md`. An ID in a code block is an example, not
  a citation, e.g. the misspelt one in section 5. Outside code blocks, the documents cite no
  undefined ID today but the decision gates DG-1, DG-4 and DG-9 (2026-10-27), which
  `6_roadmap.md` defines.
- **Features:** a planned feature is identified by its name, e.g. `traceability`. The number of
  its folder, as in `06_traceability`, is its position in the roadmap order and changes with it
  (`1_constitution.md` 6.3, 6.5). The script takes names and positions from the table of
  `6_roadmap.md` with the columns `#`, `Feature`, `State` and `Requirements`: a row's name is the
  text in backticks under `Feature`, its position the number under `#`. It finds a feature's
  folder by the part after the number, and `--check` reports a folder whose number isn't the
  feature's position. The requirements under `Requirements` count as assigned to the row's
  feature: for 33 requirements nothing else does today (no item, no gap row; 2026-10-27).
  `6_roadmap.md` is written after this feature and before it is implemented, so its table gets
  these columns.
- **Line endings:** files are read in text mode, so any line ending reads the same, and
  `7_traceability.md` is written with `newline="\n"`. With `core.autocrlf`, git checks it out on
  Windows with CRLF, which `--check` ignores.

## 3 Markers

- **Reading:** `ast`, the standard library's parser of Python source into a syntax tree, reads
  each `tests/**/test_*.py` without importing or running it. A module-level function whose name
  starts with `test_` is a test (the suite has no test classes). Its decorator
  `pytest.mark.spec("…", …)` links it to the IDs. Any other use of `mark.spec`, such as a
  module-level `pytestmark`, an alias or an argument that isn't a string literal, is an error.
- **Registration:** `markers` in `pyproject.toml` gains
  `"spec(*ids): the test cases of docs/specs this test carries out"`.
- **Migration:** a one-off script, not kept, inserts the decorators from "Implemented by" in
  `5_test.md` as it stands once the five earlier features are merged. It puts each decorator above
  the function's other decorators, and adds `import pytest` where a module lacks it (13 modules
  today). Tried on 2026-10-27 on a copy of `tests/`: the only 7 functions left without a marker
  were the tests of unused code that `code-hygiene` removes along with that code (`5_test.md` 2.7).
  10 functions carry two or three IDs; the longest decorator has 60 characters.
- **README:** the section "Tests" says that each test names its test cases with
  `@pytest.mark.spec`, and that `uv run python scripts/trace.py` regenerates
  `docs/specs/7_traceability.md` after a change to the tests or to `docs/specs/`.

## 4 Report

`7_traceability.md` opens with a line saying that `scripts/trace.py` generates it and that it
isn't edited by hand. Then:

1. **Matrix:** one table per requirement group, in the order of `2_requirements.md`:
   `Requirement | Status | Specification items | Test cases`. A planned item shows its feature,
   e.g. ``LOGGING-S05 (`secret-redaction-hardening`)``. A Missing test case is marked "Missing".
2. **Tests:** per capability, `Test case | Tests`, with the tests by module as "Implemented by"
   shows them today.
3. **Gaps:** the two lists of QUALITY-S13.
4. **Next free IDs.**
5. **Planned features:** a section per feature in roadmap order, with the gaps it closes and a
   table `Requirement | Before | After`.

Lists are sorted by document order, IDs within a cell by number.

## 5 Check

- **Output of `--check`:** in the terminal, or in the log of the CI job *trace*, one line per
  error, `FAIL <file> <ID or test>: <message>`, then a count. The count line also gives the gaps
  listed (e.g. "21 Missing test cases"), which aren't errors:

  ```
  FAIL docs/specs/5_test.md STORAGE-T10: verifies STORAGE-S99, which is defined nowhere
  FAIL docs/specs/2_requirements.md QA-8: Status is Done, the known gaps give Partial
  FAIL tests/unit/test_cli.py::test_x: no spec marker
  FAIL docs/specs/7_traceability.md: stale; run uv run python scripts/trace.py
  4 errors (listed, not errors: 21 Missing test cases, 83 requirements without an implemented item)
  ```

- **Statuses of test cases:** only those of level unit, integration or live are compared with
  the markers, including the combined level "unit, integration". A test case of level static,
  suite or ci names its carrier in its text (section 7), so its status is taken as written.
- **Header:** the requirements after "Requirements:" in the line starting with "State:" are
  compared with those whose status the feature's merge changes.

## 6 CI job

*trace* runs on Linux with Python 3.12, installs the locked dependencies as every job does
(CI-S06), and runs `uv run python scripts/trace.py --check`. It takes seconds. The protection of
`main` adds it to the required checks (CI-S01).

## 7 Documents

These change together with the markers (issue 2), since `--check` passes only with both. The
feature's own items enter the global files at its merge (issue 3).

- **`2_requirements.md`:** the intro's bullets on the status become the rule of
  `1_constitution.md` 6.2, with `7_traceability.md` named for the items and gaps behind each
  status. The 39 Status cells with a note keep the status alone. Each note is stated elsewhere:
  - the 35 Partial ones in the known gaps citing them;
  - MKT-6 ("one-minute bars") in PROVIDER-S06;
  - COR-9 ("reported in the log only") in PRICES-S05 and the gap row of COR-14;
  - COR-11 in its gap row;
  - CLD-1 in RUNS-S13.
- **`5_test.md`:**
  - The column "Implemented by" leaves every table.
  - A test case of level static, suite or ci gets what carries it out, today's cell, appended to
    its text in parentheses: the configuration, the CI job, or the demonstration (22 test cases
    once the five earlier features are merged). E.g. QUALITY-T02 ends "(`fail_under` in
    `pyproject.toml`)", CI-T02 "(demonstrated with a pull request)". The test cases of this
    feature are written so already.
  - 1.3: *Implemented* means that tests carry the test case's ID in a `spec` marker (unit,
    integration, live), or that the configuration, job or demonstration its text names exists
    (static, suite, ci). `7_traceability.md` lists the tests of each test case. The bullets on
    "Implemented by" and on tests without a test case go: every test has a test case, and
    `--check` enforces it.
  - The intro of chapter QUALITY loses its sentence on "Implemented by".
- **`1_constitution.md`:**
  - 6.1: `7_traceability.md` is generated by `scripts/trace.py`.
  - 6.2: a test case names the specification items it verifies and its level; its tests carry
    its ID in a `spec` marker.
  - 6.4 item 3: the status becomes Implemented once tests carry the ID. Item 6: `--check` passes.
  - 6.6: the last paragraph in the present tense, and that `--check` runs in the required job
    *trace*.
  - 6.7: the tables of `3_test.md` are `Change | ID | Test case | Verifies | Level | Status`. The
    sentence on "Implemented by" goes; a test case of level static, suite or ci names its carrier
    in its text.

## 8 Tests of the script

- **Loading:** `tests/unit/scripts/test_trace.py` loads the script by its path under the name
  `trace_script` (`importlib.util.spec_from_file_location`).
- **Sample:** `tests/data/trace/` holds a small consistent repository: `2_requirements.md` to
  `6_roadmap.md`, two planned features and two test modules. A fixture copies it into
  `tmp_path`. Its test modules are stored as `.py.txt` and renamed in the copy, so that pytest
  doesn't collect them.
  - QUALITY-T12 compares the report with `tests/data/trace/expected_7_traceability.md`.
  - QUALITY-T14 has one parametrised case per error of QUALITY-S15, each changing one line of
    the sample.
- **Coverage:** `source = ["src", "scripts"]` (QUALITY-S02). The `__main__` block is excluded,
  as it is everywhere.
- The tests carry `spec` markers themselves.

## 9 Decisions

| Decision | Choice | Options considered | Reason |
| -------- | ------ | ------------------ | ------ |
| Requirement of the script | a new QA-16, Should, added on this feature's branch with its gap row | QA-4 extended to the links of the specification; QA-16 as Must | decided on 2026-10-27: QA-4 is about checks of the code; extended, it would mix code with documents and wait for one more feature to be Done |
| Links from the tests | `@pytest.mark.spec(<test case IDs>)` on each test function, read with `ast`; any other form is an error | also a module-level `pytestmark` for a file of one test case (17 of 56 files); markers read through pytest's collection | decided on 2026-10-27: the link sits on the function it describes, and reading it needs no import and no environment. Markers generated from "Implemented by" on a copy of `tests/` read back unchanged for all 354 functions, in 125 ms (2026-10-27). |
| "Implemented by" | leaves `5_test.md` and the `3_test.md` files; `7_traceability.md` lists the marked tests; a test case of level static, suite or ci names its carrier in its text | `# spec:` comments in the configuration and the workflows; the column kept for static, suite and ci only; the column kept everywhere and checked | decided on 2026-10-27: each link once. 22 test cases have no test function to mark, and their carriers rarely change. |
| Status cells of `2_requirements.md` | the status alone, checked against the known gaps | the column only in `7_traceability.md`; cells written by the script | decided on 2026-10-27: readable where the requirement stands; the notes repeated the known gaps |
| `7_traceability.md` and `--check` | tracked in git; errors fail, gaps are listed; a required job *trace* | not tracked, shown as the summary of a CI job; also failing on gaps added since `main` | decided on 2026-10-27: a pull request's diff shows what it does to the links. Missing test cases and Open requirements are states, not errors: 21 and 83 today. |
| Features and their order | the feature table of `6_roadmap.md`; folders found by name, their numbers checked | the folder numbers, with only the names of unwritten features from the roadmap; a list in the script | decided on 2026-10-27: the roadmap holds the order (`1_constitution.md` 6.3), and a typo in a gap row's feature fails |
| Capability of the IDs | QUALITY | a new capability TRACE | decided on 2026-10-27: QUALITY holds the rules of the suite and the lint already |
| Dependencies of the script | the standard library | a Markdown parser, e.g. markdown-it-py | every table row is one line, so regular expressions suffice, and the script runs without the environment |
| Coverage of the script | under the gate of QUALITY-S02 | tested, but outside the gate | QA-2 asks for every line and branch of the code, not of the package only |
| Loading the script in its tests | by path, as `trace_script` | `scripts/` on `sys.path` (pytest's `pythonpath`) | `scripts/trace.py` would shadow the standard library's `trace` for every module of the run; nothing in the test environment imports that module (checked on 2026-10-27), but a later tool might |
| Header of a planned feature | checked against the statuses its merge changes | not checked | `1_constitution.md` 6.7 asks the header to name these requirements; written by hand, they can be wrong |

## 10 Implementation

| # | Issue | Covers |
| - | ----- | ------ |
| 1 | The trace script: reading, statuses, report and check; its tests and the sample; `scripts/` under coverage and lint | QUALITY-S02, S11, S13, S14, S15; QUALITY-T02, T11, T12, T13, T14, T15 |
| 2 | The markers on every test and their registration; the documents of section 7; the README; `7_traceability.md` generated | QUALITY-S12, T16 |
| 3 | The job *trace* as a required check; the merge into the global files | CI-S03, T03, T16 |

- **Order:** 1, 2, 3. `--check` passes once issue 2 is done, and issue 3 makes it required.
- **Earlier features:** all three issues come after the five earlier features have merged. The
  markers are generated from "Implemented by" as these features leave it, and the tests that
  `code-hygiene` removes have no test case. Issue 3 builds on CI-S03 as `code-hygiene` leaves it,
  and issue 1 on QUALITY-S11 as `secret-redaction-hardening` leaves it.

## 11 Open questions

None.

## 12 Changes to `4_design.md` on merge

- **14.1 (project files):** `scripts/trace.py`; in `pyproject.toml`, the `spec` marker and the
  coverage source `src` and `scripts`.
- **15 (QUALITY):** rows for the `spec` markers and for the trace report and check
  (`scripts/trace.py`, the job *trace*), and a section on the script with sections 2 to 5 and 8.
  The title becomes "QUALITY: test suite, code checks and traceability", as do those of
  `3_specs.md` 13 and `5_test.md` 14 and the capability tables.
- **Appendix A:** a new row. Decision: links are kept in one direction, where the knowledge
  arises, and the rest is generated. Reason: a link written twice drifts. Consequence:
  `7_traceability.md` is regenerated with every change to the documents or the tests, and a test
  without a marker fails CI.
- **Known limitations:** none removed.
