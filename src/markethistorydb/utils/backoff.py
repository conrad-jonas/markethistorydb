
"""Backoff helper shared by the request path and the db write path"""

from typing import Callable
import logging
import time

from markethistorydb.errors import MarketHistoryDbError, UserInterruptError

logger = logging.getLogger(__name__)

# Granularity at which a wait is broken up, so that should_stop gets polled during a long one
_SLEEP_SLICE_IN_SECS = 0.5


def _delay_before_retry(error: BaseException, attempt: int, base_delay_in_secs: float,
                        backoff_factor: float, max_delay_in_secs: float) -> float:
    """
    Works out how long to wait before *attempt* + 1.

    :param error: Error the attempt failed with; a retry_after on it overrides the backoff
    :param attempt: Number of the attempt that just failed, counting from 1
    :param base_delay_in_secs: Delay after the first failure
    :param backoff_factor: Factor the delay grows by with every further attempt
    :param max_delay_in_secs: Upper bound on the delay
    :return: Number of seconds to wait
    """
    # Errors that know their own sensible wait (a Retry-After header) override the backoff
    retry_after = getattr(error, "retry_after", None)
    if retry_after is not None:
        return min(float(retry_after), max_delay_in_secs)
    return min(base_delay_in_secs * (backoff_factor ** (attempt - 1)), max_delay_in_secs)

def _sleep(delay_in_secs: float, should_stop: Callable[[], bool]):
    """
    Sleeps *delay_in_secs* in slices, so that the wait stays interruptible.

    :param delay_in_secs: Total number of seconds to wait
    :param should_stop: Polled once per slice; returning True aborts with UserInterruptError
    :raises UserInterruptError: If *should_stop* returns True before the wait is over
    """
    deadline = time.monotonic() + delay_in_secs
    while True:
        if should_stop():
            raise UserInterruptError("User interrupted process while waiting to retry")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(_SLEEP_SLICE_IN_SECS, remaining))

def call_with_backoff[T](func: Callable[[], T], retry_on: tuple[type[BaseException], ...],
                         give_up_error: type[MarketHistoryDbError], max_attempts: int = 3,
                         base_delay_in_secs: float = 10.0, backoff_factor: float = 2.0,
                         max_delay_in_secs: float = 3600.0,
                         should_stop: Callable[[], bool] | None = None,
                         description: str | None = None) -> T:
    """
    Calls *func*, retrying it while it raises one of *retry_on* with backoff.

    :param func: Function to call, taking no arguments
    :param retry_on: Exception types worth another attempt; everything else propagates at once
    :param give_up_error: Error type raised from the last exception once the attempts are used up
    :param max_attempts: Maximum number of calls, the first one included
    :param base_delay_in_secs: Delay after the first failure
    :param backoff_factor: Factor the delay grows by with every further attempt
    :param max_delay_in_secs: Upper bound on the delay
    :param should_stop: Polled while waiting; returning True aborts with UserInterruptError
    :param description: Name of the call in log messages (the function's own name if unset)
    :return: Whatever *func* returned
    :raises MarketHistoryDbError: Of the type passed as *give_up_error*, if the last attempt
        failed too; chained from that attempt's exception
    :raises UserInterruptError: If *should_stop* returns True while waiting between attempts
    :raises ValueError: If *max_attempts* is below 1, which would leave no call to make
    """
    if max_attempts < 1:
        raise ValueError("Attempts must be at least 1, got {0}".format(max_attempts))
    name = description if description is not None else getattr(func, "__name__", repr(func))
    poll_should_stop = should_stop if should_stop is not None else (lambda: False)

    attempt = 1
    while True:
        try:
            return func()
        except retry_on as error:
            if attempt >= max_attempts:
                message = "{0} failed after {1} attempts: {2}".format(name, max_attempts, error)
                logger.error(message)
                raise give_up_error(message) from error
            delay_in_secs = _delay_before_retry(error, attempt, base_delay_in_secs,
                                                backoff_factor, max_delay_in_secs)
            # A retry that is about to happen is a warning, not an error
            logger.warning("{0} failed with {1} (attempt {2} of {3}), retrying in {4:.0f} s".format(
                name, type(error).__name__, attempt, max_attempts, delay_in_secs))
            _sleep(delay_in_secs, poll_should_stop)
        attempt += 1
