
"""Setup QuestDB"""

from pathlib import Path
import logging
import psycopg as pg

from markethistorydb.config import Config
from markethistorydb.errors import DbError

logger = logging.getLogger(__name__)


DIRPATH_SCHEMA = Path(__file__).resolve().parent / "schema"
# Schema files to set up, in dependency order
_SCHEMA_FILE_NAMES = ("exchange.sql", "fundamental.sql", "price.sql", "symbol.sql")


def _get_setup_statements(schema_file_name: str) -> str:
    logger.info("Setting up tables from '{0}'".format(schema_file_name))
    filepath_schema = DIRPATH_SCHEMA / schema_file_name
    try:
        with open(filepath_schema, "r") as file:
            return file.read()
    except OSError as error:
        raise DbError("Cannot read schema file '{0}': {1}".format(filepath_schema, error)) from error

def setup(config: Config):
    """
    Sets up QuestDB tables (drops existing ones).

    :param config: Connection settings of the DB to set up
    :raises DbError: If a schema file cannot be read, or the DB rejected a statement
    """
    try:
        with pg.connect(config.psycopg_conninfo, autocommit=True) as connection:
            with connection.cursor() as cur:
                logger.info("Setting up tables")
                for schema_file_name in _SCHEMA_FILE_NAMES:
                    cur.execute(_get_setup_statements(schema_file_name))
    except pg.Error as error:
        raise DbError("Setting up the tables failed: {0}".format(error)) from error
