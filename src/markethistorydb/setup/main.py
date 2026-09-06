#!/usr/bin/env python12.9

"""Setup QuestDB"""

from pathlib import Path
import logging
import psycopg as pg

from markethistorydb.db     import config
from markethistorydb.utils  import start_logger

logger = logging.getLogger(__name__)


DIRPATH_SCHEMA = Path(__file__).resolve().parent / "schema"
# Schema files to set up, in dependency order
_SCHEMA_FILE_NAMES = ("exchange.sql", "fundamental.sql", "price.sql", "symbol.sql")
# Answers to the "continue?" prompt that are treated as confirmation
_CONFIRMATION_ANSWERS = ("yes", "y")


def _get_setup_statements(schema_file_name: str) -> str:
    logger.info("Setting up tables from '{0}'".format(schema_file_name))
    filepath_schema = DIRPATH_SCHEMA / schema_file_name
    with open(filepath_schema, "r") as file:
        return file.read()

def setup():
    """Sets up QuestDB tables"""
    with pg.connect(config.QUESTDB_CONF_PSYCOPG, autocommit=True) as connection:
        with connection.cursor() as cur:
            logger.info("Setting up tables")
            for schema_file_name in _SCHEMA_FILE_NAMES:
                cur.execute(_get_setup_statements(schema_file_name))

def main():
    """Asks for confirmation, then sets up QuestDB"""
    start_logger()
    # Checks if user wants to proceed
    logger.warning("Do you want to continue? If DB already exist, it will be deleted! (yes/y): ")
    user_input = input("")
    if user_input.lower() in _CONFIRMATION_ANSWERS:
        logger.info("Answer is '{0}', continue setting up DB...".format(user_input.lower()))
        setup()
    else:
        logger.info("Answer is '{0}', exiting...".format(user_input.lower()))

if __name__ == "__main__":
    main()
