"""Fixtures shared by the unit and integration tests"""

# These modules still import the pre-refactor layout (db.price.tables, download_request, ...)
# and break collection for the whole session, so they stay out of it until they are ported.
# Porting them is the README's own ToDo item.
collect_ignore = [
    "test_db_access.py",
    "test_db_setup.py",
    "test_download.py",
    "test_download_request.py",
]

import logging
import pytest

import markethistorydb.fetch.eodhd.request_data as request_data_module
import markethistorydb.utils.backoff as backoff_module
from markethistorydb.errors import UserInterruptError
from tests.fakes import FakeClock, FakeRoutedApi, FakeScriptedApi


@pytest.fixture
def slept(monkeypatch) -> list[float]:
    """
    Skips the waits between retries and records how long each one would have been.

    :param monkeypatch: pytest fixture used to replace backoff._sleep
    :return: List the skipped waits are appended to, in seconds
    """
    waits: list[float] = []

    def fake_sleep(delay_in_secs, should_stop):
        if should_stop():
            raise UserInterruptError("User interrupted process while waiting to retry")
        waits.append(delay_in_secs)

    monkeypatch.setattr(backoff_module, "_sleep", fake_sleep)
    return waits


@pytest.fixture
def scripted_api(monkeypatch) -> FakeScriptedApi:
    """
    Puts a fake eodhd.com behind the request layer that answers with the responses the test
    queues, in order, whatever the URL. Suits tests of the request layer itself; see routed_api
    for tests that need a realistic payload per endpoint.

    :param monkeypatch: pytest fixture used to replace requests.get
    :return: The fake, counting the calls and taking the queued responses
    """
    fake_scripted_api = FakeScriptedApi()
    monkeypatch.setattr(request_data_module.requests, "get", fake_scripted_api.get)
    return fake_scripted_api


@pytest.fixture
def routed_api(monkeypatch) -> FakeRoutedApi:
    """
    Puts a fake eodhd.com behind the request layer that answers every endpoint with its sample
    payload, whatever the order of the requests. Suits tests of the code built on the request
    layer; see scripted_api for tests that script the exact sequence of answers.

    :param monkeypatch: pytest fixture used to replace requests.get
    :return: The fake, recording every request and taking route overrides
    """
    fake_routed_api = FakeRoutedApi()
    monkeypatch.setattr(request_data_module.requests, "get", fake_routed_api.get)
    return fake_routed_api


@pytest.fixture
def clock(monkeypatch) -> FakeClock:
    """
    Replaces the clock the backoff waits on, so that the real _sleep runs without blocking.

    :param monkeypatch: pytest fixture used to replace backoff's time module
    :return: The fake clock, recording every sleep
    """
    fake_clock = FakeClock()
    monkeypatch.setattr(backoff_module, "time", fake_clock)
    return fake_clock


@pytest.fixture
def reset_logging():
    """
    Restores the root logger after a test that sets up logging, closing the handlers it added.
    """
    root_logger = logging.getLogger()
    handlers, level = list(root_logger.handlers), root_logger.level
    yield
    for handler in root_logger.handlers:
        if handler not in handlers:
            handler.close()
    root_logger.handlers[:] = handlers
    root_logger.setLevel(level)
    logging.captureWarnings(False)
