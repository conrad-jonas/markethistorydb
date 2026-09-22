"""Command line interface: `markethistorydb fetch|setup`"""

from typing import Callable
import argparse
import logging
import sys
import threading

from markethistorydb.utils import SymbolStatus, TimeFrame

logger = logging.getLogger(__name__)


def _enum_arg(enum_cls):
    def parse(value: str):
        try:
            return enum_cls[value.upper()]
        except KeyError:
            names = ", ".join(member.name.lower() for member in enum_cls)
            raise argparse.ArgumentTypeError("invalid choice '{0}' (choose from {1})".format(value, names))
    return parse

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="markethistorydb", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser("fetch", help="fetch data from eodhd.com and insert it into the DB")
    fetch_parser.add_argument("--time-frame", type=_enum_arg(TimeFrame), default=None)
    fetch_parser.add_argument("--symbol-status", type=_enum_arg(SymbolStatus), default=None)
    fetch_parser.add_argument("--exchange", default=None, help="restrict fetching to one exchange name")

    subparsers.add_parser("setup", help="set up the QuestDB tables (asks for confirmation)")
    return parser

# Answers to the "continue?" prompt that are treated as confirmation
_CONFIRMATION_ANSWERS = ("yes", "y")


def _start_f4_listener() -> Callable[[], bool]:
    """Starts keyboard listener; returns callable telling whether F4 has been pressed"""
    from pynput import keyboard
    pressed = threading.Event()

    def on_press(key):
        if key == keyboard.Key.f4:
            pressed.set()

    keyboard.Listener(on_press=on_press).start()
    return pressed.is_set

def _fetch(client, args: argparse.Namespace):
    """Runs fetch and maps errors to process exit codes"""
    from markethistorydb.errors import ErrorCode, StorageError, UserInterruptError, RequestError, InsertError
    try:
        client.fetch(args.time_frame, args.symbol_status, args.exchange, should_stop=_start_f4_listener())
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
        sys.exit(ErrorCode.INSERT_ERROR)

def _setup(client):
    """Asks for confirmation, then sets up QuestDB"""
    logger.warning("Do you want to continue? If DB already exist, it will be deleted! (yes/y): ")
    user_input = input("")
    if user_input.lower() in _CONFIRMATION_ANSWERS:
        logger.info("Answer is '{0}', continue setting up DB...".format(user_input.lower()))
        client.setup()
    else:
        logger.info("Answer is '{0}', exiting...".format(user_input.lower()))

def main(argv: list[str] | None = None):
    args = _build_parser().parse_args(argv)
    # Imported lazily so that `--help` works without DB/API configuration
    from dotenv import load_dotenv
    from markethistorydb.client import Client
    from markethistorydb.utils  import start_logger
    load_dotenv()
    start_logger()
    client = Client()
    if args.command == "fetch":
        _fetch(client, args)
    elif args.command == "setup":
        _setup(client)

if __name__ == "__main__":
    main()
