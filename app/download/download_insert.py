#!/usr/bin/env python12.9

"""Inserts trading data from eodhd.com into DB"""
from download.download_helpers import convert_df_column_names_from_camel_to_snake_case
from misc.data_types import TimeFrame, SymbolStatus

import db.db_access as db_access
import db.db_const  as db_const

import pandas as pd


def insert_price_data(df_symbol, symbol_code: str, exchange_code: str,
                      time_frame: TimeFrame, symbol_status: SymbolStatus):
    db_access.insert_ohlcv_data(df_symbol, symbol_code, exchange_code, time_frame, symbol_status)

def insert_symbol_meta_data(series_exchange_symbol: pd.Series, symbol_code: str, exchange_code: str,
                            time_frame: TimeFrame, symbol_status: SymbolStatus):
    """Insert symbol meta data into DB"""
    df = series_exchange_symbol.to_frame().T
    db_access.insert_symbol_meta_data(df, symbol_code, exchange_code, time_frame, symbol_status)

def insert_symbol_sector_data(series_sector_and_industry: pd.Series, symbol_id: int):
    """Insert sector data for symbol into DB"""
    # Inserts symbol ID into series.
    series_sector_and_industry = pd.concat([pd.Series([symbol_id]), series_sector_and_industry])
    series_sector_and_industry.index = pd.Index(db_const.COLUMNS_SYMBOL_SECTOR[1:])
    # Inserts into DB
    df_sector_and_industry = series_sector_and_industry.to_frame().T
    db_access.insert_df_into_sqlite(df_sector_and_industry, db_const.TABLE_SYMBOL_SECTOR)

def insert_historic_fundamental_data(df_fundamental: pd.DataFrame, symbol_id: int, table_name: str):
    """Insert historical fundamental table data for symbol into DB"""
    # Inserts symbol ID into dataframe.
    df_fundamental[db_const.COLUMN_SYMBOL_META_ID] = symbol_id
    df_fundamental = convert_df_column_names_from_camel_to_snake_case(df_fundamental)
    db_access.insert_df_into_sqlite(df_fundamental, table_name)

