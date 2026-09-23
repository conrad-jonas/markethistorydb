
"""Client: single entry point for setting up the DB, fetching and reading data"""

from typing import Callable
import logging

from markethistorydb.config import Config
from markethistorydb.db     import Database, Read
from markethistorydb.fetch  import Fetcher
from markethistorydb.setup  import setup as _setup
from markethistorydb.utils  import TimeFrame, SymbolStatus

logger = logging.getLogger(__name__)


class Client(object):
    """Holds the configuration and everything derived from it; keeps no per-fetch state"""

    def __init__(self, config: Config | None = None):
        # Without explicit config it is read from the environment (at construction, never at import)
        self.config: Config = config if config is not None else Config.from_env()
        # Internal: full db access including write interface (db.insert)
        self._db: Database = Database(self.config)
        # Public read interface
        self.read: Read = self._db.read

    def setup(self):
        """
        Sets up QuestDB tables (drops existing ones).

        :raises DbError: If a schema file cannot be read, or the DB rejected a statement
        """
        _setup(self.config)

    def fetch(self, time_frame: TimeFrame | None = None, symbol_status: SymbolStatus | None = None,
              exchange: str | None = None, should_stop: Callable[[], bool] | None = None) -> int:
        """
        Fetches data from eodhd.com and inserts it into DB.

        :param time_frame: Time frame of the only pass to run (all if unset)
        :param symbol_status: Symbol status of the only pass to run (all if unset)
        :param exchange: Name of the only exchange to fetch (all if unset)
        :param should_stop: Polled between symbols; returning True aborts with UserInterruptError
        :return: Total number of requested symbols
        :raises AccountError: If the token, the plan's data limit or its access rights are what
            failed; no further pass is attempted
        :raises FetchError: If the provider could not be reached, or too many symbols failed
            in a row
        :raises DbError: If reading from or writing to the DB failed
        :raises StorageError: If free disk space has run out
        :raises UserInterruptError: If *should_stop* returned True
        """
        total_num_of_requested_symbols = 0
        total_num_of_failed_symbols = 0
        for tf in TimeFrame:
            if time_frame and tf != time_frame:
                continue
            for status in SymbolStatus:
                if symbol_status and status != symbol_status:
                    continue
                fetcher = Fetcher(self._db, self.config.eodhd_api_token, tf, status, exchange, should_stop)
                fetcher.run()
                total_num_of_requested_symbols += fetcher.num_of_requested_symbols
                total_num_of_failed_symbols += len(fetcher.failed_symbols)
        logger.info("")
        logger.info("Total number of requested symbols: {0}".format(total_num_of_requested_symbols))
        if total_num_of_failed_symbols:
            logger.warning("Total number of symbols that were skipped after an error: {0}".format(
                total_num_of_failed_symbols))
        return total_num_of_requested_symbols
