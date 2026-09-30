"""Tests for db/io/read.py"""

from datetime import datetime
import pytest

from markethistorydb.db.io.read import Read
from markethistorydb.errors import QueryError
from markethistorydb.utils import SymbolStatus, TimeFrame
from tests.fakes import FakeQuery, RecordingQuery


# --- DB reads ------------------------------------------------------------------------------


def test_reading_a_missing_record_yields_an_empty_series_not_an_index_error():
    # Callers distinguish "not in table" from "in table" by Series.empty
    assert Read(FakeQuery([])).exchange("NASDAQ").empty

def test_reading_an_existing_record_yields_its_values():
    series = Read(FakeQuery([("NASDAQ", "NASDAQ Stock Exchange")])).exchange("NASDAQ")
    assert not series.empty
    assert series.iloc[0] == "NASDAQ"

def test_more_records_than_the_unique_key_allows_is_a_query_error():
    with pytest.raises(QueryError):
        Read(FakeQuery([("NASDAQ",), ("NASDAQ",)])).exchange("NASDAQ")

def test_reading_prices_for_no_symbols_yields_an_empty_frame():
    assert Read(FakeQuery([])).ohlcv({}, TimeFrame.DAILY).empty


def _daily_row(symbol_code: str, day: int) -> tuple:
    return (datetime(2024, 1, day), "NASDAQ", symbol_code, 1.0, 2.0, 0.5, 1.5, 1.4, 100)

def _minute_row(symbol_code: str, minute: int) -> tuple:
    return (datetime(2024, 1, 2, 9, minute), "NASDAQ", symbol_code, 1.0, 2.0, 0.5, 1.5, 100.0)


def test_a_symbol_is_looked_up_by_its_whole_unique_key():
    query = RecordingQuery([("AAPL", "NASDAQ", "DAILY", "ACTIVE", "Apple Inc")])
    series = Read(query).symbol("AAPL", "NASDAQ", TimeFrame.DAILY, SymbolStatus.ACTIVE)
    assert series.tolist() == ["AAPL", "NASDAQ", "DAILY", "ACTIVE", "Apple Inc"]
    assert query.statements[0][1] == ["AAPL", "NASDAQ", "DAILY", "ACTIVE"]

def test_a_sector_is_looked_up_by_symbol_and_exchange():
    query = RecordingQuery([("AAPL", "Technology")])
    assert Read(query).sector("AAPL", "NASDAQ").tolist() == ["AAPL", "Technology"]
    assert query.statements[0][1] == ["AAPL", "NASDAQ"]

@pytest.mark.parametrize("lookup", [
    lambda read: read.symbol("AAPL", "NASDAQ", TimeFrame.DAILY, SymbolStatus.ACTIVE),
    lambda read: read.sector("AAPL", "NASDAQ"),
])
def test_a_duplicated_unique_key_is_a_query_error_naming_the_record(lookup):
    with pytest.raises(QueryError) as excinfo:
        lookup(Read(RecordingQuery([("AAPL",), ("AAPL",)])))
    assert "AAPL (NASDAQ" in str(excinfo.value)

def test_daily_prices_are_indexed_by_symbol_and_timestamp():
    query = RecordingQuery([_daily_row("AAPL", 2), _daily_row("AAPL", 3)])
    df = Read(query).ohlcv({"NASDAQ": ["AAPL"]}, TimeFrame.DAILY, datetime(2024, 1, 1), datetime(2024, 1, 31))
    assert df.index.names == ["symbol_code", "timestamp"]
    assert list(df.columns) == ["exchange_code", "open", "high", "low", "close", "adjusted_close", "volume"]
    assert "FROM daily_ohlcv" in query.texts[0]
    assert query.statements[0][1] == ["NASDAQ", datetime(2024, 1, 1), datetime(2024, 1, 31)]

def test_minute_prices_are_read_from_the_minute_table_with_its_columns():
    query = RecordingQuery([_minute_row("AAPL", 30)])
    df = Read(query).ohlcv({"NASDAQ": ["AAPL"]}, TimeFrame.MINUTE)
    assert "FROM minute_ohlcv" in query.texts[0]
    assert list(df.columns) == ["exchange_code", "open", "high", "low", "close", "volume"]
    # Without bounds, the whole history is selected
    assert query.statements[0][1][1:] == [datetime.min, datetime.max]

def test_prices_of_several_exchanges_are_concatenated():
    query = RecordingQuery([_daily_row("AAPL", 2)], [_daily_row("IBM", 2)])
    df = Read(query).ohlcv({"NASDAQ": ["AAPL"], "NYSE": ["IBM"]}, TimeFrame.DAILY)
    assert sorted(df.index.get_level_values("symbol_code")) == ["AAPL", "IBM"]
    assert [params[0] for _, params in query.statements] == ["NASDAQ", "NYSE"]

@pytest.mark.parametrize("time_frame, table_name", [
    (TimeFrame.DAILY, "daily_ohlcv"), (TimeFrame.MINUTE, "minute_ohlcv")])
def test_the_newest_prices_keep_symbol_and_timestamp_as_columns_too(time_frame, table_name):
    row = _daily_row("AAPL", 3) if time_frame == TimeFrame.DAILY else _minute_row("AAPL", 3)
    query = RecordingQuery([row])
    df = Read(query).newest_of_ohlcv({"NASDAQ": ["AAPL"]}, time_frame)
    # WritePriceData reads the timestamp column, not the index
    assert df.iloc[0]["timestamp"] == row[0]
    assert "FROM {0}".format(table_name) in query.texts[0]
    # One record per symbol, not only the newest of all of them
    assert "LATEST ON timestamp PARTITION BY symbol_code" in query.texts[0]

def test_the_newest_prices_for_no_symbols_are_an_empty_frame():
    assert Read(RecordingQuery()).newest_of_ohlcv({}, TimeFrame.DAILY).empty


# --- scalability ---------------------------------------------------------------------------

def test_prices_are_read_with_one_query_per_exchange_however_many_symbols():
    symbol_codes_per_exchange = {exchange_code: ["SYM{0}".format(i) for i in range(1000)]
                                 for exchange_code in ("NASDAQ", "NYSE", "LSE")}
    query = RecordingQuery([])
    Read(query).ohlcv(symbol_codes_per_exchange, TimeFrame.DAILY)
    assert len(query.statements) == 3
    assert all(text.count("'SYM") == 1000 for text in query.texts)


# --- security ------------------------------------------------------------------------------

def test_a_symbol_code_cannot_break_out_of_its_literal():
    malicious = "A'); DROP TABLE daily_ohlcv;--"
    query = RecordingQuery([])
    Read(query).ohlcv({"NASDAQ": ["AAPL", malicious]}, TimeFrame.DAILY)
    # The quote is doubled, so the whole code stays one string literal
    assert "IN ('AAPL', 'A''); DROP TABLE daily_ohlcv;--')" in query.texts[0]

def test_lookups_bind_their_values_as_params():
    query = RecordingQuery([])
    Read(query).exchange("US' OR '1'='1")
    text, params = query.statements[0]
    assert params == ["US' OR '1'='1"]
    assert "OR '1'" not in text
