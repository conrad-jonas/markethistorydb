#!/usr/bin/env python12.9

"""Objects used by download modules"""

from enum import IntEnum, Enum


class ExitCode(IntEnum):
    """Error codes used for calling exit()"""
    STORAGE_ERROR                   = 2
    MAX_NUM_OF_REQUEST_TRIES_ERROR  = 3
    USER_INTERRUPT_ERROR            = 4
    QUESTDB_INGRESS_ERROR           = 5

class ApiErrorCode(IntEnum):
    """Describes request error codes from eodhd.com API"""
    UNAUTHORIZED       = 401
    DATA_LIMIT_REACHED = 402
    NO_ACCESS_RIGHTS   = 403
    TICKER_NOT_FOUND   = 404
    BAD_GATEWAY        = 502

class FundamentalType(Enum):
    """Describes type of fundamental data requested from eodhd.com"""
    SECTOR_AND_INDUSTRY         = 1
    EARNINGS_QUARTERLY          = 2
    EARNINGS_ANNUALLY           = 3
    BALANCE_SHEET_QUARTERLY     = 4
    BALANCE_SHEET_ANNUALLY      = 5
    CASH_FLOW_QUARTERLY         = 6
    CASH_FLOW_ANNUALLY          = 7
    INCOME_STATEMENT_QUARTERLY  = 8
    INCOME_STATEMENT_ANNUALLY   = 9

class WriteMode(Enum):
    """Describes write behaviour when data already exist"""
    APPEND_IF_EXIST = 1
    IGNORE_IF_EXIST = 2

class StorageError(Exception):
    """Exception raised for drive space used up"""
    def __init__(self, message: str):
        """Inits instance"""
        super().__init__(message)
        self.message = message

    def __str__(self):
        """Returns error message"""
        return f"{self.message}"


class CompatibilityError(Exception):
    """Exception raised for unexpected data structure"""
    def __init__(self, message: str):
        """Inits instance"""
        super().__init__(message)
        self.message = message

    def __str__(self):
        """Returns error message"""
        return f"{self.message}"

class _RequestError(Exception):
    """Parent for request error exceptions"""
    def __init__(self, message: str, error_code: int):
        """Inits instance"""
        super().__init__(message)
        self.message = message
        self.error_code = error_code

    def __str__(self):
        """Returns error message"""
        return f"{self.message} (Error Code: {self.error_code})"

class ApiError(_RequestError):
    """Exception raised for eodhd.com API related error"""
    def __init__(self, message: str, error_code: int):
        """Inits instance"""
        super().__init__(message, error_code)

class BadGatewayError(_RequestError):
    """Exception raised for bad gateway while requesting data"""
    def __init__(self, message: str, error_code: int):
        """Inits instance"""
        super().__init__(message, error_code)

class UnauthorizedError(_RequestError):
    """Exception raised for unauthorized access while requesting data"""
    def __init__(self, message: str, error_code: int):
        """Inits instance"""
        super().__init__(message, error_code)
