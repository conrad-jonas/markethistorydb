#!/usr/bin/env python12.9

"""URL addresses, query parameters and query values for requesting data from eodhd.com"""

from urllib.parse import quote


def _path_segment(code: str) -> str:
    """
    Escapes *code* for use as a single URL path segment.

    :param code: Symbol or exchange code as the provider lists it
    :return: *code* with every character that could end the segment, the path or the query
        ('/', '?', '#', '%', ...) percent-encoded
    """
    # Codes come from the provider's own symbol lists, so they are not trusted to be URL-safe
    return quote(code, safe="")


class Url:

    class Address:
        BASE = "https://eodhd.com/api"
        EXCHANGES_LIST = f"{BASE}/exchanges-list/?"

        @staticmethod
        def exchange_symbol_list(exchange_url_code: str) -> str:
            return f"{Url.Address.BASE}/exchange-symbol-list/{_path_segment(exchange_url_code)}?"

        @staticmethod
        def eod(symbol_code: str, exchange_url_code: str) -> str:
            return f"{Url.Address.BASE}/eod/{_path_segment(symbol_code)}.{_path_segment(exchange_url_code)}?"

        @staticmethod
        def intraday(symbol_code: str, exchange_url_code: str) -> str:
            return f"{Url.Address.BASE}/intraday/{_path_segment(symbol_code)}.{_path_segment(exchange_url_code)}?"

        @staticmethod
        def fundamentals(symbol_code: str, exchange_url_code: str) -> str:
            return (f"{Url.Address.BASE}/fundamentals/{_path_segment(symbol_code)}."
                    f"{_path_segment(exchange_url_code)}?")

    class Param:
        API_TOKEN = "api_token"
        FMT = "fmt"
        FROM = "from"
        TO = "to"
        INTERVAL = "interval"
        DELISTED = "delisted"
        FILTER = "filter"

    class Value:
        JSON = "json"
        DELISTED = "1"
        INTERVAL_1M = "1m"
