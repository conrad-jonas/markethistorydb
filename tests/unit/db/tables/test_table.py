"""Tests for db/tables/table.py: the abstract base of every table's constants"""

import pytest

from markethistorydb.db.tables import Table, TimeSeriesTable, FundamentalTable


@pytest.mark.parametrize("base", [Table, TimeSeriesTable, FundamentalTable])
def test_an_abstract_base_cannot_be_instantiated(base):
    with pytest.raises(TypeError):
        base()

def test_an_abstract_base_need_not_define_the_constants():
    class Base(Table, abstract=True):
        pass

    class Complete(Base):
        NAME = "complete"
        TIMESTAMP_COLUMN = "ts"
        UNIQUE_KEY_COLUMNS = ("ts",)
        ALL_COLUMNS = ("ts",)

    assert isinstance(Complete(), Base)

def test_a_table_derived_from_an_abstract_base_must_define_the_constants():
    with pytest.raises(TypeError) as excinfo:
        class Incomplete(TimeSeriesTable):
            NAME = "incomplete"
    assert "TIMESTAMP_COLUMN, UNIQUE_KEY_COLUMNS, ALL_COLUMNS" in str(excinfo.value)

def test_a_complete_subclass_can_be_instantiated():
    class Complete(Table):
        NAME = "complete"
        TIMESTAMP_COLUMN = "ts"
        UNIQUE_KEY_COLUMNS = ("ts",)
        ALL_COLUMNS = ("ts",)

    assert isinstance(Complete(), Table)

def test_a_subclass_missing_constants_is_rejected_when_defined():
    with pytest.raises(TypeError) as excinfo:
        class Incomplete(Table):
            NAME = "incomplete"
    assert "TIMESTAMP_COLUMN, UNIQUE_KEY_COLUMNS, ALL_COLUMNS" in str(excinfo.value)

def test_inherited_constants_do_not_count_as_defined():
    # Each table must state its own constants, so a copy-pasted subclass cannot silently
    # write to its parent's table
    class Parent(Table):
        NAME = "parent"
        TIMESTAMP_COLUMN = "ts"
        UNIQUE_KEY_COLUMNS = ("ts",)
        ALL_COLUMNS = ("ts",)

    with pytest.raises(TypeError):
        class Child(Parent):
            pass
