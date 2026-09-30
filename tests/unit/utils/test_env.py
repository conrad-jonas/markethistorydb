"""Tests for utils/env.py"""

import pytest

from markethistorydb.errors import ConfigError
from markethistorydb.utils import require_env


def test_a_set_variable_is_returned_as_is(monkeypatch):
    monkeypatch.setenv("MHDB_TEST_VARIABLE", " value with spaces ")
    assert require_env("MHDB_TEST_VARIABLE") == " value with spaces "

@pytest.mark.parametrize("value", [None, ""])
def test_an_unset_or_empty_variable_is_a_config_error_naming_it(monkeypatch, value):
    # An empty token would otherwise only fail at the provider, as a rejected request
    if value is None:
        monkeypatch.delenv("MHDB_TEST_VARIABLE", raising=False)
    else:
        monkeypatch.setenv("MHDB_TEST_VARIABLE", value)
    with pytest.raises(ConfigError) as excinfo:
        require_env("MHDB_TEST_VARIABLE")
    assert "MHDB_TEST_VARIABLE" in str(excinfo.value)
