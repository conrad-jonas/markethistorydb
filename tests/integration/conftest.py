"""
Fixtures for the integration tests, which run against a real QuestDB.

Every test here drops and recreates all tables, so they only run against a throwaway instance:
the one named by the QUESTDB_TEST_* variables (in the environment or in .env), or else a QuestDB
container started for the session if Docker answers. They refuse to run if the named instance is
the one the QUESTDB_* variables point the application to. With neither, or with the named
instance unreachable, the tests are skipped.
"""

from collections.abc import Callable, Iterator, Mapping
from pathlib import Path
from typing import Any
import os
import socket
import time

import psycopg as pg
import pytest
from docker.errors import DockerException
from dotenv import dotenv_values
from psycopg import sql
from testcontainers.core.container import DockerContainer
from testcontainers.core.docker_client import DockerClient

from markethistorydb.config import Config
from markethistorydb.db import Database
from markethistorydb.setup import setup
from tests.integration_support.database_choice import (
    Container,
    Override,
    Skip,
    choose_test_database,
)

_DIRPATH_INTEGRATION_TESTS = Path(__file__).resolve().parent
_FILEPATH_DOTENV = _DIRPATH_INTEGRATION_TESTS.parents[1] / ".env"
# Seconds to wait for the test instance to accept a connection before skipping
_CONNECT_TIMEOUT_IN_SECS = 2
# Seconds to wait for a freshly started container to answer SQL before failing
_CONTAINER_START_TIMEOUT_IN_SECS = 60
# Ports QuestDB listens on inside its container: PostgreSQL wire protocol and HTTP
_CONTAINER_PG_PORT = 8812
_CONTAINER_HTTP_PORT = 9000
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


def _environment() -> dict[str, str]:
    """
    Reads the variables of .env, overridden by those of the environment, without loading .env
    into the environment.

    :return: Values by variable name
    """
    dotenv = dotenv_values(_FILEPATH_DOTENV) if _FILEPATH_DOTENV.exists() else {}
    return {**{name: value for name, value in dotenv.items() if value is not None}, **os.environ}


def _docker_available() -> bool:
    """
    Tells whether a Docker daemon answers, so that the tests can start their own QuestDB. Without
    Docker, creating the client fails at once.

    :return: True if the daemon answered
    """
    try:
        client = DockerClient().client
        client.ping()
        client.close()
    except DockerException:
        return False
    return True


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


def _override_config(choice: Override, environment: Mapping[str, str]) -> Config:
    """
    Builds the config of the instance the QUESTDB_TEST_* variables name, after making sure it is a
    throwaway one.

    :param choice: The named instance
    :param environment: Variables of the environment, over those of .env, which also locate the
        application's instance
    :return: Config pointing at the named instance
    """
    app_host = environment.get("QUESTDB_HOST", "127.0.0.1")
    test_addresses = {_address(choice.host, choice.pg_port), _address(choice.host, choice.http_port)}
    app_addresses = {_address(app_host, environment.get("QUESTDB_PG_PORT", "8812")),
                     _address(app_host, environment.get("QUESTDB_HTTP_PORT", "9000"))}
    if shared := sorted(test_addresses & app_addresses):
        pytest.exit("Refusing to run the integration tests: QUESTDB_TEST_* points at the QuestDB "
                    f"the application uses ({shared}), and the tests drop every table. Start a "
                    "separate instance with its own data directory and ports.", returncode=3)

    config = Config(eodhd_api_token="integration-test-token", questdb_password=choice.password,
                    questdb_host=choice.host, questdb_pg_port=choice.pg_port,
                    questdb_http_port=choice.http_port, questdb_user=choice.user)
    try:
        pg.connect(config.psycopg_conninfo, connect_timeout=_CONNECT_TIMEOUT_IN_SECS).close()
    except pg.Error as error:
        pytest.skip(f"Test QuestDB at {choice.host}:{choice.pg_port} is not reachable: {error}")
    return config


def _wait_for_sql(config: Config):
    """
    Waits until a freshly started QuestDB answers SQL.

    :param config: Config pointing at the instance
    :raises TimeoutError: If it doesn't answer within _CONTAINER_START_TIMEOUT_IN_SECS
    """
    deadline = time.monotonic() + _CONTAINER_START_TIMEOUT_IN_SECS
    while True:
        try:
            with pg.connect(config.psycopg_conninfo, connect_timeout=_CONNECT_TIMEOUT_IN_SECS) as connection:
                connection.execute("SELECT 1")
            return
        except pg.Error as error:
            if time.monotonic() > deadline:
                raise TimeoutError("The QuestDB container did not answer SQL within "
                                   f"{_CONTAINER_START_TIMEOUT_IN_SECS} s: {error}") from error
            time.sleep(0.5)


def _container_config(choice: Container) -> Iterator[Config]:
    """
    Starts QuestDB as a container for the session, with line.auto.create.new.columns=false as in
    production, and removes the container afterwards.

    :param choice: The container to start
    :return: Config pointing at the container, once it answers SQL
    """
    container = (DockerContainer(choice.image)
                 .with_env("QDB_LINE_AUTO_CREATE_NEW_COLUMNS", "false")
                 .with_exposed_ports(_CONTAINER_PG_PORT, _CONTAINER_HTTP_PORT))
    with container:
        config = Config(eodhd_api_token="integration-test-token", questdb_password="quest",
                        questdb_host=container.get_container_host_ip(),
                        questdb_pg_port=container.get_exposed_port(_CONTAINER_PG_PORT),
                        questdb_http_port=container.get_exposed_port(_CONTAINER_HTTP_PORT),
                        questdb_user="admin")
        _wait_for_sql(config)
        yield config


@pytest.fixture(scope="session")
def questdb_config() -> Iterator[Config]:
    """
    Builds the config of a throwaway QuestDB for the session: the instance the QUESTDB_TEST_*
    variables name, or else a container started for the session.

    :return: Config pointing at the test instance
    """
    environment = _environment()
    choice = choose_test_database(environment, _docker_available())
    if isinstance(choice, Skip):
        pytest.skip(choice.message)
    if isinstance(choice, Override):
        yield _override_config(choice, environment)
    else:
        yield from _container_config(choice)


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
