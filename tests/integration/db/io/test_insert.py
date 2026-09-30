"""
Integration tests for db/io/insert.py: ILP writes into the time series tables, SQL writes into
the lookup tables
"""

from datetime import datetime
import pandas as pd
import pytest

from markethistorydb.db import tables
from markethistorydb.errors import InsertError, SchemaMismatchError
from markethistorydb.utils import SymbolStatus, TimeFrame
from tests.integration.conftest import count, select, settle, wait_for_count


def _column_types(db, table_name: str) -> dict[str, str]:
    return dict(select(db, 'SELECT "column", type FROM table_columns(%s)', table_name))


@pytest.mark.parametrize("method, table", [
    ("exchange", tables.Exchange), ("symbol", tables.Symbol), ("sector", tables.Sector)])
def test_a_record_round_trips_without_changing_the_table_s_columns(fresh_db, method, table):
    types_before = _column_types(fresh_db, table.NAME)
    record = pd.Series({column: "{0}-value".format(column) for column in table.ALL_COLUMNS})
    record["exchange_url_code"] = "US"
    getattr(fresh_db.insert, method)(record)
    # No column was added (exchange_url_code) and none changed its type
    assert _column_types(fresh_db, table.NAME) == types_before
    stored = select(fresh_db, "SELECT {0} FROM {1}".format(", ".join(table.ALL_COLUMNS), table.NAME))
    assert list(stored[0]) == record.drop("exchange_url_code").tolist()

def test_a_missing_field_is_stored_as_null(fresh_db):
    fresh_db.insert.exchange(pd.Series({"name": "USA Stocks", "exchange_code": "US"}))
    assert select(fresh_db, "SELECT name, exchange_code, operating_mic FROM exchange") == [
        ("USA Stocks", "US", None)]

@pytest.mark.parametrize("table", [tables.Exchange, tables.Symbol, tables.Sector])
def test_the_ingress_cannot_write_a_lookup_table(fresh_db, slept, table):
    # Why Insert writes these tables through SQL: without a designated timestamp they are non-WAL,
    # and ILP over HTTP refuses non-WAL tables. The server rejects the records themselves, so
    # there is nothing to retry.
    df = pd.DataFrame({column: ["x"] for column in table.ALL_COLUMNS})
    df["timestamp"] = datetime(2024, 1, 2)
    with pytest.raises(InsertError) as excinfo:
        fresh_db.insert.table(df, table.NAME, "timestamp")
    assert "cannot insert in non-WAL table" in str(excinfo.value)
    assert slept == []
    assert count(fresh_db, table.NAME) == 0

def test_a_lookup_record_is_visible_to_the_very_next_read(fresh_db):
    # The Write* classes read right after writing to decide between insert and update. On a WAL
    # table a read can miss a write not yet applied; repeated so a single lucky read cannot pass.
    for i in range(25):
        symbol_code = "SYM{0}".format(i)
        fresh_db.insert.symbol(pd.Series({"symbol_code": symbol_code, "exchange_code": "US",
                                          "time_frame": "DAILY", "symbol_status": "ACTIVE"}))
        assert not fresh_db.read.symbol(symbol_code, "US", TimeFrame.DAILY, SymbolStatus.ACTIVE).empty, i
        fresh_db.insert.sector(pd.Series({"symbol_code": symbol_code, "exchange_code": "US"}))
        assert not fresh_db.read.sector(symbol_code, "US").empty, i

def test_minute_prices_round_trip(fresh_db):
    df = pd.DataFrame({"exchange_code": "NASDAQ", "symbol_code": "AAPL",
                       "open": 1.0, "high": 2.0, "low": 0.5, "close": [1.5, 1.6], "volume": 10.0,
                       "timestamp": [datetime(2024, 1, 2, 9, 30), datetime(2024, 1, 2, 9, 31)]})
    fresh_db.insert.ohlcv(df, "AAPL", "NASDAQ", TimeFrame.MINUTE, SymbolStatus.ACTIVE)
    wait_for_count(fresh_db, "minute_ohlcv", 2)
    assert _column_types(fresh_db, "minute_ohlcv") == {
        "timestamp": "TIMESTAMP", "exchange_code": "SYMBOL", "symbol_code": "SYMBOL",
        "open": "DOUBLE", "high": "DOUBLE", "low": "DOUBLE", "close": "DOUBLE", "volume": "DOUBLE"}

def test_prices_sent_twice_are_stored_once(fresh_db):
    # A run that is repeated after an abort re-sends what it already stored
    df = pd.DataFrame({"exchange_code": "NASDAQ", "symbol_code": "AAPL", "open": 1.0, "high": 2.0,
                       "low": 0.5, "close": [1.5, 1.6], "adjusted_close": 1.5, "volume": 100,
                       "timestamp": [datetime(2024, 1, 2), datetime(2024, 1, 3)]})
    for _ in range(2):
        fresh_db.insert.ohlcv(df, "AAPL", "NASDAQ", TimeFrame.DAILY, SymbolStatus.ACTIVE)
        settle(fresh_db, "daily_ohlcv")
    assert count(fresh_db, "daily_ohlcv") == 2


# --- scalability ---------------------------------------------------------------------------

def test_a_long_minute_history_is_written_in_one_batch(fresh_db):
    # 100 000 minutes, a little over two months of one symbol at the full 24 h a day
    num_of_minutes = 100_000
    df = pd.DataFrame({"exchange_code": "NASDAQ", "symbol_code": "AAPL", "open": 1.0,
                       "high": 2.0, "low": 0.5, "close": 1.5, "volume": 100.0,
                       "timestamp": pd.date_range("2024-01-01", periods=num_of_minutes, freq="min")})
    fresh_db.insert.ohlcv(df, "AAPL", "NASDAQ", TimeFrame.MINUTE, SymbolStatus.ACTIVE)
    wait_for_count(fresh_db, "minute_ohlcv", num_of_minutes)
    assert select(fresh_db, "SELECT min(timestamp), max(timestamp) FROM minute_ohlcv")[0] == (
        datetime(2024, 1, 1), df["timestamp"].iloc[-1].to_pydatetime())

def test_a_value_the_table_cannot_store_fails_at_once_instead_of_being_retried(fresh_db, slept):
    # QuestDB timestamps start in 1970; the request layer drops earlier days for this reason
    df = pd.DataFrame({"exchange_code": "NASDAQ", "symbol_code": "AAPL", "open": 1.0, "high": 2.0,
                       "low": 0.5, "close": 1.5, "adjusted_close": 1.5, "volume": 100,
                       "timestamp": [datetime(1969, 12, 31)]})
    with pytest.raises(InsertError):
        fresh_db.insert.ohlcv(df, "AAPL", "NASDAQ", TimeFrame.DAILY, SymbolStatus.ACTIVE)
    assert slept == []


# --- records that do not fit the table: most likely the provider changed its payload -------

def _daily_prices(**overrides) -> pd.DataFrame:
    columns = {"exchange_code": "NASDAQ", "symbol_code": "AAPL", "open": 1.0, "high": 2.0, "low": 0.5,
               "close": 1.5, "adjusted_close": 1.5, "volume": 100, "timestamp": [datetime(2024, 1, 2)]}
    columns.update(overrides)
    return pd.DataFrame(columns)

def test_a_value_of_the_wrong_type_is_a_schema_mismatch_at_once(fresh_db, slept):
    types_before = _column_types(fresh_db, "daily_ohlcv")
    with pytest.raises(SchemaMismatchError) as excinfo:
        fresh_db.insert.ohlcv(_daily_prices(close="1.5"), "AAPL", "NASDAQ", TimeFrame.DAILY, SymbolStatus.ACTIVE)
    assert "column: close; cast error" in str(excinfo.value)
    assert slept == []
    assert _column_types(fresh_db, "daily_ohlcv") == types_before

def test_a_column_the_table_does_not_have_is_a_schema_mismatch_instead_of_a_new_column(fresh_db, slept):
    auto_create = select(fresh_db, "SELECT value FROM (SHOW PARAMETERS) "
                                   "WHERE property_path = 'line.auto.create.new.columns'")
    if auto_create != [("false",)]:
        pytest.skip("The test QuestDB creates new columns (line.auto.create.new.columns is not false)")
    types_before = _column_types(fresh_db, "daily_ohlcv")
    with pytest.raises(SchemaMismatchError) as excinfo:
        fresh_db.insert.ohlcv(_daily_prices(dividend=0.25), "AAPL", "NASDAQ", TimeFrame.DAILY, SymbolStatus.ACTIVE)
    assert "column: dividend does not exist" in str(excinfo.value)
    assert slept == []
    assert _column_types(fresh_db, "daily_ohlcv") == types_before
