#!/usr/bin/env python12.9

"""Error classes and enums"""

from enum import IntEnum

from markethistorydb.utils import Error


class ApiErrorCode(IntEnum):
    """Describes request error codes from eodhd.com API"""
    UNAUTHORIZED = 401
    DATA_LIMIT_REACHED = 402
    NO_ACCESS_RIGHTS = 403
    TICKER_NOT_FOUND = 404
    BAD_GATEWAY = 502


class CompatibilityError(Error):
    """Exception raised for unexpected data structure"""

    def __init__(self, message: str):
        """Inits instance"""
        super().__init__(message)

class ApiError(Error):
    """Exception raised for eodhd.com API related error"""

    def __init__(self, message: str, error_code: int):
        """Inits instance"""
        super().__init__(message, error_code)

class BadGatewayError(Error):
    """Exception raised for bad gateway while requesting data"""

    def __init__(self, message: str, error_code: int):
        """Inits instance"""
        super().__init__(message, error_code)

class UnauthorizedError(Error):
    """Exception raised for unauthorized access while requesting data"""

    def __init__(self, message: str, error_code: int):
        """Inits instance"""
        super().__init__(message, error_code)
