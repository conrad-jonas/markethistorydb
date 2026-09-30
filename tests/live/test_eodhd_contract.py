"""
Contract tests against the real eodhd.com API: the provider still answers the way the request
layer expects and the sample payloads in tests/data/eodhd record.

A failed shape test means eodhd.com changed its API since the sample was taken: adapt the request
layer and the tables where needed, then refresh the sample, so that the unit tests run against the
new shape. A failed request layer test means a fetch run would fail on the live data.
"""

from collections.abc import Callable, Iterable
from datetime import UTC, datetime, timedelta
from typing import Any

import pandas as pd
import pytest

from markethistorydb.db import tables
from markethistorydb.errors import AccountError
from markethistorydb.fetch.eodhd import (RequestExchangeData, RequestFundamentalData, RequestPriceData,
                                         RequestSymbolData)
from markethistorydb.fetch.utils import TABLE_PER_FUNDAMENTAL_TYPE
from markethistorydb.utils import SymbolStatus, TimeFrame
from tests.fakes import load_payload

# Public token of eodhd.com; it serves eod, intraday and fundamentals for a few symbols, AAPL.US
# among them, but neither the list of exchanges nor the list of an exchange's symbols
_DEMO_API_TOKEN = "demo"
_SYMBOL = pd.Series({"symbol_code": "AAPL", "exchange_code": "NASDAQ", "exchange_url_code": "US"})
_EXCHANGE_URL_CODE = "US"
# Periods requested, long enough to hold records whatever the day the tests run on
_DAILY_PERIOD = timedelta(days=30)
_MINUTE_PERIOD = timedelta(days=7)
# Record sets of the fundamentals payload: the section, and the key of the record set within it
# (None if the section is the record set itself)
_FUNDAMENTAL_RECORD_SETS = (
    ("Earnings::History", None),
    ("Earnings::Annual", None),
    ("Financials::Balance_Sheet", "quarterly"),
    ("Financials::Balance_Sheet", "yearly"),
    ("Financials::Cash_Flow", "quarterly"),
    ("Financials::Cash_Flow", "yearly"),
    ("Financials::Income_Statement", "quarterly"),
    ("Financials::Income_Statement", "yearly"),
)


def _json_type(value: Any) -> str | None:
    """
    Names the JSON type of a parsed value, integers and floats alike as number.

    :param value: Value as json.loads returned it
    :return: JSON type name, or None for null, which says nothing about the field's type
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    return "array" if isinstance(value, list) else "object"


def _field_types(records: Iterable[dict[str, Any]]) -> dict[str, set[str]]:
    """
    Collects the fields of *records* with the JSON types their values have.

    :param records: Records as the provider sent them
    :return: Every field any record holds, with the types of its non-null values
    """
    field_types: dict[str, set[str]] = {}
    for record in records:
        for field, value in record.items():
            types = field_types.setdefault(field, set())
            value_type = _json_type(value)
            if value_type is not None:
                types.add(value_type)
    return field_types


def _assert_same_shape(live_records: list[dict[str, Any]], sample_records: list[dict[str, Any]], name: str):
    """
    Asserts that the live records have the fields of the sample records, with the same types.

    :param live_records: Records the provider sends now
    :param sample_records: Records of the sample payload
    :param name: Name of the record set in the failure message
    """
    assert live_records, "{0}: the provider sent no records".format(name)
    live, sample = _field_types(live_records), _field_types(sample_records)
    problems = []
    if added := sorted(set(live) - set(sample)):
        problems.append("fields added: {0}".format(added))
    if removed := sorted(set(sample) - set(live)):
        problems.append("fields removed: {0}".format(removed))
    # A field that is null throughout either side has no type to compare
    changed = {field: (sorted(sample[field]), sorted(live[field])) for field in set(live) & set(sample)
               if sample[field] and live[field] and not live[field] <= sample[field]}
    if changed:
        problems.append("types changed (sample -> live): {0}".format(changed))
    assert not problems, "{0}: {1}".format(name, "; ".join(problems))


def _fundamental_records(payload: dict[str, Any], section: str, period: str | None) -> list[dict[str, Any]]:
    """
    Picks one record set out of a fundamentals payload.

    :param payload: Fundamentals payload
    :param section: Section holding the record set, e.g. "Financials::Cash_Flow"
    :param period: Key of the record set within the section, or None if the section is the set
    :return: Records of the set, one per reporting period
    """
    record_set = payload[section] if period is None else payload[section][period]
    return list(record_set.values())


# --- live payloads, fetched once per run through the request layer (token masked in errors) --

@pytest.fixture(scope="module")
def live_daily_prices() -> list[dict[str, Any]]:
    request = RequestPriceData(_DEMO_API_TOKEN, TimeFrame.DAILY, _SYMBOL)
    return request._request_list(request._get_url_for_price_data(),
                                 request._get_url_params_for_price_data(datetime.now(UTC).replace(tzinfo=None) - _DAILY_PERIOD, None))

@pytest.fixture(scope="module")
def live_minute_prices() -> list[dict[str, Any]]:
    request = RequestPriceData(_DEMO_API_TOKEN, TimeFrame.MINUTE, _SYMBOL)
    end_datetime = datetime.now(UTC).replace(tzinfo=None)
    return request._request_list(request._get_url_for_price_data(), request._get_url_params_for_price_data(
        end_datetime - _MINUTE_PERIOD, end_datetime))

@pytest.fixture(scope="module")
def live_fundamentals() -> dict[str, Any]:
    request = RequestFundamentalData(_DEMO_API_TOKEN, TimeFrame.DAILY, _SYMBOL)
    return request._request_object(request._get_url_for_fundamental_data(),
                                   request._get_url_params_for_fundamental_data())

def _request_with_account_token[T](request_payload: Callable[[], T]) -> T:
    """
    Requests a payload with the account's token, skipping the test if the account cannot.

    Whether the account's token is valid, has calls left and covers the endpoint says nothing about
    the API's shape, so any of these is a skip rather than a failure. The demo token's requests
    are not wrapped: that token serving an endpoint no more is a change of the API.

    :param request_payload: Requests the payload
    :return: The payload
    """
    try:
        return request_payload()
    except AccountError as error:
        pytest.skip("eodhd.com refused EODHD_API_TOKEN ({0}): {1}".format(type(error).__name__, error))

@pytest.fixture(scope="module")
def live_exchanges(api_token) -> list[dict[str, Any]]:
    request = RequestExchangeData(api_token, TimeFrame.DAILY)
    return _request_with_account_token(lambda: request._request_list(
        request._get_url_for_exchanges_data(), request._get_url_params_for_exchanges_data()))

@pytest.fixture(scope="module")
def live_exchange_symbols(api_token) -> list[dict[str, Any]]:
    request = RequestSymbolData(api_token, TimeFrame.DAILY, SymbolStatus.ACTIVE)
    return _request_with_account_token(lambda: request._request_list(
        request._get_url_for_symbol_data(_EXCHANGE_URL_CODE), request._get_url_params_for_symbol_data()))


# --- the provider still sends what the samples record --------------------------------------

def test_daily_prices_have_the_sample_s_shape(live_daily_prices):
    _assert_same_shape(live_daily_prices, load_payload("eod"), "eod")

def test_minute_prices_have_the_sample_s_shape(live_minute_prices):
    _assert_same_shape(live_minute_prices, load_payload("intraday"), "intraday")

def test_the_fundamentals_have_the_sample_s_sections(live_fundamentals):
    _assert_same_shape([live_fundamentals], [load_payload("fundamentals")], "fundamentals")

@pytest.mark.parametrize("section, period", _FUNDAMENTAL_RECORD_SETS,
                         ids=["{0} {1}".format(section, period or "").strip() for section, period in _FUNDAMENTAL_RECORD_SETS])
def test_every_fundamental_record_set_has_the_sample_s_shape(live_fundamentals, section, period):
    sample = load_payload("fundamentals")
    if period is not None:
        # The fields next to the record sets, e.g. currency_symbol
        _assert_same_shape([live_fundamentals[section]], [sample[section]], section)
    _assert_same_shape(_fundamental_records(live_fundamentals, section, period),
                       _fundamental_records(sample, section, period), "{0} {1}".format(section, period or ""))

def test_exchanges_have_the_sample_s_shape(live_exchanges):
    _assert_same_shape(live_exchanges, load_payload("exchanges-list"), "exchanges-list")

def test_exchange_symbols_have_the_sample_s_shape(live_exchange_symbols):
    _assert_same_shape(live_exchange_symbols, load_payload("exchange-symbol-list"), "exchange-symbol-list")


# --- the request layer takes the live payloads, and yields what the tables store -----------
# The live payload is answered through the fake API, so that no endpoint is called twice.

def test_live_daily_prices_yield_the_columns_of_their_table(routed_api, live_daily_prices):
    routed_api.override("/eod/", live_daily_prices)
    df = RequestPriceData("TOKEN", TimeFrame.DAILY, _SYMBOL).get()
    assert set(df.columns) == set(tables.DailyOhlcv.ALL_COLUMNS)

def test_live_minute_prices_yield_the_columns_of_their_table(routed_api, live_minute_prices):
    routed_api.override("/intraday/", live_minute_prices)
    end_datetime = datetime.now(UTC).replace(tzinfo=None)
    df = RequestPriceData("TOKEN", TimeFrame.MINUTE, _SYMBOL).get(end_datetime - _MINUTE_PERIOD, end_datetime)
    assert set(df.columns) == set(tables.MinuteOhlcv.ALL_COLUMNS)

def test_live_fundamentals_yield_the_columns_of_their_tables(routed_api, live_fundamentals):
    routed_api.override("/fundamentals/", live_fundamentals)
    series_sector, dict_fundamental = RequestFundamentalData("TOKEN", TimeFrame.DAILY, _SYMBOL).get()
    assert len(series_sector) == len(tables.Sector.ALL_COLUMNS[2:])
    assert set(dict_fundamental) == set(TABLE_PER_FUNDAMENTAL_TYPE)
    for fundamental_type, df in dict_fundamental.items():
        # The writer adds the symbol and exchange code, the first two columns
        table = TABLE_PER_FUNDAMENTAL_TYPE[fundamental_type]
        assert set(df.columns) == set(table.ALL_COLUMNS[2:]), fundamental_type.name

def test_live_exchanges_yield_the_columns_of_their_table(routed_api, live_exchanges):
    routed_api.override("/exchanges-list/", live_exchanges)
    df = RequestExchangeData("TOKEN", TimeFrame.DAILY).get()
    assert not df.empty
    assert set(tables.Exchange.ALL_COLUMNS) <= set(df.columns)

def test_live_exchange_symbols_yield_the_columns_of_their_table(routed_api, live_exchange_symbols):
    routed_api.override("/exchange-symbol-list/", live_exchange_symbols)
    df = RequestSymbolData("TOKEN", TimeFrame.DAILY, SymbolStatus.ACTIVE).get(_EXCHANGE_URL_CODE)
    assert not df.empty
    assert list(df.columns) == list(tables.Symbol.ALL_COLUMNS)
