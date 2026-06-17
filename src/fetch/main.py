#!/usr/bin/env python12.9

"""Requests trading data from eodhd.com and inserts it into DB"""

import logging
import sys

from fetch.fetcher    import Fetcher
from fetch.errors     import ErrorCode, StorageError, UserInterruptError, RequestError, InsertError
from utils.categories import TimeFrame, SymbolStatus
from utils            import start_logger


def _print_metrics(total_num_of_requested_symbols: int):
    logging.info("")
    logging.info("Total number of requested symbols: {0}".format(total_num_of_requested_symbols))

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

if __name__ == "__main__":
    start_logger()
    try:
        fetch()
    except StorageError:
        logging.error("StorageError", exc_info=True)
        sys.exit(ErrorCode.STORAGE_ERROR)
    except UserInterruptError:
        logging.error("UserInterruptError", exc_info=True)
        sys.exit(ErrorCode.USER_INTERRUPT_ERROR)
    except RequestError:
        logging.error("RequestError", exc_info=True)
        sys.exit(ErrorCode.REQUEST_ERROR)
    except InsertError:
        logging.error("InsertError", exc_info=True)
        sys.exit(ErrorCode.QUESTDB_INGRESS_ERROR)