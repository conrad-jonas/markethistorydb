"""Integration tests for fetch/fetcher.py: whole runs against a fake eodhd.com and a real QuestDB"""

from markethistorydb.fetch.fetcher import Fetcher
from markethistorydb.utils import SymbolStatus, TimeFrame
from tests.integration.conftest import count, settle

# Tables a daily run writes to
_TABLES = ("exchange", "symbol", "sector", "daily_ohlcv", "earnings_quarterly", "balance_sheet_annually")


def _run(db, config) -> Fetcher:
    fetcher = Fetcher(db, config.eodhd_api_token, TimeFrame.DAILY, SymbolStatus.ACTIVE, "USA Stocks")
    fetcher.run()
    settle(db, *_TABLES)
    return fetcher


def test_a_daily_run_stores_every_symbol_of_the_exchange(fresh_db, questdb_config, routed_api, no_disk_check):
    fetcher = _run(fresh_db, questdb_config)
    # AAPL (NASDAQ), IBM (NYSE) and SPY (NYSE ARCA); the sample's OTC symbol is filtered out
    assert (fetcher.num_of_requested_symbols, fetcher.num_of_downloaded_symbols, fetcher.failed_symbols) == (
        3, 3, [])
    assert {table: count(fresh_db, table) for table in _TABLES} == {
        "exchange": 1, "symbol": 3, "daily_ohlcv": 9,
        # Fundamentals exist for the NASDAQ and NYSE symbols only
        "sector": 2, "earnings_quarterly": 4, "balance_sheet_annually": 4}

def test_a_second_run_asks_only_for_the_new_days_and_duplicates_nothing(fresh_db, questdb_config, routed_api,
                                                                        no_disk_check):
    _run(fresh_db, questdb_config)
    counts = {table: count(fresh_db, table) for table in _TABLES}
    routed_api.requests.clear()
    _run(fresh_db, questdb_config)
    # The sample's newest day is 2026-09-03, so the next run starts the day after
    assert {params.get("from") for params in routed_api.params("/eod/")} == {"2026-09-04"}
    assert {table: count(fresh_db, table) for table in _TABLES} == counts
