"""Tests for utils/redact.py"""

import pytest

from markethistorydb.utils import redact_api_token
from markethistorydb.utils.redact import REDACTED


@pytest.mark.parametrize("text, expected", [
    ("https://eodhd.com/api/eod/AAPL.US?api_token=SECRET&fmt=json",
     "https://eodhd.com/api/eod/AAPL.US?api_token=***&fmt=json"),
    ("https://eodhd.com/api/eod/AAPL.US?fmt=json&api_token=SECRET",
     "https://eodhd.com/api/eod/AAPL.US?fmt=json&api_token=***"),
    ("{'api_token': 'SECRET', 'fmt': 'json'}", "{'api_token': '***', 'fmt': 'json'}"),
    ('{"api_token": "SECRET"}', '{"api_token": "***"}'),
    ("api_token = SECRET)", "api_token = ***)"),
])
def test_the_token_is_masked_wherever_it_appears(text, expected):
    assert redact_api_token(text) == expected

def test_every_occurrence_on_a_line_is_masked():
    text = "first ?api_token=ONE&x=1, then retried with ?api_token=TWO"
    redacted = redact_api_token(text)
    assert "ONE" not in redacted and "TWO" not in redacted
    assert redacted.count(REDACTED) == 2

def test_every_line_of_a_multi_line_text_is_masked():
    text = "Traceback:\n  url=/eod/?api_token=SECRET\n  params={'api_token': 'SECRET'}\n"
    assert "SECRET" not in redact_api_token(text)

@pytest.mark.parametrize("text", [
    "no token here",
    "api_token_hint=keep",
    "",
])
def test_text_without_a_token_is_left_unchanged(text):
    assert redact_api_token(text) == text
