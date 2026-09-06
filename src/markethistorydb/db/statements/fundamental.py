#!/usr/bin/env python12.9


class StatementsFundamental:
    SELECT_ALL_FROM_EARNINGS_QUARTERLY = (
        "SELECT symbol_code, exchange_code, report_date, date, before_after_market, currency, eps_actual, eps_estimate "
        "eps_difference, surprise_percent "
        "FROM earnings_quarterly WHERE symbol_code=%s")
    SELECT_ALL_FROM_EARNINGS_ANNUALLY = (
        "SELECT symbol_code, exchange_code, date, eps_actual "
        "FROM earnings_annually WHERE symbol_code=%s")
    SELECT_ALL_FROM_BALANCE_SHEET_QUARTERLY = (
        "SELECT symbol_code, exchange_code, date, filing_date, currency_symbol, total_assets, intangible_assets, earning_assets, "
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
        "FROM balance_sheet_quarterly WHERE symbol_code=%s")
    SELECT_ALL_FROM_BALANCE_SHEET_ANNUALLY = (
        "SELECT symbol_code, exchange_code, date, filing_date, currency_symbol, total_assets, intangible_assets, earning_assets, "
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
        "FROM balance_sheet_annually WHERE symbol_code=%s")
    SELECT_ALL_FROM_CASH_FLOW_QUARTERLY = (
        "SELECT symbol_code, exchange_code, date, filing_date, currency_symbol, investments, change_to_liabilities, "
        "total_cashflows_from_investing_activities, net_borrowings, total_cash_from_financing_activities, "
        "change_to_operating_activities, net_income, change_in_cash, begin_period_cash_flow, end_period_cash_flow, "
        "total_cash_from_operating_activities, issuance_of_capital_stock, depreciation, "
        "other_cashflows_from_investing_activities, dividends_paid, change_to_inventory, change_to_account_receivables, "
        "sale_purchase_of_stock, other_cashflows_from_financing_activities, change_to_netincome, capital_expenditures, "
        "change_receivables, cash_flows_other_operating, exchange_rate_changes, cash_and_cash_equivalents_changes, "
        "change_in_working_capital, stock_based_compensation, other_non_cash_items, free_cash_flow "
        "FROM cash_flow_quarterly WHERE symbol_code=%s")
    SELECT_ALL_FROM_CASH_FLOW_ANNUALLY = (
        "SELECT symbol_code, exchange_code, date, filing_date, currency_symbol, investments, change_to_liabilities, "
        "total_cashflows_from_investing_activities, net_borrowings, total_cash_from_financing_activities, "
        "change_to_operating_activities, net_income, change_in_cash, begin_period_cash_flow, end_period_cash_flow, "
        "total_cash_from_operating_activities, issuance_of_capital_stock, depreciation, "
        "other_cashflows_from_investing_activities, dividends_paid, change_to_inventory, change_to_account_receivables, "
        "sale_purchase_of_stock, other_cashflows_from_financing_activities, change_to_netincome, capital_expenditures, "
        "change_receivables, cash_flows_other_operating, exchange_rate_changes, cash_and_cash_equivalents_changes, "
        "change_in_working_capital, stock_based_compensation, other_non_cash_items, free_cash_flow "
        "FROM cash_flow_annually WHERE symbol_code=%s")
    SELECT_ALL_FROM_INCOME_STATEMENT_QUARTERLY = (
        "SELECT symbol_code, exchange_code, date, filing_date, currency_symbol, research_development, "
        "effect_of_accounting_charges, income_before_tax, minority_interest, net_income, selling_general_administrative, "
        "selling_and_marketing_expenses, gross_profit, reconciled_depreciation, ebit, ebitda, "
        "depreciation_and_amortization, non_operating_income_net_other, operating_income, other_operating_expenses, "
        "interest_expense, tax_provision, interest_income, net_interest_income, extraordinary_items, non_recurring, "
        "other_items, income_tax_expense, total_revenue, total_operating_expenses, cost_of_revenue, "
        "total_other_income_expense_net, discontinued_operations, net_income_from_continuing_ops, "
        "net_income_applicable_to_common_shares "
        "FROM income_statement_quarterly WHERE symbol_code=%s")
    SELECT_ALL_FROM_INCOME_STATEMENT_ANNUALLY = (
        "SELECT symbol_code, exchange_code, date, filing_date, currency_symbol, research_development, "
        "effect_of_accounting_charges, income_before_tax, minority_interest, net_income, selling_general_administrative, "
        "selling_and_marketing_expenses, gross_profit, reconciled_depreciation, ebit, ebitda, "
        "depreciation_and_amortization, non_operating_income_net_other, operating_income, other_operating_expenses, "
        "interest_expense, tax_provision, interest_income, net_interest_income, extraordinary_items, non_recurring, "
        "other_items, income_tax_expense, total_revenue, total_operating_expenses, cost_of_revenue, "
        "total_other_income_expense_net, discontinued_operations, net_income_from_continuing_ops, "
        "net_income_applicable_to_common_shares "
        "FROM income_statement_annually WHERE symbol_code=%s")

    DROP_SYMBOL_FROM_TABLE = (
        "CREATE TABLE {table_name}_copy AS (",
        "SELECT * FROM {table_name} WHERE symbol_code!=%s AND exchange_code!=%s",
        ") TIMESTAMP({timestamp_column}) PARTITION BY YEAR WAL",
        "DEDUP UPSERT KEYS({unique_key_columns});",
        "DROP TABLE {table_name};",
        "RENAME TABLE {table_name}_copy TO {table_name};")