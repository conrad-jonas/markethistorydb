
"""Configuration for DB connection and data provider"""

from dataclasses import dataclass, field
import os

from markethistorydb.errors import ConfigError
from markethistorydb.utils  import require_env


# Seconds to wait for the DB connection to be established; without it an unreachable host is
# only noticed after psycopg's own, much longer, timeout
_CONNECT_TIMEOUT_IN_SECS = 10


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
        """
        Builds the config string for PostgreSQL.

        :return: psycopg connection string, connect timeout included
        """
        return "user={0} password={1} host={2} port={3} dbname={4} connect_timeout={5}".format(
            self.questdb_user, self.questdb_password, self.questdb_host, self.questdb_pg_port,
            self.questdb_db_name, _CONNECT_TIMEOUT_IN_SECS)

    @property
    def http_conf(self) -> str:
        """
        Builds the config string for http.

        :return: QuestDB ingress connection string
        """
        return "http::addr={0}:{1};username={2};password={3};".format(
            self.questdb_host, self.questdb_http_port, self.questdb_user, self.questdb_password)

    @staticmethod
    def _env_as_int(name: str, default: int) -> int:
        """
        Reads environment variable *name* as int, if it does not exist *name* is logged.

        :param name: Name of the environment variable
        :param default: Value returned when the variable is unset
        :return: Value of the variable as int, or *default*
        :raises ConfigError: If the variable is set to something that is not an int
        """
        value = os.environ.get(name)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError as error:
            raise ConfigError(
                "Environment variable '{0}' must be an integer, got '{1}' instead".format(
                    name, value)) from error

    @classmethod
    def from_env(cls) -> "Config":
        """
        Reads config from environment variables (see .env.example).

        :return: Config filled from the environment, defaults applied where a variable is unset
        :raises ConfigError: If a required variable is unset, or a port is not an int
        """
        return cls(
            eodhd_api_token=require_env("EODHD_API_TOKEN"),
            questdb_password=require_env("QUESTDB_PASSWORD"),
            questdb_host=os.environ.get("QUESTDB_HOST", cls.questdb_host),
            questdb_pg_port=cls._env_as_int("QUESTDB_PG_PORT", cls.questdb_pg_port),
            questdb_http_port=cls._env_as_int("QUESTDB_HTTP_PORT", cls.questdb_http_port),
            questdb_user=os.environ.get("QUESTDB_USER", cls.questdb_user),
            questdb_db_name=os.environ.get("QUESTDB_DB_NAME", cls.questdb_db_name),
        )
