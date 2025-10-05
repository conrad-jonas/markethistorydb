#!/usr/bin/env python12.9

"""Provides sql code to access SQLite DB and QuestDB"""

# --------- SQLite queries ---------

SQL_DELETE_SYMBOL_FROM_SYMBOL_META = "DELETE FROM symbol_meta WHERE symbol_code = :symbol_code"

SQL_CODE_INSERT_DUMMY_SYMBOL_INTO_SYMBOL_META = \
    """INSERT INTO symbol_meta (symbol_code, exchange_code, time_frame, symbol_status, name, country, currency, type, 
       isin) VALUES(:symbol_code, :exchange_code, "DAILY", "ACTIVE", "test_name", "test_country", "test_currency", 
       "test_type", "test_isin")"""

SQL_CODE_SELECT_SYMBOL_FROM_SYMBOL_META = """SELECT symbol_code FROM symbol_meta WHERE symbol_code=:symbol_code AND 
                                             exchange_code=:exchange_code AND time_frame=:time_frame AND 
                                             symbol_status=:symbol_status AND name=:name"""
SQL_SELECT_SYMBOL_FROM_SYMBOL_META = """SELECT symbol_code FROM symbol_meta WHERE symbol_code=:symbol_code AND 
                                        exchange_code=:exchange_code AND time_frame=:time_frame AND 
                                        symbol_status=:symbol_status AND name=:name"""

# --------- QuestDB queries --------

SQL_SELECT_CLOSE_FROM_DAILY_OHLCV = "SELECT close FROM daily_ohlcv WHERE timestamp = %s"
SQL_SELECT_CLOSE_FROM_MINUTE_OHLCV = "SELECT close FROM minute_ohlcv WHERE timestamp = %s"

SQL_SELECT_ALL_FROM_DAILY_OHLCV = ("SELECT timestamp, exchange_code, symbol_code, open, high, low, close, "
                                   "adjusted_close, volume "
                                   "FROM daily_ohlcv "
                                   "WHERE exchange_code = %s AND symbol_code IN ({}) "
                                   "AND %s <= timestamp AND timestamp <= %s")
SQL_SELECT_ALL_FROM_MINUTE_OHLCV = ("SELECT timestamp, exchange_code, symbol_code, gmt_offset, open, high, low, close, "
                                    "volume "
                                    "FROM minute_ohlcv "
                                    "WHERE exchange_code = %s AND symbol_code IN ({}) "
                                    "AND %s <= timestamp AND timestamp <= %s")



