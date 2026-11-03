"""Tests for tests/integration_support/database_choice.py"""

import pytest

from tests.integration_support.database_choice import (
    DEFAULT_IMAGE,
    Container,
    Override,
    Skip,
    choose_test_database,
)

_OVERRIDE = {"QUESTDB_TEST_HOST": "127.0.0.1", "QUESTDB_TEST_PG_PORT": "18812",
             "QUESTDB_TEST_HTTP_PORT": "19000"}


@pytest.mark.parametrize("docker_available", [True, False])
def test_the_named_instance_is_used_whether_or_not_docker_answers(docker_available):
    choice = choose_test_database(_OVERRIDE, docker_available)
    assert choice == Override(host="127.0.0.1", pg_port=18812, http_port=19000, user="admin",
                              password="quest")

def test_the_named_instance_takes_user_and_password_from_the_variables():
    environment = {**_OVERRIDE, "QUESTDB_TEST_USER": "tester", "QUESTDB_TEST_PASSWORD": "secret"}
    choice = choose_test_database(environment, docker_available=True)
    assert (choice.user, choice.password) == ("tester", "secret")

def test_without_the_variables_a_container_of_the_pinned_release_is_started():
    assert choose_test_database({}, docker_available=True) == Container(image=DEFAULT_IMAGE)

def test_the_container_image_can_be_replaced():
    # The nightly run checks the newest release this way
    environment = {"QUESTDB_TEST_IMAGE": "questdb/questdb:latest"}
    choice = choose_test_database(environment, docker_available=True)
    assert choice == Container(image="questdb/questdb:latest")

@pytest.mark.parametrize("missing", ["QUESTDB_TEST_HOST", "QUESTDB_TEST_PG_PORT", "QUESTDB_TEST_HTTP_PORT"])
def test_a_partial_set_of_variables_counts_as_unset(missing):
    environment = {name: value for name, value in _OVERRIDE.items() if name != missing}
    assert choose_test_database(environment, docker_available=True) == Container(image=DEFAULT_IMAGE)
    assert isinstance(choose_test_database(environment, docker_available=False), Skip)

def test_an_empty_variable_counts_as_unset():
    environment = {**_OVERRIDE, "QUESTDB_TEST_HOST": ""}
    assert choose_test_database(environment, docker_available=True) == Container(image=DEFAULT_IMAGE)

def test_without_the_variables_and_docker_the_tests_are_skipped_with_both_ways_named():
    choice = choose_test_database({}, docker_available=False)
    assert isinstance(choice, Skip)
    assert "QUESTDB_TEST_" in choice.message
    assert "Docker" in choice.message
