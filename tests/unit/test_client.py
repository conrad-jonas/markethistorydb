"""Tests for client.py: construction, setup and the fetch passes"""

import logging
import pytest

import markethistorydb.client as client_module
from markethistorydb.client import Client
from markethistorydb.config import Config
from markethistorydb.db import Database, Read
from markethistorydb.errors import ConfigError, DataLimitError
from markethistorydb.fetch.utils import FailedSymbol
from markethistorydb.utils import SymbolStatus, TimeFrame


def _config() -> Config:
    return Config(eodhd_api_token="token", questdb_password="secret")


class FakeFetcher:
    """Stands in for Fetcher; every instance records its pass and reports fixed numbers"""

    passes: list[tuple] = []
    error: BaseException | None = None
    failed_symbols_per_pass: list[FailedSymbol] = []

    def __init__(self, db, api_token, time_frame, symbol_status, exchange, should_stop):
        self.args = (db, api_token, time_frame, symbol_status, exchange, should_stop)
        self.num_of_requested_symbols = 10
        self.failed_symbols = list(FakeFetcher.failed_symbols_per_pass)

    def run(self):
        FakeFetcher.passes.append(self.args)
        if FakeFetcher.error is not None:
            raise FakeFetcher.error


@pytest.fixture
def fetcher(monkeypatch) -> type[FakeFetcher]:
    """
    Replaces the Fetcher the client builds for each pass.

    :param monkeypatch: pytest fixture used to replace client.Fetcher
    :return: The FakeFetcher class, whose passes list the passes that ran
    """
    FakeFetcher.passes, FakeFetcher.error = [], None
    FakeFetcher.failed_symbols_per_pass = [FailedSymbol("SYM", "NASDAQ", "RequestError")]
    monkeypatch.setattr(client_module, "Fetcher", FakeFetcher)
    return FakeFetcher


def test_an_explicit_config_is_used_as_is_and_the_environment_is_not_read(monkeypatch):
    monkeypatch.delenv("EODHD_API_TOKEN", raising=False)
    config = _config()
    client = Client(config)
    assert client.config is config
    assert isinstance(client._db, Database)
    # The public read interface is the database's own, not a copy
    assert isinstance(client.read, Read) and client.read is client._db.read

def test_without_a_config_the_environment_is_read(monkeypatch):
    monkeypatch.setenv("EODHD_API_TOKEN", "env-token")
    monkeypatch.setenv("QUESTDB_PASSWORD", "env-secret")
    assert Client().config.eodhd_api_token == "env-token"

def test_without_a_config_a_missing_variable_is_a_config_error(monkeypatch):
    monkeypatch.delenv("QUESTDB_PASSWORD", raising=False)
    monkeypatch.setenv("EODHD_API_TOKEN", "env-token")
    with pytest.raises(ConfigError):
        Client()

def test_setup_sets_up_the_db_the_config_points_to(monkeypatch):
    configs = []
    monkeypatch.setattr(client_module, "_setup", configs.append)
    client = Client(_config())
    client.setup()
    assert configs == [client.config]

def test_fetch_without_filters_runs_every_time_frame_and_status(fetcher):
    total = Client(_config()).fetch()
    assert [(args[2], args[3]) for args in fetcher.passes] == [
        (TimeFrame.DAILY, SymbolStatus.ACTIVE), (TimeFrame.DAILY, SymbolStatus.DELISTED),
        (TimeFrame.MINUTE, SymbolStatus.ACTIVE), (TimeFrame.MINUTE, SymbolStatus.DELISTED)]
    # The total adds up the requested symbols of every pass
    assert total == 40

@pytest.mark.parametrize("time_frame, symbol_status, expected_passes", [
    (TimeFrame.MINUTE, None, [(TimeFrame.MINUTE, SymbolStatus.ACTIVE),
                              (TimeFrame.MINUTE, SymbolStatus.DELISTED)]),
    (None, SymbolStatus.DELISTED, [(TimeFrame.DAILY, SymbolStatus.DELISTED),
                                   (TimeFrame.MINUTE, SymbolStatus.DELISTED)]),
    (TimeFrame.DAILY, SymbolStatus.ACTIVE, [(TimeFrame.DAILY, SymbolStatus.ACTIVE)]),
])
def test_fetch_runs_only_the_passes_the_filters_select(fetcher, time_frame, symbol_status,
                                                       expected_passes):
    Client(_config()).fetch(time_frame, symbol_status)
    assert [(args[2], args[3]) for args in fetcher.passes] == expected_passes

def test_fetch_hands_token_exchange_and_should_stop_to_every_pass(fetcher):
    client = Client(_config())

    def should_stop() -> bool:
        return False

    client.fetch(TimeFrame.DAILY, SymbolStatus.ACTIVE, "USA Stocks", should_stop)
    db, api_token, _, _, exchange, passed_should_stop = fetcher.passes[0]
    assert (db, api_token, exchange, passed_should_stop) == (
        client._db, "token", "USA Stocks", should_stop)

def test_fetch_warns_about_the_symbols_that_were_skipped(fetcher, caplog):
    with caplog.at_level(logging.INFO, logger=client_module.__name__):
        Client(_config()).fetch(TimeFrame.DAILY)
    warnings = [record.getMessage() for record in caplog.records if record.levelno == logging.WARNING]
    assert warnings == ["Total number of symbols that were skipped after an error: 2"]

def test_fetch_does_not_warn_when_nothing_was_skipped(fetcher, caplog):
    fetcher.failed_symbols_per_pass = []
    with caplog.at_level(logging.INFO, logger=client_module.__name__):
        Client(_config()).fetch(TimeFrame.DAILY)
    assert not [record for record in caplog.records if record.levelno >= logging.WARNING]

def test_an_account_error_ends_the_fetch_before_the_next_pass(fetcher):
    # A used up plan fails every later pass too, so none of them is attempted
    fetcher.error = DataLimitError("plan used up", 402)
    with pytest.raises(DataLimitError):
        Client(_config()).fetch()
    assert len(fetcher.passes) == 1
