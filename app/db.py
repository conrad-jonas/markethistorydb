#!/usr/bin/env python12.9

"""Setup DB using questdb-8.3.1-rt-windows-x86-64"""

import logger

import logging
import os
import psycopg as pg
import sqlite3

from os.path import dirname, abspath

# Bool whether to write only to terminal or also to log file
LOG_ONLY_TO_TERMINAL = False
# Working directory
WORKING_DIR = dirname(dirname(abspath(__file__)))
# SQLite DB path
SQLITE_DB_PATH = WORKING_DIR + "/db/sqlite.db"
# Path to file containing SQL commands to create QuestDB
SETUP_QUESTDB_SCRIPT_PATH = WORKING_DIR + "/db/questdb.sql"
# Path to file containing SQL commands to create SQLite DB
SETUP_SQLITE_DB_SCRIPT_PATH = WORKING_DIR + "/db/sqlite.sql"

# QuestDB password
QUESTDB_PASSWORD = "quest"
# Config string PostgreSQL
QUESTDB_CONF_PSYCOPG = "user=admin password={0} host=127.0.0.1 port=8812 dbname=qdb".format(QUESTDB_PASSWORD)

# EOD meta data table name
DB_TABLE_NAME_SYMBOL_META = "symbol_meta"
# EOD OHLCV table name
DB_TABLE_NAME_EOD_PRICE = "daily_ohlcv"
# Intraday OHLCV table name
DB_TABLE_NAME_MINUTE_PRICE = "minute_ohlcv"
# Dummy symbol and exchange
DUMMY_SYMBOL_CODE   = "DUMMY_SYMBOL"
DUMMY_EXCHANGE_CODE = "DUMMY_EXCHANGE"

def setup_questdb():
    """Sets up tables, indices, etc. for QuestDB."""

    logging.info("Setup QuestDB")
    # Connect to an existing QuestDB instance
    with pg.connect(QUESTDB_CONF_PSYCOPG, autocommit=True) as connection:
        # Open a cursor to perform database operations
        with connection.cursor() as cur:
            logging.info("Start setting up tables")
            # Reads sql statements to set up DB
            with open(SETUP_QUESTDB_SCRIPT_PATH, "r") as file:
                sql_commands = file.read()
            # Sets up DB
            cur.execute(sql_commands)
            logging.info("Tables created\n")

def setup_sqlite():
    """Sets up tables, indices, etc. for SQLite."""

    logging.info("Setup SQLite")

    # Connect / Create SQLite DB
    connection = sqlite3.connect(SQLITE_DB_PATH)
    cursor = connection.cursor()
    with open(SETUP_SQLITE_DB_SCRIPT_PATH, "r") as file:
        sql_commands = file.read()
    logging.info("Start setting up tables")
    cursor.executescript(sql_commands)
    connection.commit()
    logging.info("Tables created")

    connection.close()

def setup_script():
    """Sets up options and properties for app"""
    # Sets working directory
    os.chdir(WORKING_DIR)
    # Sets up logger
    name_of_this_file = os.path.basename(__file__)
    log_filename = "{0}.log".format(name_of_this_file[:-3])
    logger.setup_logger(LOG_ONLY_TO_TERMINAL, log_filename)
    logging.info("Start {0}".format(name_of_this_file))
    logging.info("Current working directory: {0}".format(os.getcwd()))

if __name__ == "__main__":
    # Sets up logger, etc.
    setup_script()
    # Checks if user wants to proceed
    logging.warning("Do you want to continue? If DBs already exist, they will be deleted! (yes/y): ")
    user_input = input("")
    if user_input.lower() in ["yes", "y"]:
        logging.info("Answer is '{0}', continue setting up DBs...".format(user_input.lower()))
        #setup_questdb()
        #setup_sqlite()
    else:
        logging.info("Answer is '{0}', exiting...".format(user_input.lower()))