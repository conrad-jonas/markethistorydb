"""Tests for db/io/update.py: every value lands on the placeholder of its own column"""

import re
import pandas as pd
import pytest

from markethistorydb.db import tables
from markethistorydb.db.io.update import Update
from tests.fakes import RecordingQuery


def _assignments(text: str, params: list) -> dict[str, object]:
    """
    Pairs every "column=%s" of a rendered statement with the value bound to it.

    :param text: Statement text with %s placeholders
    :param params: Values bound to the placeholders, in order
    :return: Value bound to each column, SET and WHERE columns alike
    """
    columns = re.findall(r"(\w+)=%s", text)
    assert len(columns) == len(params) == text.count("%s")
    return dict(zip(columns, params))


def _record(columns) -> pd.Series:
    # Every value names its own column, so a swapped pair shows up in the assertion
    return pd.Series({column: "value of {0}".format(column) for column in columns})


@pytest.mark.parametrize("method, table, key_columns", [
    ("exchange", tables.Exchange, (tables.Exchange.Columns.EXCHANGE_CODE,)),
    ("symbol", tables.Symbol, tables.Symbol.UNIQUE_KEY_COLUMNS),
    ("sector", tables.Sector, tables.Sector.UNIQUE_KEY_COLUMNS),
])
def test_every_value_is_bound_to_its_own_column(method, table, key_columns):
    query = RecordingQuery()
    getattr(Update(query), method)(_record(table.ALL_COLUMNS))
    text, params = query.statements[0]
    assert text.startswith("UPDATE {0} SET".format(table.NAME))
    assignments = _assignments(text, params)
    assert all(value == "value of {0}".format(column) for column, value in assignments.items())
    # The record is found by its whole unique key, so no other record is overwritten
    where = text.split(" WHERE ")[1]
    assert set(re.findall(r"(\w+)=%s", where)) == set(key_columns)
