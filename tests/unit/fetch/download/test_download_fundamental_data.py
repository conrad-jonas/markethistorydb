"""Tests for fetch/download/download_fundamental_data.py"""

import pandas as pd
import pytest

from markethistorydb.fetch.download import DownloadFundamentalData
from markethistorydb.utils import SymbolStatus, TimeFrame
from tests.fakes import FakeDb


def _symbol(exchange_code: str) -> pd.Series:
    return pd.Series({"symbol_code": "AAPL", "exchange_code": exchange_code, "exchange_url_code": "US"})

def _run(db: FakeDb, exchange_code: str = "NASDAQ") -> bool:
    return DownloadFundamentalData(db, "TOKEN", TimeFrame.DAILY, SymbolStatus.ACTIVE).run(
        _symbol(exchange_code))


@pytest.mark.parametrize("exchange_code", ["NYSE ARCA", "LSE", "FOREX"])
def test_exchanges_without_fundamentals_are_not_requested(routed_api, exchange_code):
    # Saves a request, and API quota, for every ETF, currency and non-US symbol
    assert _run(FakeDb(), exchange_code) is False
    assert routed_api.requests == []

@pytest.mark.parametrize("exchange_code", ["NASDAQ", "NYSE"])
def test_the_fundamentals_of_a_us_stock_are_stored(routed_api, exchange_code):
    db = FakeDb(sector=pd.Series(dtype=object))
    assert _run(db, exchange_code) is True
    sector = db.insert.called("sector")[0][0]
    assert (sector["symbol_code"], sector["exchange_code"]) == ("AAPL", exchange_code)
    # Each of the 8 fundamental tables is cleared of the symbol, then written
    assert len(db.delete.called("symbol_from_table")) == len(db.insert.called("table")) == 8

def test_a_symbol_without_fundamentals_stores_nothing(routed_api):
    routed_api.override("/fundamentals/", {})
    db = FakeDb()
    assert _run(db) is False
    assert db.insert.calls == [] and db.delete.calls == []
