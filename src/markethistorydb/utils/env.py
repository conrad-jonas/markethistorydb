
"""Loads .env file and provides access to required environment variables"""

import os

from dotenv import load_dotenv

load_dotenv()


def require_env(name: str) -> str:
    """Returns value of required environment variable *name* or raises if unset"""
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            "Required environment variable '{0}' is not set (see .env.example)".format(name))
    return value
