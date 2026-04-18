#!/usr/bin/env python12.9

"""Global db related constants"""

import misc.const as const

# --------- General constants ---------

# QUESTDB server path
QUESTDB_DIR_PATH = "C:/TradingAnalysis/questdb/qdbroot"

# QUESTDB exe path
QUESTDB_EXE_PATH = "C:/TradingAnalysis/questdb/questdb-9.3.3-rt-windows-x86-64/bin/questdb.exe"

# SQLite DB path
SQLITE_DB_PATH = "C:/TradingAnalysis/sqlite/sqlite.db"

# QuestDB password
QUESTDB_PASSWORD = "quest"
# Config string PostgreSQL
QUESTDB_CONF_PSYCOPG = "user=admin password={0} host=127.0.0.1 port=8812 dbname=qdb".format(QUESTDB_PASSWORD)

# Dummy symbol and exchange for test purposes
DUMMY_SYMBOL_CODE     = "DUMMY_SYMBOL"
DUMMY_EXCHANGE_CODE_A = "DUMMY_EXCHANGE_A"
DUMMY_EXCHANGE_CODE_B = "DUMMY_EXCHANGE_B"
DUMMY_SYMBOL_NAME     = "DUMMY_NAME"

# Specific column names
COLUMN_SYMBOL_CODE   = "symbol_code"
COLUMN_EXCHANGE_CODE = "exchange_code"

# --------- SQLite constants ---------

# Table names
TABLE_SYMBOL_META                = "symbol_meta"
TABLE_SYMBOL_SECTOR              = "symbol_sector"
TABLE_EARNINGS_QUARTERLY         = "earnings_quarterly"
TABLE_EARNINGS_ANNUALLY          = "earnings_annually"
TABLE_BALANCE_SHEET_QUARTERLY    = "balance_sheet_quarterly"
TABLE_BALANCE_SHEET_ANNUALLY     = "balance_sheet_annually"
TABLE_CASH_FLOW_QUARTERLY        = "cash_flow_quarterly"
TABLE_CASH_FLOW_ANNUALLY         = "cash_flow_annually"
TABLE_INCOME_STATEMENT_QUARTERLY = "income_statement_quarterly"
TABLE_INCOME_STATEMENT_ANNUALLY  = "income_statement_annually"

# Specific column names
COLUMN_SYMBOL_NAME  = "name"
COLUMN_COUNTRY      = "country"
COLUMN_CURRENCY     = "currency"
COLUMN_SYMBOL_TYPE  = "type"
COLUMN_ISIN         = "isin"

COLUMN_SYMBOL_META_ID = "id_symbol_meta"

# Column names of table (except primary key)
COLUMNS_SYMBOL_META = ["id", COLUMN_SYMBOL_META_ID, COLUMN_SYMBOL_CODE, COLUMN_EXCHANGE_CODE, "time_frame", "symbol_status",
                       COLUMN_SYMBOL_NAME, COLUMN_COUNTRY, COLUMN_CURRENCY, COLUMN_SYMBOL_TYPE, COLUMN_ISIN]
COLUMNS_SYMBOL_SECTOR = ["id", COLUMN_SYMBOL_META_ID, "sector", "industry", "gic_sector", "gic_group", "gic_industry",
                         "gic_sub_industry"]
COLUMNS_EARNINGS_QUARTERLY = ["id", COLUMN_SYMBOL_META_ID, "report_date", "date", "before_after_market", "currency",
                              "eps_actual", "eps_estimate", "eps_difference", "surprise_percent"]
COLUMNS_EARNINGS_ANNUALLY = ["id", COLUMN_SYMBOL_META_ID, "date", "eps_actual"]
COLUMNS_BALANCE_SHEET_QUARTERLY = [
    "id", COLUMN_SYMBOL_META_ID, "date", "filing_date", "currency_symbol",
    "total_assets", "intangible_assets", "earning_assets", "other_current_assets",
    "total_liab", "total_stockholder_equity", "deferred_long_term_liab",
    "other_current_liab", "common_stock", "capital_stock", "retained_earnings",
    "other_liab", "good_will", "other_assets", "cash", "cash_and_equivalents",
    "total_current_liabilities", "current_deferred_revenue", "net_debt",
    "short_term_debt", "short_long_term_debt", "short_long_term_debt_total",
    "other_stockholder_equity", "property_plant_equipment", "total_current_assets",
    "long_term_investments", "net_tangible_assets", "short_term_investments",
    "net_receivables", "long_term_debt", "inventory", "accounts_payable",
    "total_permanent_equity", "noncontrolling_interest_in_consolidated_entity",
    "temporary_equity_redeemable_noncontrolling_interests",
    "accumulated_other_comprehensive_income", "additional_paid_in_capital",
    "common_stock_total_equity", "preferred_stock_total_equity",
    "retained_earnings_total_equity", "treasury_stock", "accumulated_amortization",
    "non_currrent_assets_other", "deferred_long_term_asset_charges",
    "non_current_assets_total", "capital_lease_obligations", "long_term_debt_total",
    "non_current_liabilities_other", "non_current_liabilities_total",
    "negative_goodwill", "warrants", "capital_surpluse",
    "liabilities_and_stockholders_equity", "cash_and_short_term_investments",
    "property_plant_and_equipment_gross", "property_plant_and_equipment_net",
    "accumulated_depreciation", "net_working_capital", "net_invested_capital",
    "common_stock_shares_outstanding"]
COLUMNS_BALANCE_SHEET_ANNUALLY = [
    "id", COLUMN_SYMBOL_META_ID, "date", "filing_date", "currency_symbol", "total_assets",
    "intangible_assets", "earning_assets", "other_current_assets", "total_liab",
    "total_stockholder_equity", "deferred_long_term_liab", "other_current_liab", "common_stock",
    "capital_stock", "retained_earnings", "other_liab", "good_will", "other_assets", "cash",
    "cash_and_equivalents", "total_current_liabilities", "current_deferred_revenue", "net_debt",
    "short_term_debt", "short_long_term_debt", "short_long_term_debt_total",
    "other_stockholder_equity", "property_plant_equipment", "total_current_assets",
    "long_term_investments", "net_tangible_assets", "short_term_investments", "net_receivables",
    "long_term_debt", "inventory", "accounts_payable", "total_permanent_equity",
    "noncontrolling_interest_in_consolidated_entity",
    "temporary_equity_redeemable_noncontrolling_interests",
    "accumulated_other_comprehensive_income", "additional_paid_in_capital",
    "common_stock_total_equity", "preferred_stock_total_equity", "retained_earnings_total_equity",
    "treasury_stock", "accumulated_amortization", "non_currrent_assets_other",
    "deferred_long_term_asset_charges", "non_current_assets_total", "capital_lease_obligations",
    "long_term_debt_total", "non_current_liabilities_other", "non_current_liabilities_total",
    "negative_goodwill", "warrants", "capital_surpluse", "liabilities_and_stockholders_equity",
    "cash_and_short_term_investments", "property_plant_and_equipment_gross",
    "property_plant_and_equipment_net", "accumulated_depreciation", "net_working_capital",
    "net_invested_capital", "common_stock_shares_outstanding"]
COLUMNS_CASH_FLOW_QUARTERLY = [
    "id", COLUMN_SYMBOL_META_ID, "date", "filing_date", "currency_symbol", "investments",
    "change_to_liabilities", "total_cashflows_from_investing_activities", "net_borrowings",
    "total_cash_from_financing_activities", "change_to_operating_activities", "net_income",
    "change_in_cash", "begin_period_cash_flow", "end_period_cash_flow",
    "total_cash_from_operating_activities", "issuance_of_capital_stock", "depreciation",
    "other_cashflows_from_investing_activities", "dividends_paid", "change_to_inventory",
    "change_to_account_receivables", "sale_purchase_of_stock",
    "other_cashflows_from_financing_activities", "change_to_netincome", "capital_expenditures",
    "change_receivables", "cash_flows_other_operating", "exchange_rate_changes",
    "cash_and_cash_equivalents_changes", "change_in_working_capital", "stock_based_compensation",
    "other_non_cash_items", "free_cash_flow"]
COLUMNS_CASH_FLOW_ANNUALLY = [
    "id", COLUMN_SYMBOL_META_ID, "date", "filing_date", "currency_symbol", "investments",
    "change_to_liabilities", "total_cashflows_from_investing_activities", "net_borrowings",
    "total_cash_from_financing_activities", "change_to_operating_activities", "net_income",
    "change_in_cash", "begin_period_cash_flow", "end_period_cash_flow",
    "total_cash_from_operating_activities", "issuance_of_capital_stock", "depreciation",
    "other_cashflows_from_investing_activities", "dividends_paid", "change_to_inventory",
    "change_to_account_receivables", "sale_purchase_of_stock",
    "other_cashflows_from_financing_activities", "change_to_netincome", "capital_expenditures",
    "change_receivables", "cash_flows_other_operating", "exchange_rate_changes",
    "cash_and_cash_equivalents_changes", "change_in_working_capital", "stock_based_compensation",
    "other_non_cash_items", "free_cash_flow"]
COLUMNS_INCOME_STATEMENT_QUARTERLY = [
    "id", COLUMN_SYMBOL_META_ID, "date", "filing_date", "currency_symbol", "research_development",
    "effect_of_accounting_charges", "income_before_tax", "minority_interest", "net_income",
    "selling_general_administrative", "selling_and_marketing_expenses", "gross_profit",
    "reconciled_depreciation", "ebit", "ebitda", "depreciation_and_amortization",
    "non_operating_income_net_other", "operating_income", "other_operating_expenses",
    "interest_expense", "tax_provision", "interest_income", "net_interest_income",
    "extraordinary_items", "non_recurring", "other_items", "income_tax_expense", "total_revenue",
    "total_operating_expenses", "cost_of_revenue", "total_other_income_expense_net",
    "discontinued_operations", "net_income_from_continuing_ops",
    "net_income_applicable_to_common_shares"]
COLUMNS_INCOME_STATEMENT_ANNUALLY = [
    "id", COLUMN_SYMBOL_META_ID, "date", "filing_date", "currency_symbol", "research_development",
    "effect_of_accounting_charges", "income_before_tax", "minority_interest", "net_income",
    "selling_general_administrative", "selling_and_marketing_expenses", "gross_profit",
    "reconciled_depreciation", "ebit", "ebitda", "depreciation_and_amortization",
    "non_operating_income_net_other", "operating_income", "other_operating_expenses",
    "interest_expense", "tax_provision", "interest_income", "net_interest_income",
    "extraordinary_items", "non_recurring", "other_items", "income_tax_expense", "total_revenue",
    "total_operating_expenses", "cost_of_revenue", "total_other_income_expense_net",
    "discontinued_operations", "net_income_from_continuing_ops",
    "net_income_applicable_to_common_shares"]


# --------- QuestDB constants --------

# Table names
TABLE_NAME_DAILY_PRICE = "daily_ohlcv"
TABLE_NAME_MINUTE_PRICE = "minute_ohlcv"

# Column names of table
COLUMNS_DAILY_PRICE = ["timestamp", "exchange_code", "symbol_code", "open", "high", "low", "close", "adjusted_close",
                       "volume"]
COLUMNS_MINUTE_PRICE = ["timestamp", "exchange_code", "symbol_code", "gmt_offset", "open", "high", "low", "close",
                        "volume"]
# Specific column names
COLUMN_TIMESTAMP = "timestamp"

# ------------------------------------

