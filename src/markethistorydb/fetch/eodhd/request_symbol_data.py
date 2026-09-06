#!/usr/bin/env python12.9

"""Class for requesting symbol data from eodhd.com"""

import pandas as pd

from markethistorydb.db                       import tables
from markethistorydb.fetch.eodhd.errors       import CompatibilityError
from markethistorydb.fetch.eodhd.config       import API_TOKEN
from markethistorydb.fetch.eodhd.request_data import RequestData
from markethistorydb.utils.categories         import TimeFrame, SymbolStatus


# US exchanges to download daily and intraday data from
_US_EXCHANGE_URL_CODE = "US"
_US_EXCHANGE_CODES_EOD = ["NASDAQ", "NYSE", "NYSE ARCA"]
_US_EXCHANGE_CODES_MINUTE = ["NASDAQ", "NYSE"]


class RequestSymbolData(RequestData):
    def __init__(self, time_frame: TimeFrame, symbol_status: SymbolStatus):
        self._time_frame:       TimeFrame = time_frame
        self._symbol_status: SymbolStatus = symbol_status

    def _get_url_for_symbol_data(self, exchange_url_code: str) -> str:
        if self._symbol_status == SymbolStatus.ACTIVE:
            url_exchange_symbols = "https://eodhd.com/api/exchange-symbol-list/{0}?".format(exchange_url_code)
        else:
            url_exchange_symbols = "https://eodhd.com/api/exchange-symbol-list/{0}?".format(exchange_url_code)
        return url_exchange_symbols

    def _get_url_params_for_symbol_data(self) -> dict[str, str]:
        if self._symbol_status == SymbolStatus.ACTIVE:
            url_params = {"api_token": API_TOKEN, "fmt": "json"}
        else:
            url_params = {"api_token": API_TOKEN, "fmt": "json", "delisted": "1"}
        return url_params

    def _check_symbol_data(self, df_exchange_symbols: pd.DataFrame):
        if not self._has_columns(df_exchange_symbols,
                                 ["Code", "Name", "Country", "Exchange", "Currency", "Type", "Isin"]):
            raise CompatibilityError("Symbol data has unexpected structure!")

    def _format_symbol_data(self, df_symbols: pd.DataFrame, exchange_url_code: str) -> pd.DataFrame:
        if exchange_url_code == _US_EXCHANGE_URL_CODE and self._time_frame == TimeFrame.DAILY:
            df_symbols_filtered = df_symbols[df_symbols["Exchange"].isin(_US_EXCHANGE_CODES_EOD)]
        elif exchange_url_code == _US_EXCHANGE_URL_CODE and self._time_frame == TimeFrame.MINUTE:
            df_symbols_filtered = df_symbols[df_symbols["Exchange"].isin(_US_EXCHANGE_CODES_MINUTE)]
        else:
            df_symbols_filtered = df_symbols

        df_symbols_filtered = df_symbols_filtered.rename(
            columns={"Code": tables.Symbol.Columns.SYMBOL_CODE, "Name": tables.Symbol.Columns.NAME,
                     "Country": tables.Symbol.Columns.COUNTRY, "Exchange": tables.Symbol.Columns.EXCHANGE_CODE,
                     "Currency": tables.Symbol.Columns.CURRENCY, "Type": tables.Symbol.Columns.TYPE,
                     "Isin": tables.Symbol.Columns.ISIN})
        df_symbols_filtered.insert(1, "time_frame", self._time_frame.name)
        df_symbols_filtered.insert(2, "symbol_status", self._symbol_status.name)
        df_symbols_filtered = df_symbols_filtered[tables.Symbol.ALL_COLUMNS[:-1]]
        return df_symbols_filtered

    def get(self, exchange_url_code: str) -> pd.DataFrame:
        """Requests exchange symbol meta data"""
        url_exchange_symbols = self._get_url_for_symbol_data(exchange_url_code)
        url_params = self._get_url_params_for_symbol_data()
        # Requests data
        data_exchange_symbols = self._request_data_from_url(url_exchange_symbols, url_params)
        if data_exchange_symbols:
            # Creates and formats df
            df_symbols = pd.DataFrame(data_exchange_symbols)
            self._check_symbol_data(df_symbols)
            df_symbols_filtered = self._format_symbol_data(df_symbols, exchange_url_code)
        else:
            df_symbols_filtered = pd.DataFrame()
        return df_symbols_filtered