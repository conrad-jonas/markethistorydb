#!/usr/bin/env python12.9

"""Unit tests for access.py"""
import db.price.access
import fetch.download_db
from misc.data_types import TimeFrame, SymbolStatus

import db.price.access as db_access
import db.price.tables as db_const
import setup.main as db_setup
import db.price.queries as db_sql

import pandas  as pd
import pytest
import psycopg as pg
import sqlite3
import time

from collections.abc    import Callable
from datetime           import datetime
from pytest_mock        import MockerFixture
from questdb.ingress    import IngressError

@pytest.fixture()
def setup_questdb(backup_and_restore_questdb: Callable):
    """Creates QuestDB"""
    # Creates DB
    db_setup.setup_questdb()

@pytest.fixture()
def setup_and_cleanup_sqlite(backup_and_restore_sqlite: Callable):
    """Creates SQLite DB, inserts dummy data and cleans up afterward"""
    # Creates SQLite DB
    db_setup.setup_sqlite()
    # Connects SQLite DB
    connection = sqlite3.connect(db_const.SQLITE_DB_PATH)
    cursor = connection.cursor()

    # Inserts dummy data
    insert_params_1 = {"symbol_code": db_const.DUMMY_SYMBOL_CODE, "exchange_code": db_const.DUMMY_EXCHANGE_CODE_A,
                     "name": db_const.DUMMY_SYMBOL_NAME}
    insert_params_2 = {"symbol_code": db_const.DUMMY_SYMBOL_CODE, "exchange_code": db_const.DUMMY_EXCHANGE_CODE_B,
                       "name": db_const.DUMMY_SYMBOL_NAME}
    cursor.execute(db_sql.SQL_INSERT_DUMMY_SYMBOL_INTO_SYMBOL_META, insert_params_1)
    cursor.execute(db_sql.SQL_INSERT_DUMMY_SYMBOL_INTO_SYMBOL_META, insert_params_2)
    connection.commit()
    cursor.close()
    connection.close()

@pytest.mark.db
def test_get_id_from_symbol_meta(setup_test: Callable, setup_and_cleanup_sqlite: Callable):
    symbol_code   = db_const.DUMMY_SYMBOL_CODE
    exchange_code_a = db_const.DUMMY_EXCHANGE_CODE_A
    exchange_code_b = db_const.DUMMY_EXCHANGE_CODE_B
    symbol_name = db_const.DUMMY_SYMBOL_NAME
    time_frame = db_access.TimeFrame.DAILY
    symbol_status = SymbolStatus.ACTIVE

    assert db.price.access.select_id_from_symbol_meta(symbol_code, exchange_code_a, time_frame, symbol_status, symbol_name) == 1
    assert db.price.access.select_id_from_symbol_meta(symbol_code, exchange_code_b, time_frame, symbol_status, symbol_name) == 2

@pytest.mark.db
def test_is_symbol_already_in_db_true(setup_test: Callable, setup_and_cleanup_sqlite: Callable):
    time_frame = TimeFrame.DAILY
    symbol_status = db_access.SymbolStatus.ACTIVE

    is_symbol_already_in_db = (fetch.download_insert.is_already_in_symbol_meta(db_const.DUMMY_SYMBOL_CODE,
                                                                               db_const.DUMMY_EXCHANGE_CODE_A, time_frame,
                                                                               symbol_status, db_const.DUMMY_SYMBOL_NAME))
    assert is_symbol_already_in_db == True

@pytest.mark.db
def test_is_symbol_already_in_db_false(setup_test: Callable, setup_and_cleanup_sqlite: Callable):
    symbol_code = "test_code_XYZ"
    time_frame = TimeFrame.DAILY
    symbol_status = SymbolStatus.ACTIVE

    assert "test_code_XYZ" != db_const.DUMMY_SYMBOL_CODE

    is_symbol_already_in_db = fetch.download_insert.is_already_in_symbol_meta(symbol_code, db_const.DUMMY_EXCHANGE_CODE_A, time_frame,
                                                                              symbol_status, "test_name")
    assert is_symbol_already_in_db == False

@pytest.mark.db
@pytest.mark.parametrize("time_frame", [TimeFrame.DAILY, TimeFrame.MINUTE])
def test_insert_ohlcv_data_success(setup_test: Callable, setup_questdb: Callable, time_frame: db_access.TimeFrame):
    # Inserts data
    symbol_status = SymbolStatus.ACTIVE
    if time_frame == TimeFrame.DAILY:
        timestamp = datetime.now()
    else:
        timestamp = pd.Timestamp(datetime.now())

    if time_frame == db_access.TimeFrame.DAILY:
        data = {'datetime': [timestamp],
               'exchange_code': [db_const.DUMMY_EXCHANGE_CODE_A],
               'symbol_code': [db_const.DUMMY_SYMBOL_CODE],
               'open': [1.0],
               'high': [1.0],
               'low': [1.0],
               'close': [1.0],
               'adjusted_close': [1.0],
               'volume': [1]}
    else:
        data = {'timestamp': [timestamp],
                'exchange_code': [db_const.DUMMY_EXCHANGE_CODE_A],
                'symbol_code': [db_const.DUMMY_SYMBOL_CODE],
                'gmt_offset': [0],
                'open': [1.0],
                'high': [1.0],
                'low': [1.0],
                'close': [1.0],
                'volume': [1]}
    df_eod = pd.DataFrame(data)

    db_access.ohlcv(df_eod, db_const.DUMMY_SYMBOL_CODE, db_const.DUMMY_EXCHANGE_CODE_A, time_frame,
                    symbol_status)
    # Queries data
    time.sleep(0.5)
    with pg.connect(db_const.QUESTDB_CONF_PSYCOPG, autocommit=True) as connection:
        # Open a cursor to perform database operations
        with connection.cursor() as cur:
            if time_frame == TimeFrame.DAILY:
                query_string = db_sql.SQL_SELECT_CLOSE_FROM_DAILY_OHLCV
            else:
                query_string = db_sql.SQL_SELECT_CLOSE_FROM_MINUTE_OHLCV
            cur.execute(query_string, (timestamp,))
            rows = cur.fetchall()

            assert len(rows) == 1

@pytest.mark.db
@pytest.mark.parametrize("time_frame", [TimeFrame.DAILY, TimeFrame.MINUTE])
def test_insert_ohlcv_data_error(setup_test: Callable, setup_questdb: Callable, time_frame: db_access.TimeFrame,
                                 mocker: MockerFixture):
    # Inserts data
    symbol_status = SymbolStatus.ACTIVE
    if time_frame == TimeFrame.DAILY:
        timestamp = datetime.now()
    else:
        timestamp = pd.Timestamp(datetime.now())

    if time_frame == db_access.TimeFrame.DAILY:
        data = {'datetime': [timestamp],
               'exchange_code': [db_const.DUMMY_EXCHANGE_CODE_A],
               'symbol_code': [db_const.DUMMY_SYMBOL_CODE],
               'open': [1.0],
               'high': [1.0],
               'low': [1.0],
               'close': [1.0],
               'adjusted_close': [1.0],
               'volume': [1]}
    else:
        data = {'timestamp': [timestamp],
                'exchange_code': [db_const.DUMMY_EXCHANGE_CODE_A],
                'symbol_code': [db_const.DUMMY_SYMBOL_CODE],
                'gmt_offset': [0],
                'open': [1.0],
                'high': [1.0],
                'low': [1.0],
                'close': [1.0],
                'volume': [1]}
    df_eod = pd.DataFrame(data)

    mocker.patch("db.db_access._WAIT_TIME_IN_SECS_AFTER_DB_ERROR", 1)
    mocker.patch.object(db_access, "Sender", autospec=True)
    mock_function = mocker.patch("db.db_access.Sender.from_conf", side_effect=IngressError("None", "None"))

    with pytest.raises(SystemExit) as pytest_wrapped_error:
        db_access.ohlcv(df_eod, db_const.DUMMY_SYMBOL_CODE, db_const.DUMMY_EXCHANGE_CODE_A, time_frame,
                        symbol_status)
    assert pytest_wrapped_error.type == SystemExit
    assert mock_function.call_count == db_access._MAX_RETRIES_AFTER_DB_CONNECT_ERROR

@pytest.mark.db
@pytest.mark.parametrize("time_frame", [TimeFrame.DAILY, db_access.TimeFrame.MINUTE])
def test_insert_df_into_sqlite_1(setup_test: Callable, setup_and_cleanup_sqlite: Callable,
                                 time_frame: TimeFrame):
    symbol_status = db_access.SymbolStatus.ACTIVE
    # Inserts data
    connection = sqlite3.connect(db_const.SQLITE_DB_PATH)
    data_dict = {"symbol_code": "TestSymbol", "time_frame": time_frame.name,
                 "symbol_status": symbol_status.name, "name": "testo_name", "country": "testo_country",
                 "exchange_code": db_const.DUMMY_EXCHANGE_CODE_A, "currency": "testo_currency", "type": "testo_type",
                 "isin": "testo_isin"}
    df_exchange_symbol = pd.Series(data_dict).to_frame().T
    db_access.insert_df_into_sqlite(df_exchange_symbol, db_const.TABLE_SYMBOL_META)
    time.sleep(0.1)
    # Queries data
    df_symbol_meta = pd.read_sql(db_sql.SQL_SELECT_ALL_FROM_SYMBOL_META_BY_VALUES, con=connection,
                                 params={"symbol_code": "TestSymbol",
                                         "exchange_code": db_const.DUMMY_EXCHANGE_CODE_A, "time_frame": time_frame.name,
                                         "symbol_status": symbol_status.name, "name": "testo_name"})
    assert df_symbol_meta.shape[0] > 0
    assert df_symbol_meta.at[0, "symbol_code"] == "TestSymbol"

    connection.close()

@pytest.mark.db
@pytest.mark.parametrize("time_frame", [db_access.TimeFrame.DAILY, TimeFrame.MINUTE])
def test_insert_df_into_sqlite_2(setup_test: Callable, setup_and_cleanup_sqlite: Callable,
                                 time_frame: TimeFrame):
    # Inserts data
    connection = sqlite3.connect(db_const.SQLITE_DB_PATH)
    data_dict = {db_const.COLUMN_SYMBOL_META_ID: [1, 2], "sector": ["sector_a", "sector_b"],
                 "industry": ["industry_a", "industry_b"], "gic_sector": ["gic_sector_a", "gic_sector_b"],
                 "gic_group": ["gic_group_a", "gic_group_b"], "gic_industry": ["gic_industry_a", "gic_industry_b"],
                 "gic_sub_industry": ["gic_sub_industry_a", "gic_sub_industry_b"]}
    df_exchange_symbol = pd.DataFrame(data_dict)
    db_access.insert_df_into_sqlite(df_exchange_symbol, db_const.TABLE_SYMBOL_SECTOR)
    time.sleep(0.1)
    # Queries data
    df_symbol_meta_1 = pd.read_sql(db_sql.SQL_SELECT_ALL_FROM_SYMBOL_SECTOR, con=connection,
                                   params={"id_symbol_meta": 1})
    assert df_symbol_meta_1.shape[0] == 1
    assert df_symbol_meta_1.at[0, "sector"] == "sector_a"

    df_symbol_meta_2 = pd.read_sql(db_sql.SQL_SELECT_ALL_FROM_SYMBOL_SECTOR, con=connection,
                                   params={"id_symbol_meta": 2})
    assert df_symbol_meta_2.shape[0] == 1
    assert df_symbol_meta_2.at[0, "sector"] == "sector_b"

    connection.close()

@pytest.mark.db
@pytest.mark.parametrize("time_frame", [TimeFrame.DAILY, db_access.TimeFrame.MINUTE])
def test_insert_symbol_meta_data_success(setup_test: Callable, setup_and_cleanup_sqlite: Callable,
                                         time_frame: TimeFrame):
    symbol_status = db_access.SymbolStatus.ACTIVE
    # Inserts data
    connection = sqlite3.connect(db_const.SQLITE_DB_PATH)
    data_dict = {"symbol_code": "TestSymbol", "time_frame": time_frame.name,
                 "symbol_status": symbol_status.name, "name": "testo_name", "country": "testo_country",
                 "exchange_code": db_const.DUMMY_EXCHANGE_CODE_A, "currency": "testo_currency", "type": "testo_type",
                 "isin": "testo_isin"}
    df_exchange_symbol = pd.Series(data_dict).to_frame().T
    fetch.download_insert.insert_symbol_data(df_exchange_symbol, "TestSymbol", db_const.DUMMY_EXCHANGE_CODE_A,
                                             time_frame, symbol_status)
    time.sleep(0.1)
    # Queries data
    df_symbol_meta = pd.read_sql(db_sql.SQL_SELECT_ALL_FROM_SYMBOL_META_BY_VALUES, con=connection,
                                 params={"symbol_code": "TestSymbol",
                                         "exchange_code": db_const.DUMMY_EXCHANGE_CODE_A, "time_frame": time_frame.name,
                                         "symbol_status": symbol_status.name, "name": "testo_name"})
    assert df_symbol_meta.shape[0] > 0
    assert df_symbol_meta.at[0, "symbol_code"] == "TestSymbol"

    connection.close()

@pytest.mark.now
@pytest.mark.parametrize("time_frame", [TimeFrame.DAILY, db_access.TimeFrame.MINUTE])
def test_insert_symbol_meta_data_failed(setup_test: Callable, setup_and_cleanup_sqlite: Callable,
                                        time_frame: TimeFrame):
    symbol_status = db_access.SymbolStatus.ACTIVE
    # Inserts data
    connection = sqlite3.connect(db_const.SQLITE_DB_PATH)
    data_dict = {"symbol_code": "TestSymbol", "time_frame": time_frame.name,
                 "symbol_status": symbol_status.name, "name": "testo_name", "country": "testo_country",
                 "exchange_code": db_const.DUMMY_EXCHANGE_CODE_A, "currency": "testo_currency", "type": "testo_type",
                 "isin": "testo_isin"}
    df_exchange_symbol = pd.Series(data_dict).to_frame().T
    fetch.download_insert.insert_symbol_data(df_exchange_symbol, "TestSymbol", db_const.DUMMY_EXCHANGE_CODE_A,
                                             time_frame, symbol_status)
    time.sleep(0.1)
    # Queries data
    df_symbol_meta = pd.read_sql(db_sql.SQL_SELECT_ALL_FROM_SYMBOL_META_BY_VALUES, con=connection,
                                 params={"symbol_code": "TestSymbol",
                                         "exchange_code": db_const.DUMMY_EXCHANGE_CODE_A, "time_frame": time_frame.name,
                                         "symbol_status": symbol_status.name, "name": "testo_name"})
    assert df_symbol_meta.shape[0] > 0
    assert df_symbol_meta.at[0, "symbol_code"] == "TestSymbol"

    # Inserts data second time
    with pytest.raises(sqlite3.IntegrityError) as pytest_wrapped_error:
        fetch.download_insert.insert_symbol_data(df_exchange_symbol, "TestSymbol", db_const.DUMMY_EXCHANGE_CODE_A,
                                                 time_frame, symbol_status)
    assert pytest_wrapped_error.type == sqlite3.IntegrityError

    connection.close()