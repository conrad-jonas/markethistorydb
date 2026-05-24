#!/usr/bin/env python12.9


class StatementsSymbol:
    INSERT_DUMMY_SYMBOL_INTO_SYMBOL = (
        'INSERT INTO symbol (symbol_code, exchange_code, time_frame, symbol_status, name, country, currency, type, '
        'isin) VALUES(%s, %s, "DAILY", "ACTIVE", %s, "test_country", "test_currency", "test_type", "test_isin")')

    UPDATE_SYMBOL = (
        "UPDATE symbol SET name=%s, country=%s, currency=%s, type=%s "
        "WHERE symbol_code=%s AND exchange_code=%s AND time_frame=%s AND symbol_status=%s")
    UPDATE_SECTOR = (
        "UPDATE sector SET sector=%s, industry=%s, gic_sector=%s, gic_group=%s, gic_industry=%s, gic_sub_industry=%s "
        "FROM sector WHERE symbol_code=%s AND exchange_code=%s")

    SELECT_ALL_FROM_SYMBOL_BY_UNIQUE_KEYS = (
        "SELECT symbol_code, exchange_code, time_frame, symbol_status, name, country, currency, type, isin "
        "FROM symbol WHERE symbol_code=%s AND exchange_code=%s AND time_frame=%s AND symbol_status=%s")
    SELECT_ALL_FROM_SECTOR_BY_UNIQUE_KEYS = (
        "SELECT symbol_code, sector, industry, gic_sector, gic_group, gic_industry, gic_sub_industry "
        "FROM sector WHERE symbol_code=%s AND exchange_code=%s")

    DROP_SYMBOL_FROM_TABLE = (
        "CREATE TABLE {table_name}_copy AS (",
        "SELECT * FROM {table_name} WHERE symbol_code!=%s AND exchange_code!=%s",
        ") TIMESTAMP(created_at) PARTITION BY DAY",
        "DEDUP UPSERT KEYS({unique_key_columns});",
        "DROP TABLE {table_name};",
        "RENAME TABLE {table_name}_copy TO {table_name};")