"""Tests for fetch/eodhd/request_fundamental_data.py"""

import pandas as pd
import pytest

from markethistorydb.db import tables
from markethistorydb.errors import CompatibilityError
from markethistorydb.fetch.eodhd import RequestFundamentalData
from markethistorydb.fetch.utils import FundamentalType, TABLE_PER_FUNDAMENTAL_TYPE
from markethistorydb.utils import TimeFrame
from tests.fakes import FakeResponse, load_payload

_SYMBOL = pd.Series({"symbol_code": "AAPL", "exchange_code": "NASDAQ", "exchange_url_code": "US"})


def _get() -> tuple[pd.Series, dict[FundamentalType, pd.DataFrame]]:
    return RequestFundamentalData("TOKEN", TimeFrame.DAILY, _SYMBOL).get()


def test_the_fundamentals_are_requested_filtered_to_the_sections_that_are_stored(routed_api):
    _get()
    assert routed_api.urls() == ["https://eodhd.com/api/fundamentals/AAPL.US?"]
    params = routed_api.params("/fundamentals/")[0]
    assert (params["api_token"], params["fmt"]) == ("TOKEN", "json")
    assert set(params["filter"].split(",")) == set(load_payload("fundamentals"))

def test_a_real_payload_passes_the_checks(routed_api):
    # The sample is AAPL's actual payload, so the checks must accept it as it is. They used to
    # compare against ALL_COLUMNS[1:-1], which starts at exchange_code, and rejected every symbol.
    series_sector, dict_fundamental = _get()
    assert series_sector.tolist()[:2] == ["Technology", "Consumer Electronics"]
    assert set(dict_fundamental) == set(TABLE_PER_FUNDAMENTAL_TYPE)

def test_every_record_set_holds_its_table_s_columns_in_snake_case(routed_api):
    _, dict_fundamental = _get()
    for fundamental_type, df in dict_fundamental.items():
        table = TABLE_PER_FUNDAMENTAL_TYPE[fundamental_type]
        assert set(df.columns) == set(table.ALL_COLUMNS[2:]), fundamental_type
        # One row per reporting period
        assert len(df) == 2

def test_the_columns_that_are_not_stored_are_dropped(routed_api):
    _, dict_fundamental = _get()
    assert "preferred_stock_redeemable" not in dict_fundamental[FundamentalType.BALANCE_SHEET_QUARTERLY]
    assert "preferred_stock_and_other_adjustments" not in dict_fundamental[
        FundamentalType.INCOME_STATEMENT_ANNUALLY]

def test_a_payload_without_the_unstored_columns_passes_as_well(routed_api):
    payload = load_payload("fundamentals")
    for period in payload["Financials::Balance_Sheet"]["quarterly"].values():
        del period["preferredStockRedeemable"]
    routed_api.override("/fundamentals/", payload)
    _, dict_fundamental = _get()
    assert FundamentalType.BALANCE_SHEET_QUARTERLY in dict_fundamental

def test_a_section_without_records_is_left_out_so_the_stored_ones_are_kept(routed_api):
    payload = load_payload("fundamentals")
    payload["Earnings::Annual"] = {}
    payload["Financials::Cash_Flow"]["quarterly"] = []
    routed_api.override("/fundamentals/", payload)
    _, dict_fundamental = _get()
    assert set(dict_fundamental) == set(TABLE_PER_FUNDAMENTAL_TYPE) - {
        FundamentalType.EARNINGS_ANNUALLY, FundamentalType.CASH_FLOW_QUARTERLY}

@pytest.mark.parametrize("answer", [{}, FakeResponse(404, text="not found")])
def test_a_symbol_without_fundamentals_yields_nothing(routed_api, answer):
    routed_api.override("/fundamentals/", answer)
    series_sector, dict_fundamental = _get()
    assert series_sector.empty and dict_fundamental == {}


# --- unexpected structure: a CompatibilityError for this symbol, never a crash of the run ----

def _payload_without(*path: str) -> dict:
    payload = load_payload("fundamentals")
    parent = payload
    for key in path[:-1]:
        parent = parent[key]
    del parent[path[-1]]
    return payload

@pytest.mark.parametrize("payload", [
    _payload_without("General::GicSector"),
    _payload_without("Earnings::History"),
    _payload_without("Financials::Balance_Sheet", "yearly"),
    {**load_payload("fundamentals"), "Financials::Cash_Flow": ["not", "a", "dict"]},
    ["a", "list"],
], ids=["sector value", "earnings section", "yearly balance sheet", "section as list", "payload as list"])
def test_a_missing_or_misshapen_section_is_a_compatibility_error(routed_api, payload):
    routed_api.override("/fundamentals/", payload)
    with pytest.raises(CompatibilityError):
        _get()

def test_a_record_set_missing_a_column_is_a_compatibility_error_naming_the_type(routed_api):
    payload = load_payload("fundamentals")
    for period in payload["Financials::Income_Statement"]["yearly"].values():
        del period["totalRevenue"]
    routed_api.override("/fundamentals/", payload)
    with pytest.raises(CompatibilityError) as excinfo:
        _get()
    assert "Income statement annually" in str(excinfo.value)

def test_the_order_of_the_fields_does_not_matter(routed_api):
    payload = load_payload("fundamentals")
    history = payload["Earnings::History"]
    payload["Earnings::History"] = {date: dict(reversed(list(record.items())))
                                    for date, record in history.items()}
    routed_api.override("/fundamentals/", payload)
    assert FundamentalType.EARNINGS_QUARTERLY in _get()[1]

@pytest.mark.parametrize("num_of_values", [5, 7])
def test_sector_and_industry_must_have_one_value_per_sector_column(num_of_values):
    with pytest.raises(CompatibilityError):
        RequestFundamentalData._check_sector_and_industry_data(pd.Series(["x"] * num_of_values))
    assert len(tables.Sector.ALL_COLUMNS[2:]) == 6
