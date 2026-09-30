"""Tests for utils/backoff.py: retries, give-up errors and interruptible waits"""

import pytest

import markethistorydb.utils.backoff as backoff_module
from markethistorydb.errors import (BadGatewayError, CompatibilityError, RateLimitError, RequestError,
                                    UserInterruptError)
from markethistorydb.utils import call_with_backoff


# --- backoff helper ------------------------------------------------------------------------

def test_call_with_backoff_returns_as_soon_as_the_call_succeeds(slept):
    attempts = []

    def flaky():
        attempts.append(1)
        if len(attempts) < 2:
            raise BadGatewayError("try again", 502)
        return "done"

    assert call_with_backoff(flaky, retry_on=(BadGatewayError,), give_up_error=RequestError) == "done"
    assert len(attempts) == 2

def test_call_with_backoff_keeps_the_original_error_as_the_cause(slept):
    def always_failing():
        raise BadGatewayError("still broken", 502)

    with pytest.raises(RequestError) as excinfo:
        call_with_backoff(always_failing, retry_on=(BadGatewayError,), give_up_error=RequestError)
    assert isinstance(excinfo.value.__cause__, BadGatewayError)

def test_call_with_backoff_does_not_swallow_an_error_it_was_not_asked_to_retry(slept):
    def failing():
        raise CompatibilityError("unexpected shape")

    with pytest.raises(CompatibilityError):
        call_with_backoff(failing, retry_on=(BadGatewayError,), give_up_error=RequestError)


def test_a_wait_is_slept_in_short_slices_that_add_up_to_the_delay(clock):
    polls: list[float] = []

    def never_stop() -> bool:
        polls.append(clock.now)
        return False

    backoff_module._sleep(2.2, never_stop)
    assert all(nap <= backoff_module._SLEEP_SLICE_IN_SECS for nap in clock.naps)
    assert sum(clock.naps) == pytest.approx(2.2)
    # Polled before every slice, so an interrupt is noticed within one slice
    assert len(polls) > len(clock.naps)

def test_a_wait_ends_early_once_should_stop_turns_true(clock):
    with pytest.raises(UserInterruptError):
        backoff_module._sleep(3600.0, lambda: clock.now >= 1.0)
    # Stopped one second into an hour's wait rather than sitting it out
    assert clock.now == pytest.approx(1.0)


def test_a_single_attempt_gives_up_without_waiting(slept):
    def failing():
        raise BadGatewayError("down", 502)

    with pytest.raises(RequestError):
        call_with_backoff(failing, retry_on=(BadGatewayError,), give_up_error=RequestError, max_attempts=1)
    assert slept == []

@pytest.mark.parametrize("attempts", [0, -1])
def test_fewer_than_one_attempt_is_rejected_before_calling(slept, attempts):
    calls = []
    with pytest.raises(ValueError):
        call_with_backoff(lambda: calls.append(1), retry_on=(BadGatewayError,),
                          give_up_error=RequestError, max_attempts=attempts)
    assert calls == []

def test_the_give_up_message_names_the_call_the_attempts_and_the_last_error(slept):
    def fetch_prices():
        raise BadGatewayError("still down", 502)

    with pytest.raises(RequestError) as excinfo:
        call_with_backoff(fetch_prices, retry_on=(BadGatewayError,), give_up_error=RequestError)
    assert str(excinfo.value) == "fetch_prices failed after 3 attempts: still down (Error Code: 502)"

def test_a_callable_without_a_name_is_described_by_its_repr(slept, caplog):
    class Flaky:
        def __init__(self):
            self.num_of_calls = 0

        def __call__(self):
            self.num_of_calls += 1
            if self.num_of_calls == 1:
                raise BadGatewayError("down", 502)
            return "done"

        def __repr__(self):
            return "<Flaky>"

    with caplog.at_level("WARNING", logger=backoff_module.__name__):
        call_with_backoff(Flaky(), retry_on=(BadGatewayError,), give_up_error=RequestError)
    assert caplog.records[0].getMessage().startswith("<Flaky> failed with BadGatewayError")

def test_an_explicit_description_replaces_the_function_name(slept):
    with pytest.raises(RequestError) as excinfo:
        call_with_backoff(_always_bad_gateway, retry_on=(BadGatewayError,),
                          give_up_error=RequestError, max_attempts=1, description="Request to /eod/")
    assert str(excinfo.value).startswith("Request to /eod/ failed after 1 attempts")

def _always_bad_gateway():
    raise BadGatewayError("down", 502)


# --- scalability: waits stay bounded however long a run gets -------------------------------

def test_the_plain_backoff_is_capped_at_the_maximum_delay(slept):
    # Many attempts must not grow the wait without bound (10, 20, 40, 80 -> capped at 50)
    with pytest.raises(RequestError):
        call_with_backoff(_always_bad_gateway, retry_on=(BadGatewayError,), give_up_error=RequestError,
                          max_attempts=5, max_delay_in_secs=50.0)
    assert slept == [10.0, 20.0, 40.0, 50.0]

def test_a_zero_retry_after_is_honoured_instead_of_the_backoff(slept):
    def rate_limited():
        raise RateLimitError("slow down", 429, retry_after=0.0)

    with pytest.raises(RequestError):
        call_with_backoff(rate_limited, retry_on=(RateLimitError,), give_up_error=RequestError)
    assert slept == [0.0, 0.0]

def test_a_zero_wait_returns_after_a_single_poll(clock):
    polls = []
    backoff_module._sleep(0.0, lambda: polls.append(1) or False)
    assert clock.naps == [] and polls == [1]
