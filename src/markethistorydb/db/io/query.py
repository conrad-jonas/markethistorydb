from typing import Any

import psycopg as pg
from psycopg import sql

from markethistorydb.config import Config


class Query:
    def __init__(self, config: Config):
        self._config = config

    def execute(self, query: sql.Composed | sql.SQL, params: list[Any]) -> list[tuple]:
        with pg.connect(self._config.psycopg_conninfo, cursor_factory=pg.ClientCursor, autocommit=True) as connection:
            with connection.cursor() as cur:
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
                cur.close()
        return rows
