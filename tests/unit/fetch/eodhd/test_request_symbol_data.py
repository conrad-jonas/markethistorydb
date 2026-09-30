"""Tests for fetch/eodhd/request_symbol_data.py"""

import pytest

from markethistorydb.db import tables
from markethistorydb.errors import CompatibilityError
from markethistorydb.fetch.eodhd import RequestSymbolData
from markethistorydb.utils import SymbolStatus, TimeFrame
from tests.fakes import FakeResponse, load_payload


def _get(time_frame=TimeFrame.DAILY, symbol_status=SymbolStatus.ACTIVE, exchange_url_code="US"):
    return RequestSymbolData("TOKEN", time_frame, symbol_status).get(exchange_url_code)


def test_the_symbol_list_of_the_exchange_is_requested(routed_api):
    _get(exchange_url_code="LSE")
    assert routed_api.urls() == ["https://eodhd.com/api/exchange-symbol-list/LSE?"]
    assert routed_api.params("/exchange-symbol-list/") == [{"api_token": "TOKEN", "fmt": "json"}]

def test_delisted_symbols_are_asked_for_explicitly(routed_api):
    _get(symbol_status=SymbolStatus.DELISTED)
    assert routed_api.params("/exchange-symbol-list/")[0]["delisted"] == "1"

@pytest.mark.parametrize("time_frame, exchange_url_code, expected_codes", [
    # The US list mixes every US venue; only the ones fetched per time frame are kept
    (TimeFrame.DAILY, "US", ["AAPL", "IBM", "SPY"]),
    (TimeFrame.MINUTE, "US", ["AAPL", "IBM"]),
    (TimeFrame.DAILY, "LSE", ["AAPL", "IBM", "SPY", "ABCD"]),
])
def test_the_us_list_is_cut_down_to_the_venues_of_the_time_frame(routed_api, time_frame, exchange_url_code,
                                                                  expected_codes):
    df = _get(time_frame, exchange_url_code=exchange_url_code)
    assert df[tables.Symbol.Columns.SYMBOL_CODE].tolist() == expected_codes

def test_the_symbols_come_with_the_db_columns_time_frame_and_status(routed_api):
    df = _get(TimeFrame.MINUTE, SymbolStatus.DELISTED)
    assert list(df.columns) == list(tables.Symbol.ALL_COLUMNS)
    first = df.iloc[0]
    assert (first["symbol_code"], first["exchange_code"], first["time_frame"], first["symbol_status"],
            first["isin"]) == ("AAPL", "NASDAQ", "MINUTE", "DELISTED", "US0378331005")

@pytest.mark.parametrize("answer", [[], FakeResponse(404, text="not found")])
def test_an_exchange_without_symbols_yields_an_empty_frame(routed_api, answer):
    routed_api.override("/exchange-symbol-list/", answer)
    assert _get().empty

def test_a_missing_field_is_a_compatibility_error(routed_api):
    symbols = load_payload("exchange-symbol-list")
    for symbol in symbols:
        del symbol["Isin"]
    routed_api.override("/exchange-symbol-list/", symbols)
    with pytest.raises(CompatibilityError):
        _get()
