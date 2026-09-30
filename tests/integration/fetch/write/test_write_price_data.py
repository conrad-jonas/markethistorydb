"""Integration tests for fetch/write/write_price_data.py"""

from datetime import datetime
import pandas as pd
import pytest

from markethistorydb.fetch.write import WritePriceData
from markethistorydb.utils import SymbolStatus, TimeFrame
from tests.integration.conftest import wait_for_count

_SYMBOL = pd.Series({"symbol_code": "AAPL", "exchange_code": "NASDAQ"})


# Timestamps as the provider sends them, and the newest of them as the DB stores it
@pytest.mark.parametrize("time_frame, table_name, extra_column, timestamps, newest", [
    (TimeFrame.DAILY, "daily_ohlcv", "adjusted_close", ["2024-01-02", "2024-01-03"], datetime(2024, 1, 3)),
    (TimeFrame.MINUTE, "minute_ohlcv", "gmt_offset", [1704187800, 1704297540], datetime(2024, 1, 3, 15, 59))])
def test_the_newest_stored_timestamp_is_read_back_after_an_insert(fresh_db, time_frame, table_name, extra_column,
                                                                  timestamps, newest):
    writer = WritePriceData(fresh_db, time_frame, SymbolStatus.ACTIVE)
    assert writer.get_last_datetime_of_price_data(_SYMBOL) is None
    df = pd.DataFrame({"exchange_code": "NASDAQ", "symbol_code": "AAPL", "open": 1.0, "high": 1.0,
                       "low": 1.0, "close": 1.0, "volume": 1, extra_column: 0, "timestamp": timestamps})
    writer.insert_price_data(df, _SYMBOL)
    wait_for_count(fresh_db, table_name, 2)
    assert writer.get_last_datetime_of_price_data(_SYMBOL) == newest
