#!/usr/bin/env python12.9

"""Setup DB using questdb-8.3.1-rt-windows-x86-64"""

import app.logger as logger

import logging
import os
import psycopg as pg
import sqlite3

from os.path import dirname, abspath

# Bool whether to write only to terminal or also to log file
LOG_ONLY_TO_TERMINAL = False
# Working directory
WORKING_DIR = dirname(dirname(abspath(__file__)))

# QuestDB password
DB_PASSWORD = 'quest'
# Config string PostgreSQL
CONF_PSYCOPG = 'user=admin password={0} host=127.0.0.1 port=8812 dbname=qdb'.format(DB_PASSWORD)

def setup_questdb():
    """Sets up tables, indices, etc. for QuestDB."""

    logging.info("Setup QuestDB")
    # Connect to an existing QuestDB instance
    with pg.connect(CONF_PSYCOPG, autocommit=True) as connection:
        # Open a cursor to perform database operations
        with connection.cursor() as cur:
            logging.info('Start setting up tables')
            # Reads sql statements to set up DB
            with open(os.getcwd() + '/db/questdb.sql', 'r') as file:
                sql_commands = file.read()
            # Sets up DB
            cur.execute(sql_commands)
            logging.info('Tables created\n')

def setup_sqlite():
    """Sets up tables, indices, etc. for SQLite."""

    logging.info("Setup SQLite")

    # Connect / Create SQLite DB
    connection = sqlite3.connect(os.getcwd() +  "/db/sqlite.db")
    cursor = connection.cursor()
    with open(os.getcwd() + '/db/sqlite.sql', 'r') as file:
        sql_commands = file.read()
    logging.info('Start setting up tables')
    cursor.executescript(sql_commands)
    connection.commit()
    logging.info('Tables created')

    logging.info("Inserts test data\n")
    cursor.execute("""INSERT INTO symbol_meta (code, time_frame, symbol_status, name, country, exchange, currency, 
                      type, isin) VALUES("test_code", "DAILY", "ACTIVE", "test_name", "test_country", 
                      "test_exchange", "test_currency", "test_type", "test_isin")""")
    connection.commit()
    """df = pd.read_sql("SELECT * FROM symbol_meta", connection)
    df.at[0, "code"] = "Yes"
    df.at[1, "code"] = "No"
    df.to_sql("symbol_meta", connection, if_exists="append", index=False)
    connection.commit()
    df = pd.read_sql_query("SELECT * FROM symbol_meta", connection)"""
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

if __name__ == '__main__':
    setup_script()
    setup_questdb()
    setup_sqlite()