"""Tests for db/tables/price.py"""

import pytest

from markethistorydb.db import tables
from tests.unit.db.tables.schema import assert_matches_constants, created_tables


@pytest.mark.parametrize("table", [tables.DailyOhlcv, tables.MinuteOhlcv])
def test_the_key_columns_are_columns_of_the_table(table):
    assert table.TIMESTAMP_COLUMN in table.ALL_COLUMNS
    assert set(table.UNIQUE_KEY_COLUMNS) <= set(table.ALL_COLUMNS)

@pytest.mark.parametrize("table", [tables.DailyOhlcv, tables.MinuteOhlcv])
def test_the_schema_creates_the_table_as_the_constants_describe_it(table):
    created = created_tables("price.sql")[table.NAME]
    assert_matches_constants(created, table)
    # Re-inserting a symbol's history must not duplicate it
    assert created.dedup_keys is not None

def test_both_tables_are_listed_by_name():
    assert tables.TABLE_NAMES_PRICE == ["daily_ohlcv", "minute_ohlcv"]
