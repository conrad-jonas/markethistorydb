"""Integration tests for fetch/write/write_fundamental_data.py, fed with AAPL's real payload"""

import pandas as pd

from markethistorydb.fetch.eodhd import RequestFundamentalData
from markethistorydb.fetch.utils import TABLE_PER_FUNDAMENTAL_TYPE
from markethistorydb.fetch.write import WriteFundamentalData
from markethistorydb.utils import TimeFrame
from tests.integration.conftest import count, select, settle

_SYMBOL = pd.Series({"symbol_code": "AAPL", "exchange_code": "NASDAQ", "exchange_url_code": "US"})


def _write_fundamentals(db):
    series_sector, dict_fundamental = RequestFundamentalData("TOKEN", TimeFrame.DAILY, _SYMBOL).get()
    writer = WriteFundamentalData(db)
    writer.set_symbol_code("AAPL")
    writer.set_exchange_code("NASDAQ")
    writer.update_sector_data(series_sector)
    writer.replace_fundamental_data(dict_fundamental)
    # Only the fundamental tables are WAL; the sector table shows a write to the next read at once
    settle(db, *(table.NAME for table in TABLE_PER_FUNDAMENTAL_TYPE.values()))


def test_the_payload_fills_the_sector_and_every_fundamental_table(fresh_db, routed_api):
    # Neither used to work: the checks rejected every payload, the sector record had one index
    # entry too many, and the strings of the payload were refused by DOUBLE and TIMESTAMP columns
    _write_fundamentals(fresh_db)
    assert count(fresh_db, "sector") == 1
    for table in TABLE_PER_FUNDAMENTAL_TYPE.values():
        assert count(fresh_db, table.NAME) == 2, table.NAME
        # No column was added or retyped by ILP along the way
        assert [name for name, in select(fresh_db, 'SELECT "column" FROM table_columns(%s)', table.NAME)] == list(
            table.ALL_COLUMNS)
    total_assets = select(fresh_db, "SELECT total_assets FROM balance_sheet_quarterly ORDER BY filing_date DESC")
    assert isinstance(total_assets[0][0], float)

def test_writing_the_fundamentals_again_replaces_them_rather_than_adding_to_them(fresh_db, routed_api):
    _write_fundamentals(fresh_db)
    _write_fundamentals(fresh_db)
    assert count(fresh_db, "sector") == 1
    assert all(count(fresh_db, table.NAME) == 2 for table in TABLE_PER_FUNDAMENTAL_TYPE.values())
