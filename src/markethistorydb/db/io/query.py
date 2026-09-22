
"""Runs statements against QuestDB over the PostgreSQL wire protocol"""

from typing import Any

import psycopg as pg
from psycopg import sql

from markethistorydb.config import Config
from markethistorydb.errors import QueryError


class Query:
    def __init__(self, config: Config):
        self._config = config

    def execute(self, query: sql.Composed | sql.SQL, params: list[Any]) -> list[tuple]:
        """
        Executes *query* and returns its records.

        :param query: Statement to run, identifiers already composed
        :param params: Values bound to the statement's placeholders, in order
        :return: The selected records, or an empty list for a statement that returns none
            (UPDATE, DELETE, DDL) - fetching those raises in psycopg, so cursor.description
            decides whether there is a result set to read.
        :raises QueryError: If connecting to the DB or running the statement failed
        """
        try:
            with pg.connect(self._config.psycopg_conninfo, cursor_factory=pg.ClientCursor,
                            autocommit=True) as connection:
                with connection.cursor() as cur:
                    cur.execute(query, tuple(params))
                    rows = cur.fetchall() if cur.description is not None else []
        except pg.Error as error:
            raise QueryError("Query failed: {0}".format(error)) from error
        return rows
