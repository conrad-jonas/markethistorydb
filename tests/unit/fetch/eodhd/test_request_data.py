"""Tests for fetch/eodhd/request_data.py: status mapping, retries, network errors, token hygiene"""

import traceback
import pandas as pd
import pytest
import requests

import markethistorydb.fetch.eodhd.request_data as request_data_module
from markethistorydb.errors import (AccessRightsError, ApiError, BadGatewayError, CompatibilityError,
                                    DataLimitError, NetworkError, RateLimitError, RequestError,
                                    UnauthorizedError, UserInterruptError)
from markethistorydb.fetch.eodhd import RequestExchangeData
from markethistorydb.utils import TimeFrame
from markethistorydb.utils.redact import REDACTED
from tests.fakes import FakeResponse


def _requester(should_stop=None) -> RequestExchangeData:
    return RequestExchangeData("token", TimeFrame.DAILY, should_stop)

def _request(requester: RequestExchangeData):
    return requester._request_data_from_url("https://eodhd.com/api/exchanges-list/?", {})


# --- status code mapping -------------------------------------------------------------------

def test_ticker_not_found_yields_no_data_instead_of_an_error(scripted_api):
    scripted_api.respond_with(FakeResponse(404, text="not found"))
    assert _request(_requester()) is None

def test_successful_response_is_returned_as_parsed_json(scripted_api):
    scripted_api.respond_with(FakeResponse(200, payload=[{"Code": "US"}]))
    assert _request(_requester()) == [{"Code": "US"}]

def test_unauthorized_is_not_retried_because_a_bad_token_cannot_fix_itself(scripted_api, slept):
    scripted_api.respond_with(FakeResponse(401, text="wrong token"))
    with pytest.raises(UnauthorizedError):
        _request(_requester())
    assert scripted_api.num_of_calls == 1
    assert slept == []

def test_the_plan_being_used_up_is_not_retried_because_waiting_cannot_refill_it(scripted_api, slept):
    scripted_api.respond_with(FakeResponse(402, text="limit reached"))
    with pytest.raises(DataLimitError):
        _request(_requester())
    assert scripted_api.num_of_calls == 1
    assert slept == []

def test_an_endpoint_outside_the_plan_is_told_apart_from_a_rejected_token(scripted_api, slept):
    scripted_api.respond_with(FakeResponse(403, text="not in your plan"))
    with pytest.raises(AccessRightsError):
        _request(_requester())
    assert scripted_api.num_of_calls == 1
    assert slept == []

def test_rate_limit_is_retried_and_honours_retry_after(scripted_api, slept):
    scripted_api.respond_with(FakeResponse(429, text="slow down", headers={"Retry-After": "7"}))
    with pytest.raises(RequestError):
        _request(_requester())
    assert slept == [7.0, 7.0]

def test_rate_limit_falls_back_to_the_backoff_when_retry_after_is_a_date(scripted_api, slept):
    scripted_api.respond_with(
        FakeResponse(429, text="slow down", headers={"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"}))
    with pytest.raises(RequestError):
        _request(_requester())
    # Backoff doubles rather than repeating the base delay
    assert slept == [10.0, 20.0]

@pytest.mark.parametrize("retry_after", ["nan", "-5", "inf"])
def test_a_retry_after_that_is_no_usable_wait_falls_back_to_the_backoff(scripted_api, slept, retry_after):
    # float() accepts all three, but a nan wait never ends and a negative one does not wait at all
    scripted_api.respond_with(FakeResponse(429, text="slow down", headers={"Retry-After": retry_after}))
    with pytest.raises(RequestError):
        _request(_requester())
    assert slept == [10.0, 20.0]

def test_a_retry_after_beyond_the_cap_is_cut_down_to_it(scripted_api, slept):
    scripted_api.respond_with(FakeResponse(429, text="slow down", headers={"Retry-After": "86400"}))
    with pytest.raises(RequestError):
        _request(_requester())
    assert slept == [3600.0, 3600.0]

def test_server_error_is_retried_although_its_status_is_not_a_known_one(scripted_api, slept):
    scripted_api.respond_with(FakeResponse(503, text="unavailable"))
    with pytest.raises(RequestError):
        _request(_requester())
    assert scripted_api.num_of_calls == 3

def test_unknown_client_error_is_reported_as_an_api_error(scripted_api, slept):
    scripted_api.respond_with(FakeResponse(418, text="teapot"))
    with pytest.raises(ApiError) as excinfo:
        _request(_requester())
    assert excinfo.value.http_status == 418
    assert not isinstance(excinfo.value, (RateLimitError, DataLimitError, BadGatewayError))

def test_a_body_that_is_not_json_is_a_compatibility_error(scripted_api, slept):
    scripted_api.respond_with(FakeResponse(200, text="<html>maintenance</html>"))
    with pytest.raises(CompatibilityError):
        _request(_requester())
    # Not retried: a changed payload shape does not fix itself by waiting
    assert scripted_api.num_of_calls == 1

def test_a_retried_request_succeeds_once_the_provider_recovers(scripted_api, slept):
    scripted_api.respond_with(FakeResponse(502, text="bad gateway"))
    scripted_api.respond_with(FakeResponse(200, payload=[{"Code": "US"}]))
    assert _request(_requester()) == [{"Code": "US"}]
    assert scripted_api.num_of_calls == 2

@pytest.mark.parametrize("response, error_type", [
    (FakeResponse(401, text="x" * 10_000),                        UnauthorizedError),
    (FakeResponse(418, text="x" * 10_000),                        ApiError),
    (FakeResponse(200, text="<html>{0}</html>".format("x" * 10_000)), CompatibilityError),
])
def test_error_message_does_not_grow_with_the_response_body(scripted_api, slept, response, error_type):
    scripted_api.respond_with(response)
    with pytest.raises(error_type) as excinfo:
        _request(_requester())
    # Leaves room for the text to have some wrap around the detail
    assert len(excinfo.value.message) < 2 * request_data_module._MAX_ERROR_DETAIL_LENGTH

def test_a_timeout_is_retried_and_the_request_succeeds_once_the_host_answers(scripted_api, slept):
    scripted_api.respond_with(requests.exceptions.ReadTimeout("read timed out"))
    scripted_api.respond_with(FakeResponse(200, payload=[{"Code": "US"}]))
    assert _request(_requester()) == [{"Code": "US"}]
    assert scripted_api.num_of_calls == 2

def test_a_host_that_stays_unreachable_ends_in_a_request_error(scripted_api, slept):
    scripted_api.respond_with(requests.exceptions.ConnectionError("connection refused"))
    with pytest.raises(RequestError) as excinfo:
        _request(_requester())
    # The requests exception stays out of the contract; this package's own error takes its place
    assert isinstance(excinfo.value.__cause__, NetworkError)
    assert scripted_api.num_of_calls == 3

def test_a_request_exception_no_retry_can_fix_is_a_request_error_at_once(scripted_api, slept):
    scripted_api.respond_with(requests.exceptions.TooManyRedirects("exceeded 30 redirects"))
    with pytest.raises(RequestError):
        _request(_requester())
    assert scripted_api.num_of_calls == 1


def test_waiting_for_a_retry_is_interruptible(scripted_api):
    scripted_api.respond_with(FakeResponse(429, text="slow down"))
    with pytest.raises(UserInterruptError):
        _request(_requester(should_stop=lambda: True))
    # Aborted during the first wait rather than sitting it out
    assert scripted_api.num_of_calls == 1


@pytest.mark.parametrize("request_exception", [
    requests.exceptions.ConnectionError,
    requests.exceptions.ReadTimeout,
    requests.exceptions.TooManyRedirects,
])
def test_the_error_raised_for_a_request_exception_does_not_carry_the_api_token(
        scripted_api, slept, request_exception):
    # requests puts the full URL, token included, into its exceptions' messages. The error has
    # to be clean itself, not only once the CLI's formatter is done with it, since a caller of
    # the package may print it any way it likes.
    scripted_api.respond_with(request_exception(
        "Max retries exceeded with url: /api/exchanges-list/?api_token=SECRET&fmt=json"))
    with pytest.raises(RequestError) as excinfo:
        _request(_requester())
    # format_exception walks the whole chain, the causes and contexts included
    assert "SECRET" not in "".join(traceback.format_exception(excinfo.value))
    assert REDACTED in str(excinfo.value)


# --- payload shape -------------------------------------------------------------------------

_URL = "https://eodhd.com/api/exchanges-list/?"

def test_an_array_endpoint_hands_back_the_array(scripted_api):
    scripted_api.respond_with(FakeResponse(200, payload=[{"Code": "US"}]))
    assert _requester()._request_list(_URL, {}) == [{"Code": "US"}]

def test_an_object_endpoint_hands_back_the_object(scripted_api):
    scripted_api.respond_with(FakeResponse(200, payload={"Code": "US"}))
    assert _requester()._request_object(_URL, {}) == {"Code": "US"}

@pytest.mark.parametrize("response", [
    FakeResponse(404, text="not found"),
    FakeResponse(200, payload=[]),
    FakeResponse(200, payload={}),
], ids=["unknown ticker", "empty array", "empty object"])
def test_no_data_yields_an_empty_value_of_the_expected_shape(scripted_api, response):
    scripted_api.respond_with(response)
    requester = _requester()
    assert requester._request_list(_URL, {}) == []
    assert requester._request_object(_URL, {}) == {}

def test_an_object_where_an_array_is_expected_is_a_compatibility_error(scripted_api):
    scripted_api.respond_with(FakeResponse(200, payload={"Code": "US"}))
    with pytest.raises(CompatibilityError, match="array"):
        _requester()._request_list(_URL, {})

def test_an_array_where_an_object_is_expected_is_a_compatibility_error(scripted_api):
    scripted_api.respond_with(FakeResponse(200, payload=[{"Code": "US"}]))
    with pytest.raises(CompatibilityError, match="object"):
        _requester()._request_object(_URL, {})


# --- payload structure checks --------------------------------------------------------------

@pytest.mark.parametrize("columns, expected", [
    (["a", "b", "c"], True),
    (["c", "a", "b"], True),       # the order of the keys in a JSON object carries no meaning
    (["a", "b", "c", "d"], True),  # fields added by the provider do not break the check
    (["a", "c"], False),
    ([], False),
])
def test_the_structure_check_asks_for_every_expected_column_in_any_order(columns, expected):
    df = pd.DataFrame(columns=columns)
    assert request_data_module.RequestData._has_columns(df, ["a", "b", "c"]) is expected

def test_every_request_is_sent_with_both_a_connect_and_a_read_timeout(scripted_api, monkeypatch):
    timeouts = []
    scripted_api.respond_with(FakeResponse(200, payload=[]))
    original_get = scripted_api.get

    def get(url, params=None, timeout=None):
        timeouts.append(timeout)
        return original_get(url, params, timeout)

    monkeypatch.setattr(request_data_module.requests, "get", get)
    _request(_requester())
    assert timeouts == [(request_data_module._CONNECT_TIMEOUT_IN_SECS,
                         request_data_module._READ_TIMEOUT_IN_SECS)]

@pytest.mark.parametrize("status_code, error_type", [
    (401, UnauthorizedError), (418, ApiError), (502, RequestError)])
def test_an_error_page_echoing_the_token_does_not_carry_it_into_the_error(scripted_api, slept, status_code, error_type):
    scripted_api.respond_with(FakeResponse(status_code, text="<h1>Error</h1> GET /api/eod/X.US?api_token=SECRET"))
    with pytest.raises(error_type) as excinfo:
        _request(_requester())
    assert "SECRET" not in "".join(traceback.format_exception(excinfo.value))

def test_a_token_at_the_cut_off_point_is_masked_rather_than_cut_in_half(scripted_api, slept):
    prefix = "x" * (request_data_module._MAX_ERROR_DETAIL_LENGTH - len("api_token=SEC"))
    scripted_api.respond_with(FakeResponse(418, text=prefix + "api_token=SECRET"))
    with pytest.raises(ApiError) as excinfo:
        _request(_requester())
    assert "SEC" not in excinfo.value.message
