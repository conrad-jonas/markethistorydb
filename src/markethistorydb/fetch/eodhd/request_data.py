#!/usr/bin/env python12.9

"""Abstract class for requesting trading data from eodhd.com"""

from abc             import abstractmethod
from collections.abc import Callable
from json            import JSONDecodeError
from typing          import Any
import functools
import logging
import math
import pandas as pd
import requests

from markethistorydb.errors import (AccessRightsError, ApiError, ApiErrorCode, BadGatewayError,
                                    CompatibilityError, DataLimitError, NetworkError,
                                    RateLimitError, RequestError, UnauthorizedError)
from markethistorydb.fetch.utils  import FundamentalType
from markethistorydb.utils        import TimeFrame, call_with_backoff, redact_api_token

logger = logging.getLogger(__name__)


# Maximum number of retries after API connection error occurred
_MAX_RETRIES_AFTER_API_CONNECT_ERROR = 3
# Time to wait after connection error to host occurred
_WAIT_TIME_IN_SECS_AFTER_REQUEST_ERROR = 10
# Seconds to wait for the connection to be established and for the response to arrive; without
# these a hung host blocks the run forever
_CONNECT_TIMEOUT_IN_SECS = 10
_READ_TIMEOUT_IN_SECS    = 120
# Error bodies are logged, so only the beginning of one is kept
_MAX_ERROR_DETAIL_LENGTH = 500

# Errors worth another attempt. A rate limit says "wait", and a bad gateway or a timeout says
# "try again". Every AccountError is absent on purpose: a rejected token, a used up plan and an
# endpoint the plan does not cover all outlast any wait worth sitting through. So is
# CompatibilityError, because a changed payload shape does not fix itself either.
_RETRYABLE_ERRORS = (
    RateLimitError,
    BadGatewayError,
    NetworkError,
)


class RequestData(object):

    def __init__(self, api_token: str, time_frame: TimeFrame,
                 should_stop: Callable[[], bool] | None = None):
        """
        Inits instance.

        :param api_token: Token sent with every request to eodhd.com
        :param time_frame: Time frame the requests are made for
        :param should_stop: Polled while waiting between retries; returning True aborts the wait
        """
        self._api_token:        str = api_token
        self._time_frame: TimeFrame = time_frame
        self._should_stop: Callable[[], bool] = should_stop or (lambda: False)

    @staticmethod
    def _error_detail(response: requests.Response) -> str:
        """
        Cuts the response body down to what goes into an error message.

        :param response: Response the provider answered with
        :return: Beginning of the response body
        """
        return response.text[:_MAX_ERROR_DETAIL_LENGTH]

    @staticmethod
    def _retry_after_in_secs(response: requests.Response) -> float | None:
        """
        Reads the Retry-After header.

        :param response: Response the provider answered with
        :return: Seconds to wait, or None if the provider sent no usable header
        """
        retry_after = response.headers.get("Retry-After")
        if retry_after is None:
            return None
        try:
            retry_after_in_secs = float(retry_after)
        except ValueError:
            # The header may hold an HTTP date instead; fall back to the generic backoff
            return None
        # float() also accepts "nan", "inf" and negative numbers. A nan wait never ends and a
        # negative one does not wait at all, so fall back to the generic backoff for those too
        if not math.isfinite(retry_after_in_secs) or retry_after_in_secs < 0:
            return None
        return retry_after_in_secs

    def _raise_for_status(self, response: requests.Response):
        """
        Translates an error status into the matching error, retryable or not.

        :param response: Response the provider answered with
        :raises UnauthorizedError: If the provider rejected the token
        :raises DataLimitError: If the plan's data limit has been reached
        :raises AccessRightsError: If the plan does not cover the endpoint
        :raises RateLimitError: If the rate limit has been hit
        :raises BadGatewayError: If the provider answered with a 5xx status
        :raises ApiError: If the status is an error that none of the above covers
        """
        status = response.status_code
        if status == ApiErrorCode.UNAUTHORIZED:
            raise UnauthorizedError(self._error_detail(response), status)
        if status == ApiErrorCode.DATA_LIMIT_REACHED:
            # The plan, not the request, is what ran out, so there is nothing to wait for
            raise DataLimitError(self._error_detail(response), status)
        if status == ApiErrorCode.NO_ACCESS_RIGHTS:
            # Told apart from a rejected token: the plan is what needs upgrading, not the token
            raise AccessRightsError(self._error_detail(response), status)
        if status == ApiErrorCode.RATE_LIMITED:
            raise RateLimitError(self._error_detail(response), status,
                                 retry_after=self._retry_after_in_secs(response))
        if status >= 500:
            raise BadGatewayError(self._error_detail(response), status)
        if not response.ok:
            raise ApiError(self._error_detail(response), status)

    def _get(self, url: str, params: dict[str, Any]) -> list[dict[str, Any]] | dict[str, Any] | None:
        """
        Performs one request; every retry calls this again.

        :param url: URL to request
        :param params: Query parameters, API token included
        :return: Parsed JSON body, or None if the provider knows no such ticker
        :raises NetworkError: If the provider could not be reached or did not answer in time
        :raises RequestError: If the request failed in a way no retry can fix, e.g. an invalid URL
        :raises ApiError: If the provider answered with an error status; the subclass says which
        :raises CompatibilityError: If the body is not JSON
        """
        # A requests exception's message holds the full URL, API token included. Re-raised with
        # the token masked, and not chained, since a chained one prints with every traceback.
        try:
            response = requests.get(url, params=params,
                                    timeout=(_CONNECT_TIMEOUT_IN_SECS, _READ_TIMEOUT_IN_SECS))
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as error:
            raise NetworkError("{0}: {1}".format(
                type(error).__name__, redact_api_token(str(error)))) from None
        except requests.exceptions.RequestException as error:
            raise RequestError("{0}: {1}".format(
                type(error).__name__, redact_api_token(str(error)))) from None
        if response.status_code == ApiErrorCode.TICKER_NOT_FOUND:
            # No data for this ticker; the callers treat None as "nothing to store"
            return None
        self._raise_for_status(response)
        try:
            return response.json()
        except JSONDecodeError as error:
            raise CompatibilityError(
                "Response with status code {0} is not JSON: {1}".format(
                    response.status_code, self._error_detail(response))) from error

    def _request_data_from_url(self, url: str,
                               params: dict[str, Any]) -> list[dict[str, Any]] | dict[str, Any] | None:
        """
        Requests data from URL, retrying the errors that are worth retrying.

        :param url: URL to request
        :param params: Query parameters, API token included
        :return: Parsed JSON body, or None if the provider knows no such ticker
        :raises RequestError: If the request still fails once the retries are used up, or failed
            in a way no retry can fix; the message never holds the API token
        :raises UnauthorizedError: If the provider rejected the token; never retried
        :raises DataLimitError: If the plan's data limit has been reached; never retried
        :raises AccessRightsError: If the plan does not cover the endpoint; never retried
        :raises CompatibilityError: If the body is not JSON; never retried
        :raises UserInterruptError: If should_stop returned True while waiting to retry
        """
        return call_with_backoff(
            functools.partial(self._get, url, params),
            retry_on=_RETRYABLE_ERRORS,
            give_up_error=RequestError,
            attempts=_MAX_RETRIES_AFTER_API_CONNECT_ERROR,
            base_delay_in_secs=_WAIT_TIME_IN_SECS_AFTER_REQUEST_ERROR,
            should_stop=self._should_stop,
            # The token travels in the params, so the bare url is safe to log
            description="Request to {0}".format(url),
        )

    @staticmethod
    def _has_columns(df: pd.DataFrame, expected_column_names: list[str]):
        if list(df)[:len(expected_column_names)] != expected_column_names:
            return False
        return True

    @abstractmethod
    def get(self, *args: Any, **kwargs: Any) -> pd.DataFrame | tuple[pd.Series, dict[FundamentalType, pd.DataFrame]]:
        pass
