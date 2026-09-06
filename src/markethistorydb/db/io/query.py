from typing import Any

import psycopg as pg
from psycopg import sql

from markethistorydb.db.config import QUESTDB_CONF_PSYCOPG


class Query:
    @staticmethod
    def execute(query: sql.Composed | sql.SQL, params: list[Any]) -> list[tuple]:
        with pg.connect(QUESTDB_CONF_PSYCOPG, cursor_factory=pg.ClientCursor, autocommit=True) as connection:
            with connection.cursor() as cur:
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
                cur.close()
        return rows
