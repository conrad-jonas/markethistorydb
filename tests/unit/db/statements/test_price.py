"""Tests for db/statements/price.py"""

import pytest

from markethistorydb.db import statements, tables
from tests.unit.db.statements.checks import assert_complete_statement, statements_of


@pytest.mark.parametrize("name, text", statements_of(statements.Price).items())
def test_every_statement_is_complete(name, text):
    # Guards against the split "CREATE TABLE ... AS (" that used to be sent on its own
    assert_complete_statement(name, text)

@pytest.mark.parametrize("statement_templates, table", [
    (statements.Price.DROP_SYMBOL_FROM_DAILY_OHLCV, tables.DailyOhlcv),
    (statements.Price.DROP_SYMBOL_FROM_MINUTE_OHLCV, tables.MinuteOhlcv),
])
def test_dropping_a_symbol_copies_drops_renames_and_then_restores_the_indexes(statement_templates, table):
    assert [text.split(" ")[0] for text in statement_templates] == [
        "CREATE", "DROP", "RENAME", "ALTER", "ALTER"]
    # The copy does not inherit the indexes, and the original is gone by then
    assert statement_templates[3:] == (
        "ALTER TABLE {0} ALTER COLUMN exchange_code ADD INDEX;".format(table.NAME),
        "ALTER TABLE {0} ALTER COLUMN symbol_code ADD INDEX;".format(table.NAME))
    create = statement_templates[0]
    assert "WHERE NOT (symbol_code = %s AND exchange_code = %s)" in create
    assert "TIMESTAMP({0})".format(table.TIMESTAMP_COLUMN) in create
    assert "DEDUP UPSERT KEYS({0})".format(", ".join(table.UNIQUE_KEY_COLUMNS)) in create
    # Only the CREATE takes the symbol and exchange, as Delete passes them to it alone
    assert [text.count("%s") for text in statement_templates] == [2, 0, 0, 0, 0]

@pytest.mark.parametrize("text, table", [
    (statements.Price.SELECT_LAST_FROM_DAILY_OHLCV, tables.DailyOhlcv),
    (statements.Price.SELECT_LAST_FROM_MINUTE_OHLCV, tables.MinuteOhlcv),
])
def test_the_newest_record_is_selected_per_symbol(text, table):
    # ORDER BY ... LIMIT 1 used to return one record for all requested symbols together
    assert text.endswith("LATEST ON timestamp PARTITION BY symbol_code")
    assert "LIMIT" not in text
    assert "FROM {0}".format(table.NAME) in text

@pytest.mark.parametrize("text", [statements.Price.SELECT_ALL_FROM_DAILY_OHLCV,
                                  statements.Price.SELECT_ALL_FROM_MINUTE_OHLCV])
def test_the_range_select_takes_the_exchange_and_both_bounds_as_params(text):
    assert text.count("%s") == 3
    assert "%s <= timestamp AND timestamp <= %s" in text
    assert "IN ({symbol_codes})" in text
