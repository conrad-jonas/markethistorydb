"""Tests for fetch/write/write_price_data.py"""

from datetime import datetime
import pandas as pd

import markethistorydb.fetch.utils as utils_module
from markethistorydb.fetch.write import WritePriceData
from markethistorydb.utils import SymbolStatus, TimeFrame
from tests.fakes import FakeDb

_SYMBOL = pd.Series({"symbol_code": "AAPL", "exchange_code": "NASDAQ"})


def test_the_newest_stored_timestamp_is_returned_as_a_datetime():
    db = FakeDb(newest_of_ohlcv=pd.DataFrame({"timestamp": [pd.Timestamp("2024-03-05 16:00")]}))
    last = WritePriceData(db, TimeFrame.MINUTE, SymbolStatus.ACTIVE).get_last_datetime_of_price_data(_SYMBOL)
    assert last == datetime(2024, 3, 5, 16, 0) and type(last) is datetime
    assert db.read.called("newest_of_ohlcv") == [({"NASDAQ": ["AAPL"]}, TimeFrame.MINUTE)]

def test_a_symbol_without_stored_prices_has_no_newest_timestamp():
    db = FakeDb(newest_of_ohlcv=pd.DataFrame(columns=["timestamp"]))
    assert WritePriceData(db, TimeFrame.DAILY, SymbolStatus.ACTIVE).get_last_datetime_of_price_data(_SYMBOL) is None

def _inserted(db: FakeDb) -> pd.DataFrame:
    """
    Returns the records of the one ohlcv insert *db* recorded.

    :param db: Fake DB the writer inserted into
    :return: Records passed to the insert
    """
    [(df, *_)] = db.insert.called("ohlcv")
    return df

def test_prices_are_inserted_under_the_writer_s_time_frame_and_status():
    db = FakeDb()
    df = pd.DataFrame({"timestamp": ["2024-03-05"], "close": [1.0]})
    assert WritePriceData(db, TimeFrame.DAILY, SymbolStatus.DELISTED).insert_price_data(df, _SYMBOL) is True
    [(_, *rest)] = db.insert.called("ohlcv")
    assert rest == ["AAPL", "NASDAQ", TimeFrame.DAILY, SymbolStatus.DELISTED]

def test_daily_dates_are_inserted_as_datetimes():
    db = FakeDb()
    df = pd.DataFrame({"timestamp": ["2024-03-05", "2024-03-06"], "close": [1.0, 2.0]})
    WritePriceData(db, TimeFrame.DAILY, SymbolStatus.ACTIVE).insert_price_data(df, _SYMBOL)
    assert _inserted(db)["timestamp"].tolist() == [pd.Timestamp("2024-03-05"), pd.Timestamp("2024-03-06")]
    # The caller's frame keeps the provider's values
    assert df["timestamp"].tolist() == ["2024-03-05", "2024-03-06"]

def test_minute_unix_seconds_are_inserted_as_datetimes():
    db = FakeDb()
    df = pd.DataFrame({"timestamp": [1758700800], "close": [1.0]})
    WritePriceData(db, TimeFrame.MINUTE, SymbolStatus.ACTIVE).insert_price_data(df, _SYMBOL)
    assert _inserted(db)["timestamp"].tolist() == [pd.Timestamp("2025-09-24 08:00")]

def test_prices_from_before_1970_are_dropped_with_a_warning(caplog):
    db = FakeDb()
    df = pd.DataFrame({"timestamp": ["1969-12-31", "1970-01-01", "2024-03-05"], "close": [1.0, 2.0, 3.0]})
    with caplog.at_level("WARNING", logger=utils_module.__name__):
        WritePriceData(db, TimeFrame.DAILY, SymbolStatus.ACTIVE).insert_price_data(df, _SYMBOL)
    assert _inserted(db)["close"].tolist() == [2.0, 3.0]
    assert [record.getMessage() for record in caplog.records] == [
        "Dropped 1 DAILY price records of AAPL.NASDAQ from before 1970, which QuestDB cannot store"]

def test_nothing_is_inserted_if_every_price_is_from_before_1970():
    db = FakeDb()
    df = pd.DataFrame({"timestamp": ["1969-12-30", "1969-12-31"], "close": [1.0, 2.0]})
    assert WritePriceData(db, TimeFrame.DAILY, SymbolStatus.ACTIVE).insert_price_data(df, _SYMBOL) is False
    assert db.insert.calls == []
