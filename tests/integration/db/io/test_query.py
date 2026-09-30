"""Integration tests for db/io/query.py"""

import dataclasses
import pytest
from psycopg import sql

from markethistorydb.db.io.query import Query
from markethistorydb.errors import QueryError


def test_a_select_returns_its_records(fresh_db):
    assert fresh_db.query.execute(sql.SQL("SELECT 1 + %s"), [1]) == [(2,)]

def test_a_statement_without_a_result_set_returns_no_records(fresh_db):
    # psycopg raises on fetchall() for DDL, which Query must not call
    assert fresh_db.query.execute(sql.SQL("ALTER TABLE exchange ADD COLUMN note VARCHAR"), []) == []

def test_invalid_sql_is_a_query_error(fresh_db):
    with pytest.raises(QueryError) as excinfo:
        fresh_db.query.execute(sql.SQL("SELEC nothing"), [])
    assert "Query failed" in str(excinfo.value)

def test_a_table_that_does_not_exist_is_a_query_error(fresh_db):
    with pytest.raises(QueryError):
        fresh_db.query.execute(sql.SQL("SELECT * FROM no_such_table"), [])


# --- security ------------------------------------------------------------------------------

def test_a_wrong_password_is_rejected(questdb_config):
    wrong = dataclasses.replace(questdb_config, questdb_password="not-the-password")
    with pytest.raises(QueryError):
        Query(wrong).execute(sql.SQL("SELECT 1"), [])

def test_the_error_of_a_rejected_login_does_not_echo_the_password(questdb_config):
    wrong = dataclasses.replace(questdb_config, questdb_password="p4ssw0rd-that-must-not-leak")
    with pytest.raises(QueryError) as excinfo:
        Query(wrong).execute(sql.SQL("SELECT 1"), [])
    assert "p4ssw0rd-that-must-not-leak" not in str(excinfo.value)
