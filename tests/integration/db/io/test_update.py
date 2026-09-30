"""Integration tests for db/io/update.py"""

import pandas as pd

from markethistorydb.db import tables
from markethistorydb.utils import SymbolStatus, TimeFrame
from tests.integration.conftest import select, wait_for_count, wait_until


def _record(table, **values) -> pd.Series:
    record = pd.Series({column: "{0}-value".format(column) for column in table.ALL_COLUMNS})
    for column, value in values.items():
        record[column] = value
    return record


def test_an_exchange_update_changes_only_that_exchange(fresh_db):
    fresh_db.insert.exchange(_record(tables.Exchange, exchange_code="US"))
    fresh_db.insert.exchange(_record(tables.Exchange, exchange_code="LSE"))
    wait_for_count(fresh_db, "exchange", 2)
    fresh_db.update.exchange(_record(tables.Exchange, exchange_code="US", name="Renamed"))
    names = wait_until(fresh_db, lambda: dict(select(fresh_db, "SELECT exchange_code, name FROM exchange")),
                       lambda rows: rows["US"] == "Renamed")
    assert names["LSE"] == "name-value"

def test_a_symbol_update_is_keyed_by_time_frame_and_status_too(fresh_db):
    for time_frame in ("DAILY", "MINUTE"):
        fresh_db.insert.symbol(_record(tables.Symbol, symbol_code="AAPL", exchange_code="NASDAQ",
                                       time_frame=time_frame, symbol_status="ACTIVE"))
    wait_for_count(fresh_db, "symbol", 2)
    fresh_db.update.symbol(_record(tables.Symbol, symbol_code="AAPL", exchange_code="NASDAQ",
                                   time_frame="MINUTE", symbol_status="ACTIVE", name="Apple Inc"))
    wait_until(fresh_db, lambda: fresh_db.read.symbol("AAPL", "NASDAQ", TimeFrame.MINUTE, SymbolStatus.ACTIVE),
               lambda series: series.iloc[4] == "Apple Inc")
    assert fresh_db.read.symbol("AAPL", "NASDAQ", TimeFrame.DAILY, SymbolStatus.ACTIVE).iloc[4] == "name-value"

def test_a_sector_update_takes_effect(fresh_db):
    # UPDATE ... FROM sector used to be rejected on the WAL table
    fresh_db.insert.sector(_record(tables.Sector, symbol_code="AAPL", exchange_code="NASDAQ"))
    wait_for_count(fresh_db, "sector", 1)
    fresh_db.update.sector(_record(tables.Sector, symbol_code="AAPL", exchange_code="NASDAQ",
                                   sector="Technology"))
    series = wait_until(fresh_db, lambda: fresh_db.read.sector("AAPL", "NASDAQ"),
                        lambda series: series.iloc[1] == "Technology")
    assert series.iloc[0] == "AAPL"
