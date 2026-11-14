"""Tests for .github/scripts/live_summary.py"""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def _load_script() -> ModuleType:
    """
    Loads the script by its path; .github/scripts is no package.

    :return: The script as a module, registered in sys.modules so that its dataclass resolves
    """
    filepath = Path(__file__).resolve().parents[3] / ".github" / "scripts" / "live_summary.py"
    spec = importlib.util.spec_from_file_location("live_summary", filepath)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


live_summary = _load_script()

_REFUSAL = "eodhd.com refused EODHD_API_TOKEN (DataLimitError): Daily API limit reached"


def _junit_xml(*testcases: str) -> str:
    """
    Wraps test cases in the frame of pytest's JUnit XML.

    :param testcases: <testcase> elements
    :return: The document
    """
    return ('<?xml version="1.0" encoding="utf-8"?><testsuites name="pytest tests">'
            '<testsuite name="pytest" errors="0" failures="0" skipped="0" tests="0" time="0.1">'
            + "".join(testcases) + "</testsuite></testsuites>")


def _passed(name: str) -> str:
    """
    Writes a passed test as pytest does.

    :param name: Test's name
    :return: Its <testcase> element
    """
    return f'<testcase classname="tests.live.test_eodhd_contract" name="{name}" time="0.1" />'


def _skipped(name: str, reason: str) -> str:
    """
    Writes a skipped test as pytest does.

    :param name: Test's name
    :param reason: Reason given to pytest.skip, escaped for XML
    :return: Its <testcase> element
    """
    return (f'<testcase classname="tests.live.test_eodhd_contract" name="{name}" time="0.0">'
            f'<skipped type="pytest.skip" message="{reason}">tests/live/test_eodhd_contract.py:153: {reason}</skipped>'
            '</testcase>')


def _failed(name: str, tag: str, message: str, text: str = "") -> str:
    """
    Writes a failed test as pytest does.

    :param name: Test's name
    :param tag: "failure" for a failed assertion, "error" for an error in setup or teardown
    :param message: Message attribute, escaped for XML
    :param text: Element's text, the traceback
    :return: Its <testcase> element
    """
    return (f'<testcase classname="tests.live.test_eodhd_contract" name="{name}" time="0.2">'
            f'<{tag} message="{message}">{text}</{tag}></testcase>')


def test_the_summary_lists_the_three_groups_under_the_account_line():
    junit_xml = _junit_xml(
        _passed("test_daily_prices_have_the_sample_s_shape"),
        _passed("test_every_fundamental_record_set_has_the_sample_s_shape[Earnings-History]"),
        _failed("test_minute_prices_have_the_sample_s_shape", "failure",
                "AssertionError: the field volume is missing&#10;assert 'volume' in {}"),
        _skipped("test_exchanges_have_the_sample_s_shape", _REFUSAL),
        _skipped("test_exchange_symbols_have_the_sample_s_shape", _REFUSAL),
    )
    summary = live_summary.render_summary(live_summary.read_outcomes(junit_xml))
    assert summary.split("\n") == [
        "Account checks: not run (DataLimitError)",
        "",
        "**Passed (2)**",
        "",
        "- `test_daily_prices_have_the_sample_s_shape`",
        "- `test_every_fundamental_record_set_has_the_sample_s_shape[Earnings-History]`",
        "",
        "**Failed (1)**",
        "",
        "- `test_minute_prices_have_the_sample_s_shape`: AssertionError: the field volume is missing",
        "",
        "**Not checked (2)**",
        "",
        "- `test_exchanges_have_the_sample_s_shape`: account refused: DataLimitError",
        "- `test_exchange_symbols_have_the_sample_s_shape`: account refused: DataLimitError",
        "",
    ]

def test_an_empty_group_shows_its_count_of_zero():
    summary = live_summary.render_summary([live_summary.Outcome("test_a", live_summary.PASSED)])
    assert "**Failed (0)**" in summary.splitlines()
    assert "**Not checked (0)**" in summary.splitlines()

def test_a_skip_for_another_reason_keeps_its_reason():
    assert live_summary.describe_skip("EODHD_API_TOKEN is not set") == "EODHD_API_TOKEN is not set"

def test_a_refusal_names_its_error_type():
    reason = "eodhd.com refused EODHD_API_TOKEN (AuthenticationError): 401 Unauthorized"
    assert live_summary.describe_skip(reason) == "account refused: AuthenticationError"

def test_every_error_type_of_a_refusal_is_named_once():
    outcomes = [live_summary.Outcome("test_a", live_summary.NOT_CHECKED, "account refused: DataLimitError"),
                live_summary.Outcome("test_b", live_summary.NOT_CHECKED, "account refused: AuthenticationError"),
                live_summary.Outcome("test_c", live_summary.NOT_CHECKED, "account refused: DataLimitError")]
    assert (live_summary.describe_account_checks(outcomes)
            == "Account checks: not run (AuthenticationError, DataLimitError)")

def test_a_token_not_set_means_the_account_checks_did_not_run():
    outcomes = [live_summary.Outcome("test_a", live_summary.PASSED),
                live_summary.Outcome("test_b", live_summary.NOT_CHECKED, "EODHD_API_TOKEN is not set")]
    assert live_summary.describe_account_checks(outcomes) == "Account checks: not run (EODHD_API_TOKEN is not set)"

def test_without_a_refusal_the_account_checks_ran():
    outcomes = [live_summary.Outcome("test_a", live_summary.PASSED),
                live_summary.Outcome("test_b", live_summary.NOT_CHECKED, "needs a weekday")]
    assert live_summary.describe_account_checks(outcomes) == "Account checks: run"

def test_an_error_counts_as_failed_with_its_message_s_first_line():
    junit_xml = _junit_xml(_failed("test_a", "error", "failed on setup with &quot;ConnectionError&quot;"))
    assert live_summary.read_outcomes(junit_xml) == [
        live_summary.Outcome("test_a", live_summary.FAILED, 'failed on setup with "ConnectionError"')]

def test_a_failure_without_a_message_shows_the_first_line_of_its_text():
    junit_xml = _junit_xml(_failed("test_a", "failure", "", "\nKeyError: 'code'\nmore lines"))
    assert live_summary.read_outcomes(junit_xml) == [
        live_summary.Outcome("test_a", live_summary.FAILED, "KeyError: 'code'")]

def test_a_failure_without_message_or_text_has_no_detail():
    junit_xml = _junit_xml(_failed("test_a", "failure", ""))
    assert live_summary.read_outcomes(junit_xml) == [live_summary.Outcome("test_a", live_summary.FAILED, "")]

def test_main_prints_the_summary_of_the_named_file(tmp_path, capsys):
    filepath = tmp_path / "live.xml"
    filepath.write_text(_junit_xml(_passed("test_a")), encoding="utf-8")
    assert live_summary.main(["live_summary.py", str(filepath)]) == 0
    assert capsys.readouterr().out.startswith("Account checks: run\n\n**Passed (1)**\n\n- `test_a`\n")

def test_main_without_exactly_one_file_prints_its_usage(capsys):
    assert live_summary.main(["live_summary.py"]) == 2
    assert capsys.readouterr().err == "Usage: live_summary.py <JUnit XML file>\n"
