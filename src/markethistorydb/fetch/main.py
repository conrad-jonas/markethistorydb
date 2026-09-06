#!/usr/bin/env python12.9

"""Requests trading data from eodhd.com and inserts it into DB"""

import logging
import sys

from markethistorydb.fetch.fetcher    import Fetcher
from markethistorydb.fetch.errors     import ErrorCode, StorageError, UserInterruptError, RequestError, InsertError
from markethistorydb.utils.categories import TimeFrame, SymbolStatus
from markethistorydb.utils            import start_logger

logger = logging.getLogger(__name__)


def _print_metrics(total_num_of_requested_symbols: int):
    logger.info("")
    logger.info("Total number of requested symbols: {0}".format(total_num_of_requested_symbols))

def fetch(target_time_frame: TimeFrame = None, target_symbol_status: SymbolStatus = None,
          target_exchange_name: str = None):
    """Fetches data from eodhd.com and inserts it into DB."""
    total_num_of_requested_symbols = 0
    for time_frame in TimeFrame:
        if target_time_frame and time_frame != target_time_frame:
            continue
        for symbol_status in SymbolStatus:
            if target_symbol_status and symbol_status != target_symbol_status:
                continue
            fetcher = Fetcher(time_frame, symbol_status, target_exchange_name)
            fetcher.run()
            total_num_of_requested_symbols += fetcher.num_of_requested_symbols
    _print_metrics(total_num_of_requested_symbols)
    return True

def main(target_time_frame: TimeFrame = None, target_symbol_status: SymbolStatus = None,
         target_exchange_name: str = None):
    """Runs fetch() and maps errors to process exit codes."""
    start_logger()
    try:
        fetch(target_time_frame, target_symbol_status, target_exchange_name)
    except StorageError:
        logger.error("StorageError", exc_info=True)
        sys.exit(ErrorCode.STORAGE_ERROR)
    except UserInterruptError:
        logger.error("UserInterruptError", exc_info=True)
        sys.exit(ErrorCode.USER_INTERRUPT_ERROR)
    except RequestError:
        logger.error("RequestError", exc_info=True)
        sys.exit(ErrorCode.REQUEST_ERROR)
    except InsertError:
        logger.error("InsertError", exc_info=True)
        sys.exit(ErrorCode.QUESTDB_INGRESS_ERROR)

if __name__ == "__main__":
    main()
