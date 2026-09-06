#!/usr/bin/env python12.9


class StatementsExchange:
    UPDATE_EXCHANGE = (
        "UPDATE exchange SET name=%s, operating_mic=%s, country=%s, currency=%s, country_iso_2=%s, country_iso_3=%s"
        "WHERE exchange_code=%s")

    SELECT_ALL_FROM_EXCHANGE_BY_EXCHANGE_CODE = (
        "SELECT name, exchange_code, operating_mic, country, currency, country_iso_2, country_iso_3, created_at "
        "FROM exchange WHERE exchange_code=%s")