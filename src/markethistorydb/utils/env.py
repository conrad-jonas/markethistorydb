
"""Provides access to required environment variables"""

import os

from markethistorydb.errors import ConfigError


def require_env(name: str) -> str:
    """
    Reads required environment variable *name*, raising if it is unset.

    :param name: Name of the environment variable
    :return: Value of the variable
    :raises ConfigError: If the variable is unset or empty
    """
    value = os.environ.get(name)
    if not value:
        raise ConfigError(
            "Required environment variable '{0}' is not set (see .env.example)".format(name))
    return value
