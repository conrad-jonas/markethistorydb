"""
The choice of the QuestDB the integration tests run against: the instance the QUESTDB_TEST_*
variables name, a container started for the session, or none at all.

The choice reads nothing but its arguments, so that its branches are tested with plain values,
without Docker or a database; tests/integration/conftest.py acts on it.
"""

from collections.abc import Mapping
from dataclasses import dataclass

# The QuestDB release the error-message tests were written against; raised deliberately
DEFAULT_IMAGE = "questdb/questdb:10.0.1"
SKIP_MESSAGE = "No test QuestDB: set QUESTDB_TEST_* or install Docker"


@dataclass(frozen=True)
class Override:
    """The throwaway instance the QUESTDB_TEST_* variables name"""
    host: str
    pg_port: int
    http_port: int
    user: str
    password: str


@dataclass(frozen=True)
class Container:
    """A QuestDB container, started for the session and removed after it"""
    image: str


@dataclass(frozen=True)
class Skip:
    """No QuestDB to run against: the integration tests are skipped"""
    message: str


def choose_test_database(environment: Mapping[str, str], docker_available: bool) -> Override | Container | Skip:
    """
    Chooses where the integration tests run. The QUESTDB_TEST_* variables count only when host and
    both ports are set; a partial set is ignored.

    :param environment: Variables of the environment, over those of .env
    :param docker_available: Whether a Docker daemon answers
    :return: The instance the variables name; else a container of QUESTDB_TEST_IMAGE or
        DEFAULT_IMAGE if Docker answers; else a skip naming both ways
    """
    host = environment.get("QUESTDB_TEST_HOST")
    pg_port = environment.get("QUESTDB_TEST_PG_PORT")
    http_port = environment.get("QUESTDB_TEST_HTTP_PORT")
    if host and pg_port and http_port:
        return Override(host=host, pg_port=int(pg_port), http_port=int(http_port),
                        user=environment.get("QUESTDB_TEST_USER", "admin"),
                        password=environment.get("QUESTDB_TEST_PASSWORD", "quest"))
    if docker_available:
        return Container(image=environment.get("QUESTDB_TEST_IMAGE") or DEFAULT_IMAGE)
    return Skip(message=SKIP_MESSAGE)
