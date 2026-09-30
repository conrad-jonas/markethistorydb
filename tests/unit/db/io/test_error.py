"""Tests for db/io/error.py: the ingress retry decorator"""

import json

import pytest
from questdb import QuestDBError, QuestDBErrorCode

from markethistorydb.db.io.error import catch_ingress_error
from markethistorydb.errors import InsertError, SchemaMismatchError


class Writer:
    """Fails its first *failures* writes with an QuestDBError, then succeeds"""

    def __init__(self, failures: int):
        self.failures = failures
        self.num_of_calls = 0

    @catch_ingress_error
    def write(self, rows, table_name=None):
        self.num_of_calls += 1
        if self.num_of_calls <= self.failures:
            raise QuestDBError(QuestDBErrorCode.ServerFlushError, "flush failed")
        return (rows, table_name)


def test_a_passing_write_returns_its_result_with_the_arguments_passed_through(slept):
    assert Writer(failures=0).write([1, 2], table_name="daily_ohlcv") == ([1, 2], "daily_ohlcv")
    assert slept == []

def test_a_failing_write_is_retried_until_it_passes(slept):
    writer = Writer(failures=2)
    assert writer.write([1]) == ([1], None)
    assert writer.num_of_calls == 3
    assert slept == [10.0, 20.0]

def test_a_write_that_keeps_failing_ends_in_an_insert_error_naming_the_method(slept):
    writer = Writer(failures=99)
    with pytest.raises(InsertError) as excinfo:
        writer.write([1])
    assert writer.num_of_calls == 3
    assert str(excinfo.value).startswith("Writer.write failed after 3 attempts")
    assert isinstance(excinfo.value.__cause__, QuestDBError)

def test_other_errors_pass_through_unretried(slept):
    class Broken:
        num_of_calls = 0

        @catch_ingress_error
        def write(self):
            Broken.num_of_calls += 1
            raise KeyError("column")

    with pytest.raises(KeyError):
        Broken().write()
    assert Broken.num_of_calls == 1

def test_the_decorated_function_keeps_its_name():
    assert Writer.write.__name__ == "write"
    assert Writer.write.__qualname__ == "Writer.write"


# --- performance: only a retry that can help is waited for ---------------------------------

@pytest.mark.parametrize("code", [QuestDBErrorCode.BadDataFrame, QuestDBErrorCode.InvalidTimestamp,
                                  QuestDBErrorCode.AuthError, QuestDBErrorCode.ServerRejection])
def test_an_error_no_retry_can_fix_is_an_insert_error_at_once(slept, code):
    class Rejected:
        num_of_calls = 0

        @catch_ingress_error
        def write(self):
            Rejected.num_of_calls += 1
            raise QuestDBError(code, "Timestamp -6942499200000000 is negative")

    with pytest.raises(InsertError) as excinfo:
        Rejected().write()
    # Retrying used to cost 10 + 20 s per symbol for a frame that cannot ever be written
    assert Rejected.num_of_calls == 1 and slept == []
    assert "Rejected.write failed: Timestamp -6942499200000000 is negative" in str(excinfo.value)
    assert excinfo.value.__cause__.code == code

@pytest.mark.parametrize("code", [QuestDBErrorCode.SocketError, QuestDBErrorCode.CouldNotResolveAddr,
                                  QuestDBErrorCode.ConnectTimeout, QuestDBErrorCode.ServerFlushError])
def test_an_error_of_an_unreachable_or_busy_host_is_retried(slept, code):
    class Flaky:
        num_of_calls = 0

        @catch_ingress_error
        def write(self):
            Flaky.num_of_calls += 1
            if Flaky.num_of_calls == 1:
                raise QuestDBError(code, "host went away")
            return "written"

    assert Flaky().write() == "written"
    assert slept == [10.0]


# --- records the server rejected: a retry would be rejected the same way -------------------

def _flush_error(answer: str) -> QuestDBError:
    """
    Builds the error the client raises when the server answers a flush with an error.

    :param answer: Server's answer, as the client quotes it
    :return: Error as the client raises it
    """
    return QuestDBError(QuestDBErrorCode.ServerFlushError, "Could not flush buffer: " + answer)

def _rejection(message: str) -> str:
    return json.dumps({"code": "invalid", "message": message, "line": 1, "errorId": "38f2d38a5ddb-2"})

class Rejected:
    """Fails every write with *error*, counting the calls"""

    def __init__(self, error: QuestDBError):
        self.error = error
        self.num_of_calls = 0

    @catch_ingress_error
    def write(self):
        self.num_of_calls += 1
        raise self.error

# Messages as QuestDB 10 words them with line.auto.create.new.columns=false
@pytest.mark.parametrize("message", [
    ("failed to parse line protocol:errors encountered on line(s):\nerror in line 1: table: probe, "
     "column: newCol does not exist, creating new columns is disabled"),
    ("failed to parse line protocol:errors encountered on line(s):\nerror in line 1: table: probe, "
     "column: v; cast error from protocol type: STRING to column type: DOUBLE"),
], ids=["unknown column", "wrong type"])
def test_records_that_do_not_fit_the_table_are_a_schema_mismatch_at_once(slept, message):
    rejected = Rejected(_flush_error(_rejection(message)))
    with pytest.raises(SchemaMismatchError) as excinfo:
        rejected.write()
    assert rejected.num_of_calls == 1 and slept == []
    assert str(excinfo.value) == "Rejected.write failed: " + message
    assert isinstance(excinfo.value.__cause__, QuestDBError)

def test_records_rejected_for_another_reason_are_an_insert_error_at_once(slept):
    rejected = Rejected(_flush_error(_rejection("error in line 1: table: exchange; cannot insert in non-WAL table")))
    with pytest.raises(InsertError) as excinfo:
        rejected.write()
    assert not isinstance(excinfo.value, SchemaMismatchError)
    assert rejected.num_of_calls == 1 and slept == []
    assert "cannot insert in non-WAL table" in str(excinfo.value)

def test_a_rejection_without_a_message_is_an_insert_error_all_the_same(slept):
    rejected = Rejected(_flush_error(json.dumps({"code": "invalid"})))
    with pytest.raises(InsertError) as excinfo:
        rejected.write()
    assert rejected.num_of_calls == 1
    assert str(excinfo.value) == "Rejected.write failed: "

@pytest.mark.parametrize("answer", [
    json.dumps({"code": "internal error", "message": "column: x does not exist"}),
    json.dumps(["invalid"]),
    "<html>502 Bad Gateway</html>",
], ids=["other code", "not an object", "not json"])
def test_a_flush_error_that_is_no_rejection_of_the_records_is_retried(slept, answer):
    rejected = Rejected(_flush_error(answer))
    with pytest.raises(InsertError) as excinfo:
        rejected.write()
    assert not isinstance(excinfo.value, SchemaMismatchError)
    assert rejected.num_of_calls == 3 and slept == [10.0, 20.0]
