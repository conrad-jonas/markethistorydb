#!/usr/bin/env python12.9

"""General global constants"""

from os.path import dirname, abspath

# Bool whether to write only to terminal or also to log file
LOG_ONLY_TO_TERMINAL = False
# Working directory
WORKING_DIR = dirname(dirname(dirname(abspath(__file__))))