"""Tests for fetch/eodhd/request_price_data.py"""

from datetime import datetime
import pandas as pd
import pytest

from markethistorydb.db import tables
from markethistorydb.errors import CompatibilityError
from markethistorydb.fetch.eodhd import RequestPriceData
from markethistorydb.utils import TimeFrame
from tests.fakes import FakeResponse, load_payload

_SYMBOL = pd.Series({"symbol_code": "AAPL", "exchange_code": "NASDAQ", "exchange_url_code": "US"})


def _requester(time_frame: TimeFrame) -> RequestPriceData:
    return RequestPriceData("TOKEN", time_frame, _SYMBOL)


# --- daily ---------------------------------------------------------------------------------

def test_daily_prices_are_requested_from_the_eod_endpoint(routed_api):
    _requester(TimeFrame.DAILY).get()
    assert routed_api.urls() == ["https://eodhd.com/api/eod/AAPL.US?"]
    assert routed_api.params("/eod/") == [{"api_token": "TOKEN", "fmt": "json"}]

def test_daily_prices_are_requested_from_the_start_day_on(routed_api):
    _requester(TimeFrame.DAILY).get(datetime(2024, 3, 5, 17, 30))
    assert routed_api.params("/eod/")[0]["from"] == "2024-03-05"

def test_daily_prices_come_with_the_db_columns(routed_api):
    df = _requester(TimeFrame.DAILY).get()
    assert set(df.columns) == set(tables.DailyOhlcv.ALL_COLUMNS)
    # WritePriceData converts the dates
    assert df["timestamp"].tolist() == [row["date"] for row in load_payload("eod")]
    assert set(df["symbol_code"]) == {"AAPL"} and set(df["exchange_code"]) == {"NASDAQ"}

def test_a_daily_payload_without_adjusted_close_is_a_compatibility_error(routed_api):
    rows = load_payload("eod")
    for row in rows:
        del row["adjusted_close"]
    routed_api.override("/eod/", rows)
    with pytest.raises(CompatibilityError):
        _requester(TimeFrame.DAILY).get()


# --- minute --------------------------------------------------------------------------------

def test_minute_prices_are_requested_from_the_intraday_endpoint_for_the_period(routed_api, local_time_off_utc):
    # The period is naive UTC, as the provider's payloads and QuestDB are, whatever the local zone
    _requester(TimeFrame.MINUTE).get(datetime(2024, 1, 2), datetime(2024, 5, 1))
    assert routed_api.urls() == ["https://eodhd.com/api/intraday/AAPL.US?"]
    assert routed_api.params("/intraday/") == [{
        "api_token": "TOKEN", "fmt": "json", "interval": "1m",
        "from": "1704153600", "to": "1714521600"}]  # 2024-01-02 and 2024-05-01, 00:00 UTC

@pytest.mark.parametrize("start, end", [(None, datetime(2024, 5, 1)), (datetime(2024, 1, 2), None)])
def test_minute_prices_need_both_ends_of_the_period(routed_api, start, end):
    # The intraday endpoint caps a request at 120 days, so an open period cannot be asked for
    with pytest.raises(ValueError):
        _requester(TimeFrame.MINUTE).get(start, end)
    assert routed_api.requests == []

def test_minute_prices_come_with_the_db_columns(routed_api):
    df = _requester(TimeFrame.MINUTE).get(datetime(2024, 1, 2), datetime(2024, 5, 1))
    assert set(df.columns) == set(tables.MinuteOhlcv.ALL_COLUMNS)
    first = load_payload("intraday")[0]
    # WritePriceData converts the Unix seconds
    assert df["timestamp"].iloc[0] == first["timestamp"]

def test_a_minute_payload_without_gmtoffset_is_accepted(routed_api):
    # The Unix seconds are absolute, so the offset is not needed
    rows = load_payload("intraday")
    for row in rows:
        del row["gmtoffset"]
    routed_api.override("/intraday/", rows)
    df = _requester(TimeFrame.MINUTE).get(datetime(2024, 1, 2), datetime(2024, 5, 1))
    assert set(df.columns) == set(tables.MinuteOhlcv.ALL_COLUMNS)


# --- no data -------------------------------------------------------------------------------

@pytest.mark.parametrize("answer", [[], FakeResponse(404, text="not found")])
def test_a_symbol_without_prices_yields_an_empty_frame(routed_api, answer):
    routed_api.override("/eod/", answer)
    assert _requester(TimeFrame.DAILY).get().empty
