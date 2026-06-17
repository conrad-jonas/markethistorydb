#!/usr/bin/env python12.9

"""Setup QuestDB"""

from pathlib import Path
import logging
import psycopg as pg

from db     import config
from setup  import schema
from utils  import start_logger


DIRPATH_SCHEMA = Path(schema.__file__).resolve()
FILEPATH_EXCHANGE_SCHEMA    = Path.home().joinpath(DIRPATH_SCHEMA, "exchange.sql")
FILEPATH_FUNDAMENTAL_SCHEMA = Path.home().joinpath(DIRPATH_SCHEMA, "fundamental.sql")
FILEPATH_PRICE_SCHEMA       = Path.home().joinpath(DIRPATH_SCHEMA, "price.sql")
FILEPATH_SYMBOL_SCHEMA      = Path.home().joinpath(DIRPATH_SCHEMA, "symbol.sql")


def _get_exchange_setup_statements() -> str:
    logging.info("Setting up exchange tables")
    with open(FILEPATH_EXCHANGE_SCHEMA, "r") as file:
        return file.read()

def _get_fundamental_setup_statements() -> str:
    logging.info("Setting up fundamental tables")
    with open(FILEPATH_FUNDAMENTAL_SCHEMA, "r") as file:
        return file.read()

def _get_price_setup_statements() -> str:
    logging.info("Setting up price tables")
    with open(FILEPATH_PRICE_SCHEMA, "r") as file:
        return file.read()

def _get_symbol_setup_statements() -> str:
    logging.info("Setting up symbol tables")
    with open(FILEPATH_SYMBOL_SCHEMA, "r") as file:
        return file.read()

def _setup_tables():
    with pg.connect(config.QUESTDB_CONF_PSYCOPG, autocommit=True) as connection:
        with connection.cursor() as cur:
            logging.info("Setting up tables")
            cur.execute(_get_exchange_setup_statements())
            cur.execute(_get_fundamental_setup_statements())
            cur.execute(_get_price_setup_statements())
            cur.execute(_get_symbol_setup_statements())

def setup():
    """Sets up QuestDB"""
    start_logger()
    # Sets up db
    _setup_tables()

if __name__ == "__main__":
    start_logger()
    # Checks if user wants to proceed
    logging.warning("Do you want to continue? If DB already exist, it will be deleted! (yes/y): ")
    user_input = input("")
    if user_input.lower() in ["yes", "y"]:
        logging.info("Answer is '{0}', continue setting up DB...".format(user_input.lower()))
        _setup_tables()
    else:
        logging.info("Answer is '{0}', exiting...".format(user_input.lower()))