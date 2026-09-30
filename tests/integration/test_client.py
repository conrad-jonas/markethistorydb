"""Integration tests for client.py: the public API end to end"""

from markethistorydb import Client, SymbolStatus, TimeFrame
from tests.integration.conftest import settle


def test_setup_fetch_and_read_through_the_public_api(questdb_config, routed_api, no_disk_check):
    client = Client(questdb_config)
    client.setup()
    assert client.fetch(TimeFrame.DAILY, SymbolStatus.ACTIVE, exchange="USA Stocks") == 3
    settle(client._db, "daily_ohlcv")
    df = client.read.ohlcv({"NASDAQ": ["AAPL"], "NYSE": ["IBM"]}, TimeFrame.DAILY)
    assert sorted(set(df.index.get_level_values("symbol_code"))) == ["AAPL", "IBM"]
    assert len(df) == 6
    newest = client.read.newest_of_ohlcv({"NASDAQ": ["AAPL"]}, TimeFrame.DAILY)
    assert newest["timestamp"].iloc[0] == df["close"].xs("AAPL").index.max()
