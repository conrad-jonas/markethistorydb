#!/usr/bin/env python12.9

"""Abstract class for requesting trading data from eodhd.com"""

from abc             import abstractmethod
from collections.abc import Callable
from json            import JSONDecodeError
from typing          import Any
import functools
import logging
import pandas as pd
import requests
import time

from fetch.errors        import RequestError
from fetch.eodhd.errors  import ApiError, BadGatewayError, UnauthorizedError, ApiErrorCode


# Maximum number of retries after API connection error occurred
_MAX_RETRIES_AFTER_API_CONNECT_ERROR = 3
# Time to wait after connection error to host occurred
_WAIT_TIME_IN_SECS_AFTER_REQUEST_ERROR = 10
# Time to wait after API used up error
_WAIT_TIME_IN_SECS_AFTER_API_ERROR = 3600


class RequestData(object):

    @staticmethod
    def _catch_request_error(func: Callable) -> Callable:
        """Decorator to catch error during download of eodhd.com data"""
        @functools.wraps(func)
        def wrapper_catch_request_error(*args, **kwargs) -> Any:
            """Wrapper function"""
            num_retries = 0
            return_value = None
            while num_retries < _MAX_RETRIES_AFTER_API_CONNECT_ERROR:
                # Retries calling function when certain errors caught
                try:
                    return_value = func(*args, **kwargs)
                    break
                except ApiError:
                    logging.error("Exception ApiError occurred, wait 60 minutes till next try", exc_info=True)
                    num_retries += 1
                    time.sleep(_WAIT_TIME_IN_SECS_AFTER_API_ERROR)
                except UnauthorizedError:
                    logging.error("Exception UnauthorizedError occurred")
                    num_retries += 1
                    time.sleep(_WAIT_TIME_IN_SECS_AFTER_REQUEST_ERROR)
                except BadGatewayError:
                    logging.error("Exception BadGatewayError occurred")
                    num_retries += 1
                    time.sleep(_WAIT_TIME_IN_SECS_AFTER_REQUEST_ERROR)
                except requests.exceptions.Timeout:
                    logging.error("Exception Timeout occurred")
                    num_retries += 1
                    time.sleep(_WAIT_TIME_IN_SECS_AFTER_REQUEST_ERROR)
                except requests.exceptions.ConnectionError:
                    logging.error("Exception ConnectionError occurred")
                    num_retries += 1
                    time.sleep(_WAIT_TIME_IN_SECS_AFTER_REQUEST_ERROR)
            else:
                logging.error("Max number of retries of calling function {0} exceeded".format(func))
                raise RequestError
            return return_value

        return wrapper_catch_request_error

    @staticmethod
    @_catch_request_error
    def _request_data_from_url(url: str, params: dict[str, Any]) -> list[dict[str, Any]] | dict[str, Any] | None:
        """Requests data from URL"""
        response = requests.get(url, params=params)
        # Catches errors
        if response.status_code == ApiErrorCode.TICKER_NOT_FOUND:
            # Ticker not found error occurred
            data_request = None
        elif response.status_code == ApiErrorCode.BAD_GATEWAY:
            # Bad gateway error occurred
            raise BadGatewayError(response.text, response.status_code)
        elif response.status_code == ApiErrorCode.UNAUTHORIZED:
            # Unauthorized error occurred
            raise UnauthorizedError(response.text, response.status_code)
        elif response.status_code in ApiErrorCode:
            # API used up
            raise ApiError(response.text, response.status_code)
        else:
            try:
                data_request = response.json()
            except JSONDecodeError as error:
                logging.error("Request status '{0}' with status code {1} occurred".format(
                    response.text, response.status_code))
                raise error
        return data_request

    @staticmethod
    def _has_columns(df: pd.DataFrame, expected_column_names: list[str]):
        if list(df)[:len(expected_column_names)] != expected_column_names:
            return False
        return True

    @abstractmethod
    def get(self, *args) -> pd.DataFrame | dict:
        pass