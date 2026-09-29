"""Tests for db/database.py"""

from markethistorydb.config import Config
from markethistorydb.db import Database, Delete, Insert, Query, Read, Update


def test_the_interfaces_share_one_query_and_the_config():
    config = Config(eodhd_api_token="token", questdb_password="secret")
    db = Database(config)
    assert isinstance(db.query, Query) and db.query._config is config
    assert isinstance(db.read, Read) and db.read._query is db.query
    assert isinstance(db.update, Update) and db.update._query is db.query
    assert isinstance(db.delete, Delete) and db.delete._query is db.query
    assert isinstance(db.insert, Insert) and db.insert._config is config

def test_building_a_database_does_not_connect(monkeypatch):
    # Client() builds one on construction, which must work without a reachable DB
    import markethistorydb.db.io.query as query_module
    monkeypatch.setattr(query_module.pg, "connect", _no_connection)
    Database(Config(eodhd_api_token="token", questdb_password="secret"))

def _no_connection(*args, **kwargs):
    raise AssertionError("connected while building the Database")
