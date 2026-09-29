"""Tests for db/io/insert.py: what reaches the ingress or the SQL interface, and in how many batches"""

import numpy as np
import pandas as pd
import pytest
from questdb import QuestDBError, QuestDBErrorCode

import markethistorydb.db.io.error as error_module
import markethistorydb.db.io.insert as insert_module
from markethistorydb.config import Config
from markethistorydb.db import tables
from markethistorydb.db.io.insert import Insert
from markethistorydb.errors import InsertError, QueryError
from markethistorydb.utils import SymbolStatus, TimeFrame
from tests.fakes import RecordingQuery


class FakeSender:
    """Stands in for questdb's Sender, recording the batches written instead of sending them"""

    confs: list[str] = []
    batches: list[tuple[pd.DataFrame, str, object]] = []
    error: BaseException | None = None

    @classmethod
    def from_conf(cls, conf: str) -> "FakeSender":
        cls.confs.append(conf)
        return cls()

    def dataframe(self, df, table_name, at):
        if FakeSender.error is not None:
            raise FakeSender.error
        FakeSender.batches.append((df.copy(), table_name, at))

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


@pytest.fixture
def sender(monkeypatch) -> type[FakeSender]:
    """
    Replaces the ingress Sender.

    :param monkeypatch: pytest fixture used to replace insert.Sender
    :return: The FakeSender class, whose batches list what was written
    """
    FakeSender.confs, FakeSender.batches, FakeSender.error = [], [], None
    monkeypatch.setattr(insert_module, "Sender", FakeSender)
    return FakeSender


class FailingQuery:
    """Stands in for db.io.Query, failing every statement as Query does when the DB rejects it"""

    def execute(self, query, params):
        raise QueryError("Query failed: table does not exist")


def _insert(query=None) -> Insert:
    return Insert(Config(eodhd_api_token="token", questdb_password="secret"),
                  query if query is not None else RecordingQuery())


def test_a_frame_is_written_with_the_config_s_ingress_settings(sender):
    df = pd.DataFrame({"timestamp": pd.to_datetime(["2024-01-02"]), "close": [1.0]})
    _insert().table(df, "daily_ohlcv", "timestamp")
    assert sender.confs == [Config(eodhd_api_token="token", questdb_password="secret").http_conf]
    written, table_name, at = sender.batches[0]
    assert (table_name, at) == ("daily_ohlcv", "timestamp")
    assert written.equals(df)

@pytest.mark.parametrize("method, table", [
    ("exchange", tables.Exchange), ("symbol", tables.Symbol), ("sector", tables.Sector)])
def test_a_lookup_record_is_written_through_sql_not_the_ingress(sender, method, table):
    # ILP over HTTP rejects the non-WAL lookup tables ("cannot insert in non-WAL table")
    query = RecordingQuery()
    record = pd.Series({column: "{0}-value".format(column) for column in table.ALL_COLUMNS})
    getattr(_insert(query), method)(record)
    assert sender.batches == []
    assert query.texts == [
        "INSERT INTO {0} ({1}) VALUES ({2})".format(
            table.NAME, ", ".join(table.ALL_COLUMNS), ", ".join(["%s"] * len(table.ALL_COLUMNS)))]
    assert query.statements[0][1] == record.tolist()

def test_fields_the_table_does_not_define_are_not_written():
    # exchange_url_code only routes the requests; the table has no column for it
    query = RecordingQuery()
    record = pd.Series({column: "v" for column in tables.Symbol.ALL_COLUMNS})
    record["exchange_url_code"] = "US"
    _insert(query).symbol(record)
    assert query.statements[0][1] == ["v"] * len(tables.Symbol.ALL_COLUMNS)

def test_a_missing_field_or_value_is_written_as_null():
    # A value the payload leaves empty arrives as NaN; a field it lacks is absent from the record
    query = RecordingQuery()
    _insert(query).exchange(pd.Series({"name": "USA Stocks", "exchange_code": "US", "operating_mic": np.nan}))
    assert query.statements[0][1] == ["USA Stocks", "US"] + [None] * 5

def test_numpy_scalars_are_written_as_plain_python_values():
    # A record taken from a DataFrame row holds numpy scalars, which psycopg does not bind
    query = RecordingQuery()
    record = pd.Series({column: "v" for column in tables.Exchange.ALL_COLUMNS})
    record["name"] = np.str_("USA Stocks")
    _insert(query).exchange(record)
    assert type(query.statements[0][1][0]) is str

def test_a_rejected_lookup_record_is_reported_as_an_insert_error_without_retrying(slept):
    # The CLI maps InsertError to its own exit code, as it did while the tables were written via ILP
    with pytest.raises(InsertError) as excinfo:
        _insert(FailingQuery()).sector(pd.Series({"symbol_code": "AAPL", "exchange_code": "US"}))
    assert "sector" in str(excinfo.value)
    assert isinstance(excinfo.value.__cause__, QueryError)
    assert slept == []

@pytest.mark.parametrize("time_frame, table", [
    (TimeFrame.DAILY, tables.DailyOhlcv), (TimeFrame.MINUTE, tables.MinuteOhlcv)])
def test_prices_go_to_the_table_of_their_time_frame(sender, time_frame, table):
    df = pd.DataFrame({"timestamp": pd.to_datetime(["2024-01-02"]), "close": [1.0]})
    _insert().ohlcv(df, "AAPL", "NASDAQ", time_frame, SymbolStatus.ACTIVE)
    assert sender.batches[0][1:] == (table.NAME, table.TIMESTAMP_COLUMN)

def test_an_ingress_error_is_retried_then_reported_as_an_insert_error(sender, slept):
    sender.error = QuestDBError(QuestDBErrorCode.ServerFlushError, "server is down")
    with pytest.raises(InsertError) as excinfo:
        _insert().table(pd.DataFrame({"timestamp": pd.to_datetime(["2024-01-02"]), "close": [1.0]}),
                        "daily_ohlcv", "timestamp")
    assert len(sender.confs) == error_module._MAX_RETRIES_AFTER_DB_CONNECT_ERROR
    assert "Insert.table failed" in str(excinfo.value)


# --- scalability ---------------------------------------------------------------------------

def test_a_symbol_s_prices_are_written_in_one_batch_not_row_by_row(sender):
    df = pd.DataFrame({"timestamp": pd.date_range("2000-01-01", periods=10_000, freq="D"),
                       "close": 1.0})
    _insert().ohlcv(df, "AAPL", "NASDAQ", TimeFrame.DAILY, SymbolStatus.ACTIVE)
    assert len(sender.batches) == 1 and len(sender.batches[0][0]) == 10_000
