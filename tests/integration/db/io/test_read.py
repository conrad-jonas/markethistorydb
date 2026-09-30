"""Integration tests for db/io/read.py"""

from datetime import datetime
import pandas as pd

from markethistorydb.utils import SymbolStatus, TimeFrame
from tests.integration.conftest import count, wait_for_count


def _daily_prices(symbol_code: str, exchange_code: str, days: list[int]) -> pd.DataFrame:
    return pd.DataFrame({
        "exchange_code": exchange_code, "symbol_code": symbol_code,
        "open": 1.0, "high": 2.0, "low": 0.5, "close": [float(day) for day in days],
        "adjusted_close": 1.0, "volume": 100,
        "timestamp": [datetime(2024, 1, day) for day in days]})

def _store_daily(db, symbol_code: str, exchange_code: str, days: list[int]):
    before = count(db, "daily_ohlcv")
    db.insert.ohlcv(_daily_prices(symbol_code, exchange_code, days), symbol_code, exchange_code,
                    TimeFrame.DAILY, SymbolStatus.ACTIVE)
    wait_for_count(db, "daily_ohlcv", before + len(days))


def test_records_that_are_not_stored_read_as_empty(fresh_db):
    assert fresh_db.read.exchange("US").empty
    assert fresh_db.read.symbol("AAPL", "NASDAQ", TimeFrame.DAILY, SymbolStatus.ACTIVE).empty
    assert fresh_db.read.sector("AAPL", "NASDAQ").empty
    assert fresh_db.read.ohlcv({"NASDAQ": ["AAPL"]}, TimeFrame.DAILY).empty
    assert fresh_db.read.newest_of_ohlcv({"NASDAQ": ["AAPL"]}, TimeFrame.MINUTE).empty

def test_the_date_bounds_are_inclusive(fresh_db):
    _store_daily(fresh_db, "AAPL", "NASDAQ", [2, 3, 4, 5])
    df = fresh_db.read.ohlcv({"NASDAQ": ["AAPL"]}, TimeFrame.DAILY, datetime(2024, 1, 3), datetime(2024, 1, 4))
    assert df["close"].tolist() == [3.0, 4.0]

def test_without_bounds_the_whole_history_is_read(fresh_db):
    # datetime.min and datetime.max are the defaults; QuestDB must accept them as bounds
    _store_daily(fresh_db, "AAPL", "NASDAQ", [2, 3])
    assert len(fresh_db.read.ohlcv({"NASDAQ": ["AAPL"]}, TimeFrame.DAILY)) == 2

def test_only_the_requested_symbols_of_each_exchange_are_read(fresh_db):
    _store_daily(fresh_db, "AAPL", "NASDAQ", [2])
    _store_daily(fresh_db, "MSFT", "NASDAQ", [2])
    _store_daily(fresh_db, "AAPL", "LSE", [2])
    _store_daily(fresh_db, "IBM", "NYSE", [2])
    df = fresh_db.read.ohlcv({"NASDAQ": ["AAPL"], "NYSE": ["IBM"]}, TimeFrame.DAILY)
    assert sorted(zip(df.index.get_level_values("symbol_code"), df["exchange_code"])) == [
        ("AAPL", "NASDAQ"), ("IBM", "NYSE")]

def test_the_newest_record_is_read_for_every_symbol(fresh_db):
    _store_daily(fresh_db, "AAPL", "NASDAQ", [2, 5])
    _store_daily(fresh_db, "MSFT", "NASDAQ", [3, 4])
    df = fresh_db.read.newest_of_ohlcv({"NASDAQ": ["AAPL", "MSFT"]}, TimeFrame.DAILY)
    newest = dict(zip(df["symbol_code"], df["timestamp"]))
    assert newest == {"AAPL": pd.Timestamp(2024, 1, 5), "MSFT": pd.Timestamp(2024, 1, 4)}


# --- security ------------------------------------------------------------------------------

def test_injection_attempts_in_lookups_find_nothing_and_change_nothing(fresh_db):
    _store_daily(fresh_db, "AAPL", "NASDAQ", [2])
    assert fresh_db.read.exchange("x' OR '1'='1").empty
    assert fresh_db.read.sector("AAPL' --", "NASDAQ").empty
    assert fresh_db.read.ohlcv({"NASDAQ": ["A'); DROP TABLE daily_ohlcv; --"]}, TimeFrame.DAILY).empty
    assert fresh_db.read.ohlcv({"NASDAQ' OR '1'='1": ["AAPL"]}, TimeFrame.DAILY).empty
    assert count(fresh_db, "daily_ohlcv") == 1
