#!/usr/bin/env python12.9

"""Class for requesting fundamental data from eodhd.com"""

import pandas as pd

from collections.abc import Callable

from markethistorydb.db                       import tables
from markethistorydb.errors                    import CompatibilityError
from markethistorydb.fetch.utils              import (FundamentalType, TABLE_PER_FUNDAMENTAL_TYPE,
                                                     convert_df_column_names_from_camel_to_snake_case)
from markethistorydb.fetch.eodhd.request_data import JsonObject, RequestData
from markethistorydb.fetch.eodhd.url          import Url
from markethistorydb.utils         import TimeFrame

# Keys of the sector and industry values in the payload, in the order of tables.Sector's columns
_SECTOR_AND_INDUSTRY_KEYS = ("General::Sector", "General::Industry", "General::GicSector",
                             "General::GicGroup", "General::GicIndustry", "General::GicSubIndustry")
# Columns of tables.Sector the payload provides: all but the symbol and exchange code the writer
# adds
_SECTOR_AND_INDUSTRY_COLUMNS = tables.Sector.ALL_COLUMNS[2:]
# Columns every fundamental table has that the writer adds, so the payload does not carry them
_COLUMNS_ADDED_BY_WRITER = (tables.EarningsQuarterly.Columns.SYMBOL_CODE,
                            tables.EarningsQuarterly.Columns.EXCHANGE_CODE)
# Columns the payload carries that have no counterpart in the tables
_COLUMNS_NOT_STORED = {
    FundamentalType.BALANCE_SHEET_QUARTERLY:    ["preferredStockRedeemable"],
    FundamentalType.BALANCE_SHEET_ANNUALLY:     ["preferredStockRedeemable"],
    FundamentalType.INCOME_STATEMENT_QUARTERLY: ["preferredStockAndOtherAdjustments"],
    FundamentalType.INCOME_STATEMENT_ANNUALLY:  ["preferredStockAndOtherAdjustments"],
}


class RequestFundamentalData(RequestData):
    def __init__(self, api_token: str, time_frame: TimeFrame, series_symbol: pd.Series,
                 should_stop: Callable[[], bool] | None = None):
        super().__init__(api_token, time_frame, should_stop)
        self._symbol_code: str = series_symbol[tables.Symbol.Columns.SYMBOL_CODE]
        self._exchange_url_code: str = series_symbol["exchange_url_code"]

    def _get_url_for_fundamental_data(self) -> str:
        return Url.Address.fundamentals(self._symbol_code, self._exchange_url_code)

    def _get_url_params_for_fundamental_data(self) -> dict[str, str]:
        filter_value = ("General::Sector,General::Industry,General::GicSector,General::GicGroup,General::GicIndustry,"
                        "General::GicSubIndustry,Earnings::History,Earnings::Annual,Financials::Balance_Sheet,"
                        "Financials::Cash_Flow,Financials::Income_Statement")
        url_params = {
            Url.Param.API_TOKEN: self._api_token,
            Url.Param.FMT: Url.Value.JSON,
            Url.Param.FILTER: filter_value,
        }
        return url_params

    @staticmethod
    def _check_sector_and_industry_data(series_sector_and_industry: pd.Series):
        """
        Checks that sector and industry hold one value per column of the sector table.

        :param series_sector_and_industry: Sector and industry values of the symbol
        :raises CompatibilityError: If the number of values does not match the sector table
        """
        if series_sector_and_industry.shape[0] != len(_SECTOR_AND_INDUSTRY_COLUMNS):
            raise CompatibilityError("Sector and industry data has unexpected structure!")

    def _check_fundamental_data(self, series_sector_and_industry: pd.Series,
                                dict_fundamental_data: dict[FundamentalType, pd.DataFrame]):
        """
        Checks that every fundamental record set holds the columns of the table it goes to.

        :param series_sector_and_industry: Sector and industry values of the symbol
        :param dict_fundamental_data: Records per fundamental type
        :raises CompatibilityError: If sector and industry or one of the record sets does not
            have the expected structure
        """
        self._check_sector_and_industry_data(series_sector_and_industry)
        for fundamental_type, df_fundamental in dict_fundamental_data.items():
            table = TABLE_PER_FUNDAMENTAL_TYPE[fundamental_type]
            expected_column_names = [column for column in table.ALL_COLUMNS
                                     if column not in _COLUMNS_ADDED_BY_WRITER]
            if not self._has_columns(df_fundamental, expected_column_names):
                raise CompatibilityError("{0} data has unexpected structure!".format(
                    fundamental_type.name.replace("_", " ").capitalize()))

    @staticmethod
    def _rearrange_fundamental_data(
            data_fundamental: JsonObject
    ) -> tuple[pd.Series, dict[FundamentalType, pd.DataFrame]]:
        """
        Splits the payload into sector and industry and one record set per fundamental type.

        :param data_fundamental: Parsed payload of the fundamentals endpoint
        :return: Sector and industry values, and records per fundamental type with one row per
            reporting period
        :raises CompatibilityError: If a section is missing or not shaped as expected
        """
        try:
            series_sector_and_industry = pd.Series(
                [data_fundamental[key] for key in _SECTOR_AND_INDUSTRY_KEYS])
            balance_sheet    = data_fundamental["Financials::Balance_Sheet"]
            cash_flow        = data_fundamental["Financials::Cash_Flow"]
            income_statement = data_fundamental["Financials::Income_Statement"]
            dict_fundamental_data: dict[FundamentalType, pd.DataFrame] = {
                FundamentalType.EARNINGS_QUARTERLY:         pd.DataFrame(data_fundamental["Earnings::History"]).T,
                FundamentalType.EARNINGS_ANNUALLY:          pd.DataFrame(data_fundamental["Earnings::Annual"]).T,
                FundamentalType.BALANCE_SHEET_QUARTERLY:    pd.DataFrame(balance_sheet["quarterly"]).T,
                FundamentalType.BALANCE_SHEET_ANNUALLY:     pd.DataFrame(balance_sheet["yearly"]).T,
                FundamentalType.CASH_FLOW_QUARTERLY:        pd.DataFrame(cash_flow["quarterly"]).T,
                FundamentalType.CASH_FLOW_ANNUALLY:         pd.DataFrame(cash_flow["yearly"]).T,
                FundamentalType.INCOME_STATEMENT_QUARTERLY: pd.DataFrame(income_statement["quarterly"]).T,
                FundamentalType.INCOME_STATEMENT_ANNUALLY:  pd.DataFrame(income_statement["yearly"]).T,
            }
        except (KeyError, TypeError, ValueError) as error:
            raise CompatibilityError("Fundamental data has unexpected structure: {0}: {1}".format(
                type(error).__name__, error)) from error
        return series_sector_and_industry, dict_fundamental_data

    @staticmethod
    def _format_fundamental_data(
            dict_fundamental_data: dict[FundamentalType, pd.DataFrame]) -> dict[FundamentalType, pd.DataFrame]:
        """
        Drops the record sets without any records and the columns that are not stored, and
        renames the remaining columns from camel case to snake case.

        :param dict_fundamental_data: Records per fundamental type, as rearranged from the payload
        :return: Record sets that hold at least one record, columns in snake case. A type the
            provider has no records for is left out, so that the symbol's stored records of that
            type are kept rather than replaced by nothing.
        """
        dict_formatted: dict[FundamentalType, pd.DataFrame] = {}
        for fundamental_type, df_fundamental in dict_fundamental_data.items():
            if df_fundamental.empty:
                continue
            df_fundamental = df_fundamental.drop(
                columns=_COLUMNS_NOT_STORED.get(fundamental_type, []), errors="ignore")
            dict_formatted[fundamental_type] = convert_df_column_names_from_camel_to_snake_case(df_fundamental)
        return dict_formatted

    def get(self) -> tuple[pd.Series, dict[FundamentalType, pd.DataFrame]]:
        """
        Requests fundamental data for symbol.

        :return: Sector and industry of the symbol, and its records per fundamental type, with
            every type that has no records left out; both empty if the provider has no
            fundamental data for the symbol
        :raises CompatibilityError: If the payload or one of its record sets does not have the
            expected structure
        :raises RequestError: If the request still fails once the retries are used up
        :raises AccountError: If the token, the plan's data limit or its access rights are what
            failed
        :raises UserInterruptError: If should_stop returned True while waiting to retry
        """
        url_fundamental = self._get_url_for_fundamental_data()
        url_params      = self._get_url_params_for_fundamental_data()
        # Requests data
        data_fundamental = self._request_object(url_fundamental, url_params)
        if data_fundamental:
            # Rearranges and formats data
            series_sector_and_industry, dict_fundamental_data = self._rearrange_fundamental_data(data_fundamental)
            dict_fundamental_data = self._format_fundamental_data(dict_fundamental_data)
            self._check_fundamental_data(series_sector_and_industry, dict_fundamental_data)
        else:
            series_sector_and_industry, dict_fundamental_data = pd.Series(dtype=object), {}

        return series_sector_and_industry, dict_fundamental_data
