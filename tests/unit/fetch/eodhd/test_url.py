"""Tests for fetch/eodhd/url.py"""

from urllib.parse import urlsplit
import pytest

from markethistorydb.fetch.eodhd import Url


def test_each_endpoint_has_its_documented_address():
    assert Url.Address.EXCHANGES_LIST == "https://eodhd.com/api/exchanges-list/?"
    assert Url.Address.exchange_symbol_list("US") == "https://eodhd.com/api/exchange-symbol-list/US?"
    assert Url.Address.eod("AAPL", "US") == "https://eodhd.com/api/eod/AAPL.US?"
    assert Url.Address.intraday("AAPL", "US") == "https://eodhd.com/api/intraday/AAPL.US?"
    assert Url.Address.fundamentals("AAPL", "US") == "https://eodhd.com/api/fundamentals/AAPL.US?"

@pytest.mark.parametrize("symbol_code", ["BRK-B", "BRK.B", "0700", "VOW3"])
def test_ordinary_codes_are_left_readable(symbol_code):
    assert Url.Address.eod(symbol_code, "XETRA").endswith("/eod/{0}.XETRA?".format(symbol_code))


# --- security: a code from the provider's lists cannot redirect the request ----------------

@pytest.mark.parametrize("build", [Url.Address.eod, Url.Address.intraday, Url.Address.fundamentals])
@pytest.mark.parametrize("symbol_code", [
    "../exchanges-list/", "AAPL?api_token=OTHER&", "AAPL#", "A/B", "AAPL%2F"])
def test_a_symbol_code_stays_within_its_path_segment(build, symbol_code):
    parts = urlsplit(build(symbol_code, "US") + "api_token=TOKEN")
    # The query is ours alone, and the path keeps its three segments
    assert parts.query == "api_token=TOKEN"
    assert parts.fragment == ""
    assert len(parts.path.split("/")) == 4

def test_an_exchange_code_stays_within_its_path_segment():
    parts = urlsplit(Url.Address.exchange_symbol_list("US/../../other?x=") + "fmt=json")
    assert parts.path == "/api/exchange-symbol-list/US%2F..%2F..%2Fother%3Fx%3D"
    assert parts.query == "fmt=json"
