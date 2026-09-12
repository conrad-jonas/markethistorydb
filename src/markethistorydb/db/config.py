#!/usr/bin/env python12.9

"""Global db related constants"""

import os

from markethistorydb.utils.env import require_env


# QuestDB server path
QUESTDB_DIR_PATH = os.environ.get("QUESTDB_DIR_PATH", "C:/TradingAnalysis/questdb/qdbroot")
# QuestDB exe path
QUESTDB_EXE_PATH = os.environ.get(
    "QUESTDB_EXE_PATH", "C:/TradingAnalysis/questdb/questdb-9.3.3-rt-windows-x86-64/bin/questdb.exe")
# QuestDB connection settings
QUESTDB_HOST      = os.environ.get("QUESTDB_HOST", "127.0.0.1")
QUESTDB_PG_PORT   = os.environ.get("QUESTDB_PG_PORT", "8812")
QUESTDB_HTTP_PORT = os.environ.get("QUESTDB_HTTP_PORT", "9000")
QUESTDB_USER      = os.environ.get("QUESTDB_USER", "admin")
QUESTDB_DB_NAME   = os.environ.get("QUESTDB_DB_NAME", "qdb")
# QuestDB password (must be provided via environment, never hardcoded)
QUESTDB_PASSWORD = require_env("QUESTDB_PASSWORD")
# Config string PostgreSQL
QUESTDB_CONF_PSYCOPG = "user={0} password={1} host={2} port={3} dbname={4}".format(
    QUESTDB_USER, QUESTDB_PASSWORD, QUESTDB_HOST, QUESTDB_PG_PORT, QUESTDB_DB_NAME)
# Config string http
QUESTDB_CONF_HTTP = "http::addr={0}:{1};username={2};password={3};".format(
    QUESTDB_HOST, QUESTDB_HTTP_PORT, QUESTDB_USER, QUESTDB_PASSWORD)
