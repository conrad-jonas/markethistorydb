"""Fails on purpose: shows that a failing unit test fails the unit checks (CI-T01)"""

import pytest


def test_a_failing_unit_test_fails_the_unit_checks():
    pytest.fail("Fails on purpose, to show that the unit checks catch a failing test")
