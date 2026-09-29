"""Tests for db/statements/exchange.py"""

import pytest

from markethistorydb.db import statements, tables
from tests.unit.db.statements.checks import assert_complete_statement, statements_of


@pytest.mark.parametrize("name, text", statements_of(statements.Exchange).items())
def test_every_statement_is_complete(name, text):
    assert_complete_statement(name, text)

def test_the_insert_takes_every_column_in_definition_order():
    # Insert.exchange binds one value per column, in ALL_COLUMNS order
    assert statements.Exchange.INSERT_EXCHANGE == "INSERT INTO exchange ({0}) VALUES ({1})".format(
        ", ".join(tables.Exchange.ALL_COLUMNS), ", ".join(["%s"] * len(tables.Exchange.ALL_COLUMNS)))

def test_the_update_sets_every_column_but_the_key():
    text = statements.Exchange.UPDATE_EXCHANGE
    set_part, where_part = text.split(" WHERE ")
    expected = set(tables.Exchange.ALL_COLUMNS) - {tables.Exchange.Columns.EXCHANGE_CODE}
    assert {column for column in expected if "{0}=%s".format(column) in set_part} == expected
    assert where_part == "exchange_code=%s"

def test_the_select_reads_every_column_by_exchange_code():
    text = statements.Exchange.SELECT_ALL_FROM_EXCHANGE_BY_EXCHANGE_CODE
    assert text == "SELECT {0} FROM exchange WHERE exchange_code=%s".format(
        ", ".join(tables.Exchange.ALL_COLUMNS))
