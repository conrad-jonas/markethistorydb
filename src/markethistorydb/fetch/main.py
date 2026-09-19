#!/usr/bin/env python12.9

"""Requests trading data from eodhd.com and inserts it into DB"""

from typing import Callable
import logging
import sys
import threading

from markethistorydb.config           import Config
from markethistorydb.db               import Database
from markethistorydb.fetch.fetcher    import Fetcher
from markethistorydb.fetch.errors     import ErrorCode, StorageError, UserInterruptError, RequestError, InsertError
from markethistorydb.utils.categories import TimeFrame, SymbolStatus
from markethistorydb.utils            import start_logger

logger = logging.getLogger(__name__)


def _print_metrics(total_num_of_requested_symbols: int):
    logger.info("")
    logger.info("Total number of requested symbols: {0}".format(total_num_of_requested_symbols))

def _start_f4_listener() -> Callable[[], bool]:
    """Starts keyboard listener; returns callable telling whether F4 has been pressed"""
    from pynput import keyboard
    pressed = threading.Event()

    def on_press(key):
        if key == keyboard.Key.f4:
            pressed.set()

    keyboard.Listener(on_press=on_press).start()
    return pressed.is_set

def fetch(config: Config, target_time_frame: TimeFrame = None, target_symbol_status: SymbolStatus = None,
          target_exchange_name: str = None, should_stop: Callable[[], bool] | None = None):
    """Fetches data from eodhd.com and inserts it into DB."""
    db = Database(config)
    total_num_of_requested_symbols = 0
    for time_frame in TimeFrame:
        if target_time_frame and time_frame != target_time_frame:
            continue
        for symbol_status in SymbolStatus:
            if target_symbol_status and symbol_status != target_symbol_status:
                continue
            fetcher = Fetcher(db, config.eodhd_api_token, time_frame, symbol_status, target_exchange_name,
                              should_stop)
            fetcher.run()
            total_num_of_requested_symbols += fetcher.num_of_requested_symbols
    _print_metrics(total_num_of_requested_symbols)
    return True

def main(target_time_frame: TimeFrame = None, target_symbol_status: SymbolStatus = None,
         target_exchange_name: str = None):
    """Runs fetch() and maps errors to process exit codes."""
    start_logger()
    try:
        fetch(Config.from_env(), target_time_frame, target_symbol_status, target_exchange_name,
              should_stop=_start_f4_listener())
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
