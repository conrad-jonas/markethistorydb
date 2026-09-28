
"""Error hierarchy and process exit codes for the whole package"""

from enum import IntEnum


class ErrorCode(IntEnum):
    """
    Exit codes the CLI returns to the process.

    2 is left unused on purpose: argparse exits with it on a bad command line
    """
    SUCCESS               = 0
    REQUEST_ERROR         = 3
    USER_INTERRUPT_ERROR  = 4
    INSERT_ERROR          = 5
    CONFIG_ERROR          = 6
    COMPATIBILITY_ERROR   = 7
    DB_ERROR              = 8
    UNKNOWN_ERROR         = 9
    STORAGE_ERROR         = 10
    AUTH_ERROR            = 11
    FETCH_ERROR           = 12
    DATA_LIMIT_ERROR      = 13
    ACCESS_RIGHTS_ERROR   = 14


class ApiErrorCode(IntEnum):
    """HTTP status codes the eodhd.com API is known to return"""
    UNAUTHORIZED       = 401
    DATA_LIMIT_REACHED = 402
    NO_ACCESS_RIGHTS   = 403
    TICKER_NOT_FOUND   = 404
    RATE_LIMITED       = 429
    BAD_GATEWAY        = 502


class MarketHistoryDbError(Exception):
    """Parent class of every error raised by this package"""

    def __init__(self, message: str, error_code: int | None = None):
        """
        Inits instance.

        :param message: Error message, without any error code suffix
        :param error_code: Code appended to the message by __str__, where one is known
        """
        super().__init__(message)
        self._message: str = message
        self._error_code: int | None = error_code

    @property
    def message(self) -> str:
        """
        Reads the error message.

        :return: Error message without the error code suffix
        """
        return self._message

    @property
    def error_code(self) -> int | None:
        """
        Reads the error code.

        :return: Error code, or None if none has been passed
        """
        return self._error_code

    def __str__(self) -> str:
        """
        Renders the error for output.

        :return: Error message, with the error code appended where one is known
        """
        if self._error_code is None:
            error_msg = "{0}".format(self._message)
        else:
            error_msg = "{0} (Error Code: {1})".format(self._message, self._error_code)
        return error_msg


class ConfigError(MarketHistoryDbError):
    """Exception raised for a missing or unusable configuration value"""

class StorageError(MarketHistoryDbError):
    """Exception raised for drive space used up"""

class UserInterruptError(MarketHistoryDbError):
    """Exception raised when user interrupts download"""


class FetchError(MarketHistoryDbError):
    """Parent class of every error raised while fetching data from the provider"""

class RequestError(FetchError):
    """
    Exception raised when a request failed finally, i.e. after all retries, or failed in a way
    no retry can fix
    """

class NetworkError(FetchError):
    """
    Exception raised when the provider could not be reached or did not answer in time.

    Stands in for the requests exception, whose message holds the full URL, API token included;
    the message of this one has the token masked.
    """

class CompatibilityError(FetchError):
    """Exception raised for unexpected data structure"""

class NoDataError(FetchError):
    """Exception raised when the provider returned no data where the run cannot go on without it"""

class ApiError(FetchError):
    """Exception raised when the provider answered with an error status"""

    def __init__(self, message: str, error_code: int, retry_after: float | None = None):
        """
        Inits instance.

        :param message: Error message, without any error code suffix
        :param error_code: HTTP status the provider answered with
        :param retry_after: Seconds to wait before retrying, taken from the provider's
            Retry-After header where it sends one. Read by utils.backoff.
        """
        super().__init__(message, error_code)
        self.retry_after: float | None = retry_after

    @property
    def http_status(self) -> int | None:
        """
        Reads the HTTP status the provider answered with.

        :return: HTTP status, or None if none has been passed
        """
        return self._error_code

class AccountError(ApiError):
    """
    Parent class of every error about the account or the plan behind the token.

    Nothing about the individual request or symbol is to blame, so neither waiting nor moving
    on to the next symbol can help: the run ends and the CLI reports what needs attention.
    """

class UnauthorizedError(AccountError):
    """Exception raised when the provider rejected the token"""

class DataLimitError(AccountError):
    """Exception raised when the API plan's data limit has been reached"""

class AccessRightsError(AccountError):
    """Exception raised when the plan does not cover the endpoint that was requested"""

class RateLimitError(ApiError):
    """Exception raised when the API rate limit has been hit"""

class BadGatewayError(ApiError):
    """Exception raised for a server side error while requesting data"""


class DbError(MarketHistoryDbError):
    """Parent class of every error raised while talking to the DB"""

class InsertError(DbError):
    """Exception raised when insert into db failed"""

class SchemaMismatchError(InsertError):
    """
    Exception raised when the DB rejected records that do not fit the table: a column the table
    does not have, or a value of a type its column cannot store.

    QuestDB is meant to run with line.auto.create.new.columns=false, so that a field the provider
    starts sending ends up here instead of silently as a new column. Most likely the provider
    changed its payload, so no retry can help.
    """

class QueryError(DbError):
    """Exception raised when a query failed or returned an unexpected number of records"""
