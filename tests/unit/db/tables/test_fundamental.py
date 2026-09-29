"""Tests for db/tables/fundamental.py"""

import pytest

from markethistorydb.db import tables
from tests.unit.db.tables.schema import assert_matches_constants, created_tables

_FUNDAMENTAL_TABLES = [
    tables.EarningsQuarterly, tables.EarningsAnnually,
    tables.BalanceSheetQuarterly, tables.BalanceSheetAnnually,
    tables.CashFlowQuarterly, tables.CashFlowAnnually,
    tables.IncomeStatementQuarterly, tables.IncomeStatementAnnually,
]


@pytest.mark.parametrize("table", _FUNDAMENTAL_TABLES)
def test_the_key_columns_are_columns_of_the_table(table):
    assert table.TIMESTAMP_COLUMN in table.ALL_COLUMNS
    assert set(table.UNIQUE_KEY_COLUMNS) <= set(table.ALL_COLUMNS)

@pytest.mark.parametrize("table", _FUNDAMENTAL_TABLES)
def test_every_table_starts_with_the_symbol_and_exchange_code(table):
    # The request layer checks the payload against the columns after these two, which the
    # writer adds itself
    assert table.ALL_COLUMNS[:2] == ("symbol_code", "exchange_code")

@pytest.mark.parametrize("table", _FUNDAMENTAL_TABLES)
def test_every_table_shares_the_fundamental_base_and_its_columns(table):
    # The writer handles every table through type[FundamentalTable] and reads the codes from
    # table.Columns
    assert issubclass(table, tables.FundamentalTable)
    assert issubclass(table.Columns, tables.FundamentalTable.Columns)
    assert (table.Columns.SYMBOL_CODE, table.Columns.EXCHANGE_CODE) == table.ALL_COLUMNS[:2]

@pytest.mark.parametrize("table", _FUNDAMENTAL_TABLES)
def test_the_schema_creates_the_table_as_the_constants_describe_it(table):
    created = created_tables("fundamental.sql")[table.NAME]
    assert_matches_constants(created, table)
    assert created.dedup_keys is not None

def test_every_table_is_listed_by_name_once():
    assert tables.TABLE_NAMES_FUNDAMENTAL == [table.NAME for table in _FUNDAMENTAL_TABLES]
