"""Tests for setup/main.py"""

import psycopg as pg
import pytest

import markethistorydb.setup.main as schema_setup
from markethistorydb.config import Config
from markethistorydb.errors import DbError
from tests.fakes import FakeConnection


class ScriptCursor:
    """Records the scripts executed on it; fails on the one containing *fail_on*"""

    def __init__(self, fail_on: str | None = None):
        self.scripts: list[str] = []
        self._fail_on = fail_on

    def execute(self, script):
        if self._fail_on is not None and self._fail_on in script:
            raise pg.errors.SyntaxError("found [tok=')'] missing column definition")
        self.scripts.append(script)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _config() -> Config:
    return Config(eodhd_api_token="token", questdb_password="secret")


@pytest.fixture
def connections(monkeypatch) -> list[tuple]:
    """
    Replaces psycopg's connect, recording each connection's arguments.

    :param monkeypatch: pytest fixture used to replace setup.main.pg.connect
    :return: List of (conninfo, kwargs, cursor) per connection made
    """
    made: list[tuple] = []

    def connect(conninfo, **kwargs):
        cursor = ScriptCursor()
        made.append((conninfo, kwargs, cursor))
        return FakeConnection(cursor)

    monkeypatch.setattr(schema_setup.pg, "connect", connect)
    return made


def test_every_schema_file_runs_in_dependency_order_over_one_connection(connections):
    schema_setup.setup(_config())
    assert len(connections) == 1
    conninfo, kwargs, cursor = connections[0]
    assert conninfo == _config().psycopg_conninfo and kwargs == {"autocommit": True}
    expected = [(schema_setup.DIRPATH_SCHEMA / name).read_text() for name in schema_setup._SCHEMA_FILE_NAMES]
    assert cursor.scripts == expected
    assert schema_setup._SCHEMA_FILE_NAMES == ("exchange.sql", "fundamental.sql", "price.sql", "symbol.sql")

def test_a_schema_file_that_cannot_be_read_is_a_db_error_naming_it(connections, monkeypatch, tmp_path):
    monkeypatch.setattr(schema_setup, "DIRPATH_SCHEMA", tmp_path)
    with pytest.raises(DbError) as excinfo:
        schema_setup.setup(_config())
    assert "exchange.sql" in str(excinfo.value)
    assert isinstance(excinfo.value.__cause__, OSError)

def test_a_statement_the_db_rejects_is_a_db_error(monkeypatch):
    monkeypatch.setattr(schema_setup.pg, "connect",
                        lambda *args, **kwargs: FakeConnection(ScriptCursor(fail_on="CREATE TABLE")))
    with pytest.raises(DbError) as excinfo:
        schema_setup.setup(_config())
    assert "missing column definition" in str(excinfo.value)

def test_an_unreachable_db_is_a_db_error(monkeypatch):
    def refuse(*args, **kwargs):
        raise pg.OperationalError("connection refused")

    monkeypatch.setattr(schema_setup.pg, "connect", refuse)
    with pytest.raises(DbError):
        schema_setup.setup(_config())
