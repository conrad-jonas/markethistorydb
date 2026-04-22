#!/usr/bin/env python12.9

"""Helpers for testing"""

import db.db_const as db_const

import ctypes
import os
import pytest
import shutil
import subprocess
import time

from os.path import dirname, abspath

QUESTDB_DIR_TEST_PATH = db_const.QUESTDB_DIR_PATH + "_test"
SQLITE_DB_TEST_PATH = db_const.SQLITE_DB_PATH + "_test"


def _is_admin() -> bool:
    """Checks if user has admin rights

    :return: True if user has admin rights"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def _run_command(command):
    """Runs *command* via cmd.exe

    :param command: Command string to be run via cmd.exe"""
    if _is_admin():
        subprocess.run(["cmd.exe", command], check=True)
    else:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", "cmd.exe", command, None, 0)

def _backup_questdb() -> str:
    """Backs up questdb db

    :return: Dirpath of original QuestDB server
    """
    # Stops db server
    command = f"{db_const.QUESTDB_EXE_PATH} stop"
    _run_command(command)
    # Sets up test db directory
    if os.path.exists(QUESTDB_DIR_TEST_PATH):
        shutil.rmtree(QUESTDB_DIR_TEST_PATH)
    os.mkdir(QUESTDB_DIR_TEST_PATH)
    # Sets up test db server
    command = f'{db_const.QUESTDB_EXE_PATH} install -d "{QUESTDB_DIR_TEST_PATH}'
    _run_command(command)
    # Starts test db server
    command = f'{db_const.QUESTDB_EXE_PATH} start -d "{QUESTDB_DIR_TEST_PATH}'
    _run_command(command)
    original_db_dir_path = str(db_const.QUESTDB_DIR_PATH)
    db_const.QUESTDB_DIR_PATH = QUESTDB_DIR_TEST_PATH
    return original_db_dir_path

def _restore_questdb(original_db_dir_path: str):
    """Restores questdb db

    :param original_db_dir_path: Dirpath of original QuestDB server
    """
    # Stops and removes db server
    command = f'{db_const.QUESTDB_EXE_PATH} stop'
    _run_command(command)
    command = f'{db_const.QUESTDB_EXE_PATH} remove -d "{QUESTDB_DIR_TEST_PATH}'
    _run_command(command)
    # Deletes test db directory
    if os.path.exists(QUESTDB_DIR_TEST_PATH):
        shutil.rmtree(QUESTDB_DIR_TEST_PATH)
    # Restores original db
    db_const.QUESTDB_DIR_PATH = original_db_dir_path
    # Sets up test db server
    command = f'{db_const.QUESTDB_EXE_PATH} install -d "{db_const.QUESTDB_DIR_PATH}'
    _run_command(command)
    # Starts test db server
    command = f'{db_const.QUESTDB_EXE_PATH} start -d "{db_const.QUESTDB_DIR_PATH}'
    _run_command(command)

@pytest.fixture()
def backup_and_restore_questdb():
    """Backs up and restores existing questdb db"""
    original_db_dir_path = _backup_questdb()

    yield

    _restore_questdb(original_db_dir_path)

@pytest.fixture()
def backup_and_restore_sqlite():
    """Backs up and restores existing sqlite db"""
    original_sqlite_db_path = str(db_const.SQLITE_DB_PATH)
    db_const.SQLITE_DB_PATH = SQLITE_DB_TEST_PATH
    if os.path.exists(db_const.SQLITE_DB_PATH):
        os.remove(db_const.SQLITE_DB_PATH)

    yield

    if os.path.exists(db_const.SQLITE_DB_PATH):
        os.remove(db_const.SQLITE_DB_PATH)
    db_const.SQLITE_DB_PATH = str(original_sqlite_db_path)


@pytest.fixture()
def setup_test():
    """Sets up test environment"""
    os.chdir(dirname(dirname(abspath(__file__))))
    yield