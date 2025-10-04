#!/usr/bin/env python12.9

"""Global data types"""

from enum import Enum

class TimeFrame(Enum):
    """Describes timeframe for trading data"""
    DAILY  = 1
    MINUTE = 2

class SymbolStatus(Enum):
    """Describes status of requested"""
    ACTIVE   = 1
    DELISTED = 2