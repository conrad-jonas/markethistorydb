"""Tests for db/io/delete.py: the statements sent for each table family"""

import pytest

from markethistorydb.db import tables
from markethistorydb.db.io.delete import Delete
from tests.fakes import RecordingQuery


def _delete(table, *results: list[tuple]) -> RecordingQuery:
    query = RecordingQuery(*results)
    Delete(query).symbol_from_table("AAPL", "NASDAQ", table.NAME, table.TIMESTAMP_COLUMN,
                                    list(table.UNIQUE_KEY_COLUMNS))
    return query

def _swap(query: RecordingQuery) -> list[tuple[str, list]]:
    """
    Leaves out the lookup for a copy left over from an interrupted deletion.

    :param query: Query the deletion ran on, without a leftover copy to clean up
    :return: The statements of the copy and swap, with their parameters
    """
    return query.statements[1:]


@pytest.mark.parametrize("table", [tables.Symbol, tables.Sector])
def test_a_symbol_table_is_copied_without_the_symbol_then_swapped_in(table):
    statements = _swap(_delete(table))
    copy_name = '"{0}_copy"'.format(table.NAME)
    assert [text for text, _ in statements] == [
        'CREATE TABLE {0} AS (SELECT * FROM "{1}" WHERE NOT (symbol_code = %s AND exchange_code = %s));'.format(
            copy_name, table.NAME),
        'DROP TABLE "{0}";'.format(table.NAME),
        'RENAME TABLE {0} TO "{1}";'.format(copy_name, table.NAME),
    ]
    assert [params for _, params in statements] == [["AAPL", "NASDAQ"], [], []]

@pytest.mark.parametrize("table", [tables.EarningsQuarterly, tables.BalanceSheetAnnually])
def test_a_fundamental_table_keeps_its_timestamp_and_dedup_keys(table):
    text = _swap(_delete(table))[0][0]
    assert 'TIMESTAMP("{0}")'.format(table.TIMESTAMP_COLUMN) in text
    assert "DEDUP UPSERT KEYS({0})".format(
        ", ".join('"{0}"'.format(column) for column in table.UNIQUE_KEY_COLUMNS)) in text
    assert "NOT (symbol_code = %s AND exchange_code = %s)" in text

@pytest.mark.parametrize("table", [tables.DailyOhlcv, tables.MinuteOhlcv])
def test_a_price_table_is_rebuilt_and_gets_its_indexes_back(table):
    texts = [text for text, _ in _swap(_delete(table))]
    assert [text.split(" ")[0] for text in texts] == [
        "CREATE", "DROP", "RENAME", "ALTER", "ALTER"]
    assert texts[3:] == [
        "ALTER TABLE {0} ALTER COLUMN exchange_code ADD INDEX;".format(table.NAME),
        "ALTER TABLE {0} ALTER COLUMN symbol_code ADD INDEX;".format(table.NAME)]
    assert _swap(_delete(table))[0][1] == ["AAPL", "NASDAQ"]


# --- copies left over from an interrupted deletion -----------------------------------------

@pytest.mark.parametrize("table", [tables.Symbol, tables.EarningsAnnually, tables.DailyOhlcv])
def test_the_table_and_its_copy_are_looked_up_before_the_copy_is_made(table):
    query = _delete(table)
    assert query.statements[0] == (
        "SELECT table_name FROM tables() WHERE table_name IN (%s, %s)",
        [table.NAME, "{0}_copy".format(table.NAME)])
    assert query.texts[1].startswith("CREATE TABLE")

def test_a_leftover_copy_is_dropped_while_the_table_still_exists():
    # The table was never dropped, so it still holds every record the copy has
    query = _delete(tables.EarningsAnnually, [("earnings_annually",), ("earnings_annually_copy",)], [])
    assert query.texts[1] == 'DROP TABLE "earnings_annually_copy";'
    assert query.texts[2].startswith('CREATE TABLE "earnings_annually_copy"')

def test_a_leftover_copy_takes_the_table_s_name_back_once_the_table_is_gone():
    # The deletion stopped between dropping the table and renaming the copy, so the copy holds
    # the only records
    query = _delete(tables.EarningsAnnually, [("earnings_annually_copy",)], [])
    assert query.texts[1] == 'RENAME TABLE "earnings_annually_copy" TO "earnings_annually";'
    assert query.texts[2].startswith('CREATE TABLE "earnings_annually_copy"')


# --- security ------------------------------------------------------------------------------

@pytest.mark.parametrize("table_name", ["exchange", "unknown", 'symbol"; DROP TABLE daily_ohlcv; --'])
def test_a_table_outside_the_known_families_is_left_alone(table_name):
    # The table name ends up in DDL, so only the known tables may get there
    query = RecordingQuery()
    Delete(query).symbol_from_table("AAPL", "NASDAQ", table_name, None, [])
    assert query.statements == []

def test_table_names_are_quoted_as_identifiers():
    text = _swap(_delete(tables.EarningsQuarterly))[0][0]
    assert 'FROM "earnings_quarterly"' in text and '"earnings_quarterly_copy"' in text
