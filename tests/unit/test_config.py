"""Tests for config.py"""

import dataclasses
import pytest
from psycopg.conninfo import conninfo_to_dict
from questdb import Sender

from markethistorydb.config import Config
from markethistorydb.errors import ConfigError


# --- configuration -------------------------------------------------------------------------

def test_the_db_connection_gives_up_rather_than_hanging_on_an_unreachable_host():
    conninfo = Config(eodhd_api_token="token", questdb_password="secret").psycopg_conninfo
    assert "connect_timeout=" in conninfo

def test_a_port_that_is_not_a_number_is_a_config_error(monkeypatch):
    monkeypatch.setenv("EODHD_API_TOKEN", "token")
    monkeypatch.setenv("QUESTDB_PASSWORD", "secret")
    monkeypatch.setenv("QUESTDB_PG_PORT", "notaport")
    with pytest.raises(ConfigError) as excinfo:
        Config.from_env()
    # The message names the variable, so the user knows which one to fix
    assert "QUESTDB_PG_PORT" in str(excinfo.value)

def test_a_missing_token_is_a_config_error_naming_the_variable(monkeypatch):
    monkeypatch.delenv("EODHD_API_TOKEN", raising=False)
    monkeypatch.setenv("QUESTDB_PASSWORD", "secret")
    with pytest.raises(ConfigError) as excinfo:
        Config.from_env()
    assert "EODHD_API_TOKEN" in str(excinfo.value)

def test_neither_secret_shows_up_in_the_repr():
    text = repr(Config(eodhd_api_token="tok-secret", questdb_password="hunter2"))
    assert "hunter2" not in text
    assert "tok-secret" not in text

@pytest.mark.parametrize("password", [
    "pw hostaddr=203.0.113.1",
    "with space",
    "it's",
    "back\\slash",
])
def test_the_password_cannot_break_out_of_the_db_connection_string(password):
    # Unquoted, the space would end the password and let the rest pass as settings of its own
    conninfo = conninfo_to_dict(
        Config(eodhd_api_token="token", questdb_password=password).psycopg_conninfo)
    assert conninfo["password"] == password
    assert "hostaddr" not in conninfo

@pytest.mark.parametrize("password, escaped", [
    ("a;b",   "a;;b"),
    ("a;;b",  "a;;;;b"),
    ("ends;", "ends;;"),
])
def test_a_semicolon_in_the_password_cannot_end_the_ingress_config_early(password, escaped):
    http_conf = Config(eodhd_api_token="token", questdb_password=password).http_conf
    assert "password={0};".format(escaped) in http_conf
    # Has the real parser accept it;
    Sender.from_conf(http_conf)


def test_unset_optional_variables_fall_back_to_the_defaults(monkeypatch):
    monkeypatch.setenv("EODHD_API_TOKEN", "token")
    monkeypatch.setenv("QUESTDB_PASSWORD", "secret")
    for name in ("QUESTDB_HOST", "QUESTDB_PG_PORT", "QUESTDB_HTTP_PORT", "QUESTDB_USER",
                 "QUESTDB_DB_NAME"):
        monkeypatch.delenv(name, raising=False)
    config = Config.from_env()
    assert (config.questdb_host, config.questdb_pg_port, config.questdb_http_port,
            config.questdb_user, config.questdb_db_name) == ("127.0.0.1", 8812, 9000, "admin", "qdb")

def test_every_optional_variable_overrides_its_default(monkeypatch):
    monkeypatch.setenv("EODHD_API_TOKEN", "token")
    monkeypatch.setenv("QUESTDB_PASSWORD", "secret")
    monkeypatch.setenv("QUESTDB_HOST", "db.internal")
    monkeypatch.setenv("QUESTDB_PG_PORT", "18812")
    monkeypatch.setenv("QUESTDB_HTTP_PORT", "19000")
    monkeypatch.setenv("QUESTDB_USER", "reader")
    monkeypatch.setenv("QUESTDB_DB_NAME", "market")
    assert Config.from_env() == Config(
        eodhd_api_token="token", questdb_password="secret", questdb_host="db.internal",
        questdb_pg_port=18812, questdb_http_port=19000, questdb_user="reader",
        questdb_db_name="market")

def test_the_psycopg_connection_string_carries_every_setting():
    config = Config(eodhd_api_token="token", questdb_password="secret", questdb_host="db.internal",
                    questdb_pg_port=18812, questdb_user="reader", questdb_db_name="market")
    assert conninfo_to_dict(config.psycopg_conninfo) == {
        "user": "reader", "password": "secret", "host": "db.internal", "port": "18812",
        "dbname": "market", "connect_timeout": "10"}

def test_the_ingress_config_string_carries_every_setting():
    config = Config(eodhd_api_token="token", questdb_password="secret", questdb_host="db.internal",
                    questdb_http_port=19000, questdb_user="writer")
    assert config.http_conf == "http::addr=db.internal:19000;username=writer;password=secret;"

def test_a_config_cannot_be_changed_once_built():
    config = Config(eodhd_api_token="token", questdb_password="secret")
    with pytest.raises(dataclasses.FrozenInstanceError):
        config.questdb_host = "elsewhere"
