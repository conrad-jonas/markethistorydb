#!/usr/bin/env python12.9

"""Constants, data classes and helper functions for fetching and validating data from eodhd.com."""

from dataclasses import dataclass
from enum import Enum
import logging
import pandas as pd

import markethistorydb.db.tables as tables

logger = logging.getLogger(__name__)

# QuestDB stores no designated timestamp before the Unix epoch: the server rejects one written
# through SQL, and the ingress client refuses to send one
_EPOCH = pd.Timestamp(0)


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


# Table the records of each fundamental type are written to, in the order they are requested
# and written. Sector and industry are a single record per symbol and go to tables.Sector.
TABLE_PER_FUNDAMENTAL_TYPE: dict[FundamentalType, type[tables.FundamentalTable]] = {
    FundamentalType.EARNINGS_QUARTERLY:         tables.EarningsQuarterly,
    FundamentalType.EARNINGS_ANNUALLY:          tables.EarningsAnnually,
    FundamentalType.BALANCE_SHEET_QUARTERLY:    tables.BalanceSheetQuarterly,
    FundamentalType.BALANCE_SHEET_ANNUALLY:     tables.BalanceSheetAnnually,
    FundamentalType.CASH_FLOW_QUARTERLY:        tables.CashFlowQuarterly,
    FundamentalType.CASH_FLOW_ANNUALLY:         tables.CashFlowAnnually,
    FundamentalType.INCOME_STATEMENT_QUARTERLY: tables.IncomeStatementQuarterly,
    FundamentalType.INCOME_STATEMENT_ANNUALLY:  tables.IncomeStatementAnnually,
}


def convert_df_column_names_from_camel_to_snake_case(df: pd.DataFrame) -> pd.DataFrame:
    """
    Converts column names of dataframe from camel case to snake case.

    :param df: Dataframe whose columns are renamed in place
    :return: The same dataframe, with renamed columns
    """
    df.columns = (df.columns.str.replace('(?<=[a-z])(?=[A-Z])', '_', regex=True).str.lower())
    return df


def drop_records_before_1970(df: pd.DataFrame, timestamp_column: str, records_name: str,
                             symbol_name: str) -> pd.DataFrame:
    """
    Drops the records whose designated timestamp is before 1970, which QuestDB cannot store,
    and logs a warning naming how many were dropped.

    :param df: Records, *timestamp_column* holding datetimes; the frame is not modified
    :param timestamp_column: Designated timestamp column of the table the records are written to
    :param records_name: What the records are, for the log, e.g. "DAILY price"
    :param symbol_name: Symbol the records belong to, for the log, e.g. "IBM.NYSE"
    :return: New frame with the records from 1970 on and a fresh index
    """
    df_kept = df[df[timestamp_column] >= _EPOCH].reset_index(drop=True)
    num_of_dropped = len(df) - len(df_kept)
    if num_of_dropped:
        logger.warning("Dropped {0} {1} records of {2} from before 1970, which QuestDB cannot store".format(
            num_of_dropped, records_name, symbol_name))
    return df_kept
