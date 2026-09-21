from typing import ClassVar


class Table:
    """Abstract data class for tables"""

    #: Name of the table as used in statements.
    NAME: ClassVar[str]

    #: Designated timestamp column QuestDB partitions and orders by.
    TIMESTAMP_COLUMN: ClassVar[str]

    #: Names of the columns that form the unique/dedup key.
    UNIQUE_KEY_COLUMNS: ClassVar[tuple[str, ...]]

    #: Names of every column of the table, in definition order.
    ALL_COLUMNS: ClassVar[tuple[str, ...]]

    #: Class attributes every concrete subclass must define.
    _REQUIRED_CLASS_ATTRS: ClassVar[tuple[str, ...]] = (
        "NAME", "TIMESTAMP_COLUMN", "UNIQUE_KEY_COLUMNS", "ALL_COLUMNS"
    )

    class Columns:
        """Contains columns names as class attributes"""

    def __new__(cls, *args, **kwargs):
        """
        Prevents direct instantiation of :class:`Table` itself.

        :param args: Positional arguments forwarded to the next class in the MRO
        :param kwargs: Keyword arguments forwarded to the next class in the MRO
        :return: New instance of *cls*
        :raises TypeError: If *cls* is :class:`Table` itself rather than a subclass
        """
        if cls is Table:
            raise TypeError("Table is abstract and cannot be instantiated directly")
        return super().__new__(cls, *args, **kwargs)

    def __init_subclass__(cls, **kwargs) -> None:
        """
        Verifies that *cls* defines the required table constants.

        :param kwargs: Additional keyword arguments forwarded to the next
            class in the MRO
        :raises TypeError: If *cls* is missing one of the required class
            attributes
        """
        super().__init_subclass__(**kwargs)
        missing = [name for name in Table._REQUIRED_CLASS_ATTRS if name not in vars(cls)]
        if missing:
            raise TypeError(f"{cls.__name__} must define class attribute(s): {', '.join(missing)}")
