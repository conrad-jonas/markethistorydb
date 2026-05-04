#!/usr/bin/env python12.9

"""Setup DB using questdb-8.3.1-rt-windows-x86-64"""

import db.db_const as db_const
import misc.const  as const
import misc.logger as logger

import logging
import os
import psycopg as pg
import sqlite3

# Path to file containing SQL commands to create QuestDB
SETUP_QUESTDB_SCRIPT_PATH = const.WORKING_DIR + "/db/questdb.sql"
# Path to file containing SQL commands to create SQLite DB
SETUP_SQLITE_DB_SCRIPT_PATH = const.WORKING_DIR + "/db/sqlite.sql"


def _create_questdb():
    """Sets up tables, indices, etc. for QuestDB."""

    logging.info("Setup QuestDB")
    # Connect to an existing QuestDB instance
    with pg.connect(db_const.QUESTDB_CONF_PSYCOPG, autocommit=True) as connection:
        # Open a cursor to perform database operations
        with connection.cursor() as cur:
            logging.info("Start setting up tables")
            # Reads sql statements to set up DB
            with open(SETUP_QUESTDB_SCRIPT_PATH, "r") as file:
                sql_commands = file.read()
            # Sets up DB
            cur.execute(sql_commands)
            logging.info("Tables created\n")

def _create_sqlite():
    """Sets up tables, indices, etc. for SQLite."""

    logging.info("Setup SQLite")

    # Connect / Create SQLite DB
    connection = sqlite3.connect(db_const.SQLITE_DB_PATH)
    cursor = connection.cursor()
    with open(SETUP_SQLITE_DB_SCRIPT_PATH, "r") as file:
        sql_commands = file.read()
    logging.info("Start setting up tables")
    cursor.executescript(sql_commands)
    connection.commit()
    logging.info("Tables created")

    connection.close()

def _setup_script():
    """Sets up options and properties for app"""
    # Sets working directory
    os.chdir(const.WORKING_DIR)
    # Sets up logger
    name_of_this_file = os.path.basename(__file__)
    log_filename = "{0}.log".format(name_of_this_file[:-3])
    logger.setup_logger(const.LOG_ONLY_TO_TERMINAL, log_filename)
    logging.info("Start {0}".format(name_of_this_file))
    logging.info("Current working directory: {0}".format(os.getcwd()))

def setup_questdb():
    """Sets up QuestDB"""
    # Sets up logger, etc.
    _setup_script()
    # Creates DB
    _create_questdb()

def setup_sqlite():
    """Sets up SQLite-DB"""
    # Sets up logger, etc.
    _setup_script()
    # Creates DB
    _create_sqlite()

def setup_all():
    """Sets up QuestDB and SQLite-DB"""
    # Sets up logger, etc.
    _setup_script()
    # Checks if user wants to proceed
    logging.warning("Do you want to continue? If DBs already exist, they will be deleted! (yes/y): ")
    user_input = input("")
    if user_input.lower() in ["yes", "y"]:
        logging.info("Answer is '{0}', continue setting up DBs...".format(user_input.lower()))
        _create_questdb()
        _create_sqlite()
    else:
        logging.info("Answer is '{0}', exiting...".format(user_input.lower()))

if __name__ == "__main__":
    setup_all()