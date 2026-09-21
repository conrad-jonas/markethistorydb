#!/usr/bin/env python12.9

"""URL addresses, query parameters and query values for requesting data from eodhd.com"""


class Url:

    class Address:
        BASE = "https://eodhd.com/api"
        EXCHANGES_LIST = f"{BASE}/exchanges-list/?"

        @staticmethod
        def exchange_symbol_list(exchange_url_code: str) -> str:
            return f"{Url.Address.BASE}/exchange-symbol-list/{exchange_url_code}?"

        @staticmethod
        def eod(symbol_code: str, exchange_url_code: str) -> str:
            return f"{Url.Address.BASE}/eod/{symbol_code}.{exchange_url_code}?"

        @staticmethod
        def intraday(symbol_code: str, exchange_url_code: str) -> str:
            return f"{Url.Address.BASE}/intraday/{symbol_code}.{exchange_url_code}?"

        @staticmethod
        def fundamentals(symbol_code: str, exchange_url_code: str) -> str:
            return f"{Url.Address.BASE}/fundamentals/{symbol_code}.{exchange_url_code}?"

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
