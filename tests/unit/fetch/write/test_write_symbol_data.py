"""Tests for fetch/write/write_symbol_data.py"""

import pandas as pd

from markethistorydb.fetch.write import WriteSymbolData
from markethistorydb.utils import SymbolStatus, TimeFrame
from tests.fakes import FakeDb

_SYMBOL = pd.Series({"symbol_code": "AAPL", "exchange_code": "NASDAQ", "name": "Apple Inc"})


def _writer(db: FakeDb) -> WriteSymbolData:
    return WriteSymbolData(db, TimeFrame.MINUTE, SymbolStatus.DELISTED)


def test_the_symbol_is_looked_up_under_the_writer_s_time_frame_and_status():
    db = FakeDb(symbol=pd.Series(dtype=object))
    _writer(db).update_symbol_data(_SYMBOL)
    assert db.read.called("symbol") == [("AAPL", "NASDAQ", TimeFrame.MINUTE, SymbolStatus.DELISTED)]

def test_a_new_symbol_is_inserted():
    db = FakeDb(symbol=pd.Series(dtype=object))
    _writer(db).update_symbol_data(_SYMBOL)
    assert db.insert.called("symbol") == [(_SYMBOL,)] and db.update.calls == []

def test_a_stored_symbol_is_updated_so_it_is_not_duplicated():
    db = FakeDb(symbol=pd.Series(["AAPL"]))
    _writer(db).update_symbol_data(_SYMBOL)
    assert db.update.called("symbol") == [(_SYMBOL,)] and db.insert.calls == []
