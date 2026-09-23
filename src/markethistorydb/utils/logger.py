
"""Logging setup for the CLI

The library itself never configures logging (see markethistorydb/__init__.py); only the CLI
calls start_logger().
"""

from logging.handlers import RotatingFileHandler
from pathlib import Path
import logging
import re
import sys

logger = logging.getLogger(__name__)


# Bool whether to write only to terminal or also to log file
LOG_ONLY_TO_TERMINAL = False
# Name of the log file written to the working directory
LOG_FILE_NAME = "markethistorydb.log"
# Size at which the log file gets rotated, and how many rotations are kept
_MAX_LOG_FILE_SIZE_IN_BYTES = 10 * 2**20
_NUM_OF_LOG_FILE_BACKUPS = 5
# Matches the value of the eodhd.com API token, both in a query string (api_token=...) and in a
# dict repr ('api_token': '...'). requests puts the full URL, token included, into the message
# of e.g. a ConnectionError, so the token can surface in any log line or traceback.
_API_TOKEN_PATTERN = re.compile(r"""(api_token['"]?\s*[=:]\s*['"]?)[^&\s'",)}]+""")
_REDACTED = "***"


class _RedactingFormatter(logging.Formatter):
    """Formatter that masks the API token in the fully formatted record, traceback included"""

    def format(self, record: logging.LogRecord) -> str:
        """
        Formats *record*, then masks every API token in the result.

        :param record: Record to format
        :return: Formatted record with the API token replaced by _REDACTED
        """
        # Redacting the finished string rather than record.msg also covers the args, the
        # traceback and the stack info, which are only added during formatting
        return _API_TOKEN_PATTERN.sub(r"\g<1>" + _REDACTED, super().format(record))


def _build_formatter() -> logging.Formatter:
    """
    Builds the formatter used by every handler.

    :return: Formatter writing timestamp, level and message, with the API token masked
    """
    return _RedactingFormatter(
        fmt="{asctime} - {levelname} - {message}",
        style="{",
        datefmt="%d.%m.%Y-%H:%M:%S",
    )

def _setup_logger(log_only_to_terminal: bool, log_dir: Path, level: int):
    """
    Sets up handlers on the root logger, replacing any this function installed before.

    :param log_only_to_terminal: True writes to stdout only, skipping the rotating log file
    :param log_dir: Directory the log file is written to
    :param level: Level of the root logger
    """
    formatter = _build_formatter()
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if not log_only_to_terminal:
        # Rotating, so that a run over several days cannot fill the disk with one log file
        handlers.append(RotatingFileHandler(
            log_dir / LOG_FILE_NAME,
            maxBytes=_MAX_LOG_FILE_SIZE_IN_BYTES,
            backupCount=_NUM_OF_LOG_FILE_BACKUPS,
            encoding="utf-8",
        ))

    root_logger = logging.getLogger()
    # force=True closes and drops handlers from an earlier call, so calling twice is harmless
    logging.basicConfig(level=level, handlers=handlers, force=True)
    for handler in root_logger.handlers:
        handler.setFormatter(formatter)
    # Warnings (e.g. pandas FutureWarning) belong in the log file too, not only on stderr
    logging.captureWarnings(True)

def start_logger(log_dir: Path | str | None = None, level: int = logging.INFO):
    """
    Sets up logging for the application.

    :param log_dir: Directory the log file is written to (working directory if unset)
    :param level: Level of the root logger
    """
    log_dir = Path(log_dir) if log_dir is not None else Path.cwd()
    _setup_logger(LOG_ONLY_TO_TERMINAL, log_dir, level)
    logger.info("Logger has been set up")
    logger.info("Current working directory: {0}".format(Path.cwd()))
