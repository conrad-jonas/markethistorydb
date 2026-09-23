#!/usr/bin/env python12.9

"""Enums and helper functions"""

from dataclasses import dataclass
from enum import Enum
import pandas as pd


@dataclass(frozen=True)
class FailedSymbol:
    """A symbol whose download failed, and what kind of error caused it"""

    symbol_code:      str
    exchange_code:    str
    error_type_name:  str


class FundamentalType(Enum):
    """Describes type of fundamental data requested from eodhd.com"""
    SECTOR_AND_INDUSTRY         = 1
    EARNINGS_QUARTERLY          = 2
    EARNINGS_ANNUALLY           = 3
    BALANCE_SHEET_QUARTERLY     = 4
    BALANCE_SHEET_ANNUALLY      = 5
    CASH_FLOW_QUARTERLY         = 6
    CASH_FLOW_ANNUALLY          = 7
    INCOME_STATEMENT_QUARTERLY  = 8
    INCOME_STATEMENT_ANNUALLY   = 9


def convert_df_column_names_from_camel_to_snake_case(df: pd.DataFrame) -> pd.DataFrame:
    """
    Converts column names of dataframe from camel case to snake case.

    :param df: Dataframe whose columns are renamed in place
    :return: The same dataframe, with renamed columns
    """
    df.columns = (df.columns.str.replace('(?<=[a-z])(?=[A-Z])', '_', regex=True).str.lower())
    return df