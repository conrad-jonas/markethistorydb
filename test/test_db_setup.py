#!/usr/bin/env python12.9

"""Unit tests for db_setup.py"""

import db.db_const as db_const
import db.db_setup as db_setup
import db.db_sql as db_sql

import pytest
import psycopg as pg
import sqlite3
import time

from collections.abc import Callable

@pytest.mark.db
def test_setup_questdb(setup_test: Callable, backup_and_restore_questdb: Callable):
    db_setup._create_questdb()
    time.sleep(0.5)
    # Check if tables and columns exist
    tables_to_check = {db_const.TABLE_NAME_DAILY_PRICE: db_const.COLUMNS_DAILY_PRICE,
                       db_const.TABLE_NAME_MINUTE_PRICE: db_const.COLUMNS_MINUTE_PRICE}
    with pg.connect(db_const.QUESTDB_CONF_PSYCOPG, autocommit=True) as connection:
        for table in tables_to_check:
            for column in tables_to_check[table]:
                # Open a cursor to perform database operations
                with connection.cursor() as cur:
                    query_string = db_sql.SQL_SELECT_SCHEMA_QUESTDB
                    cur.execute(query_string, (table, column))
                    rows = cur.fetchall()
                    assert len(rows) == 1

@pytest.mark.db
def test_setup_sqlite(setup_test: Callable, backup_and_restore_sqlite: Callable):
    db_setup._create_sqlite()
    time.sleep(0.5)
    # Check if db, tables and columns exist
    tables_to_check = {
        db_const.TABLE_SYMBOL_SECTOR: db_const.COLUMNS_SYMBOL_SECTOR,
        db_const.TABLE_SYMBOL_META: db_const.COLUMNS_SYMBOL_META,
        db_const.TABLE_EARNINGS_QUARTERLY: db_const.COLUMNS_EARNINGS_QUARTERLY,
        db_const.TABLE_EARNINGS_ANNUALLY: db_const.COLUMNS_EARNINGS_ANNUALLY,
        db_const.TABLE_BALANCE_SHEET_QUARTERLY: db_const.COLUMNS_BALANCE_SHEET_QUARTERLY,
        db_const.TABLE_BALANCE_SHEET_ANNUALLY: db_const.COLUMNS_BALANCE_SHEET_ANNUALLY,
        db_const.TABLE_CASH_FLOW_QUARTERLY: db_const.COLUMNS_CASH_FLOW_QUARTERLY,
        db_const.TABLE_CASH_FLOW_ANNUALLY: db_const.COLUMNS_CASH_FLOW_ANNUALLY,
        db_const.TABLE_INCOME_STATEMENT_QUARTERLY: db_const.COLUMNS_INCOME_STATEMENT_QUARTERLY,
        db_const.TABLE_INCOME_STATEMENT_ANNUALLY: db_const.COLUMNS_INCOME_STATEMENT_ANNUALLY
    }
    connection = sqlite3.connect(db_const.SQLITE_DB_PATH, autocommit=True)
    for table in tables_to_check:
        for column in tables_to_check[table]:
            # Open a cursor to perform database operations
            cur = connection.cursor()
            query_string = db_sql.SQL_SELECT_SCHEMA_SQLITE
            params = {"table_name": table, "column_name": column}
            cur.execute(query_string, params)
            rows = cur.fetchall()
            assert len(rows) == 1
    connection.close()