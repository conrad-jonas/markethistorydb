"""Tests for errors.py: messages, codes and the shape of the hierarchy"""

import pytest

from markethistorydb.errors import (AccessRightsError, AccountError, ApiError, ApiErrorCode,
                                    BadGatewayError, CompatibilityError, ConfigError,
                                    DataLimitError, DbError, ErrorCode, FetchError, InsertError,
                                    MarketHistoryDbError, NetworkError, NoDataError, QueryError,
                                    RateLimitError,
                                    RequestError, StorageError, UnauthorizedError,
                                    UserInterruptError)


def test_an_error_without_a_code_renders_as_its_message():
    error = MarketHistoryDbError("disk full")
    assert (str(error), error.message, error.error_code) == ("disk full", "disk full", None)

def test_an_error_with_a_code_appends_it_to_the_rendered_message_only():
    error = MarketHistoryDbError("rejected", 401)
    assert str(error) == "rejected (Error Code: 401)"
    assert error.message == "rejected"
    assert error.error_code == 401

def test_an_api_error_exposes_the_http_status_and_the_retry_after():
    error = RateLimitError("slow down", ApiErrorCode.RATE_LIMITED, retry_after=7.0)
    assert (error.http_status, error.retry_after) == (429, 7.0)
    assert ApiError("teapot", 418).retry_after is None

@pytest.mark.parametrize("error_class, parent", [
    # The tree in the README's "Error handling" section
    (ConfigError, MarketHistoryDbError), (StorageError, MarketHistoryDbError),
    (UserInterruptError, MarketHistoryDbError), (FetchError, MarketHistoryDbError),
    (RequestError, FetchError), (NetworkError, FetchError), (CompatibilityError, FetchError),
    (NoDataError, FetchError), (ApiError, FetchError), (AccountError, ApiError), (UnauthorizedError, AccountError),
    (DataLimitError, AccountError), (AccessRightsError, AccountError),
    (RateLimitError, ApiError), (BadGatewayError, ApiError),
    (DbError, MarketHistoryDbError), (InsertError, DbError), (QueryError, DbError),
])
def test_each_error_sits_where_the_documented_hierarchy_puts_it(error_class, parent):
    assert error_class.__bases__ == (parent,)

def test_exit_code_2_stays_reserved_for_argparse():
    assert 2 not in {code.value for code in ErrorCode}
    assert ErrorCode.SUCCESS == 0
