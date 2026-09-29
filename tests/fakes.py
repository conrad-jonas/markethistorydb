"""Test doubles shared by the unit and integration tests"""

from json import JSONDecodeError
from pathlib import Path
from typing import Any
import json

# Sample payloads of the eodhd.com endpoints, trimmed from real responses where the public demo
# token serves them (eod, intraday, fundamentals) and written after the documented format
# otherwise (exchanges-list, exchange-symbol-list)
DIRPATH_EODHD_PAYLOADS = Path(__file__).resolve().parent / "data" / "eodhd"


def load_payload(name: str) -> Any:
    """
    Loads a sample payload of an eodhd.com endpoint.

    :param name: File name of the payload without its .json suffix, e.g. "fundamentals"
    :return: The parsed payload, freshly loaded, so that a test may modify it
    """
    with open(DIRPATH_EODHD_PAYLOADS / "{0}.json".format(name), encoding="utf-8") as file:
        return json.load(file)


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


class FakeScriptedApi:
    """
    Stands in for requests.get without any knowledge of eodhd.com: answers each request with the
    next response the test queued, whatever the URL, repeating the last one, and counts the calls.

    A queued exception is raised instead of answered, as requests raises a timeout or a refused
    connection.

    Suits tests of the request layer itself (statuses, retries, malformed bodies), which script
    the exact sequence of answers. Tests of the code built on the request layer, which need a
    realistic payload per endpoint, use FakeRoutedApi instead.
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


class FakeRoutedApi:
    """
    Stands in for requests.get like eodhd.com would: routes each request by its URL to the sample
    payload of the endpoint, whatever the order of the requests, and records every request with
    its query parameters.

    A route can be overridden with a payload, a FakeResponse, an exception to raise, or a
    callable taking (url, params) and returning any of these.

    Suits tests of the code built on the request layer (requesting, downloading, writing), where
    the answer depends on the endpoint rather than on the order of the calls. Tests that script
    the exact sequence of answers regardless of the URL use FakeScriptedApi instead.
    """

    # URL fragment of each endpoint, and the sample payload it answers with
    _ROUTES = (
        ("/exchanges-list/",       "exchanges-list"),
        ("/exchange-symbol-list/", "exchange-symbol-list"),
        ("/eod/",                  "eod"),
        ("/intraday/",             "intraday"),
        ("/fundamentals/",         "fundamentals"),
    )

    def __init__(self):
        self.requests: list[tuple[str, dict[str, Any]]] = []
        self._overrides: dict[str, Any] = {}

    def override(self, url_fragment: str, answer: Any):
        """
        Answers every request whose URL contains *url_fragment* with *answer* instead.

        :param url_fragment: Part of the URL to match, e.g. "/eod/" or "/eod/AAPL.US"
        :param answer: Payload, FakeResponse, exception, or callable taking (url, params)
        """
        self._overrides[url_fragment] = answer

    def urls(self, url_fragment: str = "") -> list[str]:
        """
        Lists the requested URLs.

        :param url_fragment: Only URLs containing it are listed (all if empty)
        :return: Requested URLs, in request order
        """
        return [url for url, _ in self.requests if url_fragment in url]

    def params(self, url_fragment: str) -> list[dict[str, Any]]:
        """
        Lists the query parameters of the requests to one endpoint.

        :param url_fragment: Part of the URL to match
        :return: Query parameters of every matching request, in request order
        """
        return [params for url, params in self.requests if url_fragment in url]

    def get(self, url, params=None, timeout=None) -> FakeResponse:
        self.requests.append((url, dict(params or {})))
        assert timeout is not None
        answer = None
        # The longest matching fragment wins, so "/eod/AAPL.US" beats "/eod/"
        for fragment in sorted(self._overrides, key=len, reverse=True):
            if fragment in url:
                answer = self._overrides[fragment]
                break
        else:
            for fragment, payload_name in self._ROUTES:
                if fragment in url:
                    answer = load_payload(payload_name)
                    break
            else:
                raise AssertionError("No route for {0}".format(url))
        if callable(answer) and not isinstance(answer, FakeResponse):
            answer = answer(url, params)
        if isinstance(answer, BaseException):
            raise answer
        if isinstance(answer, FakeResponse):
            return answer
        return FakeResponse(200, payload=answer)


class FakeClock:
    """Stands in for the time module; sleeping advances the clock instead of blocking"""

    def __init__(self):
        self.now = 0.0
        self.naps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, secs: float):
        self.naps.append(secs)
        self.now += secs


class FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def execute(self, query, params):
        return self._rows


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


class RecordingQuery:
    """
    Stands in for db.io.Query: records every statement with its parameters and answers from a
    queue of result sets, repeating the last one.
    """

    def __init__(self, *results: list[tuple]):
        self.statements: list[tuple[str, list[Any]]] = []
        self._results: list[list[tuple]] = list(results) or [[]]

    def execute(self, query, params) -> list[tuple]:
        # Rendered without a connection, as psycopg quotes identifiers and literals then
        self.statements.append((query.as_string(None), list(params)))
        return self._results[min(len(self.statements) - 1, len(self._results) - 1)]

    @property
    def texts(self) -> list[str]:
        """
        Lists the executed statements.

        :return: Statement texts, in execution order
        """
        return [text for text, _ in self.statements]


class Recorder:
    """
    Records every method called on it, and answers with the value configured for the method.

    A configured value that is callable is called with the method's arguments instead.
    """

    def __init__(self, **answers: Any):
        self.calls: list[tuple[str, tuple, dict]] = []
        self._answers = answers

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)

        def method(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            answer = self._answers.get(name)
            return answer(*args, **kwargs) if callable(answer) else answer
        return method

    def called(self, name: str) -> list[tuple]:
        """
        Lists the arguments of every call of one method.

        :param name: Name of the method
        :return: Positional arguments of each call, in call order
        """
        return [args for called_name, args, _ in self.calls if called_name == name]


class FakeDb:
    """Stands in for db.Database; every interface records its calls"""

    def __init__(self, **read_answers: Any):
        self.read = Recorder(**read_answers)
        self.insert = Recorder()
        self.update = Recorder()
        self.delete = Recorder()
