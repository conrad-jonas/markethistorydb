#!/usr/bin/env python12.9

"""Global db related constants"""


# QUESTDB server path
QUESTDB_DIR_PATH = "C:/TradingAnalysis/questdb/qdbroot"
# QUESTDB exe path
QUESTDB_EXE_PATH = "C:/TradingAnalysis/questdb/questdb-9.3.3-rt-windows-x86-64/bin/questdb.exe"
# QuestDB password
QUESTDB_PASSWORD = "quest"
# Config string PostgreSQL
QUESTDB_CONF_PSYCOPG = "user=admin password={0} host=127.0.0.1 port=8812 dbname=qdb".format(QUESTDB_PASSWORD)
# Config string http
QUESTDB_CONF_HTTP = "http::addr=localhost:9000;username=admin;password={0};".format(QUESTDB_DIR_PATH)
