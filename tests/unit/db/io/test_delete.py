"""Tests for db/io/delete.py: the statements sent for each table family"""

import pytest

from markethistorydb.db import tables
from markethistorydb.db.io.delete import Delete
from tests.fakes import RecordingQuery


def _delete(table) -> RecordingQuery:
    query = RecordingQuery()
    Delete(query).symbol_from_table("AAPL", "NASDAQ", table.NAME, table.TIMESTAMP_COLUMN,
                                    list(table.UNIQUE_KEY_COLUMNS))
    return query


@pytest.mark.parametrize("table", [tables.Symbol, tables.Sector])
def test_a_symbol_table_is_copied_without_the_symbol_then_swapped_in(table):
    query = _delete(table)
    copy_name = '"{0}_copy"'.format(table.NAME)
    assert query.texts == [
        'CREATE TABLE {0} AS (SELECT * FROM "{1}" WHERE NOT (symbol_code = %s AND exchange_code = %s));'.format(
            copy_name, table.NAME),
        'DROP TABLE "{0}";'.format(table.NAME),
        'RENAME TABLE {0} TO "{1}";'.format(copy_name, table.NAME),
    ]
    assert [params for _, params in query.statements] == [["AAPL", "NASDAQ"], [], []]

@pytest.mark.parametrize("table", [tables.EarningsQuarterly, tables.BalanceSheetAnnually])
def test_a_fundamental_table_keeps_its_timestamp_and_dedup_keys(table):
    text = _delete(table).texts[0]
    assert 'TIMESTAMP("{0}")'.format(table.TIMESTAMP_COLUMN) in text
    assert "DEDUP UPSERT KEYS({0})".format(
        ", ".join('"{0}"'.format(column) for column in table.UNIQUE_KEY_COLUMNS)) in text
    assert "NOT (symbol_code = %s AND exchange_code = %s)" in text

@pytest.mark.parametrize("table", [tables.DailyOhlcv, tables.MinuteOhlcv])
def test_a_price_table_is_rebuilt_and_gets_its_indexes_back(table):
    query = _delete(table)
    assert [text.split(" ")[0] for text in query.texts] == [
        "CREATE", "DROP", "RENAME", "ALTER", "ALTER"]
    assert query.texts[3:] == [
        "ALTER TABLE {0} ALTER COLUMN exchange_code ADD INDEX;".format(table.NAME),
        "ALTER TABLE {0} ALTER COLUMN symbol_code ADD INDEX;".format(table.NAME)]
    assert query.statements[0][1] == ["AAPL", "NASDAQ"]


# --- security ------------------------------------------------------------------------------

@pytest.mark.parametrize("table_name", ["exchange", "unknown", 'symbol"; DROP TABLE daily_ohlcv; --'])
def test_a_table_outside_the_known_families_is_left_alone(table_name):
    # The table name ends up in DDL, so only the known tables may get there
    query = RecordingQuery()
    Delete(query).symbol_from_table("AAPL", "NASDAQ", table_name, None, [])
    assert query.statements == []

def test_table_names_are_quoted_as_identifiers():
    text = _delete(tables.EarningsQuarterly).texts[0]
    assert 'FROM "earnings_quarterly"' in text and '"earnings_quarterly_copy"' in text
