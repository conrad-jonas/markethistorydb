# MarketHistoryDB

Fetches market data (prices, fundamentals, reference data) from providers and stores it in
QuestDB, as the data source of a trading backtester. A Python library with a command line; a
REST API is planned.

## Where things are

- `docs/specs/`: the specification, the source of truth for what the system does and why. Start
  with `1_constitution.md` (purpose, rules, workflow) and `6_roadmap.md` (what comes next).
  Planned changes are in `docs/specs/planned_features/<nn>_<feature>/`.
- `src/markethistorydb/`: the package. Its target layout and dependency rule are in
  `1_constitution.md`, section 4; existing code moves there with the feature `target-architecture`.
- `tests/unit/`, `tests/integration/`, `tests/live/`: the three test levels. The `conftest.py` of
  each level sets its marker.

## Commands

The project is managed with uv. Never call `python` or `pip` directly.

- `uv sync`: installs the package and the development tools.
- `uv run pytest -m unit --cov`: unit tests; fails below 100 % line and branch coverage.
- `uv run pytest -m integration`: integration tests against a throwaway QuestDB named by
  `QUESTDB_TEST_HOST`, `QUESTDB_TEST_PG_PORT` and `QUESTDB_TEST_HTTP_PORT` (environment or
  `.env`). Skipped without them; they refuse to run against the application's database.
- `uv run pytest -m live`: contract tests against the real eodhd.com API. They spend calls of the
  account behind `EODHD_API_TOKEN`: run them only when asked. A plain `uv run pytest` includes them.
- `uv run ruff check`: lint. Ruff has no configuration yet and reports existing findings; the
  feature `code-hygiene` configures it and fixes them.
- `uv add <package>`, `uv remove <package>`: change dependencies; never edit them in
  `pyproject.toml` by hand.

## After every change

1. The unit tests pass with 100 % coverage.
2. A change to the database path has an integration test, and the integration tests pass.
3. `uv run ruff check` reports no finding in the lines the change added.
4. The README, the user docs and the specification documents are updated in the same change when
   behaviour, command line or schema change (`1_constitution.md`, 5.2).

## Rules that are easy to miss

The full rules are in `1_constitution.md`, section 5. The ones most often relevant:

- Decision logic lives in pure functions, tested with plain values (5.1, rule 1).
- A symbol is always a method argument, never constructor or setter state (5.1, rule 2).
- Test doubles are checked against the real interface: `create_autospec`, or contract tests for
  hand-written fakes (5.1, rule 4).
- No test patches a private name; if one has to, the production code is missing a seam (5.1,
  rule 6).
- Tests never run against a production database.
- Docstring conventions: `.claude/rules/docstrings.md`, loaded when Python files are read or edited.

## Specification documents

- IDs, statuses and the workflow are defined in `1_constitution.md`, section 6.
- Requirements are solution-neutral. A planned feature is cited by its name, never by its number.

## Git

- `main` only receives merges. Every change is made on a branch named `feature/…`, `fix/…`,
  `test/…`, `refactor/…`, `chore/…` or, for the specification documents, `docs/…`, and merged
  with `git merge --no-ff` (`1_constitution.md`, 5.3).
- One commit per logical change: a subject line and a short prose body wrapped at about 70
  columns.
