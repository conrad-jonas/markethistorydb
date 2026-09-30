"""Tests for fetch/eodhd/request_exchange_data.py"""

import pytest

from markethistorydb.db import tables
from markethistorydb.errors import CompatibilityError
from markethistorydb.fetch.eodhd import RequestExchangeData
from markethistorydb.utils import TimeFrame
from tests.fakes import load_payload


def test_the_exchange_list_is_requested_with_the_token_as_json(routed_api):
    RequestExchangeData("TOKEN", TimeFrame.DAILY).get()
    assert routed_api.urls() == ["https://eodhd.com/api/exchanges-list/?"]
    assert routed_api.params("/exchanges-list/") == [{"api_token": "TOKEN", "fmt": "json"}]

@pytest.mark.parametrize("time_frame, expected_names", [
    (TimeFrame.DAILY, ["USA Stocks", "London Exchange", "FOREX"]),
    (TimeFrame.MINUTE, ["USA Stocks", "FOREX"]),
])
def test_only_the_exchanges_of_the_time_frame_are_kept(routed_api, time_frame, expected_names):
    df = RequestExchangeData("TOKEN", time_frame).get()
    assert df[tables.Exchange.Columns.NAME].tolist() == expected_names

def test_the_columns_are_renamed_to_the_db_columns(routed_api):
    df = RequestExchangeData("TOKEN", TimeFrame.DAILY).get()
    assert list(df.columns) == list(tables.Exchange.ALL_COLUMNS)
    assert df.iloc[0][tables.Exchange.Columns.EXCHANGE_CODE] == "US"

def test_the_order_of_the_fields_does_not_matter(routed_api):
    routed_api.override("/exchanges-list/", [dict(reversed(list(exchange.items())))
                                        for exchange in load_payload("exchanges-list")])
    df = RequestExchangeData("TOKEN", TimeFrame.DAILY).get()
    assert df[tables.Exchange.Columns.EXCHANGE_CODE].tolist() == ["US", "LSE", "FOREX"]

def test_a_missing_field_is_a_compatibility_error(routed_api):
    exchanges = load_payload("exchanges-list")
    for exchange in exchanges:
        del exchange["OperatingMIC"]
    routed_api.override("/exchanges-list/", exchanges)
    with pytest.raises(CompatibilityError):
        RequestExchangeData("TOKEN", TimeFrame.DAILY).get()

def test_no_exchange_list_at_all_is_a_compatibility_error(routed_api):
    # Without exchanges nothing else can be fetched, so an empty answer must not pass silently
    routed_api.override("/exchanges-list/", [])
    with pytest.raises(CompatibilityError):
        RequestExchangeData("TOKEN", TimeFrame.DAILY).get()
