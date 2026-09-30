"""Reads the CREATE TABLE statements of the setup schema files, for comparing them to the constants"""

from dataclasses import dataclass
import re

from markethistorydb.setup.main import DIRPATH_SCHEMA

# CREATE TABLE statement: name, column block, and the clauses after the block up to the ';'
_CREATE_TABLE_PATTERN = re.compile(
    r"CREATE TABLE IF NOT EXISTS (\w+) \((.*?)\n\)([^;]*);", re.DOTALL)


@dataclass(frozen=True)
class CreatedTable:
    """A table as a schema file creates it"""

    name:              str
    column_lines:      list[str]
    column_names:      list[str]
    timestamp_column:  str | None
    dedup_keys:        list[str] | None
    is_wal:            bool
    clauses:           str


def _without_comments(sql_text: str) -> str:
    return "\n".join(line.split("--")[0].rstrip() for line in sql_text.splitlines())


def created_tables(schema_file_name: str) -> dict[str, CreatedTable]:
    """
    Parses the tables a schema file creates.

    :param schema_file_name: File name within setup/schema, e.g. "price.sql"
    :return: Every created table, keyed by name
    """
    sql_text = _without_comments((DIRPATH_SCHEMA / schema_file_name).read_text(encoding="utf-8"))
    tables: dict[str, CreatedTable] = {}
    for name, block, clauses in _CREATE_TABLE_PATTERN.findall(sql_text):
        column_lines = [line.strip() for line in block.splitlines() if line.strip()]
        dedup = re.search(r"DEDUP UPSERT KEYS\s*\(([^)]*)\)", clauses)
        timestamp = re.search(r"TIMESTAMP\((\w+)\)", clauses)
        tables[name] = CreatedTable(
            name=name,
            column_lines=column_lines,
            column_names=[line.split()[0].rstrip(",") for line in column_lines],
            timestamp_column=timestamp.group(1) if timestamp else None,
            dedup_keys=[key.strip() for key in dedup.group(1).split(",")] if dedup else None,
            is_wal=bool(re.search(r"\bWAL\b", clauses)),
            clauses=clauses.strip(),
        )
    return tables


def assert_matches_constants(created: CreatedTable, table: type):
    """
    Asserts that a schema file creates *table* the way its constants describe it.

    :param created: Table as the schema file creates it
    :param table: The table's constants class
    """
    assert created.column_names == list(table.ALL_COLUMNS)
    # A missing comma merges two columns into one definition; a trailing one before the ')'
    # is rejected by QuestDB. Either way setup() fails.
    assert all(line.endswith(",") for line in created.column_lines[:-1]), created.column_lines
    assert not created.column_lines[-1].endswith(","), created.column_lines[-1]
    assert all(len(line.rstrip(",").split()) >= 2 for line in created.column_lines)
    assert created.timestamp_column == table.TIMESTAMP_COLUMN
    if created.timestamp_column is None:
        # QuestDB only makes a partitioned table WAL, and only a table with a designated timestamp
        # can be partitioned
        assert not created.is_wal and "PARTITION BY" not in created.clauses
    if created.dedup_keys is not None:
        # QuestDB demands the designated timestamp among the keys, and a WAL table
        assert created.timestamp_column in created.dedup_keys
        assert created.is_wal
        assert set(created.dedup_keys) == set(table.UNIQUE_KEY_COLUMNS)
