"""Tests for the package's __init__.py: the public API and library logging etiquette"""

import logging

import markethistorydb


def test_the_public_api_is_importable_from_the_package():
    from markethistorydb import Client, Config, MarketHistoryDbError, SymbolStatus, TimeFrame
    assert all((Client, Config, MarketHistoryDbError, SymbolStatus, TimeFrame))

def test_the_package_only_adds_a_null_handler_and_leaves_the_rest_to_the_application():
    handlers = logging.getLogger(markethistorydb.__name__).handlers
    assert [type(handler) for handler in handlers] == [logging.NullHandler]
