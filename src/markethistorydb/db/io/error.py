from dataclasses import dataclass
from typing import Callable, ClassVar
import functools
import json

from questdb import QuestDBError, QuestDBErrorCode

from markethistorydb.errors      import InsertError, SchemaMismatchError
from markethistorydb.utils       import call_with_backoff

# Time to wait after connection error to host occurred
_WAIT_TIME_IN_SECS_AFTER_DB_ERROR = 10
# Maximum number of retries after db connection error occurred
_MAX_RETRIES_AFTER_DB_CONNECT_ERROR = 3
# Ingress errors a later attempt can get past: the host was unreachable or busy. Every other code
# (a frame that cannot be serialised, rejected credentials, ...) fails the same way on every
# attempt, so waiting 10 + 20 s before giving up would only slow the run down.
_TRANSIENT_INGRESS_ERROR_CODES = {
    QuestDBErrorCode.CouldNotResolveAddr,
    QuestDBErrorCode.SocketError,
    QuestDBErrorCode.ConnectTimeout,
    QuestDBErrorCode.ServerFlushError,
    QuestDBErrorCode.ServerInternalError,
    QuestDBErrorCode.FailoverRetry,
}


@dataclass(frozen=True)
class _ServerRejection:
    """
    Server's answer when it rejected the records themselves, which no retry can fix.

    QuestDB reports it as a ServerFlushError, the same code as a server that failed to take the
    records, with the server's JSON answer appended:

        Could not flush buffer: {"code": "invalid", "message": "column: v; cast error from ..."}
    """
    _PREFIX: ClassVar[str] = "Could not flush buffer: "
    _CODE: ClassVar[str] = "invalid"
    # Found in the message when the records do not fit the table, e.g.
    # "column: newCol does not exist, creating new columns is disabled" or
    # "column: v; cast error from protocol type: STRING to column type: DOUBLE"
    _SCHEMA_MISMATCH_FRAGMENTS: ClassVar[tuple[str, ...]] = ("does not exist", "cast error")

    message: str

    @classmethod
    def from_error(cls, error: QuestDBError) -> "_ServerRejection | None":
        """
        Reads the server's rejection out of an ingress error.

        :param error: Error the ingress write failed with
        :return: The rejection, or None for any other error (one the client raised, or a server
            that failed to take the records)
        """
        if error.code != QuestDBErrorCode.ServerFlushError:
            return None
        _, _, answer_text = str(error).partition(cls._PREFIX)
        try:
            answer = json.loads(answer_text)
        except json.JSONDecodeError:
            return None
        if not isinstance(answer, dict) or answer.get("code") != cls._CODE:
            return None
        return cls(str(answer.get("message", "")))

    @property
    def is_schema_mismatch(self) -> bool:
        """
        Tells whether the server rejected the records because they do not fit the table.

        :return: True if the message names a missing column or a type that cannot be cast
        """
        return any(fragment in self.message for fragment in self._SCHEMA_MISMATCH_FRAGMENTS)


def catch_ingress_error[**P, T](func: Callable[P, T]) -> Callable[P, T]:
    """
    Decorator that retries *func* while QuestDB's ingress fails transiently, then gives up as
    InsertError. An ingress error no retry can fix becomes an InsertError at once, one about
    records that do not fit the table a SchemaMismatchError.

    :param func: Decorated function performing the ingress write
    :return: Wrapped *func* that retries on transient QuestDBErrors
    """
    @functools.wraps(func)
    def attempt(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            return func(*args, **kwargs)
        except QuestDBError as error:
            rejection = _ServerRejection.from_error(error)
            if rejection is not None:
                error_type = SchemaMismatchError if rejection.is_schema_mismatch else InsertError
                error_message = "{0} failed: {1}".format(func.__qualname__, rejection.message)
                raise error_type(error_message) from error
            if error.code in _TRANSIENT_INGRESS_ERROR_CODES:
                raise
            raise InsertError("{0} failed: {1}".format(func.__qualname__, error)) from error

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        return call_with_backoff(
            functools.partial(attempt, *args, **kwargs),
            retry_on=(QuestDBError,),
            give_up_error=InsertError,
            max_attempts=_MAX_RETRIES_AFTER_DB_CONNECT_ERROR,
            base_delay_in_secs=_WAIT_TIME_IN_SECS_AFTER_DB_ERROR,
            description=func.__qualname__,
        )
    return wrapper
