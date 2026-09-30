"""Tests for fetch/utils.py"""

import dataclasses
import pandas as pd
import pytest

from markethistorydb.db import tables
import markethistorydb.fetch.utils as utils_module
from markethistorydb.fetch.utils import (FailedSymbol, FundamentalType, TABLE_PER_FUNDAMENTAL_TYPE,
                                         convert_df_column_names_from_camel_to_snake_case,
                                         drop_records_before_1970)


@pytest.mark.parametrize("camel, snake", [
    ("totalAssets", "total_assets"),
    ("reportDate", "report_date"),
    ("nonCurrrentAssetsOther", "non_currrent_assets_other"),
    ("filing_date", "filing_date"),
    ("currency_symbol", "currency_symbol"),
    ("date", "date"),
])
def test_camel_case_columns_become_snake_case_and_snake_case_ones_stay(camel, snake):
    df = pd.DataFrame(columns=[camel])
    assert list(convert_df_column_names_from_camel_to_snake_case(df).columns) == [snake]

def test_the_columns_are_renamed_in_place_and_the_frame_returned():
    df = pd.DataFrame({"epsActual": [1.0]})
    assert convert_df_column_names_from_camel_to_snake_case(df) is df
    assert list(df.columns) == ["eps_actual"]

def test_every_fundamental_type_but_sector_and_industry_has_its_own_table():
    assert set(TABLE_PER_FUNDAMENTAL_TYPE) == set(FundamentalType) - {FundamentalType.SECTOR_AND_INDUSTRY}
    assert len(set(TABLE_PER_FUNDAMENTAL_TYPE.values())) == len(TABLE_PER_FUNDAMENTAL_TYPE)
    assert TABLE_PER_FUNDAMENTAL_TYPE[FundamentalType.CASH_FLOW_ANNUALLY] is tables.CashFlowAnnually

def test_a_failed_symbol_is_an_immutable_record():
    failed_symbol = FailedSymbol("AAPL", "NASDAQ", "RequestError")
    with pytest.raises(dataclasses.FrozenInstanceError):
        failed_symbol.symbol_code = "IBM"
    assert failed_symbol == FailedSymbol("AAPL", "NASDAQ", "RequestError")


# --- 1970 cutoff ---------------------------------------------------------------------------

def _dated(*timestamps: str) -> pd.DataFrame:
    return pd.DataFrame({"ts": pd.to_datetime(list(timestamps)), "v": range(len(timestamps))},
                        index=range(10, 10 + len(timestamps)))

def test_records_from_before_1970_are_dropped_and_the_rest_get_a_fresh_index():
    # QuestDB rejects a designated timestamp before 1970, but takes the epoch itself
    df = drop_records_before_1970(_dated("1969-12-31 23:59:59", "1970-01-01 00:00:00", "2024-03-05 00:00:00"),
                                  "ts", "DAILY price", "IBM.NYSE")
    assert df["v"].tolist() == [1, 2] and df.index.tolist() == [0, 1]

def test_dropping_records_is_logged_with_the_symbol_and_their_number(caplog):
    with caplog.at_level("WARNING", logger=utils_module.__name__):
        drop_records_before_1970(_dated("1962-01-02", "1969-12-31", "2024-03-05"), "ts", "DAILY price", "IBM.NYSE")
    assert [record.getMessage() for record in caplog.records] == [
        "Dropped 2 DAILY price records of IBM.NYSE from before 1970, which QuestDB cannot store"]

def test_nothing_is_logged_when_no_record_is_from_before_1970(caplog):
    with caplog.at_level("WARNING", logger=utils_module.__name__):
        df = drop_records_before_1970(_dated("1970-01-01", "2024-03-05"), "ts", "DAILY price", "IBM.NYSE")
    assert len(df) == 2 and caplog.records == []

def test_the_caller_s_records_are_not_filtered():
    df = _dated("1962-01-02", "2024-03-05")
    drop_records_before_1970(df, "ts", "DAILY price", "IBM.NYSE")
    assert len(df) == 2 and df.index.tolist() == [10, 11]
