"""Integration tests for db/io/delete.py: a symbol's records go, everything else stays"""

from datetime import datetime
import pandas as pd
import pytest

from markethistorydb.db import tables
from markethistorydb.utils import SymbolStatus, TimeFrame
from tests.integration.conftest import count, select, settle, wait_for_count

# The record to delete, and its neighbours that share its symbol or its exchange
_TARGET = ("AAPL", "NASDAQ")
_NEIGHBOURS = [("MSFT", "NASDAQ"), ("AAPL", "LSE")]


def _delete(db, table):
    db.delete.symbol_from_table(*_TARGET, table.NAME, table.TIMESTAMP_COLUMN, list(table.UNIQUE_KEY_COLUMNS))
    settle(db, table.NAME)

def _remaining(db, table_name: str) -> list[tuple]:
    return sorted(select(db, "SELECT DISTINCT symbol_code, exchange_code FROM {0}".format(table_name)))


@pytest.mark.parametrize("time_frame, table", [
    (TimeFrame.DAILY, tables.DailyOhlcv), (TimeFrame.MINUTE, tables.MinuteOhlcv)])
def test_a_price_table_loses_the_symbol_only_and_keeps_its_indexes_and_dedup(fresh_db, time_frame, table):
    for symbol_code, exchange_code in [_TARGET] + _NEIGHBOURS:
        df = pd.DataFrame({"exchange_code": exchange_code, "symbol_code": symbol_code, "open": 1.0,
                           "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1,
                           "timestamp": [datetime(2024, 1, 2), datetime(2024, 1, 3)]})
        if time_frame == TimeFrame.DAILY:
            df["adjusted_close"] = 1.0
        else:
            df["gmt_offset"] = 0
        db_insert = fresh_db.insert.ohlcv
        db_insert(df, symbol_code, exchange_code, time_frame, SymbolStatus.ACTIVE)
    wait_for_count(fresh_db, table.NAME, 6)

    _delete(fresh_db, table)
    assert _remaining(fresh_db, table.NAME) == sorted(_NEIGHBOURS)
    indexed = {name for name, is_indexed in select(
        fresh_db, 'SELECT "column", indexed FROM table_columns(%s)', table.NAME) if is_indexed}
    assert indexed == {"exchange_code", "symbol_code"}
    assert select(fresh_db, "SELECT dedup, walEnabled FROM tables() WHERE table_name = %s", table.NAME) == [
        (True, True)]

@pytest.mark.parametrize("table", [tables.Symbol, tables.Sector])
def test_a_symbol_table_loses_the_symbol_only(fresh_db, table):
    for symbol_code, exchange_code in [_TARGET] + _NEIGHBOURS:
        record = pd.Series({column: "x" for column in table.ALL_COLUMNS})
        record["symbol_code"], record["exchange_code"] = symbol_code, exchange_code
        getattr(fresh_db.insert, table.NAME)(record)
    # No wait: the copy must hold every row written so far, which a WAL table could still hold back
    _delete(fresh_db, table)
    assert _remaining(fresh_db, table.NAME) == sorted(_NEIGHBOURS)
    # The swapped-in copy is non-WAL like the original, so the next insert through SQL still works
    assert select(fresh_db, "SELECT designatedTimestamp, walEnabled FROM tables() WHERE table_name = %s",
                  table.NAME) == [(None, False)]
    record["symbol_code"], record["exchange_code"] = _TARGET
    getattr(fresh_db.insert, table.NAME)(record)
    assert _remaining(fresh_db, table.NAME) == sorted([_TARGET] + _NEIGHBOURS)

def test_a_fundamental_table_loses_the_symbol_only(fresh_db):
    table = tables.EarningsAnnually
    df = pd.DataFrame({"symbol_code": [code for code, _ in [_TARGET] + _NEIGHBOURS],
                       "exchange_code": [exchange for _, exchange in [_TARGET] + _NEIGHBOURS],
                       "date": datetime(2024, 12, 31), "eps_actual": 1.0})
    fresh_db.insert.table(df, table.NAME, table.TIMESTAMP_COLUMN)
    wait_for_count(fresh_db, table.NAME, 3)
    _delete(fresh_db, table)
    assert _remaining(fresh_db, table.NAME) == sorted(_NEIGHBOURS)
    assert count(fresh_db, "tables() WHERE table_name = 'earnings_annually_copy'") == 0
