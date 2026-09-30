"""
Fixtures for the integration tests, which run against a real QuestDB.

Every test here drops and recreates all tables, so they only run against a throwaway instance
named by the QUESTDB_TEST_* variables (in the environment or in .env), and refuse to run if that
instance is the one the QUESTDB_* variables point the application to. Without the variables, or
with the instance unreachable, the tests are skipped.
"""

from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any
import os
import socket
import time

import psycopg as pg
import pytest
from dotenv import dotenv_values
from psycopg import sql

from markethistorydb.config import Config
from markethistorydb.db import Database
from markethistorydb.setup import setup

_DIRPATH_INTEGRATION_TESTS = Path(__file__).resolve().parent
_FILEPATH_DOTENV = _DIRPATH_INTEGRATION_TESTS.parents[1] / ".env"
# Seconds to wait for the test instance to accept a connection before skipping
_CONNECT_TIMEOUT_IN_SECS = 2
# Seconds to wait for a WAL table to apply a write before failing
_WAL_APPLY_TIMEOUT_IN_SECS = 15


def pytest_collection_modifyitems(items: list[pytest.Item]):
    """
    Marks every test in this directory with the integration marker, so that -m "not integration"
    leaves them out.

    :param items: Every collected test of the session
    """
    for item in items:
        if item.path.is_relative_to(_DIRPATH_INTEGRATION_TESTS):
            item.add_marker(pytest.mark.integration)


def _setting(name: str, default: str | None = None) -> str | None:
    """
    Reads a setting from the environment, falling back to .env without loading it wholesale.

    :param name: Name of the variable
    :param default: Value returned when the variable is set nowhere
    :return: Value of the variable, or *default*
    """
    if name in os.environ:
        return os.environ[name]
    return dotenv_values(_FILEPATH_DOTENV).get(name, default) if _FILEPATH_DOTENV.exists() else default


def _address(host: str, port: str | int) -> tuple[str, int]:
    """
    Normalises a host and port, so that "localhost" and "127.0.0.1" compare equal.

    :param host: Host name or IP address
    :param port: Port number
    :return: IP address and port
    """
    try:
        return socket.gethostbyname(host), int(port)
    except OSError:
        return host, int(port)


@pytest.fixture(scope="session")
def questdb_config() -> Config:
    """
    Builds the config of the throwaway test instance, after making sure it is one.

    :return: Config pointing at the instance the QUESTDB_TEST_* variables name
    """
    host = _setting("QUESTDB_TEST_HOST")
    pg_port = _setting("QUESTDB_TEST_PG_PORT")
    http_port = _setting("QUESTDB_TEST_HTTP_PORT")
    if not (host and pg_port and http_port):
        pytest.skip("QUESTDB_TEST_HOST, QUESTDB_TEST_PG_PORT and QUESTDB_TEST_HTTP_PORT are not set")

    app_host = _setting("QUESTDB_HOST", "127.0.0.1")
    test_addresses = {_address(host, pg_port), _address(host, http_port)}
    app_addresses = {_address(app_host, _setting("QUESTDB_PG_PORT", "8812")),
                     _address(app_host, _setting("QUESTDB_HTTP_PORT", "9000"))}
    if test_addresses & app_addresses:
        pytest.exit("Refusing to run the integration tests: QUESTDB_TEST_* points at the QuestDB "
                    "the application uses ({0}), and the tests drop every table. Start a separate "
                    "instance with its own data directory and ports.".format(
                        sorted(test_addresses & app_addresses)), returncode=3)

    config = Config(eodhd_api_token="integration-test-token",
                    questdb_password=_setting("QUESTDB_TEST_PASSWORD", "quest"),
                    questdb_host=host, questdb_pg_port=int(pg_port), questdb_http_port=int(http_port),
                    questdb_user=_setting("QUESTDB_TEST_USER", "admin"))
    try:
        pg.connect(config.psycopg_conninfo, connect_timeout=_CONNECT_TIMEOUT_IN_SECS).close()
    except pg.Error as error:
        pytest.skip("Test QuestDB at {0}:{1} is not reachable: {2}".format(host, pg_port, error))
    return config


@pytest.fixture
def fresh_db(questdb_config) -> Database:
    """
    Sets the test instance up from scratch, so that every test starts on empty tables.

    :param questdb_config: Config of the test instance
    :return: Database interfaces on the fresh instance
    """
    setup(questdb_config)
    return Database(questdb_config)


def select(db: Database, statement: str, *params: Any) -> list[tuple]:
    """
    Runs a raw statement on the test instance.

    :param db: Database to run it on
    :param statement: Statement text, %s for every parameter
    :param params: Values bound to the placeholders
    :return: Selected records
    """
    return db.query.execute(sql.SQL(statement), list(params))


def count(db: Database, table_name: str, where: str = "", *params: Any) -> int:
    """
    Counts the records of a table.

    :param db: Database to count on
    :param table_name: Table to count
    :param where: Optional condition, without the WHERE keyword
    :param params: Values bound to the condition's placeholders
    :return: Number of matching records
    """
    statement = "SELECT count() FROM {0}".format(table_name)
    if where:
        statement += " WHERE " + where
    return select(db, statement, *params)[0][0]


def wait_until[T](db: Database, read: Callable[[], T], is_done: Callable[[T], bool]) -> T:
    """
    Polls *read* until *is_done* accepts its result, since WAL tables apply writes asynchronously.

    :param db: Database the writes went to, inspected for suspended tables on timeout
    :param read: Reads the state that is waited for
    :param is_done: Tells whether the state has been reached
    :return: The last result of *read*
    """
    deadline = time.monotonic() + _WAL_APPLY_TIMEOUT_IN_SECS
    while True:
        result = read()
        if is_done(result):
            return result
        if time.monotonic() > deadline:
            suspended = select(db, "SELECT name FROM wal_tables() WHERE suspended")
            raise AssertionError("Gave up waiting; last result {0!r}; suspended WAL tables: {1}".format(
                result, suspended))
        time.sleep(0.1)


def wait_for_count(db: Database, table_name: str, expected: int, where: str = "", *params: Any) -> int:
    """
    Waits until a table holds *expected* matching records.

    :param db: Database to count on
    :param table_name: Table to count
    :param expected: Number of records to wait for
    :param where: Optional condition, without the WHERE keyword
    :param params: Values bound to the condition's placeholders
    :return: The final count
    """
    return wait_until(db, lambda: count(db, table_name, where, *params), lambda n: n == expected)


def settle(db: Database, *table_names: str):
    """
    Waits until every write to *table_names* has been applied, whatever it was.

    :param db: Database the writes went to
    :param table_names: Tables to wait for
    """
    def pending() -> list[tuple]:
        return select(db, "SELECT name FROM wal_tables() WHERE writerTxn != sequencerTxn AND name IN ({0})".format(
            ", ".join("'{0}'".format(name) for name in table_names)))

    wait_until(db, pending, lambda rows: rows == [])


@pytest.fixture
def no_disk_check(monkeypatch):
    """
    Skips the Fetcher's free disk space check, which depends on the machine running the tests.

    :param monkeypatch: pytest fixture used to replace Fetcher._check_storage_space
    """
    from markethistorydb.fetch.fetcher import Fetcher
    monkeypatch.setattr(Fetcher, "_check_storage_space", staticmethod(lambda: None))


def iter_tables() -> Iterator[type]:
    """
    Lists the constants class of every table setup creates.

    :return: Iterator over the table classes
    """
    from markethistorydb.db import tables
    yield from (tables.Exchange, tables.Symbol, tables.Sector, tables.DailyOhlcv, tables.MinuteOhlcv,
                tables.EarningsQuarterly, tables.EarningsAnnually, tables.BalanceSheetQuarterly,
                tables.BalanceSheetAnnually, tables.CashFlowQuarterly, tables.CashFlowAnnually,
                tables.IncomeStatementQuarterly, tables.IncomeStatementAnnually)
