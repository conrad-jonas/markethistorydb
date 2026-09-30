"""Tests for utils/logger.py"""

from logging.handlers import RotatingFileHandler
from pathlib import Path
import logging
import sys
import warnings
import pytest
import requests

import markethistorydb.utils.logger as logger_module
from markethistorydb.utils.redact import REDACTED


# --- API token redaction -------------------------------------------------------------------

def _formatted(message: str, *args, exc_info=None) -> str:
    """
    Formats one record the way the CLI's log handlers do.

    :param message: Log message, %-style placeholders included
    :param args: Values for the placeholders in *message*
    :param exc_info: Exception info attached to the record, as sys.exc_info() returns it
    :return: The line as it would be written to the terminal and the log file
    """
    record = logging.LogRecord("test", logging.ERROR, __file__, 0, message, args, exc_info)
    return logger_module._build_formatter().format(record)


@pytest.mark.parametrize("leak", [
    "https://eodhd.com/api/eod/AAPL.US?api_token=SECRET&fmt=json",
    "{'api_token': 'SECRET', 'fmt': 'json'}",
])
def test_the_api_token_is_masked_in_the_message_its_args_and_the_traceback(leak):
    try:
        raise requests.exceptions.ConnectionError(leak)
    except requests.exceptions.ConnectionError:
        line = _formatted("{0} failed, params %s".format(leak), leak, exc_info=sys.exc_info())
    assert "SECRET" not in line
    assert REDACTED in line


# --- handlers ------------------------------------------------------------------------------

def _file_handlers() -> list[RotatingFileHandler]:
    return [handler for handler in logging.getLogger().handlers
            if isinstance(handler, RotatingFileHandler)]


def test_start_logger_writes_to_stdout_and_to_a_log_file_in_the_given_dir(tmp_path, reset_logging):
    logger_module.start_logger(tmp_path)
    handlers = logging.getLogger().handlers
    assert any(type(handler) is logging.StreamHandler and handler.stream is sys.stdout
               for handler in handlers)
    assert [Path(handler.baseFilename) for handler in _file_handlers()] == [
        tmp_path / logger_module.LOG_FILE_NAME]
    assert _file_handlers()[0].encoding == "utf-8"

def test_every_handler_masks_the_token(tmp_path, reset_logging):
    logger_module.start_logger(tmp_path)
    assert all(isinstance(handler.formatter, logger_module._RedactingFormatter)
               for handler in logging.getLogger().handlers)
    logging.getLogger("markethistorydb.test").error("GET /eod/AAPL.US?api_token=SECRET")
    for handler in logging.getLogger().handlers:
        handler.flush()
    text = (tmp_path / logger_module.LOG_FILE_NAME).read_text(encoding="utf-8")
    assert "api_token=***" in text and "SECRET" not in text

def test_the_log_dir_defaults_to_the_working_directory(tmp_path, monkeypatch, reset_logging):
    monkeypatch.chdir(tmp_path)
    logger_module.start_logger()
    assert Path(_file_handlers()[0].baseFilename).parent == tmp_path

def test_only_the_terminal_is_written_to_when_so_configured(tmp_path, monkeypatch, reset_logging):
    monkeypatch.setattr(logger_module, "LOG_ONLY_TO_TERMINAL", True)
    logger_module.start_logger(tmp_path)
    assert _file_handlers() == []
    assert not (tmp_path / logger_module.LOG_FILE_NAME).exists()

def test_starting_the_logger_twice_does_not_duplicate_handlers(tmp_path, reset_logging):
    logger_module.start_logger(tmp_path)
    logger_module.start_logger(tmp_path)
    assert len(logging.getLogger().handlers) == 2

def test_the_level_is_applied_to_the_root_logger(tmp_path, reset_logging):
    logger_module.start_logger(tmp_path, level=logging.WARNING)
    assert logging.getLogger().level == logging.WARNING

def test_warnings_are_routed_into_the_log(tmp_path, reset_logging):
    logger_module.start_logger(tmp_path)
    warnings.warn("pandas is about to change something", FutureWarning)
    for handler in logging.getLogger().handlers:
        handler.flush()
    assert "pandas is about to change something" in (
        tmp_path / logger_module.LOG_FILE_NAME).read_text(encoding="utf-8")


# --- scalability: the log cannot fill the disk ---------------------------------------------

def test_the_log_file_is_rotated_so_its_disk_use_is_capped(tmp_path, reset_logging):
    logger_module.start_logger(tmp_path)
    handler = _file_handlers()[0]
    assert (handler.maxBytes, handler.backupCount) == (10 * 2**20, 5)

def test_rotation_keeps_no_more_than_the_configured_backups(tmp_path, monkeypatch, reset_logging):
    monkeypatch.setattr(logger_module, "_MAX_LOG_FILE_SIZE_IN_BYTES", 200)
    monkeypatch.setattr(logger_module, "_NUM_OF_LOG_FILE_BACKUPS", 2)
    logger_module.start_logger(tmp_path)
    for i in range(200):
        logging.getLogger("markethistorydb.test").info("line %d %s", i, "x" * 50)
    assert len(list(tmp_path.glob(logger_module.LOG_FILE_NAME + "*"))) == 3
