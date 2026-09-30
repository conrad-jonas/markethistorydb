"""Tests for fetch/download/download_price_data.py"""

from datetime import date, datetime, timedelta
import math
import pandas as pd
import pytest

import markethistorydb.fetch.download.download_price_data as download_price_module
from markethistorydb.fetch.download import DownloadPriceData
from markethistorydb.utils import SymbolStatus, TimeFrame
from tests.fakes import FakeDb, load_payload

_SYMBOL = pd.Series({"symbol_code": "AAPL", "exchange_code": "NASDAQ", "exchange_url_code": "US"})
# "Today" for every test that depends on it
_TODAY = datetime(2025, 9, 25, 15, 30)


class _FrozenDateTime(datetime):
    """datetime whose today() is _TODAY"""

    @classmethod
    def today(cls):
        return cls(_TODAY.year, _TODAY.month, _TODAY.day, _TODAY.hour, _TODAY.minute)


@pytest.fixture(autouse=True)
def frozen_today(monkeypatch):
    """
    Pins "today" of the module under test to _TODAY.

    :param monkeypatch: pytest fixture used to replace the module's datetime
    """
    monkeypatch.setattr(download_price_module, "datetime", _FrozenDateTime)


def _stored(last_timestamp: datetime | None) -> FakeDb:
    """
    Builds a DB whose newest stored price is at *last_timestamp*.

    :param last_timestamp: Timestamp of the newest stored price, None for no prices
    :return: Fake DB answering newest_of_ohlcv accordingly
    """
    if last_timestamp is None:
        return FakeDb(newest_of_ohlcv=pd.DataFrame(columns=["timestamp"]))
    return FakeDb(newest_of_ohlcv=pd.DataFrame({"timestamp": [pd.Timestamp(last_timestamp)]}))

def _downloader(db: FakeDb, time_frame: TimeFrame) -> DownloadPriceData:
    return DownloadPriceData(db, "TOKEN", time_frame, SymbolStatus.ACTIVE)


# --- daily ---------------------------------------------------------------------------------

def test_a_new_symbol_s_daily_history_is_requested_in_full_and_stored(routed_api):
    db = _stored(None)
    assert _downloader(db, TimeFrame.DAILY).run(_SYMBOL) is True
    assert "from" not in routed_api.params("/eod/")[0]
    df, symbol_code, exchange_code, time_frame, symbol_status = db.insert.called("ohlcv")[0]
    assert (len(df), symbol_code, exchange_code, time_frame, symbol_status) == (
        3, "AAPL", "NASDAQ", TimeFrame.DAILY, SymbolStatus.ACTIVE)

def test_a_stored_symbol_is_only_requested_from_the_day_after_its_newest_price(routed_api):
    _downloader(_stored(datetime(2024, 3, 5)), TimeFrame.DAILY).run(_SYMBOL)
    assert routed_api.params("/eod/")[0]["from"] == "2024-03-06"

def test_the_newest_price_is_looked_up_for_the_symbol_on_its_exchange(routed_api):
    db = _stored(None)
    _downloader(db, TimeFrame.DAILY).run(_SYMBOL)
    assert db.read.called("newest_of_ohlcv") == [({"NASDAQ": ["AAPL"]}, TimeFrame.DAILY)]

def test_no_prices_are_logged_and_nothing_is_stored(routed_api, caplog):
    routed_api.override("/eod/", [])
    db = _stored(None)
    with caplog.at_level("INFO", logger=download_price_module.__name__):
        assert _downloader(db, TimeFrame.DAILY).run(_SYMBOL) is False
    assert db.insert.calls == []
    assert caplog.records[-1].getMessage() == "No data exists for symbol AAPL (NASDAQ, DAILY, ACTIVE)"

def test_a_symbol_whose_prices_are_all_from_before_1970_is_not_stored(routed_api):
    rows = load_payload("eod")
    for row in rows:
        row["date"] = "1969-12-31"
    routed_api.override("/eod/", rows)
    db = _stored(None)
    assert _downloader(db, TimeFrame.DAILY).run(_SYMBOL) is False
    assert db.insert.calls == []


# --- minute --------------------------------------------------------------------------------

def test_minute_prices_are_requested_from_one_minute_after_the_newest_one(routed_api):
    _downloader(_stored(datetime(2025, 9, 20, 15, 59)), TimeFrame.MINUTE).run(_SYMBOL)
    params = routed_api.params("/intraday/")
    assert params[0]["from"] == str(int(datetime(2025, 9, 20, 16, 0).timestamp()))
    assert params[-1]["to"] == str(int(datetime(2025, 9, 25).timestamp()))

def test_the_minute_chunks_are_merged_into_one_frame_with_a_fresh_index(routed_api):
    db = _stored(None)
    assert _downloader(db, TimeFrame.MINUTE).run(_SYMBOL) is True
    df = db.insert.called("ohlcv")[0][0]
    num_of_requests = len(routed_api.urls("/intraday/"))
    assert len(df) == 3 * num_of_requests
    assert df.index.tolist() == list(range(len(df)))

def test_minute_prices_that_are_already_up_to_date_are_not_requested(routed_api):
    # This used to end in pd.concat([]) raising ValueError, which aborted the whole run
    db = _stored(datetime(2025, 9, 24, 23, 59))
    assert _downloader(db, TimeFrame.MINUTE).run(_SYMBOL) is False
    assert routed_api.requests == [] and db.insert.calls == []


# --- scalability: the minute history is split into as few requests as the API allows -------

def test_the_whole_minute_history_is_split_into_contiguous_chunks_of_at_most_120_days():
    periods = DownloadPriceData._get_time_periods_for_minute_data_requests()
    days = (_TODAY.date() - date(2005, 1, 1)).days
    assert len(periods) == math.ceil(days / 120)
    assert periods[0][0] == datetime(2005, 1, 1)
    assert periods[-1][1] == datetime(2025, 9, 25)
    assert all(end - start <= timedelta(days=120) for start, end in periods)
    # Each chunk starts where the previous one ended: no gap, no overlap
    assert all(previous[1] == current[0] for previous, current in zip(periods, periods[1:]))

def test_a_recent_start_needs_a_single_chunk():
    assert DownloadPriceData._get_time_periods_for_minute_data_requests(datetime(2025, 9, 1)) == [
        (datetime(2025, 9, 1), datetime(2025, 9, 25))]

@pytest.mark.parametrize("start", [datetime(2025, 9, 25), datetime(2025, 9, 25, 12, 0)])
def test_a_start_of_today_needs_no_chunk(start):
    assert DownloadPriceData._get_time_periods_for_minute_data_requests(start) == []
