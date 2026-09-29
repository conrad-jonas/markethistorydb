"""Tests for db/io/query.py"""

import pytest

from psycopg import sql

import markethistorydb.db.io.query as query_module
from markethistorydb.db.io.query import Query
from markethistorydb.errors import DbError, QueryError
from tests.fakes import FakeConfig, FakeConnection, FakeCursor


def _query_with_cursor(monkeypatch, cursor) -> Query:
    monkeypatch.setattr(query_module.pg, "connect", lambda *args, **kwargs: FakeConnection(cursor))
    return Query(FakeConfig())


def test_a_statement_without_a_result_set_returns_no_records(monkeypatch):
    # UPDATE, DELETE and DDL produce no records, and fetching from them raises in psycopg
    query = _query_with_cursor(monkeypatch, FakeCursor(description=None, rows=[]))
    assert query.execute("UPDATE exchange SET name = %s", ["NASDAQ"]) == []

def test_a_select_returns_its_records(monkeypatch):
    query = _query_with_cursor(monkeypatch, FakeCursor(description=[("name",)], rows=[("NASDAQ",)]))
    assert query.execute("SELECT name FROM exchange", []) == [("NASDAQ",)]

def test_a_failing_statement_is_reported_as_a_db_error(monkeypatch):
    class FailingCursor(FakeCursor):
        def execute(self, query, params):
            raise query_module.pg.OperationalError("connection refused")

    query = _query_with_cursor(monkeypatch, FailingCursor(description=None, rows=[]))
    with pytest.raises(QueryError) as excinfo:
        query.execute("SELECT 1", [])
    assert isinstance(excinfo.value, DbError)


def test_the_params_are_bound_as_a_tuple_and_never_formatted_into_the_statement(monkeypatch):
    class RecordingCursor(FakeCursor):
        def execute(self, query, params):
            self.executed = (query, params)

    cursor = RecordingCursor(description=None, rows=[])
    query = _query_with_cursor(monkeypatch, cursor)
    query.execute(sql.SQL("SELECT * FROM exchange WHERE exchange_code = %s"), ["x' OR '1'='1"])
    assert cursor.executed[1] == ("x' OR '1'='1",)
    assert "OR '1'" not in cursor.executed[0].as_string(None)

def test_every_statement_connects_with_autocommit_and_client_side_binding(monkeypatch):
    connects = []

    def connect(conninfo, **kwargs):
        connects.append((conninfo, kwargs))
        return FakeConnection(FakeCursor(description=None, rows=[]))

    monkeypatch.setattr(query_module.pg, "connect", connect)
    Query(FakeConfig()).execute(sql.SQL("SELECT 1"), [])
    # QuestDB has no transactions to commit, and ClientCursor is what QuestDB's PG wire expects
    assert connects == [(FakeConfig.psycopg_conninfo,
                         {"cursor_factory": query_module.pg.ClientCursor, "autocommit": True})]
