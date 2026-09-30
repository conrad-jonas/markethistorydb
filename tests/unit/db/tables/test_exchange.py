"""Tests for db/tables/exchange.py"""

from markethistorydb.db import tables
from tests.unit.db.tables.schema import assert_matches_constants, created_tables


def test_the_key_columns_are_columns_of_the_table():
    assert set(tables.Exchange.UNIQUE_KEY_COLUMNS) <= set(tables.Exchange.ALL_COLUMNS)

def test_the_schema_creates_the_table_as_the_constants_describe_it():
    assert_matches_constants(created_tables("exchange.sql")["exchange"], tables.Exchange)

def test_the_table_is_not_wal_so_a_write_is_visible_to_the_next_read():
    # WriteExchangeData reads before it inserts; a WAL table could hide a record not yet applied
    created = created_tables("exchange.sql")["exchange"]
    assert (tables.Exchange.TIMESTAMP_COLUMN, created.is_wal) == (None, False)

def test_the_table_is_listed_by_name():
    assert tables.TABLES_NAMES_EXCHANGE == ["exchange"]
