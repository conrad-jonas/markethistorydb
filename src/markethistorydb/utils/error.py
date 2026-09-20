
"""Parent class for custom errors"""


class Error(Exception):
    """Exception parent class"""

    def __init__(self, message: str, error_code: int | None = None):
        """Inits instance"""
        super().__init__(message)
        self._message: str = message
        self._error_code: int = error_code

    def __str__(self):
        """Returns error message"""
        if self._error_code is None:
            error_msg = f"{self._message}"
        else:
            error_msg = f"{self._message} (Error Code: {self._error_code})"
        return error_msg