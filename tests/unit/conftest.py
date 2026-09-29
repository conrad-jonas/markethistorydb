"""Hooks for the unit tests, which fake the eodhd.com API and the database"""

from pathlib import Path

import pytest

_DIRPATH_UNIT_TESTS = Path(__file__).resolve().parent


def pytest_collection_modifyitems(items: list[pytest.Item]):
    """
    Marks every test in this directory with the unit marker, so that -m unit selects them.

    :param items: Every collected test of the session
    """
    for item in items:
        if item.path.is_relative_to(_DIRPATH_UNIT_TESTS):
            item.add_marker(pytest.mark.unit)
