"""Tests for the package's __main__.py (python -m markethistorydb)"""

import runpy
import pytest

from markethistorydb import cli


def test_running_the_package_exits_with_the_code_main_returns(monkeypatch):
    monkeypatch.setattr(cli, "main", lambda: 7)
    with pytest.raises(SystemExit) as exit_info:
        runpy.run_module("markethistorydb", run_name="__main__")
    assert exit_info.value.code == 7
