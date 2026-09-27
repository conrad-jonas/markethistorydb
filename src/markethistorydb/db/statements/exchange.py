#!/usr/bin/env python12.9

import markethistorydb.db.tables as tables

_TABLE          = tables.Exchange.NAME
_COLUMNS        = ", ".join(tables.Exchange.ALL_COLUMNS)
_NAME           = tables.Exchange.Columns.NAME
_EXCHANGE_CODE  = tables.Exchange.Columns.EXCHANGE_CODE
_OPERATING_MIC  = tables.Exchange.Columns.OPERATING_MIC
_COUNTRY        = tables.Exchange.Columns.COUNTRY
_CURRENCY       = tables.Exchange.Columns.CURRENCY
_COUNTRY_ISO_2  = tables.Exchange.Columns.COUNTRY_ISO_2
_COUNTRY_ISO_3  = tables.Exchange.Columns.COUNTRY_ISO_3
_PLACEHOLDERS   = ", ".join(["%s"] * len(tables.Exchange.ALL_COLUMNS))


class StatementsExchange:
    INSERT_EXCHANGE = f"INSERT INTO {_TABLE} ({_COLUMNS}) VALUES ({_PLACEHOLDERS})"

    UPDATE_EXCHANGE = (
        f"UPDATE {_TABLE} SET {_NAME}=%s, {_OPERATING_MIC}=%s, {_COUNTRY}=%s, {_CURRENCY}=%s, "
        f"{_COUNTRY_ISO_2}=%s, {_COUNTRY_ISO_3}=%s WHERE {_EXCHANGE_CODE}=%s")

    SELECT_ALL_FROM_EXCHANGE_BY_EXCHANGE_CODE = f"SELECT {_COLUMNS} FROM {_TABLE} WHERE {_EXCHANGE_CODE}=%s"
