"""Tests for fetch/fetcher.py: per-symbol isolation, abort conditions and the run summary"""

from types import SimpleNamespace
import logging
import pandas as pd
import pytest
import requests

import markethistorydb.fetch.fetcher as fetcher_module
from markethistorydb.db.tables import Symbol
from markethistorydb.errors import (AccessRightsError, CompatibilityError, DataLimitError, FetchError,
                                    InsertError, MarketHistoryDbError, RequestError, StorageError,
                                    UnauthorizedError, UserInterruptError)
from markethistorydb.fetch.fetcher import Fetcher
from markethistorydb.fetch.utils import FailedSymbol
from markethistorydb.utils import SymbolStatus, TimeFrame
from tests.fakes import FakeDb, FakeResponse


# --- per-symbol isolation ------------------------------------------------------------------

def _symbols(count: int) -> pd.DataFrame:
    return pd.DataFrame({
        Symbol.Columns.SYMBOL_CODE: ["SYM{0}".format(i) for i in range(count)],
        Symbol.Columns.EXCHANGE_CODE: ["NASDAQ"] * count,
    })

def _fetcher(monkeypatch) -> Fetcher:
    """
    Builds a Fetcher whose download handlers are replaced by the test.

    :param monkeypatch: pytest fixture used to disable the storage space check
    :return: Fetcher running against no DB
    """
    monkeypatch.setattr(Fetcher, "_check_storage_space", staticmethod(lambda: None))
    return Fetcher(db=None, api_token="token", time_frame=TimeFrame.DAILY,
                   symbol_status=SymbolStatus.ACTIVE)


def test_a_symbol_that_fails_is_recorded_and_the_run_carries_on(monkeypatch):
    fetcher = _fetcher(monkeypatch)
    downloaded = []

    def download(series_symbol):
        symbol_code = series_symbol[Symbol.Columns.SYMBOL_CODE]
        if symbol_code == "SYM1":
            raise CompatibilityError("unexpected shape")
        downloaded.append(symbol_code)

    monkeypatch.setattr(fetcher, "_download_historical_data", download)
    fetcher._download_all_symbols(_symbols(3))

    assert downloaded == ["SYM0", "SYM2"]
    assert fetcher.failed_symbols == [FailedSymbol("SYM1", "NASDAQ", "CompatibilityError")]

def test_a_failing_insert_only_costs_its_own_symbol(monkeypatch):
    fetcher = _fetcher(monkeypatch)

    def download(series_symbol):
        if series_symbol[Symbol.Columns.SYMBOL_CODE] == "SYM0":
            raise InsertError("ingress gave up")

    monkeypatch.setattr(fetcher, "_download_historical_data", download)
    fetcher._download_all_symbols(_symbols(2))
    assert len(fetcher.failed_symbols) == 1

@pytest.mark.parametrize("error", [RequestError("gave up"), InsertError("ingress gave up")])
def test_enough_failures_in_a_row_abort_the_run(monkeypatch, error):
    from markethistorydb.fetch.fetcher import _MAX_CONSECUTIVE_SYMBOL_FAILURES

    fetcher = _fetcher(monkeypatch)
    monkeypatch.setattr(fetcher, "_download_historical_data",
                        lambda series_symbol: (_ for _ in ()).throw(error))

    with pytest.raises(FetchError) as excinfo:
        fetcher._download_all_symbols(_symbols(_MAX_CONSECUTIVE_SYMBOL_FAILURES + 5))
    assert "in a row" in str(excinfo.value)
    assert excinfo.value.__cause__ is error
    # Stopped at the limit instead of working through the rest of the list
    assert len(fetcher.failed_symbols) == _MAX_CONSECUTIVE_SYMBOL_FAILURES

def test_the_failure_streak_resets_after_a_symbol_succeeds(monkeypatch):
    from markethistorydb.fetch.fetcher import _MAX_CONSECUTIVE_SYMBOL_FAILURES

    fetcher = _fetcher(monkeypatch)
    # Fails every symbol but one, so the streak never reaches the limit
    def download(series_symbol):
        index = int(series_symbol[Symbol.Columns.SYMBOL_CODE].removeprefix("SYM"))
        if index != _MAX_CONSECUTIVE_SYMBOL_FAILURES - 1:
            raise RequestError("gave up")

    monkeypatch.setattr(fetcher, "_download_historical_data", download)
    fetcher._download_all_symbols(_symbols(_MAX_CONSECUTIVE_SYMBOL_FAILURES + 1))
    assert len(fetcher.failed_symbols) == _MAX_CONSECUTIVE_SYMBOL_FAILURES

def test_a_user_interrupt_is_never_treated_as_a_symbol_failure(monkeypatch):
    fetcher = _fetcher(monkeypatch)
    monkeypatch.setattr(fetcher, "_download_historical_data",
                        lambda series_symbol: (_ for _ in ()).throw(UserInterruptError("stopped")))

    with pytest.raises(UserInterruptError):
        fetcher._download_all_symbols(_symbols(3))
    assert fetcher.failed_symbols == []

def test_running_out_of_disk_space_ends_the_run(monkeypatch):
    fetcher = _fetcher(monkeypatch)
    monkeypatch.setattr(fetcher, "_download_historical_data",
                        lambda series_symbol: (_ for _ in ()).throw(StorageError("disk full")))

    with pytest.raises(StorageError):
        fetcher._download_all_symbols(_symbols(3))

def _free_disk_space_in_gb(monkeypatch, free_in_gb: int):
    """
    Makes the fetcher see *free_in_gb* of free disk space.

    :param monkeypatch: pytest fixture used to replace the fetcher's shutil
    :param free_in_gb: Free space disk_usage() reports, in GB
    """
    usage = SimpleNamespace(free=free_in_gb * fetcher_module._BYTES_PER_GB)
    monkeypatch.setattr(fetcher_module, "shutil", SimpleNamespace(disk_usage=lambda path: usage))

def test_less_free_disk_space_than_the_minimum_is_a_storage_error(monkeypatch):
    _free_disk_space_in_gb(monkeypatch, fetcher_module._MIN_FREE_SPACE_IN_GB - 1)
    with pytest.raises(StorageError):
        Fetcher._check_storage_space()

def test_exactly_the_minimum_free_disk_space_is_enough(monkeypatch):
    _free_disk_space_in_gb(monkeypatch, fetcher_module._MIN_FREE_SPACE_IN_GB)
    Fetcher._check_storage_space()

@pytest.mark.parametrize("error", [
    DataLimitError("plan used up", 402),
    UnauthorizedError("wrong token", 401),
    AccessRightsError("not in your plan", 403),
])
def test_an_account_level_error_ends_the_run_at_the_first_symbol(monkeypatch, error):
    # Every remaining symbol would fail the same way, so the streak counter must not be waited out
    from markethistorydb.fetch.fetcher import _MAX_CONSECUTIVE_SYMBOL_FAILURES

    fetcher = _fetcher(monkeypatch)
    attempted: list[str] = []

    def download(series_symbol):
        attempted.append(series_symbol[Symbol.Columns.SYMBOL_CODE])
        raise error

    monkeypatch.setattr(fetcher, "_download_historical_data", download)
    with pytest.raises(type(error)):
        fetcher._download_all_symbols(_symbols(_MAX_CONSECUTIVE_SYMBOL_FAILURES + 5))
    assert len(attempted) == 1

def test_the_symbol_the_run_ends_on_is_recorded_as_a_failure(monkeypatch):
    # _log_summary subtracts failed_symbols from the requested count, so the aborting symbol
    # must be in there or it reads as downloaded
    fetcher = _fetcher(monkeypatch)
    monkeypatch.setattr(fetcher, "_download_historical_data",
                        lambda series_symbol: (_ for _ in ()).throw(DataLimitError("used up", 402)))

    with pytest.raises(DataLimitError):
        fetcher._download_all_symbols(_symbols(3))
    assert fetcher.failed_symbols == [FailedSymbol("SYM0", "NASDAQ", "DataLimitError")]


# --- run() and its summary -----------------------------------------------------------------

def _run_with(monkeypatch, symbol_outcomes: dict[str, BaseException | None],
              target_exchange_name: str | None = None) -> Fetcher:
    """
    Runs a Fetcher whose download handlers are fakes, each symbol failing or not as told.

    :param monkeypatch: pytest fixture used to disable the storage space check
    :param symbol_outcomes: Error each symbol's download raises, None for a success; in order
    :param target_exchange_name: Exchange the run is restricted to, if any
    :return: The Fetcher after its run, whether that ended in an error or not
    """
    monkeypatch.setattr(Fetcher, "_check_storage_space", staticmethod(lambda: None))
    fetcher = Fetcher(db=None, api_token="token", time_frame=TimeFrame.DAILY,
                      symbol_status=SymbolStatus.ACTIVE, target_exchange_name=target_exchange_name)
    df_symbols = pd.DataFrame({Symbol.Columns.SYMBOL_CODE: list(symbol_outcomes),
                               Symbol.Columns.EXCHANGE_CODE: ["NASDAQ"] * len(symbol_outcomes)})
    monkeypatch.setattr(fetcher._downloadExchangeData, "run", lambda: pd.Series(["US", "LSE"]))
    monkeypatch.setattr(fetcher._downloadSymbolData, "run", lambda exchange_codes: df_symbols)

    def download_price(series_symbol):
        error = symbol_outcomes[series_symbol[Symbol.Columns.SYMBOL_CODE]]
        if error is not None:
            raise error

    monkeypatch.setattr(fetcher._downloadPriceData, "run", download_price)
    monkeypatch.setattr(fetcher._downloadFundamentalData, "run", lambda series_symbol: True)
    try:
        fetcher.run()
    except MarketHistoryDbError:
        # Some runs are meant to end early; the tests look at what the run left behind
        pass
    return fetcher

def _info_lines(caplog) -> list[str]:
    return [record.getMessage() for record in caplog.records
            if record.name == fetcher_module.__name__ and record.levelno == logging.INFO]


def test_a_run_counts_the_requested_downloaded_and_failed_symbols(monkeypatch, caplog):
    with caplog.at_level(logging.INFO, logger=fetcher_module.__name__):
        fetcher = _run_with(monkeypatch, {"A": None, "B": RequestError("gave up"), "C": None})
    assert (fetcher.num_of_requested_symbols, fetcher.num_of_downloaded_symbols) == (3, 2)
    assert "Number of exchanges: 2, Number of requested symbols: 3" in _info_lines(caplog)
    assert "Downloaded 2 of 3 symbols, 1 failed" in _info_lines(caplog)
    assert "  failed: B (NASDAQ) - RequestError" in _info_lines(caplog)

def test_a_run_restricted_to_one_exchange_reports_one_exchange(monkeypatch, caplog):
    with caplog.at_level(logging.INFO, logger=fetcher_module.__name__):
        _run_with(monkeypatch, {"A": None}, target_exchange_name="USA Stocks")
    assert "Number of exchanges: 1, Number of requested symbols: 1" in _info_lines(caplog)

def test_the_summary_is_logged_even_when_the_run_ends_early(monkeypatch, caplog):
    with caplog.at_level(logging.INFO, logger=fetcher_module.__name__):
        _run_with(monkeypatch, {"A": None, "B": StorageError("disk full"), "C": None, "D": None})
    # B ended the run without being recorded, so it counts as not attempted with C and D
    assert "Downloaded 1 of 4 symbols, 0 failed, 3 not attempted" in _info_lines(caplog)

def test_should_stop_ends_the_run_before_the_next_symbol(monkeypatch):
    stop_requests = iter([False, True])
    monkeypatch.setattr(Fetcher, "_check_storage_space", staticmethod(lambda: None))
    fetcher = Fetcher(db=None, api_token="token", time_frame=TimeFrame.DAILY,
                      symbol_status=SymbolStatus.ACTIVE, should_stop=lambda: next(stop_requests))
    downloaded = []
    monkeypatch.setattr(fetcher._downloadPriceData, "run",
                        lambda series_symbol: downloaded.append(series_symbol[Symbol.Columns.SYMBOL_CODE]))
    monkeypatch.setattr(fetcher._downloadFundamentalData, "run", lambda series_symbol: True)
    with pytest.raises(UserInterruptError):
        fetcher._download_all_symbols(_symbols(3))
    assert downloaded == ["SYM0"]

def test_the_disk_is_checked_before_every_symbol(monkeypatch):
    fetcher = Fetcher(db=None, api_token="token", time_frame=TimeFrame.DAILY,
                      symbol_status=SymbolStatus.ACTIVE)
    _free_disk_space_in_gb(monkeypatch, 0)
    monkeypatch.setattr(fetcher._downloadPriceData, "run", lambda series_symbol: pytest.fail("downloaded"))
    with pytest.raises(StorageError):
        fetcher._download_all_symbols(_symbols(1))


# --- scalability: a long run leaves a bounded record ---------------------------------------

def test_the_summary_names_at_most_ten_failures_however_many_there_were(monkeypatch, caplog):
    fetcher = _fetcher(monkeypatch)
    fetcher.num_of_requested_symbols = 10_000
    fetcher.failed_symbols = [FailedSymbol("SYM{0}".format(i), "NASDAQ", "RequestError")
                              for i in range(10_000)]
    with caplog.at_level(logging.INFO, logger=fetcher_module.__name__):
        fetcher._log_summary()
    lines = _info_lines(caplog)
    assert len(lines) == 1 + fetcher_module._NUM_OF_FAILURES_IN_SUMMARY + 1
    assert lines[-1] == "  ... and 9990 more"


# --- security: the token never reaches a log record ----------------------------------------

def test_no_log_record_of_a_run_with_retries_and_failures_holds_the_token(routed_api, slept, caplog):
    # The formatter masks the token too, but a library user attaches handlers of their own, so
    # the records themselves must already be clean
    token = "TOKEN-SECRET-123"
    leak = "Max retries exceeded with url: /api/eod/AAPL.US?api_token={0}&fmt=json".format(token)
    routed_api.override("/eod/AAPL.US", requests.exceptions.ConnectionError(leak))
    routed_api.override("/eod/IBM.US", FakeResponse(503, text="api_token={0}".format(token)))
    db = FakeDb(exchange=pd.Series(dtype=object), symbol=pd.Series(dtype=object),
                sector=pd.Series(dtype=object), newest_of_ohlcv=pd.DataFrame(columns=["timestamp"]))
    fetcher = Fetcher(db, token, TimeFrame.DAILY, SymbolStatus.ACTIVE, target_exchange_name="USA Stocks")
    fetcher._check_storage_space = lambda: None
    with caplog.at_level(logging.DEBUG):
        fetcher.run()
    assert len(fetcher.failed_symbols) == 2 and slept
    assert token not in caplog.text
    assert all(token not in str(record.args) for record in caplog.records)
