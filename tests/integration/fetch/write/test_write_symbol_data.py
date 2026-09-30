"""Integration tests for fetch/write/write_symbol_data.py"""

import pandas as pd

from markethistorydb.fetch.write import WriteSymbolData
from markethistorydb.utils import SymbolStatus, TimeFrame
from tests.integration.conftest import count, select


def _symbol(name: str) -> pd.Series:
    # As DownloadSymbolData hands it over, exchange_url_code included
    return pd.Series({"symbol_code": "AAPL", "time_frame": "DAILY", "symbol_status": "ACTIVE",
                      "name": name, "exchange_code": "NASDAQ", "country": "USA", "currency": "USD",
                      "type": "Common Stock", "isin": "US0378331005", "exchange_url_code": "US"})


def test_writing_a_symbol_twice_keeps_one_record_with_the_newer_values(fresh_db):
    # Back to back, as a run writes them: the second write's read must see the first insert, which
    # the non-WAL table guarantees - on a WAL table it could miss it and insert a duplicate
    writer = WriteSymbolData(fresh_db, TimeFrame.DAILY, SymbolStatus.ACTIVE)
    writer.update_symbol_data(_symbol("Apple"))
    writer.update_symbol_data(_symbol("Apple Inc"))
    assert select(fresh_db, "SELECT name FROM symbol") == [("Apple Inc",)]
    assert count(fresh_db, "symbol") == 1
    # The routing field was not stored as a column of its own
    assert "exchange_url_code" not in [name for name, in select(
        fresh_db, "SELECT \"column\" FROM table_columns('symbol')")]
