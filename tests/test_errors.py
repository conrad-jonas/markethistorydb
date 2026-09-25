
"""Tests for the error paths: status mapping, retries, empty reads and per-symbol isolation"""

from json import JSONDecodeError
import logging
import sys
import traceback
import pandas as pd
import pytest
import requests
from psycopg.conninfo import conninfo_to_dict
from questdb.ingress import Sender

import markethistorydb.db.io.query as query_module
import markethistorydb.fetch.eodhd.request_data as request_data_module
import markethistorydb.utils.backoff as backoff_module
import markethistorydb.utils.logger as logger_module
from markethistorydb import cli
from markethistorydb.config import Config
from markethistorydb.db.io.query import Query
from markethistorydb.db.io.read  import Read
from markethistorydb.db.tables   import Symbol
from markethistorydb.errors import (AccessRightsError, AccountError, ApiError, BadGatewayError,
                                    CompatibilityError, ConfigError, DataLimitError, DbError,
                                    ErrorCode, FetchError, InsertError, MarketHistoryDbError,
                                    NetworkError, QueryError, RateLimitError, RequestError,
                                    StorageError, UnauthorizedError, UserInterruptError)
from markethistorydb.fetch.eodhd import RequestExchangeData
from markethistorydb.fetch.fetcher import Fetcher
from markethistorydb.fetch.utils import FailedSymbol
from markethistorydb.utils import SymbolStatus, TimeFrame, call_with_backoff
from markethistorydb.utils.redact import REDACTED


class FakeResponse:
    """Stands in for requests.Response; only the attributes _get touches are implemented"""

    def __init__(self, status_code: int = 200, payload=None, text: str = "", headers=None):
        self.status_code = status_code
        self.text = text
        self.headers = headers if headers is not None else {}
        self._payload = payload

    @property
    def ok(self) -> bool:
        return self.status_code < 400

    def json(self):
        if self._payload is None:
            raise JSONDecodeError("Expecting value", self.text, 0)
        return self._payload


@pytest.fixture
def slept(monkeypatch) -> list[float]:
    """
    Skips the waits between retries and records how long each one would have been.

    :param monkeypatch: pytest fixture used to replace backoff._sleep
    :return: List the skipped waits are appended to, in seconds
    """
    waits: list[float] = []

    def fake_sleep(delay_in_secs, should_stop):
        if should_stop():
            raise UserInterruptError("User interrupted process while waiting to retry")
        waits.append(delay_in_secs)

    monkeypatch.setattr(backoff_module, "_sleep", fake_sleep)
    return waits

class FakeApi:
    """
    Answers the request layer with queued responses, repeating the last one, and counts calls.

    A queued exception is raised instead of answered, as requests raises a timeout or a refused
    connection.
    """

    def __init__(self):
        self.responses: list[FakeResponse | Exception] = []
        self.calls: list[str] = []

    def respond_with(self, *responses: FakeResponse | Exception):
        self.responses.extend(responses)

    @property
    def num_of_calls(self) -> int:
        return len(self.calls)

    def get(self, url, params=None, timeout=None) -> FakeResponse:
        self.calls.append(url)
        # Timeouts are what keep a hung host from blocking the run, so they must be passed
        assert timeout is not None
        response = self.responses[min(len(self.calls) - 1, len(self.responses) - 1)]
        if isinstance(response, Exception):
            raise response
        return response


@pytest.fixture
def api(monkeypatch) -> FakeApi:
    """
    Puts a fake eodhd.com behind the request layer.

    :param monkeypatch: pytest fixture used to replace requests.get
    :return: The fake the test queues responses on
    """
    fake_api = FakeApi()
    monkeypatch.setattr(request_data_module.requests, "get", fake_api.get)
    return fake_api


def _requester(should_stop=None) -> RequestExchangeData:
    return RequestExchangeData("token", TimeFrame.DAILY, should_stop)

def _request(requester: RequestExchangeData):
    return requester._request_data_from_url("https://eodhd.com/api/exchanges-list/?", {})


# --- status code mapping -------------------------------------------------------------------

def test_ticker_not_found_yields_no_data_instead_of_an_error(api):
    api.respond_with(FakeResponse(404, text="not found"))
    assert _request(_requester()) is None

def test_successful_response_is_returned_as_parsed_json(api):
    api.respond_with(FakeResponse(200, payload=[{"Code": "US"}]))
    assert _request(_requester()) == [{"Code": "US"}]

def test_unauthorized_is_not_retried_because_a_bad_token_cannot_fix_itself(api, slept):
    api.respond_with(FakeResponse(401, text="wrong token"))
    with pytest.raises(UnauthorizedError):
        _request(_requester())
    assert api.num_of_calls == 1
    assert slept == []

def test_the_plan_being_used_up_is_not_retried_because_waiting_cannot_refill_it(api, slept):
    api.respond_with(FakeResponse(402, text="limit reached"))
    with pytest.raises(DataLimitError):
        _request(_requester())
    assert api.num_of_calls == 1
    assert slept == []

def test_an_endpoint_outside_the_plan_is_told_apart_from_a_rejected_token(api, slept):
    api.respond_with(FakeResponse(403, text="not in your plan"))
    with pytest.raises(AccessRightsError):
        _request(_requester())
    assert api.num_of_calls == 1
    assert slept == []

def test_rate_limit_is_retried_and_honours_retry_after(api, slept):
    api.respond_with(FakeResponse(429, text="slow down", headers={"Retry-After": "7"}))
    with pytest.raises(RequestError):
        _request(_requester())
    assert slept == [7.0, 7.0]

def test_rate_limit_falls_back_to_the_backoff_when_retry_after_is_a_date(api, slept):
    api.respond_with(
        FakeResponse(429, text="slow down", headers={"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"}))
    with pytest.raises(RequestError):
        _request(_requester())
    # Backoff doubles rather than repeating the base delay
    assert slept == [10.0, 20.0]

@pytest.mark.parametrize("retry_after", ["nan", "-5", "inf"])
def test_a_retry_after_that_is_no_usable_wait_falls_back_to_the_backoff(api, slept, retry_after):
    # float() accepts all three, but a nan wait never ends and a negative one does not wait at all
    api.respond_with(FakeResponse(429, text="slow down", headers={"Retry-After": retry_after}))
    with pytest.raises(RequestError):
        _request(_requester())
    assert slept == [10.0, 20.0]

def test_a_retry_after_beyond_the_cap_is_cut_down_to_it(api, slept):
    api.respond_with(FakeResponse(429, text="slow down", headers={"Retry-After": "86400"}))
    with pytest.raises(RequestError):
        _request(_requester())
    assert slept == [3600.0, 3600.0]

def test_server_error_is_retried_although_its_status_is_not_a_known_one(api, slept):
    api.respond_with(FakeResponse(503, text="unavailable"))
    with pytest.raises(RequestError):
        _request(_requester())
    assert api.num_of_calls == 3

def test_unknown_client_error_is_reported_as_an_api_error(api, slept):
    api.respond_with(FakeResponse(418, text="teapot"))
    with pytest.raises(ApiError) as excinfo:
        _request(_requester())
    assert excinfo.value.http_status == 418
    assert not isinstance(excinfo.value, (RateLimitError, DataLimitError, BadGatewayError))

def test_a_body_that_is_not_json_is_a_compatibility_error(api, slept):
    api.respond_with(FakeResponse(200, text="<html>maintenance</html>"))
    with pytest.raises(CompatibilityError):
        _request(_requester())
    # Not retried: a changed payload shape does not fix itself by waiting
    assert api.num_of_calls == 1

def test_a_retried_request_succeeds_once_the_provider_recovers(api, slept):
    api.respond_with(FakeResponse(502, text="bad gateway"))
    api.respond_with(FakeResponse(200, payload=[{"Code": "US"}]))
    assert _request(_requester()) == [{"Code": "US"}]
    assert api.num_of_calls == 2

def test_error_message_does_not_grow_with_the_response_body(api, slept):
    api.respond_with(FakeResponse(401, text="x" * 10_000))
    with pytest.raises(UnauthorizedError) as excinfo:
        _request(_requester())
    assert len(excinfo.value.message) <= request_data_module._MAX_ERROR_DETAIL_LENGTH

def test_a_timeout_is_retried_and_the_request_succeeds_once_the_host_answers(api, slept):
    api.respond_with(requests.exceptions.ReadTimeout("read timed out"))
    api.respond_with(FakeResponse(200, payload=[{"Code": "US"}]))
    assert _request(_requester()) == [{"Code": "US"}]
    assert api.num_of_calls == 2

def test_a_host_that_stays_unreachable_ends_in_a_request_error(api, slept):
    api.respond_with(requests.exceptions.ConnectionError("connection refused"))
    with pytest.raises(RequestError) as excinfo:
        _request(_requester())
    # The requests exception stays out of the contract; this package's own error takes its place
    assert isinstance(excinfo.value.__cause__, NetworkError)
    assert api.num_of_calls == 3

def test_a_request_exception_no_retry_can_fix_is_a_request_error_at_once(api, slept):
    api.respond_with(requests.exceptions.TooManyRedirects("exceeded 30 redirects"))
    with pytest.raises(RequestError):
        _request(_requester())
    assert api.num_of_calls == 1


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

def test_waiting_for_a_retry_is_interruptible(api):
    api.respond_with(FakeResponse(429, text="slow down"))
    with pytest.raises(UserInterruptError):
        _request(_requester(should_stop=lambda: True))
    # Aborted during the first wait rather than sitting it out
    assert api.num_of_calls == 1


# --- DB reads ------------------------------------------------------------------------------

class FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def execute(self, query, params):
        return self._rows


def test_reading_a_missing_record_yields_an_empty_series_not_an_index_error():
    # Callers distinguish "not in table" from "in table" by Series.empty
    assert Read(FakeQuery([])).exchange("NASDAQ").empty

def test_reading_an_existing_record_yields_its_values():
    series = Read(FakeQuery([("NASDAQ", "NASDAQ Stock Exchange")])).exchange("NASDAQ")
    assert not series.empty
    assert series.iloc[0] == "NASDAQ"

def test_more_records_than_the_unique_key_allows_is_a_query_error():
    with pytest.raises(QueryError):
        Read(FakeQuery([("NASDAQ",), ("NASDAQ",)])).exchange("NASDAQ")

def test_reading_prices_for_no_symbols_yields_an_empty_frame():
    assert Read(FakeQuery([])).ohlcv({}, TimeFrame.DAILY).empty


class FakeCursor:
    """Cursor whose description is None for statements that return no records, as psycopg's is"""

    def __init__(self, description, rows):
        self.description = description
        self._rows = rows

    def execute(self, query, params):
        pass

    def fetchall(self):
        if self.description is None:
            raise AssertionError("fetchall() must not be called when there is no result set")
        return self._rows

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeConfig:
    psycopg_conninfo = "user=test host=localhost"


def _query_with_cursor(monkeypatch, cursor) -> Query:
    monkeypatch.setattr(query_module.pg, "connect", lambda *args, **kwargs: FakeConnection(cursor))
    return Query(FakeConfig())


def test_a_statement_without_a_result_set_returns_no_records(monkeypatch):
    # UPDATE, DELETE and DDL produce no records, and fetching from them raises in psycopg
    query = _query_with_cursor(monkeypatch, FakeCursor(description=None, rows=[]))
    assert query.execute("UPDATE exchange SET name = %s", ["NASDAQ"]) == []

def test_a_select_returns_its_records(monkeypatch):
    query = _query_with_cursor(monkeypatch, FakeCursor(description=[("name",)], rows=[("NASDAQ",)]))
    assert query.execute("SELECT name FROM exchange", []) == [("NASDAQ",)]

def test_a_failing_statement_is_reported_as_a_db_error(monkeypatch):
    class FailingCursor(FakeCursor):
        def execute(self, query, params):
            raise query_module.pg.OperationalError("connection refused")

    query = _query_with_cursor(monkeypatch, FailingCursor(description=None, rows=[]))
    with pytest.raises(QueryError) as excinfo:
        query.execute("SELECT 1", [])
    assert isinstance(excinfo.value, DbError)


# --- configuration -------------------------------------------------------------------------

def test_the_db_connection_gives_up_rather_than_hanging_on_an_unreachable_host():
    conninfo = Config(eodhd_api_token="token", questdb_password="secret").psycopg_conninfo
    assert "connect_timeout=" in conninfo

def test_a_port_that_is_not_a_number_is_a_config_error(monkeypatch):
    monkeypatch.setenv("EODHD_API_TOKEN", "token")
    monkeypatch.setenv("QUESTDB_PASSWORD", "secret")
    monkeypatch.setenv("QUESTDB_PG_PORT", "notaport")
    with pytest.raises(ConfigError) as excinfo:
        Config.from_env()
    # The message names the variable, so the user knows which one to fix
    assert "QUESTDB_PG_PORT" in str(excinfo.value)

def test_a_missing_token_is_a_config_error_naming_the_variable(monkeypatch):
    monkeypatch.delenv("EODHD_API_TOKEN", raising=False)
    monkeypatch.setenv("QUESTDB_PASSWORD", "secret")
    with pytest.raises(ConfigError) as excinfo:
        Config.from_env()
    assert "EODHD_API_TOKEN" in str(excinfo.value)

def test_neither_secret_shows_up_in_the_repr():
    text = repr(Config(eodhd_api_token="tok-secret", questdb_password="hunter2"))
    assert "hunter2" not in text
    assert "tok-secret" not in text

@pytest.mark.parametrize("password", [
    "pw hostaddr=203.0.113.1",
    "with space",
    "it's",
    "back\\slash",
])
def test_the_password_cannot_break_out_of_the_db_connection_string(password):
    # Unquoted, the space would end the password and let the rest pass as settings of its own
    conninfo = conninfo_to_dict(
        Config(eodhd_api_token="token", questdb_password=password).psycopg_conninfo)
    assert conninfo["password"] == password
    assert "hostaddr" not in conninfo

@pytest.mark.parametrize("password, escaped", [
    ("a;b",   "a;;b"),
    ("a;;b",  "a;;;;b"),
    ("ends;", "ends;;"),
])
def test_a_semicolon_in_the_password_cannot_end_the_ingress_config_early(password, escaped):
    http_conf = Config(eodhd_api_token="token", questdb_password=password).http_conf
    assert "password={0};".format(escaped) in http_conf
    # Has the real parser accept it;
    Sender.from_conf(http_conf)


# --- API token redaction -------------------------------------------------------------------

def _formatted(message: str, *args, exc_info=None) -> str:
    """
    Formats one record the way the CLI's log handlers do.

    :param message: Log message, %-style placeholders included
    :param args: Values for the placeholders in *message*
    :param exc_info: Exception info attached to the record, as sys.exc_info() returns it
    :return: The line as it would be written to the terminal and the log file
    """
    record = logging.LogRecord("test", logging.ERROR, __file__, 0, message, args, exc_info)
    return logger_module._build_formatter().format(record)


@pytest.mark.parametrize("leak", [
    "https://eodhd.com/api/eod/AAPL.US?api_token=SECRET&fmt=json",
    "{'api_token': 'SECRET', 'fmt': 'json'}",
])
def test_the_api_token_is_masked_in_the_message_its_args_and_the_traceback(leak):
    try:
        raise requests.exceptions.ConnectionError(leak)
    except requests.exceptions.ConnectionError:
        line = _formatted("{0} failed, params %s".format(leak), leak, exc_info=sys.exc_info())
    assert "SECRET" not in line
    assert REDACTED in line

@pytest.mark.parametrize("request_exception", [
    requests.exceptions.ConnectionError,
    requests.exceptions.ReadTimeout,
    requests.exceptions.TooManyRedirects,
])
def test_the_error_raised_for_a_request_exception_does_not_carry_the_api_token(
        api, slept, request_exception):
    # requests puts the full URL, token included, into its exceptions' messages. The error has
    # to be clean itself, not only once the CLI's formatter is done with it, since a caller of
    # the package may print it any way it likes.
    api.respond_with(request_exception(
        "Max retries exceeded with url: /api/exchanges-list/?api_token=SECRET&fmt=json"))
    with pytest.raises(RequestError) as excinfo:
        _request(_requester())
    # format_exception walks the whole chain, the causes and contexts included
    assert "SECRET" not in "".join(traceback.format_exception(excinfo.value))
    assert REDACTED in str(excinfo.value)


# --- per-symbol isolation ------------------------------------------------------------------

def _symbols(count: int) -> pd.DataFrame:
    return pd.DataFrame({
        Symbol.Columns.SYMBOL_CODE: ["SYM{0}".format(i) for i in range(count)],
        Symbol.Columns.EXCHANGE_CODE: ["NASDAQ"] * count,
    })

def _fetcher(monkeypatch) -> Fetcher:
    """
    Builds a Fetcher whose download handlers are replaced by the test.

    :param monkeypatch: pytest fixture used to disable the storage space check
    :return: Fetcher running against no DB
    """
    monkeypatch.setattr(Fetcher, "_check_storage_space", staticmethod(lambda: None))
    return Fetcher(db=None, api_token="token", time_frame=TimeFrame.DAILY,
                   symbol_status=SymbolStatus.ACTIVE)


def test_a_symbol_that_fails_is_recorded_and_the_run_carries_on(monkeypatch):
    fetcher = _fetcher(monkeypatch)
    downloaded = []

    def download(series_symbol):
        symbol_code = series_symbol[Symbol.Columns.SYMBOL_CODE]
        if symbol_code == "SYM1":
            raise CompatibilityError("unexpected shape")
        downloaded.append(symbol_code)

    monkeypatch.setattr(fetcher, "_download_historical_data", download)
    fetcher._download_all_symbols(_symbols(3))

    assert downloaded == ["SYM0", "SYM2"]
    assert fetcher.failed_symbols == [FailedSymbol("SYM1", "NASDAQ", "CompatibilityError")]

def test_a_failing_insert_only_costs_its_own_symbol(monkeypatch):
    fetcher = _fetcher(monkeypatch)

    def download(series_symbol):
        if series_symbol[Symbol.Columns.SYMBOL_CODE] == "SYM0":
            raise InsertError("ingress gave up")

    monkeypatch.setattr(fetcher, "_download_historical_data", download)
    fetcher._download_all_symbols(_symbols(2))
    assert len(fetcher.failed_symbols) == 1

def test_enough_failures_in_a_row_abort_the_run(monkeypatch):
    from markethistorydb.fetch.fetcher import _MAX_CONSECUTIVE_SYMBOL_FAILURES

    fetcher = _fetcher(monkeypatch)
    monkeypatch.setattr(fetcher, "_download_historical_data",
                        lambda series_symbol: (_ for _ in ()).throw(RequestError("gave up")))

    with pytest.raises(FetchError) as excinfo:
        fetcher._download_all_symbols(_symbols(_MAX_CONSECUTIVE_SYMBOL_FAILURES + 5))
    assert "in a row" in str(excinfo.value)
    assert isinstance(excinfo.value.__cause__, RequestError)
    # Stopped at the limit instead of working through the rest of the list
    assert len(fetcher.failed_symbols) == _MAX_CONSECUTIVE_SYMBOL_FAILURES

def test_the_failure_streak_resets_after_a_symbol_succeeds(monkeypatch):
    from markethistorydb.fetch.fetcher import _MAX_CONSECUTIVE_SYMBOL_FAILURES

    fetcher = _fetcher(monkeypatch)
    # Fails every symbol but one, so the streak never reaches the limit
    def download(series_symbol):
        index = int(series_symbol[Symbol.Columns.SYMBOL_CODE].removeprefix("SYM"))
        if index != _MAX_CONSECUTIVE_SYMBOL_FAILURES - 1:
            raise RequestError("gave up")

    monkeypatch.setattr(fetcher, "_download_historical_data", download)
    fetcher._download_all_symbols(_symbols(_MAX_CONSECUTIVE_SYMBOL_FAILURES + 1))
    assert len(fetcher.failed_symbols) == _MAX_CONSECUTIVE_SYMBOL_FAILURES

def test_a_user_interrupt_is_never_treated_as_a_symbol_failure(monkeypatch):
    fetcher = _fetcher(monkeypatch)
    monkeypatch.setattr(fetcher, "_download_historical_data",
                        lambda series_symbol: (_ for _ in ()).throw(UserInterruptError("stopped")))

    with pytest.raises(UserInterruptError):
        fetcher._download_all_symbols(_symbols(3))
    assert fetcher.failed_symbols == []

def test_running_out_of_disk_space_ends_the_run(monkeypatch):
    fetcher = _fetcher(monkeypatch)
    monkeypatch.setattr(fetcher, "_download_historical_data",
                        lambda series_symbol: (_ for _ in ()).throw(StorageError("disk full")))

    with pytest.raises(StorageError):
        fetcher._download_all_symbols(_symbols(3))

@pytest.mark.parametrize("error", [
    DataLimitError("plan used up", 402),
    UnauthorizedError("wrong token", 401),
    AccessRightsError("not in your plan", 403),
])
def test_an_account_level_error_ends_the_run_at_the_first_symbol(monkeypatch, error):
    # Every remaining symbol would fail the same way, so the streak counter must not be waited out
    from markethistorydb.fetch.fetcher import _MAX_CONSECUTIVE_SYMBOL_FAILURES

    fetcher = _fetcher(monkeypatch)
    attempted: list[str] = []

    def download(series_symbol):
        attempted.append(series_symbol[Symbol.Columns.SYMBOL_CODE])
        raise error

    monkeypatch.setattr(fetcher, "_download_historical_data", download)
    with pytest.raises(type(error)):
        fetcher._download_all_symbols(_symbols(_MAX_CONSECUTIVE_SYMBOL_FAILURES + 5))
    assert len(attempted) == 1

def test_the_symbol_the_run_ends_on_is_recorded_as_a_failure(monkeypatch):
    # _log_summary subtracts failed_symbols from the requested count, so the aborting symbol
    # must be in there or it reads as downloaded
    fetcher = _fetcher(monkeypatch)
    monkeypatch.setattr(fetcher, "_download_historical_data",
                        lambda series_symbol: (_ for _ in ()).throw(DataLimitError("used up", 402)))

    with pytest.raises(DataLimitError):
        fetcher._download_all_symbols(_symbols(3))
    assert fetcher.failed_symbols == [FailedSymbol("SYM0", "NASDAQ", "DataLimitError")]


# --- cli exit codes ------------------------------------------------------------------------

@pytest.fixture
def cli_client(monkeypatch):
    """
    Runs the CLI against a Client whose fetch raises whatever the test sets.

    :param monkeypatch: pytest fixture used to replace the logger, dotenv and the Client
    :return: List the test appends the error to be raised to
    """
    # cli imports both by name, so its own bindings are the ones to replace; patching them at
    # their source would leave the tests writing a real log file and reading the real .env
    monkeypatch.setattr(cli, "start_logger", lambda *args, **kwargs: None)
    monkeypatch.setattr(cli, "load_dotenv", lambda *args, **kwargs: False)

    raised: list[BaseException] = []

    class FakeClient:
        def __init__(self, config=None):
            pass

        def fetch(self, *args, **kwargs):
            if raised:
                raise raised[0]
            return 0

    # cli imported Client by name, so its own binding is the one to replace; patching
    # markethistorydb.client.Client would leave the CLI talking to the real provider
    monkeypatch.setattr(cli, "Client", FakeClient)
    return raised


@pytest.mark.parametrize("error, expected_exit_code", [
    (None,                               ErrorCode.SUCCESS),
    (ConfigError("no token"),            ErrorCode.CONFIG_ERROR),
    (UserInterruptError("stopped"),      ErrorCode.USER_INTERRUPT_ERROR),
    (KeyboardInterrupt(),                ErrorCode.USER_INTERRUPT_ERROR),
    (StorageError("disk full"),          ErrorCode.STORAGE_ERROR),
    (RequestError("gave up"),            ErrorCode.REQUEST_ERROR),
    (CompatibilityError("bad shape"),    ErrorCode.COMPATIBILITY_ERROR),
    (UnauthorizedError("wrong token", 401), ErrorCode.AUTH_ERROR),
    (ApiError("teapot", 418),            ErrorCode.FETCH_ERROR),
    (DataLimitError("plan used up", 402), ErrorCode.DATA_LIMIT_ERROR),
    (AccessRightsError("not in plan", 403), ErrorCode.ACCESS_RIGHTS_ERROR),
    (FetchError("too many in a row"),    ErrorCode.FETCH_ERROR),
    (InsertError("ingress gave up"),     ErrorCode.INSERT_ERROR),
    (QueryError("select failed"),        ErrorCode.DB_ERROR),
])
def test_cli_maps_each_error_to_its_exit_code(cli_client, error, expected_exit_code):
    if error is not None:
        cli_client.append(error)
    assert cli.main(["fetch"]) == expected_exit_code

def test_a_subclass_wins_over_the_parent_whatever_the_entries_are_ordered_like():
    # InsertError inherits DbError, and both are mapped; the lookup must not settle for the parent
    assert cli._exit_code_for(InsertError("ingress gave up")) is ErrorCode.INSERT_ERROR
    # The AccountError layer sits between these three and ApiError, and must shadow none of them
    assert cli._exit_code_for(UnauthorizedError("wrong token", 401)) is ErrorCode.AUTH_ERROR
    assert cli._exit_code_for(DataLimitError("used up", 402)) is ErrorCode.DATA_LIMIT_ERROR
    assert cli._exit_code_for(AccessRightsError("not in plan", 403)) is ErrorCode.ACCESS_RIGHTS_ERROR
    # AccountError is abstract and deliberately unmapped, so it falls back to its parent's code
    assert cli._exit_code_for(AccountError("something", 400)) is ErrorCode.FETCH_ERROR

def test_every_exit_code_can_actually_be_produced_by_some_error():
    mapped = set(cli._ERROR_EXIT_CODES.values()) | {ErrorCode.SUCCESS, ErrorCode.UNKNOWN_ERROR}
    assert mapped == set(ErrorCode)

def _error_classes(base: type[MarketHistoryDbError]) -> set[type[MarketHistoryDbError]]:
    """
    Collects every class below *base*, however deep it sits.

    :param base: Class to walk the subclasses of
    :return: All subclasses of *base*, the intermediate parents included
    """
    subclasses: set[type[MarketHistoryDbError]] = set()
    for subclass in base.__subclasses__():
        subclasses.add(subclass)
        subclasses |= _error_classes(subclass)
    return subclasses

def _an_instance_of(error_class: type[MarketHistoryDbError]) -> MarketHistoryDbError:
    """
    Builds a throwaway instance of *error_class*, whatever its __init__ expects.

    :param error_class: Class to instantiate
    :return: Instance carrying a placeholder message
    """
    if issubclass(error_class, ApiError):
        return error_class("boom", 500)
    return error_class("boom")

def test_every_error_the_package_raises_maps_to_an_exit_code():
    # UNKNOWN_ERROR is for what escapes the hierarchy, not for a class that was forgotten in the map
    unmapped = sorted(error_class.__name__ for error_class in _error_classes(MarketHistoryDbError)
                      if cli._exit_code_for(_an_instance_of(error_class)) is ErrorCode.UNKNOWN_ERROR)
    assert not unmapped, "no exit code for: {0}".format(", ".join(unmapped))

def test_argparse_usage_errors_keep_an_exit_code_of_their_own():
    # argparse exits with 2 on a bad command line, so no error of ours may claim that code
    assert 2 not in set(ErrorCode)
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["fetch", "--time-frame", "fortnightly"])
    assert exit_info.value.code == 2
