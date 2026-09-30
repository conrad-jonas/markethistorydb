"""Tests for fetch/write/write_exchange_data.py"""

import pandas as pd

from markethistorydb.fetch.write import WriteExchangeData
from tests.fakes import FakeDb

_EXCHANGE = pd.Series({"name": "USA Stocks", "exchange_code": "US"})


def test_a_new_exchange_is_inserted():
    db = FakeDb(exchange=pd.Series(dtype=object))
    WriteExchangeData(db).update_exchange_data(_EXCHANGE)
    assert db.read.called("exchange") == [("US",)]
    assert db.insert.called("exchange") == [(_EXCHANGE,)] and db.update.calls == []

def test_a_stored_exchange_is_updated_so_it_is_not_duplicated():
    # ILP appends a duplicate rather than rejecting it, so the read decides
    db = FakeDb(exchange=pd.Series(["USA Stocks", "US"]))
    WriteExchangeData(db).update_exchange_data(_EXCHANGE)
    assert db.update.called("exchange") == [(_EXCHANGE,)] and db.insert.calls == []
