import functools
import logging
import time
from typing import Callable, Any

from questdb.ingress import IngressError

# Time to wait after connection error to host occurred
_WAIT_TIME_IN_SECS_AFTER_DB_ERROR = 10
# Maximum number of retries after db connection error occurred
_MAX_RETRIES_AFTER_DB_CONNECT_ERROR = 3


def catch_ingress_error(func: Callable) -> Callable:
    """Decorator to catch error during db interaction"""
    @functools.wraps(func)
    def wrapper_catch_insert_in_questdb_error(*args, **kwargs) -> Any:
        """Wrapper function"""
        num_retries = 0
        error = None
        while num_retries < _MAX_RETRIES_AFTER_DB_CONNECT_ERROR:
            # Retries calling function when certain errors caught
            try:
                return_value = func(*args, **kwargs)
                break
            except IngressError as e:
                error = e
                logging.error("IngressError occurred")
                num_retries += 1
                time.sleep(_WAIT_TIME_IN_SECS_AFTER_DB_ERROR)
        else:
            logging.error("Max number of retries of calling function {0} exceeded".format(func))
            logging.error(type(error).__name__, exc_info=True)
            raise IngressError
        return return_value
    return wrapper_catch_insert_in_questdb_error
