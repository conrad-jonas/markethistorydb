#!/usr/bin/env python12.9

"""Error classes and enums"""

from enum import IntEnum

from utils.error import Error


class ErrorCode(IntEnum):
    """Error codes used for calling sys.exit()"""
    STORAGE_ERROR         = 2
    REQUEST_ERROR         = 3
    USER_INTERRUPT_ERROR  = 4
    QUESTDB_INGRESS_ERROR = 5

class StorageError(Error):
    """Exception raised for drive space used up"""
    def __init__(self, message: str):
        """Inits instance"""
        super().__init__(message)

class RequestError(Error):
    """Exception raised when request failed finally"""
    def __init__(self, message: str):
        """Inits instance"""
        super().__init__(message)

class UserInterruptError(Error):
    """Exception raised when user interrupts download"""
    def __init__(self, message: str):
        """Inits instance"""
        super().__init__(message)

class InsertError(Error):
    """Exception raised when insert into db failed"""
    def __init__(self, message: str):
        """Inits instance"""
        super().__init__(message)