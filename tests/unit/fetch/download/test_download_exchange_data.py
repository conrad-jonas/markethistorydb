"""Tests for fetch/download/download_exchange_data.py"""

import pandas as pd
import pytest

from markethistorydb.errors import NoDataError
from markethistorydb.fetch.download import DownloadExchangeData
from markethistorydb.utils import TimeFrame
from tests.fakes import FakeDb


def _run(db: FakeDb, target_exchange_name: str | None = None) -> pd.Series:
    return DownloadExchangeData(db, "TOKEN", TimeFrame.DAILY, target_exchange_name).run()


def test_every_exchange_of_the_time_frame_is_stored_and_its_code_returned(routed_api):
    db = FakeDb(exchange=pd.Series(dtype=object))
    assert _run(db).tolist() == ["US", "LSE", "FOREX"]
    assert [series["exchange_code"] for series, in db.insert.called("exchange")] == ["US", "LSE", "FOREX"]

def test_only_the_target_exchange_is_kept_when_one_is_named(routed_api):
    db = FakeDb(exchange=pd.Series(dtype=object))
    assert _run(db, "London Exchange").tolist() == ["LSE"]
    assert len(db.insert.called("exchange")) == 1

def test_a_target_exchange_that_is_not_listed_raises_and_writes_nothing(routed_api):
    db = FakeDb(exchange=pd.Series(dtype=object))
    with pytest.raises(NoDataError, match="Moon Exchange"):
        _run(db, "Moon Exchange")
    # apply() on an empty frame used to call the writer once with an empty row
    assert db.read.calls == [] and db.insert.calls == []

def test_an_exchange_already_stored_is_updated_rather_than_inserted_again(routed_api):
    db = FakeDb(exchange=pd.Series(["stored"]))
    _run(db, "USA Stocks")
    assert db.insert.calls == []
    assert [series["exchange_code"] for series, in db.update.called("exchange")] == ["US"]
