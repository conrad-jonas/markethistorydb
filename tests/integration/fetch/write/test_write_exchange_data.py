"""Integration tests for fetch/write/write_exchange_data.py"""

import pandas as pd

from markethistorydb.db import tables
from markethistorydb.fetch.write import WriteExchangeData
from tests.integration.conftest import count, select


def _exchange(name: str) -> pd.Series:
    return pd.Series({"name": name, "exchange_code": "US", "operating_mic": "XNAS", "country": "USA",
                      "currency": "USD", "country_iso_2": "US", "country_iso_3": "USA"},
                     index=list(tables.Exchange.ALL_COLUMNS))


def test_writing_an_exchange_twice_keeps_one_record_with_the_newer_values(fresh_db):
    # Back to back, as a run writes them: the second write's read must see the first insert, which
    # the non-WAL table guarantees - on a WAL table it could miss it and insert a duplicate
    writer = WriteExchangeData(fresh_db)
    writer.update_exchange_data(_exchange("USA Stocks"))
    writer.update_exchange_data(_exchange("US Stocks"))
    assert select(fresh_db, "SELECT name FROM exchange") == [("US Stocks",)]
    assert count(fresh_db, "exchange") == 1
