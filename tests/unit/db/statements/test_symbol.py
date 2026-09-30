"""Tests for db/statements/symbol.py"""

import pytest

from markethistorydb.db import statements, tables
from tests.unit.db.statements.checks import assert_complete_statement, statements_of


@pytest.mark.parametrize("name, text", statements_of(statements.Symbol).items())
def test_every_statement_is_complete(name, text):
    assert_complete_statement(name, text)

def test_the_sector_update_has_no_join():
    # QuestDB rejects UPDATE ... FROM on WAL tables ("UPDATE statements with join are not
    # supported yet for WAL tables"); kept join-free so the table may become WAL again
    assert " FROM " not in statements.Symbol.UPDATE_SECTOR

@pytest.mark.parametrize("text, table", [
    (statements.Symbol.INSERT_SYMBOL, tables.Symbol), (statements.Symbol.INSERT_SECTOR, tables.Sector)])
def test_an_insert_takes_every_column_in_definition_order(text, table):
    # Insert.symbol and Insert.sector bind one value per column, in ALL_COLUMNS order
    assert text == "INSERT INTO {0} ({1}) VALUES ({2})".format(
        table.NAME, ", ".join(table.ALL_COLUMNS), ", ".join(["%s"] * len(table.ALL_COLUMNS)))

@pytest.mark.parametrize("text, key_columns", [
    (statements.Symbol.UPDATE_SYMBOL, tables.Symbol.UNIQUE_KEY_COLUMNS),
    (statements.Symbol.UPDATE_SECTOR, tables.Sector.UNIQUE_KEY_COLUMNS),
    (statements.Symbol.SELECT_ALL_FROM_SYMBOL_BY_UNIQUE_KEYS, tables.Symbol.UNIQUE_KEY_COLUMNS),
    (statements.Symbol.SELECT_ALL_FROM_SECTOR_BY_UNIQUE_KEYS, tables.Sector.UNIQUE_KEY_COLUMNS),
])
def test_a_record_is_addressed_by_its_whole_unique_key(text, key_columns):
    where = text.split(" WHERE ")[1]
    assert where == " AND ".join("{0}=%s".format(column) for column in key_columns)

def test_the_symbol_select_reads_the_columns_the_record_is_built_from():
    # Read.symbol turns the row into a Series by position
    assert statements.Symbol.SELECT_ALL_FROM_SYMBOL_BY_UNIQUE_KEYS.startswith(
        "SELECT {0} FROM symbol".format(", ".join(tables.Symbol.ALL_COLUMNS)))

def test_the_symbol_copy_keeps_every_other_symbol_and_stays_non_wal():
    create = statements.Symbol.DROP_SYMBOL_FROM_TABLE[0]
    assert "WHERE NOT (symbol_code = %s AND exchange_code = %s)" in create
    # Like schema/symbol.sql: without a designated timestamp the copy is neither partitioned
    # nor WAL, so Insert can keep writing it through SQL
    assert create.endswith("));")
    assert not any(clause in create for clause in ("TIMESTAMP(", "PARTITION BY", "WAL", "DEDUP"))
