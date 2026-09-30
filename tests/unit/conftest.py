"""Hooks and fixtures for the unit tests, which fake the eodhd.com API and the database"""

from collections.abc import Iterator
from pathlib import Path
import os
import time

import pytest

_DIRPATH_UNIT_TESTS = Path(__file__).resolve().parent
# A zone off UTC all year round, so that reading a UTC datetime as local time always shows
_TIME_ZONE_OFF_UTC = "EST5EDT"


def pytest_collection_modifyitems(items: list[pytest.Item]):
    """
    Marks every test in this directory with the unit marker, so that -m unit selects them.

    :param items: Every collected test of the session
    """
    for item in items:
        if item.path.is_relative_to(_DIRPATH_UNIT_TESTS):
            item.add_marker(pytest.mark.unit)


@pytest.fixture
def local_time_off_utc() -> Iterator[None]:
    """
    Moves the local time zone off UTC, so that a UTC datetime read as local time shifts by
    hours instead of passing unnoticed on a machine that runs in UTC.

    Only POSIX can switch the zone of a running process (time.tzset); elsewhere the test runs in
    the machine's own zone.
    """
    if not hasattr(time, "tzset"):
        yield
        return
    previous = os.environ.get("TZ")
    os.environ["TZ"] = _TIME_ZONE_OFF_UTC
    time.tzset()
    try:
        yield
    finally:
        if previous is None:
            del os.environ["TZ"]
        else:
            os.environ["TZ"] = previous
        time.tzset()
