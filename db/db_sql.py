#!/usr/bin/env python12.9

"""Provides sql code to access SQLite DB and QuestDB"""

# --------- SQLite queries ---------

SQL_TRUNCATE_TABLE = "DELETE FROM :table_name"

SQL_DELETE_SYMBOL_FROM_SYMBOL_META = "DELETE FROM symbol_meta WHERE symbol_code = :symbol_code"

SQL_INSERT_DUMMY_SYMBOL_INTO_SYMBOL_META = (
    'INSERT INTO symbol_meta (symbol_code, exchange_code, time_frame, symbol_status, name, country, currency, type, '
    'isin) VALUES(:symbol_code, :exchange_code, "DAILY", "ACTIVE", :name, "test_country", "test_currency", '
    '"test_type", "test_isin")')

SQL_SELECT_ALL_FROM_SYMBOL_META_BY_VALUES = (
    "SELECT id, symbol_code, exchange_code, time_frame, symbol_status, name, country, currency, type, isin "
    "FROM symbol_meta WHERE symbol_code=:symbol_code AND exchange_code=:exchange_code AND time_frame=:time_frame AND "
    "symbol_status=:symbol_status AND name=:name")
SQL_SELECT_ALL_FROM_SYMBOL_META_BY_ID = (
    "SELECT id, symbol_code, exchange_code, time_frame, symbol_status, name, country, currency, type, isin "
    "FROM symbol_meta WHERE id=:id")
SQL_SELECT_ALL_FROM_SYMBOL_SECTOR = (
    "SELECT id, id_symbol_meta, sector, industry, gic_sector, gic_group, gic_industry, gic_sub_industry "
    "FROM symbol_sector WHERE id_symbol_meta=:id_symbol_meta")
SQL_SELECT_ALL_FROM_EARNINGS_QUARTERLY = (
    "SELECT id, id_symbol_meta, report_date, date, before_after_market, currency, eps_actual, eps_estimate "
    "eps_difference, surprise_percent "
    "FROM earnings_quarterly WHERE id_symbol_meta=:id_symbol_meta")
SQL_SELECT_ALL_FROM_EARNINGS_ANNUALLY = (
    "SELECT id, id_symbol_meta, date, eps_actual "
    "FROM earnings_annually WHERE id_symbol_meta=:id_symbol_meta")
SQL_SELECT_ALL_FROM_BALANCE_SHEET_QUARTERLY = (
    "SELECT id, id_symbol_meta, date, filing_date, currency_symbol, total_assets, intangible_assets, earning_assets, "
    "other_current_assets, total_liab, total_stockholder_equity, deferred_long_term_liab, other_current_liab, "
    "common_stock, capital_stock, retained_earnings, other_liab, good_will, other_assets, cash, cash_and_equivalents, "
    "total_current_liabilities, current_deferred_revenue, net_debt, short_term_debt, short_long_term_debt, "
    "short_long_term_debt_total, other_stockholder_equity, property_plant_equipment, total_current_assets, "
    "long_term_investments, net_tangible_assets, short_term_investments, net_receivables, long_term_debt, inventory, "
    "accounts_payable, total_permanent_equity, noncontrolling_interest_in_consolidated_entity, "
    "temporary_equity_redeemable_noncontrolling_interests, accumulated_other_comprehensive_income, "
    "additional_paid_in_capital, common_stock_total_equity, preferred_stock_total_equity, "
    "retained_earnings_total_equity, treasury_stock, accumulated_amortization, non_currrent_assets_other, "
    "deferred_long_term_asset_charges, non_current_assets_total, capital_lease_obligations, long_term_debt_total, "
    "non_current_liabilities_other, non_current_liabilities_total, negative_goodwill, warrants, capital_surpluse, "
    "liabilities_and_stockholders_equity, cash_and_short_term_investments, property_plant_and_equipment_gross, "
    "property_plant_and_equipment_net, accumulated_depreciation, net_working_capital, net_invested_capital, "
    "common_stock_shares_outstanding "
    "FROM balance_sheet_quarterly WHERE id_symbol_meta=:id_symbol_meta")
SQL_SELECT_ALL_FROM_BALANCE_SHEET_ANNUALLY = (
    "SELECT id, id_symbol_meta, date, filing_date, currency_symbol, total_assets, intangible_assets, earning_assets, "
    "other_current_assets, total_liab, total_stockholder_equity, deferred_long_term_liab, other_current_liab, "
    "common_stock, capital_stock, retained_earnings, other_liab, good_will, other_assets, cash, cash_and_equivalents, "
    "total_current_liabilities, current_deferred_revenue, net_debt, short_term_debt, short_long_term_debt, "
    "short_long_term_debt_total, other_stockholder_equity, property_plant_equipment, total_current_assets, "
    "long_term_investments, net_tangible_assets, short_term_investments, net_receivables, long_term_debt, inventory, "
    "accounts_payable, total_permanent_equity, noncontrolling_interest_in_consolidated_entity, "
    "temporary_equity_redeemable_noncontrolling_interests, accumulated_other_comprehensive_income, "
    "additional_paid_in_capital, common_stock_total_equity, preferred_stock_total_equity, "
    "retained_earnings_total_equity, treasury_stock, accumulated_amortization, non_currrent_assets_other, "
    "deferred_long_term_asset_charges, non_current_assets_total, capital_lease_obligations, long_term_debt_total, "
    "non_current_liabilities_other, non_current_liabilities_total, negative_goodwill, warrants, capital_surpluse, "
    "liabilities_and_stockholders_equity, cash_and_short_term_investments, property_plant_and_equipment_gross, "
    "property_plant_and_equipment_net, accumulated_depreciation, net_working_capital, net_invested_capital, "
    "common_stock_shares_outstanding "
    "FROM balance_sheet_annually WHERE id_symbol_meta=:id_symbol_meta")
SQL_SELECT_ALL_FROM_CASH_FLOW_QUARTERLY = (
    "SELECT id, id_symbol_meta, date, filing_date, currency_symbol, investments, change_to_liabilities, "
    "total_cashflows_from_investing_activities, net_borrowings, total_cash_from_financing_activities, "
    "change_to_operating_activities, net_income, change_in_cash, begin_period_cash_flow, end_period_cash_flow, "
    "total_cash_from_operating_activities, issuance_of_capital_stock, depreciation, "
    "other_cashflows_from_investing_activities, dividends_paid, change_to_inventory, change_to_account_receivables, "
    "sale_purchase_of_stock, other_cashflows_from_financing_activities, change_to_netincome, capital_expenditures, "
    "change_receivables, cash_flows_other_operating, exchange_rate_changes, cash_and_cash_equivalents_changes, "
    "change_in_working_capital, stock_based_compensation, other_non_cash_items, free_cash_flow "
    "FROM cash_flow_quarterly WHERE id_symbol_meta=:id_symbol_meta")
SQL_SELECT_ALL_FROM_CASH_FLOW_ANNUALLY = (
    "SELECT id, id_symbol_meta, date, filing_date, currency_symbol, investments, change_to_liabilities, "
    "total_cashflows_from_investing_activities, net_borrowings, total_cash_from_financing_activities, "
    "change_to_operating_activities, net_income, change_in_cash, begin_period_cash_flow, end_period_cash_flow, "
    "total_cash_from_operating_activities, issuance_of_capital_stock, depreciation, "
    "other_cashflows_from_investing_activities, dividends_paid, change_to_inventory, change_to_account_receivables, "
    "sale_purchase_of_stock, other_cashflows_from_financing_activities, change_to_netincome, capital_expenditures, "
    "change_receivables, cash_flows_other_operating, exchange_rate_changes, cash_and_cash_equivalents_changes, "
    "change_in_working_capital, stock_based_compensation, other_non_cash_items, free_cash_flow "
    "FROM cash_flow_annually WHERE id_symbol_meta=:id_symbol_meta")
SQL_SELECT_ALL_FROM_INCOME_STATEMENT_QUARTERLY = (
    "SELECT id, id_symbol_meta, date, filing_date, currency_symbol, research_development, "
    "effect_of_accounting_charges, income_before_tax, minority_interest, net_income, selling_general_administrative, "
    "selling_and_marketing_expenses, gross_profit, reconciled_depreciation, ebit, ebitda, "
    "depreciation_and_amortization, non_operating_income_net_other, operating_income, other_operating_expenses, "
    "interest_expense, tax_provision, interest_income, net_interest_income, extraordinary_items, non_recurring, "
    "other_items, income_tax_expense, total_revenue, total_operating_expenses, cost_of_revenue, "
    "total_other_income_expense_net, discontinued_operations, net_income_from_continuing_ops, "
    "net_income_applicable_to_common_shares "
    "FROM income_statement_quarterly WHERE id_symbol_meta=:id_symbol_meta")
SQL_SELECT_ALL_FROM_INCOME_STATEMENT_ANNUALLY = (
    "SELECT id, id_symbol_meta, date, filing_date, currency_symbol, research_development, "
    "effect_of_accounting_charges, income_before_tax, minority_interest, net_income, selling_general_administrative, "
    "selling_and_marketing_expenses, gross_profit, reconciled_depreciation, ebit, ebitda, "
    "depreciation_and_amortization, non_operating_income_net_other, operating_income, other_operating_expenses, "
    "interest_expense, tax_provision, interest_income, net_interest_income, extraordinary_items, non_recurring, "
    "other_items, income_tax_expense, total_revenue, total_operating_expenses, cost_of_revenue, "
    "total_other_income_expense_net, discontinued_operations, net_income_from_continuing_ops, "
    "net_income_applicable_to_common_shares "
    "FROM income_statement_annually WHERE id_symbol_meta=:id_symbol_meta")

SQL_SELECT_SCHEMA_SQLITE = "SELECT COUNT(*) AS CNTREC FROM pragma_table_info(:table_name) WHERE name=:column_name"

# --------- QuestDB queries --------

SQL_SELECT_CLOSE_FROM_DAILY_OHLCV = "SELECT close FROM daily_ohlcv WHERE timestamp = %s"
SQL_SELECT_CLOSE_FROM_MINUTE_OHLCV = "SELECT close FROM minute_ohlcv WHERE timestamp = %s"

SQL_SELECT_ALL_FROM_DAILY_OHLCV = (
    "SELECT timestamp, exchange_code, symbol_code, open, high, low, close, adjusted_close, volume "
    "FROM daily_ohlcv WHERE exchange_code = %s AND symbol_code IN ({symbol_codes}) "
    "AND %s <= timestamp AND timestamp <= %s")
SQL_SELECT_LAST_FROM_DAILY_OHLCV = (
    "SELECT timestamp, exchange_code, symbol_code, open, high, low, close, adjusted_close, volume "
    "FROM daily_ohlcv WHERE exchange_code = %s AND symbol_code IN ({symbol_codes}) "
    "ORDER BY timestamp DESC LIMIT 1")
SQL_SELECT_ALL_FROM_MINUTE_OHLCV = (
    "SELECT timestamp, exchange_code, symbol_code, gmt_offset, open, high, low, close, volume "
    "FROM minute_ohlcv WHERE exchange_code = %s AND symbol_code IN ({symbol_codes}) "
    "AND %s <= timestamp AND timestamp <= %s")
SQL_SELECT_LAST_FROM_MINUTE_OHLCV = (
    "SELECT timestamp, exchange_code, symbol_code, gmt_offset, open, high, low, close, volume "
    "FROM minute_ohlcv WHERE exchange_code = %s AND symbol_code IN ({symbol_codes}) "
    "ORDER BY timestamp DESC LIMIT 1")

SQL_SELECT_SCHEMA_QUESTDB = "SELECT * FROM INFORMATION_SCHEMA.columns WHERE table_name = %s AND column_name = %s"