"""Tests for cli.py: exit codes, the setup confirmation and argument parsing"""

import logging
import pytest

from markethistorydb import cli
from markethistorydb.errors import (AccessRightsError, AccountError, ApiError, CompatibilityError,
                                    ConfigError, DataLimitError, ErrorCode, FetchError, InsertError,
                                    MarketHistoryDbError, NoDataError, QueryError, RequestError,
                                    SchemaMismatchError, StorageError,
                                    UnauthorizedError, UserInterruptError)
from markethistorydb.utils import SymbolStatus, TimeFrame


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
    (NoDataError("no exchanges"),        ErrorCode.FETCH_ERROR),
    (InsertError("ingress gave up"),     ErrorCode.INSERT_ERROR),
    # An InsertError, but caused by the provider's payload no longer fitting the tables
    (SchemaMismatchError("new column"),  ErrorCode.COMPATIBILITY_ERROR),
    (QueryError("select failed"),        ErrorCode.DB_ERROR),
    (RuntimeError("bug"),                ErrorCode.UNKNOWN_ERROR),
])
def test_cli_maps_each_error_to_its_exit_code(cli_client, error, expected_exit_code):
    if error is not None:
        cli_client.append(error)
    assert cli.main(["fetch"]) == expected_exit_code

def test_a_config_error_while_building_the_client_is_a_config_error_code(monkeypatch, cli_client):
    # Client() reads the environment, so that is where a missing token actually surfaces
    class UnconfiguredClient:
        def __init__(self, config=None):
            raise ConfigError("Required environment variable 'EODHD_API_TOKEN' is not set")

    monkeypatch.setattr(cli, "Client", UnconfiguredClient)
    assert cli.main(["fetch"]) == ErrorCode.CONFIG_ERROR


class FakeSetupClient:
    """Counts the setups run on it, rather than dropping any tables"""

    def __init__(self):
        self.num_of_setups = 0

    def setup(self):
        self.num_of_setups += 1


def _typed(answer: str | BaseException):
    """
    Builds a stand-in for input() that answers with *answer*.

    :param answer: Text the user types, or the exception input() raises instead (EOFError for a
        closed stdin)
    :return: Function to put in place of builtins.input
    """
    def fake_input(prompt: str = "") -> str:
        if isinstance(answer, BaseException):
            raise answer
        return answer
    return fake_input


@pytest.mark.parametrize("answer", ["", "no", "n", "yess", EOFError()])
def test_setup_drops_nothing_unless_the_user_confirms(monkeypatch, answer):
    client = FakeSetupClient()
    monkeypatch.setattr("builtins.input", _typed(answer))
    cli._setup(client)
    assert client.num_of_setups == 0

@pytest.mark.parametrize("answer", ["yes", "Y"])
def test_setup_runs_once_the_user_confirms(monkeypatch, answer):
    client = FakeSetupClient()
    monkeypatch.setattr("builtins.input", _typed(answer))
    cli._setup(client)
    assert client.num_of_setups == 1

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


# --- commands and arguments ----------------------------------------------------------------

class RecordingClient:
    """Stands in for Client, recording the fetch arguments and the setups it is asked to run"""

    instances: list["RecordingClient"] = []

    def __init__(self, config=None):
        self.fetch_args: list[tuple] = []
        self.num_of_setups = 0
        RecordingClient.instances.append(self)

    def fetch(self, *args):
        self.fetch_args.append(args)
        return 0

    def setup(self):
        self.num_of_setups += 1


@pytest.fixture
def recording_client(monkeypatch) -> type[RecordingClient]:
    """
    Runs the CLI against a RecordingClient, with neither a log file nor the real .env.

    :param monkeypatch: pytest fixture used to replace the logger, dotenv and the Client
    :return: The RecordingClient class, whose instances list the clients the CLI built
    """
    monkeypatch.setattr(cli, "start_logger", lambda *args, **kwargs: None)
    monkeypatch.setattr(cli, "load_dotenv", lambda *args, **kwargs: False)
    monkeypatch.setattr(cli, "Client", RecordingClient)
    RecordingClient.instances = []
    return RecordingClient


def test_setup_command_runs_the_setup_once_confirmed(monkeypatch, recording_client):
    monkeypatch.setattr("builtins.input", _typed("yes"))
    assert cli.main(["setup"]) == ErrorCode.SUCCESS
    assert recording_client.instances[0].num_of_setups == 1

def test_fetch_options_reach_the_client_as_enum_members(recording_client):
    cli.main(["fetch", "--time-frame", "minute", "--symbol-status", "DELISTED",
              "--exchange", "USA Stocks"])
    assert recording_client.instances[0].fetch_args == [
        (TimeFrame.MINUTE, SymbolStatus.DELISTED, "USA Stocks")]

def test_fetch_without_options_leaves_every_filter_unset(recording_client):
    cli.main(["fetch"])
    assert recording_client.instances[0].fetch_args == [(None, None, None)]

def test_an_invalid_choice_names_the_valid_ones(capsys):
    with pytest.raises(SystemExit):
        cli.main(["fetch", "--symbol-status", "zombie"])
    assert "choose from active, delisted" in capsys.readouterr().err

def test_a_missing_command_is_a_usage_error(capsys):
    with pytest.raises(SystemExit) as exit_info:
        cli.main([])
    assert exit_info.value.code == 2

def test_an_error_outside_every_mapped_class_is_an_unknown_error():
    assert cli._exit_code_for(MarketHistoryDbError("unmapped")) is ErrorCode.UNKNOWN_ERROR


# --- what gets logged ----------------------------------------------------------------------

def test_an_account_error_is_reported_without_a_traceback(cli_client, caplog):
    # The user has to fix the token or the plan; a traceback would bury that message
    cli_client.append(UnauthorizedError("wrong token", 401))
    with caplog.at_level(logging.ERROR, logger=cli.__name__):
        cli.main(["fetch"])
    record = caplog.records[-1]
    assert record.exc_info is None
    assert "wrong token" in record.getMessage()

def test_a_config_error_is_reported_without_a_traceback(cli_client, caplog):
    cli_client.append(ConfigError("Required environment variable 'EODHD_API_TOKEN' is not set"))
    with caplog.at_level(logging.ERROR, logger=cli.__name__):
        cli.main(["fetch"])
    assert caplog.records[-1].exc_info is None
    assert "EODHD_API_TOKEN" in caplog.records[-1].getMessage()

@pytest.mark.parametrize("error", [RequestError("gave up"), RuntimeError("bug")])
def test_any_other_failure_is_logged_with_its_traceback(cli_client, caplog, error):
    # Logged rather than left to the interpreter, so that it reaches the (redacting) log file
    cli_client.append(error)
    with caplog.at_level(logging.ERROR, logger=cli.__name__):
        cli.main(["fetch"])
    assert caplog.records[-1].exc_info is not None
