"""
Fixtures for the live tests, which call the real eodhd.com API.

They run by default; -m "not live" leaves them out, e.g. without network access. Endpoints the
public demo token serves are called with it; the others need EODHD_API_TOKEN (in the environment
or in .env), spending API calls of that account, and are skipped without it, or when eodhd.com
refuses it (rejected, out of calls, or not covering the endpoint).
"""

from pathlib import Path
import os

import pytest
from dotenv import dotenv_values

_DIRPATH_LIVE_TESTS = Path(__file__).resolve().parent
_FILEPATH_DOTENV = _DIRPATH_LIVE_TESTS.parents[1] / ".env"


def pytest_collection_modifyitems(items: list[pytest.Item]):
    """
    Marks every test in this directory with the live marker, so that -m "not live" leaves them
    out.

    :param items: Every collected test of the session
    """
    for item in items:
        if item.path.is_relative_to(_DIRPATH_LIVE_TESTS):
            item.add_marker(pytest.mark.live)


@pytest.fixture(scope="session")
def api_token() -> str:
    """
    Reads the account's API token, for the endpoints the demo token does not serve.

    :return: Value of EODHD_API_TOKEN, from the environment or else from .env
    """
    token = os.environ.get("EODHD_API_TOKEN")
    if not token and _FILEPATH_DOTENV.exists():
        token = dotenv_values(_FILEPATH_DOTENV).get("EODHD_API_TOKEN")
    if not token:
        pytest.skip("EODHD_API_TOKEN is not set")
    return token
