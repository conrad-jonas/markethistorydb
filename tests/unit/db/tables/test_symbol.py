"""Tests for db/tables/symbol.py"""

import pytest

from markethistorydb.db import tables
from tests.unit.db.tables.schema import assert_matches_constants, created_tables


@pytest.mark.parametrize("table", [tables.Symbol, tables.Sector])
def test_the_key_columns_are_columns_of_the_table(table):
    assert set(table.UNIQUE_KEY_COLUMNS) <= set(table.ALL_COLUMNS)

@pytest.mark.parametrize("table", [tables.Symbol, tables.Sector])
def test_the_schema_creates_the_table_as_the_constants_describe_it(table):
    # Caught the missing comma after sector.gic_sub_industry and the trailing ones before ')'
    assert_matches_constants(created_tables("symbol.sql")[table.NAME], table)

@pytest.mark.parametrize("table", [tables.Symbol, tables.Sector])
def test_the_table_is_not_wal_so_a_write_is_visible_to_the_next_read(table):
    # The Write* classes read before they insert; a WAL table could hide a record not yet applied
    # and so let the same key be inserted twice
    created = created_tables("symbol.sql")[table.NAME]
    assert (table.TIMESTAMP_COLUMN, created.is_wal) == (None, False)

def test_both_tables_are_listed_by_name():
    assert tables.TABLE_NAMES_SYMBOL == ["symbol", "sector"]
