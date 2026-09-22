from typing import Callable
import functools

from questdb.ingress import IngressError

from markethistorydb.errors      import InsertError
from markethistorydb.utils       import call_with_backoff

# Time to wait after connection error to host occurred
_WAIT_TIME_IN_SECS_AFTER_DB_ERROR = 10
# Maximum number of retries after db connection error occurred
_MAX_RETRIES_AFTER_DB_CONNECT_ERROR = 3


def catch_ingress_error[**P, T](func: Callable[P, T]) -> Callable[P, T]:
    """
    Decorator that retries *func* while QuestDB's ingress fails, then gives up as InsertError.

    :param func: Decorated function performing the ingress write
    :return: Wrapped *func* that retries on IngressError
    """
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        return call_with_backoff(
            functools.partial(func, *args, **kwargs),
            retry_on=(IngressError,),
            give_up_error=InsertError,
            attempts=_MAX_RETRIES_AFTER_DB_CONNECT_ERROR,
            base_delay_in_secs=_WAIT_TIME_IN_SECS_AFTER_DB_ERROR,
            description=func.__qualname__,
        )
    return wrapper
