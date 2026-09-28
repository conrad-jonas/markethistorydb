from typing import ClassVar


class Table:
    """Abstract data class for tables"""

    #: Name of the table as used in statements.
    NAME: ClassVar[str]

    # TIMESTAMP_COLUMN is required as well, but not declared here: a declaration fixes its type
    # for every subclass, and it is a str for a :class:`TimeSeriesTable` but None for the lookup
    # tables.

    #: Names of the columns that form the unique/dedup key.
    UNIQUE_KEY_COLUMNS: ClassVar[tuple[str, ...]]

    #: Names of every column of the table, in definition order.
    ALL_COLUMNS: ClassVar[tuple[str, ...]]

    #: Class attributes every concrete subclass must define.
    _REQUIRED_CLASS_ATTRS: ClassVar[tuple[str, ...]] = (
        "NAME", "TIMESTAMP_COLUMN", "UNIQUE_KEY_COLUMNS", "ALL_COLUMNS"
    )

    #: Whether the class is a base for other tables rather than a table itself.
    _ABSTRACT: ClassVar[bool] = True

    class Columns:
        """Contains columns names as class attributes"""

    def __new__(cls, *args, **kwargs):
        """
        Prevents direct instantiation of :class:`Table` and the other abstract bases.

        :param args: Positional arguments forwarded to the next class in the MRO
        :param kwargs: Keyword arguments forwarded to the next class in the MRO
        :return: New instance of *cls*
        :raises TypeError: If *cls* is an abstract base rather than a concrete table
        """
        if cls._ABSTRACT:
            raise TypeError(f"{cls.__name__} is abstract and cannot be instantiated directly")
        return super().__new__(cls, *args, **kwargs)

    def __init_subclass__(cls, abstract: bool = False, **kwargs) -> None:
        """
        Verifies that *cls* defines the required table constants, unless *cls* is an abstract
        intermediate base such as :class:`TimeSeriesTable`.

        :param abstract: Whether *cls* is a base for other tables rather than a table itself
        :param kwargs: Additional keyword arguments forwarded to the next
            class in the MRO
        :raises TypeError: If *cls* is missing one of the required class
            attributes
        """
        super().__init_subclass__(**kwargs)
        cls._ABSTRACT = abstract
        if abstract:
            return
        missing = [name for name in Table._REQUIRED_CLASS_ATTRS if name not in vars(cls)]
        if missing:
            raise TypeError(f"{cls.__name__} must define class attribute(s): {', '.join(missing)}")


class TimeSeriesTable(Table, abstract=True):
    """Abstract base for the tables with a designated timestamp, the ones written through ILP"""

    #: Designated timestamp column QuestDB partitions and orders by.
    TIMESTAMP_COLUMN: ClassVar[str]
