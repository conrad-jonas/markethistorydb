"""Integration tests for setup/main.py: the schema files against a real QuestDB"""

import pytest

from markethistorydb.db import statements
from markethistorydb.setup import setup
from tests.integration.conftest import count, iter_tables, select, settle, wait_for_count


@pytest.mark.parametrize("table", list(iter_tables()), ids=lambda table: table.NAME)
def test_every_table_is_created_as_its_constants_describe_it(fresh_db, table):
    # setup() used to fail on the first file: QuestDB rejects the trailing comma before ')' and
    # DEDUP keys without the designated timestamp, so every table was left to ILP to invent
    column_names = [name for name, in select(
        fresh_db, 'SELECT "column" FROM table_columns(%s)', table.NAME)]
    assert column_names == list(table.ALL_COLUMNS)
    designated, is_wal = select(
        fresh_db, "SELECT designatedTimestamp, walEnabled FROM tables() WHERE table_name = %s", table.NAME)[0]
    # The time series tables are WAL (DEDUP needs it); the lookup tables have no designated
    # timestamp, so QuestDB creates them non-WAL
    assert (designated, is_wal) == (table.TIMESTAMP_COLUMN, table.TIMESTAMP_COLUMN is not None)

@pytest.mark.parametrize("table", list(iter_tables()), ids=lambda table: table.NAME)
def test_every_column_is_found_through_the_meta_statement(fresh_db, table):
    # StatementsMeta.SELECT_SCHEMA has no caller in the package; this is what keeps it honest
    for column_name in table.ALL_COLUMNS:
        assert len(select(fresh_db, statements.Meta.SELECT_SCHEMA, table.NAME, column_name)) == 1

def test_the_price_tables_index_the_columns_they_are_filtered_by(fresh_db):
    for table_name in ("daily_ohlcv", "minute_ohlcv"):
        indexed = {name for name, is_indexed in select(
            fresh_db, 'SELECT "column", indexed FROM table_columns(%s)', table_name) if is_indexed}
        assert indexed == {"exchange_code", "symbol_code"}

def test_running_setup_again_starts_from_empty_tables(fresh_db, questdb_config):
    select(fresh_db, "INSERT INTO exchange (exchange_code) VALUES ('US')")
    select(fresh_db, "INSERT INTO daily_ohlcv (timestamp, exchange_code, symbol_code) VALUES (now(), 'US', 'AAPL')")
    wait_for_count(fresh_db, "daily_ohlcv", 1)
    assert count(fresh_db, "exchange") == 1
    setup(questdb_config)
    settle(fresh_db, "daily_ohlcv")
    assert (count(fresh_db, "exchange"), count(fresh_db, "daily_ohlcv")) == (0, 0)
