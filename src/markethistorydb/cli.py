"""Command line interface: `markethistorydb fetch|setup`"""

import argparse
import logging
import sys

from dotenv import load_dotenv

from markethistorydb.client import Client
from markethistorydb.errors import (AccessRightsError, AccountError, CompatibilityError,
                                    ConfigError, DataLimitError, DbError, ErrorCode, FetchError,
                                    InsertError, MarketHistoryDbError, RequestError, StorageError,
                                    UnauthorizedError, UserInterruptError)
from markethistorydb.utils import SymbolStatus, TimeFrame, start_logger

logger = logging.getLogger(__name__)


# Maps an error to the exit code it leaves the process with. Looked up along the error's MRO,
# so the order of the entries carries no meaning: a subclass always wins over its parent.
_ERROR_EXIT_CODES: dict[type[MarketHistoryDbError], ErrorCode] = {
    UserInterruptError:  ErrorCode.USER_INTERRUPT_ERROR,
    StorageError:        ErrorCode.STORAGE_ERROR,
    ConfigError:         ErrorCode.CONFIG_ERROR,
    UnauthorizedError:   ErrorCode.AUTH_ERROR,
    DataLimitError:      ErrorCode.DATA_LIMIT_ERROR,
    AccessRightsError:   ErrorCode.ACCESS_RIGHTS_ERROR,
    CompatibilityError:  ErrorCode.COMPATIBILITY_ERROR,
    RequestError:        ErrorCode.REQUEST_ERROR,
    FetchError:          ErrorCode.FETCH_ERROR,
    InsertError:         ErrorCode.INSERT_ERROR,
    DbError:             ErrorCode.DB_ERROR,
}

# Answers to the "continue?" prompt that are treated as confirmation
_CONFIRMATION_ANSWERS = ("yes", "y")


def _enum_arg(enum_cls):
    def parse(value: str):
        try:
            return enum_cls[value.upper()]
        except KeyError as error:
            names = ", ".join(member.name.lower() for member in enum_cls)
            raise argparse.ArgumentTypeError(
                "invalid choice '{0}' (choose from {1})".format(value, names)) from error
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


def _exit_code_for(error: MarketHistoryDbError) -> ErrorCode:
    """
    Looks up the exit code *error* should leave the process with.

    :param error: Error the run failed with
    :return: Exit code mapped to the most derived of the error's classes that _ERROR_EXIT_CODES
        knows, else ErrorCode.UNKNOWN_ERROR
    """
    # The MRO is ordered most derived first, so the first hit is the most specific entry
    for error_type in type(error).__mro__:
        if error_type in _ERROR_EXIT_CODES:
            return _ERROR_EXIT_CODES[error_type]
    return ErrorCode.UNKNOWN_ERROR

def _fetch(client, args: argparse.Namespace):
    """
    Runs fetch. Ctrl+C aborts it; main turns the KeyboardInterrupt into an exit code.

    :param client: Client the fetch runs on
    :param args: Parsed `fetch` arguments (time_frame, symbol_status, exchange)
    :raises MarketHistoryDbError: If the fetch failed; main turns it into an exit code
    """
    client.fetch(args.time_frame, args.symbol_status, args.exchange)

def _setup(client):
    """
    Asks for confirmation, then sets up QuestDB.

    :param client: Client the setup runs on
    :raises DbError: If a schema file cannot be read, or the DB rejected a statement
    """
    logger.warning("Do you want to continue? If DB already exist, it will be deleted! (yes/y): ")
    try:
        user_input = input("")
    except EOFError:
        # Nothing on stdin to confirm with; dropping the tables unasked is not an option
        logger.info("No answer given, exiting...")
        return
    if user_input.lower() in _CONFIRMATION_ANSWERS:
        logger.info("Answer is '{0}', continue setting up DB...".format(user_input.lower()))
        client.setup()
    else:
        logger.info("Answer is '{0}', exiting...".format(user_input.lower()))

def _run(args: argparse.Namespace) -> int:
    """
    Builds the client and runs the requested command.

    :param args: Parsed command line arguments
    :return: ErrorCode.SUCCESS, once the command has run without raising
    :raises ConfigError: If the DB or API configuration is missing or unusable
    :raises MarketHistoryDbError: If the command failed; main turns it into an exit code
    """
    load_dotenv()
    client = Client()
    if args.command == "fetch":
        _fetch(client, args)
    elif args.command == "setup":
        _setup(client)
    return ErrorCode.SUCCESS

def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    start_logger()
    try:
        return _run(args)
    except ConfigError as error:
        # A missing token is the user's to fix, so it gets a message rather than a traceback
        logger.error(str(error))
        return _exit_code_for(error)
    except (UserInterruptError, KeyboardInterrupt):
        logger.info("Run was interrupted, exiting...")
        return ErrorCode.USER_INTERRUPT_ERROR
    except AccountError as error:
        # The token or the plan is the user's to fix, so it gets a message rather than a traceback
        logger.error("eodhd.com rejected the account or plan, stopping: {0}".format(error))
        return _exit_code_for(error)
    except MarketHistoryDbError as error:
        logger.exception("Command '{0}' failed".format(args.command))
        return _exit_code_for(error)
    except Exception:
        # A bug or a failure nobody foresaw. Logged here rather than left to the interpreter,
        # so that the traceback lands in the log file too, and with the API token masked
        logger.exception("Command '{0}' failed unexpectedly".format(args.command))
        return ErrorCode.UNKNOWN_ERROR

if __name__ == "__main__":
    sys.exit(main())
