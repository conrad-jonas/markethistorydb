"""Tests for db/statements/fundamental.py"""

import pytest

from markethistorydb.db import statements, tables
from tests.unit.db.statements.checks import assert_complete_statement, statements_of


@pytest.mark.parametrize("name, text", statements_of(statements.Fundamental).items())
def test_every_statement_is_complete(name, text):
    assert_complete_statement(name, text)

def test_the_copy_keeps_every_record_but_those_of_the_one_symbol_on_the_one_exchange():
    # "symbol_code != x AND exchange_code != y" would also drop the symbol's records on every
    # other exchange and every other symbol's records on this one
    create = statements.Fundamental.DROP_SYMBOL_FROM_TABLE[0]
    assert "WHERE NOT (symbol_code = %s AND exchange_code = %s)" in create
    assert create.count("%s") == 2

def test_the_symbol_is_dropped_by_copy_drop_and_rename_in_that_order():
    assert [text.split(" ")[0] for text in statements.Fundamental.DROP_SYMBOL_FROM_TABLE] == [
        "CREATE", "DROP", "RENAME"]
    assert all("%s" not in text for text in statements.Fundamental.DROP_SYMBOL_FROM_TABLE[1:])

@pytest.mark.parametrize("name, table", [
    ("EARNINGS_QUARTERLY", tables.EarningsQuarterly), ("EARNINGS_ANNUALLY", tables.EarningsAnnually),
    ("BALANCE_SHEET_QUARTERLY", tables.BalanceSheetQuarterly),
    ("BALANCE_SHEET_ANNUALLY", tables.BalanceSheetAnnually),
    ("CASH_FLOW_QUARTERLY", tables.CashFlowQuarterly), ("CASH_FLOW_ANNUALLY", tables.CashFlowAnnually),
    ("INCOME_STATEMENT_QUARTERLY", tables.IncomeStatementQuarterly),
    ("INCOME_STATEMENT_ANNUALLY", tables.IncomeStatementAnnually),
])
def test_each_select_reads_its_own_table_by_symbol(name, table):
    text = getattr(statements.Fundamental, "SELECT_ALL_FROM_{0}".format(name))
    assert text == "SELECT {0} FROM {1} WHERE symbol_code=%s".format(
        ", ".join(table.ALL_COLUMNS), table.NAME)
