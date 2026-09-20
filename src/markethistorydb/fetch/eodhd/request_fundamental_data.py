#!/usr/bin/env python12.9

"""Class for requesting fundamental data from eodhd.com"""

from typing import Any
import pandas as pd

from markethistorydb.db                       import tables
from markethistorydb.fetch.utils              import FundamentalType, convert_df_column_names_from_camel_to_snake_case
from markethistorydb.fetch.eodhd.errors       import CompatibilityError
from markethistorydb.fetch.eodhd.request_data import RequestData
from markethistorydb.utils         import TimeFrame

class RequestFundamentalData(RequestData):
    def __init__(self, api_token: str, time_frame: TimeFrame, series_symbol: pd.Series):
        self._api_token: str = api_token
        self._time_frame: TimeFrame = time_frame
        self._symbol_code: str = series_symbol[tables.Symbol.Columns.SYMBOL_CODE]
        self._exchange_url_code: str = series_symbol["exchange_url_code"]

    def _get_url_for_fundamental_data(self) -> str:
        return RequestData.Url.fundamentals(self._symbol_code, self._exchange_url_code)

    def _get_url_params_for_fundamental_data(self) -> dict[str, str]:
        filter_value = ("General::Sector,General::Industry,General::GicSector,General::GicGroup,General::GicIndustry,"
                        "General::GicSubIndustry,Earnings::History,Earnings::Annual,Financials::Balance_Sheet,"
                        "Financials::Cash_Flow,Financials::Income_Statement")
        url_params = {
            RequestData.Params.API_TOKEN: self._api_token,
            RequestData.Params.FMT: RequestData.Values.JSON,
            RequestData.Params.FILTER: filter_value,
        }
        return url_params

    @staticmethod
    def _check_sector_and_industry_data(series_sector_and_industry: pd.Series):
        if not series_sector_and_industry.shape[0] == len(tables.Sector.ALL_COLUMNS[1:-1]):
            raise CompatibilityError("Sector and industry data has unexpected structure!")

    def _check_earnings_quarterly_data(self,
                                       dict_fundamental_data: dict[FundamentalType, pd.DataFrame]):
        df_earnings_quarterly = convert_df_column_names_from_camel_to_snake_case(
            dict_fundamental_data[FundamentalType.EARNINGS_QUARTERLY])
        if not self._has_columns(df_earnings_quarterly, tables.EarningsQuarterly.ALL_COLUMNS[1:-1]):
            raise CompatibilityError("Earnings quarterly data has unexpected structure!")

    def _check_earnings_annually_data(self,
                                      dict_fundamental_data: dict[FundamentalType, pd.DataFrame]):
        df_earnings_annually = convert_df_column_names_from_camel_to_snake_case(
            dict_fundamental_data[FundamentalType.EARNINGS_ANNUALLY])
        if not self._has_columns(df_earnings_annually, tables.EarningsAnnually.ALL_COLUMNS[1:-1]):
            raise CompatibilityError("Earnings annually data has unexpected structure!")

    def _check_balance_sheet_quarterly_data(self,
                                            dict_fundamental_data: dict[FundamentalType, pd.DataFrame]):
        df_balance_sheet_quarterly = convert_df_column_names_from_camel_to_snake_case(
            dict_fundamental_data[FundamentalType.BALANCE_SHEET_QUARTERLY])
        if not self._has_columns(df_balance_sheet_quarterly, tables.BalanceSheetQuarterly.ALL_COLUMNS[1:-1]):
            raise CompatibilityError("Balance sheet quarterly data has unexpected structure!")

    def _check_balance_sheet_annually_data(self,
                                           dict_fundamental_data: dict[FundamentalType, pd.DataFrame]):
        df_balance_sheet_annually = convert_df_column_names_from_camel_to_snake_case(
            dict_fundamental_data[FundamentalType.BALANCE_SHEET_ANNUALLY])
        if not self._has_columns(df_balance_sheet_annually, tables.BalanceSheetAnnually.ALL_COLUMNS[1:-1]):
            raise CompatibilityError("Balance sheet annually data has unexpected structure!")

    def _check_cash_flow_quarterly_data(self,
                                        dict_fundamental_data: dict[FundamentalType, pd.DataFrame]):
        df_cash_flow_quarterly = convert_df_column_names_from_camel_to_snake_case(
            dict_fundamental_data[FundamentalType.CASH_FLOW_QUARTERLY])
        if not self._has_columns(df_cash_flow_quarterly, tables.CashFlowQuarterly.ALL_COLUMNS[1:-1]):
            raise CompatibilityError("Cash flow quarterly data has unexpected structure!")

    def _check_cash_flow_annually_data(self,
                                       dict_fundamental_data: dict[FundamentalType, pd.DataFrame]):
        df_cash_flow_annually = convert_df_column_names_from_camel_to_snake_case(
            dict_fundamental_data[FundamentalType.CASH_FLOW_ANNUALLY])
        if not self._has_columns(df_cash_flow_annually, tables.CashFlowAnnually.ALL_COLUMNS[1:-1]):
            raise CompatibilityError("Cash flow annually data has unexpected structure!")

    def _check_income_quarterly_data(self,
                                     dict_fundamental_data: dict[FundamentalType, pd.DataFrame]):
        df_income_statement_quarterly = convert_df_column_names_from_camel_to_snake_case(
            dict_fundamental_data[FundamentalType.INCOME_STATEMENT_QUARTERLY])
        if not self._has_columns(df_income_statement_quarterly, tables.IncomeStatementQuarterly.ALL_COLUMNS[1:-1]):
            raise CompatibilityError("Income statement quarterly data has unexpected structure!")

    def _check_income_annually_data(self,
                                    dict_fundamental_data: dict[FundamentalType, pd.DataFrame]):
        df_income_statement_annually = convert_df_column_names_from_camel_to_snake_case(
            dict_fundamental_data[FundamentalType.INCOME_STATEMENT_ANNUALLY])
        if not self._has_columns(df_income_statement_annually, tables.IncomeStatementAnnually.ALL_COLUMNS[1:-1]):
            raise CompatibilityError("Income statement annually data has unexpected structure!")

    def _check_fundamental_data(self, series_sector_and_industry: pd.Series,
                                dict_fundamental_data: dict[FundamentalType, pd.DataFrame]):
        self._check_sector_and_industry_data(series_sector_and_industry)
        self._check_earnings_quarterly_data(dict_fundamental_data)
        self._check_earnings_annually_data(dict_fundamental_data)
        self._check_balance_sheet_quarterly_data(dict_fundamental_data)
        self._check_balance_sheet_annually_data(dict_fundamental_data)
        self._check_cash_flow_quarterly_data(dict_fundamental_data)
        self._check_cash_flow_annually_data(dict_fundamental_data)
        self._check_income_quarterly_data(dict_fundamental_data)
        self._check_income_annually_data(dict_fundamental_data)

    @staticmethod
    def _rearrange_fundamental_data(
            data_fundamental: dict[str, Any]) -> tuple[pd.Series, dict[FundamentalType, pd.DataFrame]]:
        series_sector_and_industry = pd.Series([data_fundamental["General::Sector"],
                                                data_fundamental["General::Industry"],
                                                data_fundamental["General::GicSector"],
                                                data_fundamental["General::GicGroup"],
                                                data_fundamental["General::GicIndustry"],
                                                data_fundamental["General::GicSubIndustry"]])
        dict_fundamental_data: dict[FundamentalType, pd.DataFrame] = {
            FundamentalType.EARNINGS_QUARTERLY:      pd.DataFrame(data_fundamental["Earnings::History"]).T,
            FundamentalType.EARNINGS_ANNUALLY:       pd.DataFrame(data_fundamental["Earnings::Annual"]).T,
            FundamentalType.BALANCE_SHEET_QUARTERLY: pd.DataFrame(data_fundamental["Financials::Balance_Sheet"]["quarterly"]).T,
            FundamentalType.BALANCE_SHEET_ANNUALLY:  pd.DataFrame(data_fundamental["Financials::Balance_Sheet"]["yearly"]).T,
            FundamentalType.CASH_FLOW_QUARTERLY:     pd.DataFrame(data_fundamental["Financials::Cash_Flow"]["quarterly"]).T,
            FundamentalType.CASH_FLOW_ANNUALLY:      pd.DataFrame(data_fundamental["Financials::Cash_Flow"]["yearly"]).T,
            FundamentalType.INCOME_STATEMENT_QUARTERLY: pd.DataFrame(
                                                     data_fundamental["Financials::Income_Statement"]["quarterly"]).T,
            FundamentalType.INCOME_STATEMENT_ANNUALLY: pd.DataFrame(
                                                     data_fundamental["Financials::Income_Statement"]["yearly"]).T
        }
        return series_sector_and_industry, dict_fundamental_data

    @staticmethod
    def _format_fundamental_data(
            dict_fundamental_data: dict[FundamentalType, pd.DataFrame]) -> dict[FundamentalType, pd.DataFrame]:
        dict_fundamental_data[FundamentalType.BALANCE_SHEET_QUARTERLY].drop("preferredStockRedeemable",
                                                                            axis=1, inplace=True)
        dict_fundamental_data[FundamentalType.BALANCE_SHEET_ANNUALLY].drop("preferredStockRedeemable",
                                                                           axis=1, inplace=True)
        dict_fundamental_data[FundamentalType.INCOME_STATEMENT_QUARTERLY].drop("preferredStockAndOtherAdjustments",
                                                                               axis=1, inplace=True)
        dict_fundamental_data[FundamentalType.INCOME_STATEMENT_ANNUALLY].drop("preferredStockAndOtherAdjustments",
                                                                              axis=1, inplace=True)
        return dict_fundamental_data

    def get(self) -> tuple[pd.Series, dict[FundamentalType, pd.DataFrame]]:
        """Requests fundamental data for symbol"""
        url_fundamental = self._get_url_for_fundamental_data()
        url_params      = self._get_url_params_for_fundamental_data()
        # Requests data
        data_fundamental = self._request_data_from_url(url_fundamental, url_params)
        if data_fundamental:
            # Rearranges and formats data
            series_sector_and_industry, dict_fundamental_data = self._rearrange_fundamental_data(data_fundamental)
            dict_fundamental_data = self._format_fundamental_data(dict_fundamental_data)
        else:
            series_sector_and_industry, dict_fundamental_data = pd.Series(dtype=object), {}
        self._check_fundamental_data(series_sector_and_industry, dict_fundamental_data)

        return series_sector_and_industry, dict_fundamental_data