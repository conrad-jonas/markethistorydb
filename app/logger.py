#!/usr/bin/env python12.9

"""Contains logger class."""

import logging
import sys
import os

class Logger(object):
    """Logger to redirect stdout and stderr."""

    def __init__(self, filepath: str):
        """Inits instance."""

        self.terminal = sys.stdout
        self.log = open(filepath, "a")

    def write(self, message: str):
        """Writes message to terminal and log file."""
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        """Method is needed for python 3 compatibility"""
        pass

def setup_logger(log_only_to_terminal: bool, log_filename: str):
    """Sets up logger"""
    if not log_only_to_terminal:
        # Logs also to file
        # Log filename and path
        log_filepath = os.getcwd() + "\\" + log_filename
        # Redirects stdout and stderr
        sys.stdout = Logger(log_filepath)
        sys.stderr = sys.stdout

    # Configure logging messages
    logging.basicConfig(
            encoding="utf-8",
            format="{asctime} - {levelname} - {message}",
            style="{",
            datefmt="%d.%m.%Y-%H:%M",
            handlers=[logging.StreamHandler(sys.stdout)]
    )

    logging.getLogger().setLevel(logging.INFO)
    print("")
    logging.info("Logger has been set up")