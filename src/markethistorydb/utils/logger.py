#!/usr/bin/env python12.9

"""Contains logger class."""

import logging
import sys
import os


# Bool whether to write only to terminal or also to log file
LOG_ONLY_TO_TERMINAL = False


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

def _setup_logger(log_only_to_terminal: bool, log_filename: str):
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


def start_logger():
    """Sets up options and properties for app"""
    # Sets up logger
    name_of_this_file = os.path.basename(__file__)
    log_filename = "{0}.log".format(name_of_this_file[:-3])
    _setup_logger(LOG_ONLY_TO_TERMINAL, log_filename)
    logging.info("Start {0}".format(name_of_this_file))
    logging.info("Current working directory: {0}".format(os.getcwd()))