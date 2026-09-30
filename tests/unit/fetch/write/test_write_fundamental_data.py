"""Tests for fetch/write/write_fundamental_data.py"""

import pandas as pd
import pytest

import markethistorydb.fetch.utils as utils_module
from markethistorydb.db import tables
from markethistorydb.errors import SchemaMismatchError
from markethistorydb.fetch.utils import FundamentalType, TABLE_PER_FUNDAMENTAL_TYPE
from markethistorydb.fetch.write import WriteFundamentalData
from tests.fakes import FakeDb

_SECTOR_AND_INDUSTRY = pd.Series(["Technology", "Consumer Electronics", "Information Technology",
                                  "Hardware", "Peripherals", "Storage"])


def _writer(db: FakeDb) -> WriteFundamentalData:
    writer = WriteFundamentalData(db)
    writer.set_symbol_code("AAPL")
    writer.set_exchange_code("NASDAQ")
    return writer

def _balance_sheet(**overrides) -> pd.DataFrame:
    """
    Builds balance sheet records the way the provider sends them: strings throughout.

    :param overrides: Columns to replace, as camel case name and list of values
    :return: Two quarterly records, columns in camel case
    """
    columns = {"date": ["2024-06-30", "2024-03-31"], "filing_date": ["2024-08-02", "2024-05-03"],
               "currency_symbol": ["USD", "USD"], "totalAssets": ["331612000000.00", None]}
    columns.update(overrides)
    return pd.DataFrame(columns, index=["2024-06-30", "2024-03-31"])


# --- sector --------------------------------------------------------------------------------

def test_a_new_sector_record_is_inserted_with_every_sector_column():
    db = FakeDb(sector=pd.Series(dtype=object))
    _writer(db).update_sector_data(_SECTOR_AND_INDUSTRY)
    series = db.insert.called("sector")[0][0]
    # This used to set a 9-name index on 8 values and fail on every symbol
    assert list(series.index) == list(tables.Sector.ALL_COLUMNS)
    assert series.tolist() == ["AAPL", "NASDAQ"] + _SECTOR_AND_INDUSTRY.tolist()
    assert db.read.called("sector") == [("AAPL", "NASDAQ")]

def test_a_stored_sector_record_is_updated_so_it_is_not_duplicated():
    db = FakeDb(sector=pd.Series(["AAPL"]))
    _writer(db).update_sector_data(_SECTOR_AND_INDUSTRY)
    assert len(db.update.called("sector")) == 1 and db.insert.calls == []


# --- records -------------------------------------------------------------------------------

def test_the_symbol_s_records_are_deleted_before_the_new_ones_are_written():
    db = FakeDb()
    _writer(db).replace_fundamental_data({FundamentalType.BALANCE_SHEET_QUARTERLY: _balance_sheet()})
    table = tables.BalanceSheetQuarterly
    assert db.delete.called("symbol_from_table") == [
        ("AAPL", "NASDAQ", table.NAME, table.TIMESTAMP_COLUMN, table.UNIQUE_KEY_COLUMNS)]
    assert [(name, args[1:]) for name, args, _ in db.delete.calls + db.insert.calls] == [
        ("symbol_from_table", ("NASDAQ", table.NAME, table.TIMESTAMP_COLUMN, table.UNIQUE_KEY_COLUMNS)),
        ("table", (table.NAME, table.TIMESTAMP_COLUMN))]

def test_only_the_tables_of_the_given_types_are_touched():
    db = FakeDb()
    _writer(db).replace_fundamental_data({
        FundamentalType.EARNINGS_ANNUALLY: pd.DataFrame({"date": ["2024-12-31"], "epsActual": [6.1]}),
        FundamentalType.BALANCE_SHEET_QUARTERLY: _balance_sheet()})
    assert [args[1] for args in db.insert.called("table")] == [
        TABLE_PER_FUNDAMENTAL_TYPE[FundamentalType.EARNINGS_ANNUALLY].NAME,
        TABLE_PER_FUNDAMENTAL_TYPE[FundamentalType.BALANCE_SHEET_QUARTERLY].NAME]

def test_the_records_are_written_in_the_types_their_columns_store():
    # The provider sends amounts and dates as strings, which DOUBLE and TIMESTAMP columns reject
    db = FakeDb()
    _writer(db).replace_fundamental_data({FundamentalType.BALANCE_SHEET_QUARTERLY: _balance_sheet()})
    df = db.insert.called("table")[0][0]
    assert list(df.columns) == ["date", "filing_date", "currency_symbol", "total_assets",
                                "symbol_code", "exchange_code"]
    assert str(df["date"].dtype).startswith("datetime64") and str(df["filing_date"].dtype).startswith("datetime64")
    assert df["total_assets"].dtype == "float64"
    assert df["total_assets"].iloc[0] == 331612000000.0 and pd.isna(df["total_assets"].iloc[1])
    assert df["symbol_code"].tolist() == ["AAPL", "AAPL"] and df["currency_symbol"].tolist() == ["USD", "USD"]
    # A fresh index, so that the ingress gets plain, contiguous columns
    assert df.index.tolist() == [0, 1]

@pytest.mark.parametrize("amount", ["n/a", "", None])
def test_an_amount_that_is_no_number_is_stored_as_null(amount):
    db = FakeDb()
    _writer(db).replace_fundamental_data({
        FundamentalType.BALANCE_SHEET_QUARTERLY: _balance_sheet(totalAssets=[amount, "1.0"])})
    df = db.insert.called("table")[0][0]
    assert pd.isna(df["total_assets"].iloc[0]) and df["total_assets"].iloc[1] == 1.0

def test_a_record_without_its_designated_timestamp_is_dropped():
    # QuestDB cannot store a row without its designated timestamp, and would reject the batch
    db = FakeDb()
    _writer(db).replace_fundamental_data({
        FundamentalType.BALANCE_SHEET_QUARTERLY: _balance_sheet(filing_date=["2024-08-02", None])})
    assert len(db.insert.called("table")[0][0]) == 1

def test_the_stored_records_are_kept_when_no_record_has_its_designated_timestamp():
    # Deleting first would replace the symbol's records with nothing
    db = FakeDb()
    _writer(db).replace_fundamental_data({
        FundamentalType.BALANCE_SHEET_QUARTERLY: _balance_sheet(filing_date=[None, None])})
    assert db.delete.calls == [] and db.insert.calls == []

def test_records_from_before_1970_are_dropped_with_a_warning(caplog):
    # The ingress client would refuse the whole batch, after the stored records were deleted
    db = FakeDb()
    with caplog.at_level("WARNING", logger=utils_module.__name__):
        _writer(db).replace_fundamental_data({
            FundamentalType.BALANCE_SHEET_QUARTERLY: _balance_sheet(filing_date=["2024-08-02", "1969-05-03"])})
    assert db.insert.called("table")[0][0]["filing_date"].tolist() == [pd.Timestamp("2024-08-02")]
    assert [record.getMessage() for record in caplog.records] == [
        "Dropped 1 balance_sheet_quarterly records of AAPL.NASDAQ from before 1970, which QuestDB cannot store"]

def test_the_stored_records_are_kept_when_every_record_is_from_before_1970():
    db = FakeDb()
    _writer(db).replace_fundamental_data({
        FundamentalType.BALANCE_SHEET_QUARTERLY: _balance_sheet(filing_date=["1969-08-02", "1969-05-03"])})
    assert db.delete.calls == [] and db.insert.calls == []

def test_a_date_column_other_than_the_designated_timestamp_keeps_a_date_from_before_1970():
    db = FakeDb()
    _writer(db).replace_fundamental_data({
        FundamentalType.BALANCE_SHEET_QUARTERLY: _balance_sheet(date=["1969-06-30", "2024-03-31"])})
    assert db.insert.called("table")[0][0]["date"].tolist() == [pd.Timestamp("1969-06-30"),
                                                                pd.Timestamp("2024-03-31")]

def test_a_column_the_table_does_not_have_fails_before_the_stored_records_are_deleted():
    # The DB would reject the records only after the delete, losing the symbol's stored records
    db = FakeDb()
    with pytest.raises(SchemaMismatchError) as excinfo:
        _writer(db).replace_fundamental_data({
            FundamentalType.BALANCE_SHEET_QUARTERLY: _balance_sheet(newFieldFromProvider=["1.0", "2.0"])})
    assert db.delete.calls == [] and db.insert.calls == []
    assert str(excinfo.value) == ("Table balance_sheet_quarterly has no column(s) new_field_from_provider "
                                  "the records of AAPL.NASDAQ hold")

def test_the_caller_s_records_are_not_modified():
    df_balance_sheet = _balance_sheet()
    df_before = df_balance_sheet.copy()
    _writer(FakeDb()).replace_fundamental_data({FundamentalType.BALANCE_SHEET_QUARTERLY: df_balance_sheet})
    pd.testing.assert_frame_equal(df_balance_sheet, df_before)
