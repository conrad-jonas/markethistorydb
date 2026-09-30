"""Tests for fetch/download/download_symbol_data.py"""

import pandas as pd
import pytest

from markethistorydb.errors import NoDataError
from markethistorydb.fetch.download import DownloadSymbolData
from markethistorydb.utils import SymbolStatus, TimeFrame
from tests.fakes import FakeDb


def _run(db: FakeDb, exchange_url_codes: list[str]) -> pd.DataFrame:
    return DownloadSymbolData(db, "TOKEN", TimeFrame.DAILY, SymbolStatus.ACTIVE).run(
        pd.Series(exchange_url_codes))


def test_the_symbols_of_every_exchange_are_stored_and_returned(routed_api):
    db = FakeDb(symbol=pd.Series(dtype=object))
    df = _run(db, ["US", "LSE"])
    assert routed_api.urls() == ["https://eodhd.com/api/exchange-symbol-list/US?",
                            "https://eodhd.com/api/exchange-symbol-list/LSE?"]
    # US is cut down to its daily venues (3 of 4), LSE keeps all 4
    assert len(df) == 7 and len(db.insert.called("symbol")) == 7

def test_every_symbol_remembers_the_exchange_code_its_urls_are_built_with(routed_api):
    df = _run(FakeDb(symbol=pd.Series(dtype=object)), ["US", "LSE"])
    assert df["exchange_url_code"].tolist() == ["US"] * 3 + ["LSE"] * 4
    # ... while its own exchange_code stays the venue
    assert df["exchange_code"].tolist()[:3] == ["NASDAQ", "NYSE", "NYSE ARCA"]

def test_a_stored_symbol_is_updated_rather_than_inserted_again(routed_api):
    db = FakeDb(symbol=pd.Series(["stored"]))
    _run(db, ["US"])
    assert db.insert.calls == [] and len(db.update.called("symbol")) == 3

def test_an_exchange_without_symbols_is_skipped(routed_api):
    routed_api.override("/exchange-symbol-list/LSE", [])
    df = _run(FakeDb(symbol=pd.Series(dtype=object)), ["LSE", "US"])
    assert set(df["exchange_url_code"]) == {"US"}

def test_no_symbols_anywhere_raises_naming_the_exchanges_and_writes_nothing(routed_api):
    routed_api.override("/exchange-symbol-list/", [])
    db = FakeDb(symbol=pd.Series(dtype=object))
    with pytest.raises(NoDataError, match="US, LSE"):
        _run(db, ["US", "LSE"])
    assert db.read.calls == [] and db.insert.calls == []
