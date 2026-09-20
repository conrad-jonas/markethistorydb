
"""Configuration for DB connection and data provider"""

from dataclasses import dataclass, field
import os

from markethistorydb.utils import require_env


@dataclass(frozen=True)
class Config:
    """Connection settings; secrets are excluded from repr"""
    # API token for eodhd.com
    eodhd_api_token:  str = field(repr=False)
    # QuestDB password
    questdb_password: str = field(repr=False)
    questdb_host:     str = "127.0.0.1"
    questdb_pg_port:  int = 8812
    questdb_http_port: int = 9000
    questdb_user:     str = "admin"
    questdb_db_name:  str = "qdb"

    @property
    def psycopg_conninfo(self) -> str:
        """Config string PostgreSQL"""
        return "user={0} password={1} host={2} port={3} dbname={4}".format(
            self.questdb_user, self.questdb_password, self.questdb_host, self.questdb_pg_port, self.questdb_db_name)

    @property
    def http_conf(self) -> str:
        """Config string http"""
        return "http::addr={0}:{1};username={2};password={3};".format(
            self.questdb_host, self.questdb_http_port, self.questdb_user, self.questdb_password)

    @classmethod
    def from_env(cls) -> "Config":
        """Reads config from environment variables (see .env.example)"""
        return cls(
            eodhd_api_token=require_env("EODHD_API_TOKEN"),
            questdb_password=require_env("QUESTDB_PASSWORD"),
            questdb_host=os.environ.get("QUESTDB_HOST", cls.questdb_host),
            questdb_pg_port=int(os.environ.get("QUESTDB_PG_PORT", cls.questdb_pg_port)),
            questdb_http_port=int(os.environ.get("QUESTDB_HTTP_PORT", cls.questdb_http_port)),
            questdb_user=os.environ.get("QUESTDB_USER", cls.questdb_user),
            questdb_db_name=os.environ.get("QUESTDB_DB_NAME", cls.questdb_db_name),
        )
