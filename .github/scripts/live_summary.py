"""
Turns the JUnit XML of the live tests into the Markdown of the nightly run's summary page.

Usage: live_summary.py <JUnit XML file>; the Markdown goes to standard output. The tests are
listed in three groups: passed, failed, and not checked with the reason. A test skipped because
eodhd.com refused the account's token shows as "account refused: <error type>"; the first line
says whether the account's tests ran.
"""

import sys
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

PASSED = "Passed"
FAILED = "Failed"
NOT_CHECKED = "Not checked"

# The skip reasons of tests/live: a refused token, and a token not set at all
_PREFIX_ACCOUNT_REFUSED = "eodhd.com refused EODHD_API_TOKEN ("
_REASON_TOKEN_NOT_SET = "EODHD_API_TOKEN is not set"
_PREFIX_ACCOUNT_REFUSED_SHOWN = "account refused: "


@dataclass(frozen=True)
class Outcome:
    """The outcome of one test: its group, and the failure's first line or the skip's reason"""

    test: str  # Test's name as pytest reports it, with its parameters, e.g. "test_a[Earnings]"
    group: str  # PASSED, FAILED or NOT_CHECKED
    detail: str = ""  # Failure's first line or skip's reason as shown; "" for a passed test


def describe_skip(reason: str) -> str:
    """
    Describes why a test was not checked.

    :param reason: Reason the test was skipped with
    :return: "account refused: <error type>" for a refused token, else the reason itself
    """
    if not reason.startswith(_PREFIX_ACCOUNT_REFUSED):
        return reason
    error_type = reason.removeprefix(_PREFIX_ACCOUNT_REFUSED).partition(")")[0]
    return _PREFIX_ACCOUNT_REFUSED_SHOWN + error_type


def read_outcomes(junit_xml: str) -> list[Outcome]:
    """
    Reads the outcome of every test from pytest's JUnit XML.

    :param junit_xml: Content of the file pytest wrote with --junitxml
    :return: One outcome per test, in the order of the file; an error counts as failed
    """
    outcomes = []
    for case in ElementTree.fromstring(junit_xml).iter("testcase"):
        test = case.get("name", "")
        problem = next((child for child in case if child.tag in ("failure", "error")), None)
        skipped = case.find("skipped")
        if problem is not None:
            outcomes.append(Outcome(test, FAILED, _first_line(problem.get("message") or problem.text or "")))
        elif skipped is not None:
            outcomes.append(Outcome(test, NOT_CHECKED, describe_skip(skipped.get("message", ""))))
        else:
            outcomes.append(Outcome(test, PASSED))
    return outcomes


def describe_account_checks(outcomes: list[Outcome]) -> str:
    """
    Describes whether the tests that need the account's token ran.

    :param outcomes: Outcome of every test
    :return: "Account checks: not run (<why>)", naming each error type of a refusal, or
        "Account checks: run"
    """
    refusals = sorted({outcome.detail.removeprefix(_PREFIX_ACCOUNT_REFUSED_SHOWN) for outcome in outcomes
                       if outcome.detail.startswith(_PREFIX_ACCOUNT_REFUSED_SHOWN)})
    if refusals:
        return f"Account checks: not run ({', '.join(refusals)})"
    if any(outcome.detail == _REASON_TOKEN_NOT_SET for outcome in outcomes):
        return f"Account checks: not run ({_REASON_TOKEN_NOT_SET})"
    return "Account checks: run"


def render_summary(outcomes: list[Outcome]) -> str:
    """
    Renders the summary page.

    :param outcomes: Outcome of every test
    :return: Markdown: the account line, then the groups passed, failed and not checked, each
        with its count and its tests
    """
    lines = [describe_account_checks(outcomes), ""]
    for group in (PASSED, FAILED, NOT_CHECKED):
        members = [outcome for outcome in outcomes if outcome.group == group]
        lines += [f"**{group} ({len(members)})**", ""]
        lines += [f"- `{outcome.test}`" + (": " + outcome.detail if outcome.detail else "")
                  for outcome in members]
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    """
    Prints the summary of the JUnit XML file named by the only argument.

    :param argv: Command line, the script's name first
    :return: Exit code: 0, or 2 without exactly one file
    """
    if len(argv) != 2:
        print("Usage: live_summary.py <JUnit XML file>", file=sys.stderr)
        return 2
    print(render_summary(read_outcomes(Path(argv[1]).read_text(encoding="utf-8"))))
    return 0


def _first_line(text: str) -> str:
    """
    Picks the first line of a failure's message or text.

    :param text: Message or text, possibly empty
    :return: Its first line without surrounding blanks, or "" if there is none
    """
    return next(iter(text.strip().splitlines()), "")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
