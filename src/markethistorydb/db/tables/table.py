from abc import ABC, abstractmethod


class Table(ABC):
    """Abstract data class for tables"""
    @classmethod
    @property
    @abstractmethod
    def NAME(cls):
        """Table name"""
        raise NotImplementedError

    class Columns:
        """Contains columns names as class attributes"""

    @classmethod
    @property
    @abstractmethod
    def TIMESTAMP_COLUMN(cls):
        """Designated timestamp column"""
        raise NotImplementedError

    @classmethod
    @property
    @abstractmethod
    def UNIQUE_KEY_COLUMNS(cls):
        """Columns that form the unique/dedup key"""
        raise NotImplementedError

    @classmethod
    @property
    @abstractmethod
    def ALL_COLUMNS(cls):
        """All columns in definition order"""
        raise NotImplementedError