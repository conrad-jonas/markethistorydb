
"""Setup QuestDB"""

from pathlib import Path
import logging
import psycopg as pg

from markethistorydb.config import Config

logger = logging.getLogger(__name__)


DIRPATH_SCHEMA = Path(__file__).resolve().parent / "schema"
# Schema files to set up, in dependency order
_SCHEMA_FILE_NAMES = ("exchange.sql", "fundamental.sql", "price.sql", "symbol.sql")


def _get_setup_statements(schema_file_name: str) -> str:
    logger.info("Setting up tables from '{0}'".format(schema_file_name))
    filepath_schema = DIRPATH_SCHEMA / schema_file_name
    with open(filepath_schema, "r") as file:
        return file.read()

def setup(config: Config):
    """Sets up QuestDB tables (drops existing ones)"""
    with pg.connect(config.psycopg_conninfo, autocommit=True) as connection:
        with connection.cursor() as cur:
            logger.info("Setting up tables")
            for schema_file_name in _SCHEMA_FILE_NAMES:
                cur.execute(_get_setup_statements(schema_file_name))
