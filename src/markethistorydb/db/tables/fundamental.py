#!/usr/bin/env python12.9

from markethistorydb.db.tables import Table

# Dummy symbol and exchange for test purposes
DUMMY_SYMBOL_CODE     = "DUMMY_SYMBOL"
DUMMY_EXCHANGE_CODE_A = "DUMMY_EXCHANGE_A"
DUMMY_EXCHANGE_CODE_B = "DUMMY_EXCHANGE_B"
DUMMY_SYMBOL_NAME     = "DUMMY_NAME"

# ---------------------------------------------------------------------------
# Shared column definitions
# ---------------------------------------------------------------------------

class _BalanceSheetColumns:
    """Column constants shared by balance_sheet_quarterly and balance_sheet_annually."""
    SYMBOL_CODE                                          = "symbol_code"
    EXCHANGE_CODE                                        = "exchange_code"
    DATE                                                 = "date"
    FILING_DATE                                          = "filing_date"
    CURRENCY_SYMBOL                                      = "currency_symbol"
    TOTAL_ASSETS                                         = "total_assets"
    INTANGIBLE_ASSETS                                    = "intangible_assets"
    EARNING_ASSETS                                       = "earning_assets"
    OTHER_CURRENT_ASSETS                                 = "other_current_assets"
    TOTAL_LIAB                                           = "total_liab"
    TOTAL_STOCKHOLDER_EQUITY                             = "total_stockholder_equity"
    DEFERRED_LONG_TERM_LIAB                              = "deferred_long_term_liab"
    OTHER_CURRENT_LIAB                                   = "other_current_liab"
    COMMON_STOCK                                         = "common_stock"
    CAPITAL_STOCK                                        = "capital_stock"
    RETAINED_EARNINGS                                    = "retained_earnings"
    OTHER_LIAB                                           = "other_liab"
    GOOD_WILL                                            = "good_will"
    OTHER_ASSETS                                         = "other_assets"
    CASH                                                 = "cash"
    CASH_AND_EQUIVALENTS                                 = "cash_and_equivalents"
    TOTAL_CURRENT_LIABILITIES                            = "total_current_liabilities"
    CURRENT_DEFERRED_REVENUE                             = "current_deferred_revenue"
    NET_DEBT                                             = "net_debt"
    SHORT_TERM_DEBT                                      = "short_term_debt"
    SHORT_LONG_TERM_DEBT                                 = "short_long_term_debt"
    SHORT_LONG_TERM_DEBT_TOTAL                           = "short_long_term_debt_total"
    OTHER_STOCKHOLDER_EQUITY                             = "other_stockholder_equity"
    PROPERTY_PLANT_EQUIPMENT                             = "property_plant_equipment"
    TOTAL_CURRENT_ASSETS                                 = "total_current_assets"
    LONG_TERM_INVESTMENTS                                = "long_term_investments"
    NET_TANGIBLE_ASSETS                                  = "net_tangible_assets"
    SHORT_TERM_INVESTMENTS                               = "short_term_investments"
    NET_RECEIVABLES                                      = "net_receivables"
    LONG_TERM_DEBT                                       = "long_term_debt"
    INVENTORY                                            = "inventory"
    ACCOUNTS_PAYABLE                                     = "accounts_payable"
    TOTAL_PERMANENT_EQUITY                               = "total_permanent_equity"
    NONCONTROLLING_INTEREST_IN_CONSOLIDATED_ENTITY       = "noncontrolling_interest_in_consolidated_entity"
    TEMPORARY_EQUITY_REDEEMABLE_NONCONTROLLING_INTERESTS = "temporary_equity_redeemable_noncontrolling_interests"
    ACCUMULATED_OTHER_COMPREHENSIVE_INCOME               = "accumulated_other_comprehensive_income"
    ADDITIONAL_PAID_IN_CAPITAL                           = "additional_paid_in_capital"
    COMMON_STOCK_TOTAL_EQUITY                            = "common_stock_total_equity"
    PREFERRED_STOCK_TOTAL_EQUITY                         = "preferred_stock_total_equity"
    RETAINED_EARNINGS_TOTAL_EQUITY                       = "retained_earnings_total_equity"
    TREASURY_STOCK                                       = "treasury_stock"
    ACCUMULATED_AMORTIZATION                             = "accumulated_amortization"
    NON_CURRRENT_ASSETS_OTHER                            = "non_currrent_assets_other"
    DEFERRED_LONG_TERM_ASSET_CHARGES                     = "deferred_long_term_asset_charges"
    NON_CURRENT_ASSETS_TOTAL                             = "non_current_assets_total"
    CAPITAL_LEASE_OBLIGATIONS                            = "capital_lease_obligations"
    LONG_TERM_DEBT_TOTAL                                 = "long_term_debt_total"
    NON_CURRENT_LIABILITIES_OTHER                        = "non_current_liabilities_other"
    NON_CURRENT_LIABILITIES_TOTAL                        = "non_current_liabilities_total"
    NEGATIVE_GOODWILL                                    = "negative_goodwill"
    WARRANTS                                             = "warrants"
    CAPITAL_SURPLUSE                                     = "capital_surpluse"
    LIABILITIES_AND_STOCKHOLDERS_EQUITY                  = "liabilities_and_stockholders_equity"
    CASH_AND_SHORT_TERM_INVESTMENTS                      = "cash_and_short_term_investments"
    PROPERTY_PLANT_AND_EQUIPMENT_GROSS                   = "property_plant_and_equipment_gross"
    PROPERTY_PLANT_AND_EQUIPMENT_NET                     = "property_plant_and_equipment_net"
    ACCUMULATED_DEPRECIATION                             = "accumulated_depreciation"
    NET_WORKING_CAPITAL                                  = "net_working_capital"
    NET_INVESTED_CAPITAL                                 = "net_invested_capital"
    COMMON_STOCK_SHARES_OUTSTANDING                      = "common_stock_shares_outstanding"

_BALANCE_SHEET_ALL_COLUMNS = (
    _BalanceSheetColumns.SYMBOL_CODE,
    _BalanceSheetColumns.EXCHANGE_CODE,
    _BalanceSheetColumns.DATE,
    _BalanceSheetColumns.FILING_DATE,
    _BalanceSheetColumns.CURRENCY_SYMBOL,
    _BalanceSheetColumns.TOTAL_ASSETS,
    _BalanceSheetColumns.INTANGIBLE_ASSETS,
    _BalanceSheetColumns.EARNING_ASSETS,
    _BalanceSheetColumns.OTHER_CURRENT_ASSETS,
    _BalanceSheetColumns.TOTAL_LIAB,
    _BalanceSheetColumns.TOTAL_STOCKHOLDER_EQUITY,
    _BalanceSheetColumns.DEFERRED_LONG_TERM_LIAB,
    _BalanceSheetColumns.OTHER_CURRENT_LIAB,
    _BalanceSheetColumns.COMMON_STOCK,
    _BalanceSheetColumns.CAPITAL_STOCK,
    _BalanceSheetColumns.RETAINED_EARNINGS,
    _BalanceSheetColumns.OTHER_LIAB,
    _BalanceSheetColumns.GOOD_WILL,
    _BalanceSheetColumns.OTHER_ASSETS,
    _BalanceSheetColumns.CASH,
    _BalanceSheetColumns.CASH_AND_EQUIVALENTS,
    _BalanceSheetColumns.TOTAL_CURRENT_LIABILITIES,
    _BalanceSheetColumns.CURRENT_DEFERRED_REVENUE,
    _BalanceSheetColumns.NET_DEBT,
    _BalanceSheetColumns.SHORT_TERM_DEBT,
    _BalanceSheetColumns.SHORT_LONG_TERM_DEBT,
    _BalanceSheetColumns.SHORT_LONG_TERM_DEBT_TOTAL,
    _BalanceSheetColumns.OTHER_STOCKHOLDER_EQUITY,
    _BalanceSheetColumns.PROPERTY_PLANT_EQUIPMENT,
    _BalanceSheetColumns.TOTAL_CURRENT_ASSETS,
    _BalanceSheetColumns.LONG_TERM_INVESTMENTS,
    _BalanceSheetColumns.NET_TANGIBLE_ASSETS,
    _BalanceSheetColumns.SHORT_TERM_INVESTMENTS,
    _BalanceSheetColumns.NET_RECEIVABLES,
    _BalanceSheetColumns.LONG_TERM_DEBT,
    _BalanceSheetColumns.INVENTORY,
    _BalanceSheetColumns.ACCOUNTS_PAYABLE,
    _BalanceSheetColumns.TOTAL_PERMANENT_EQUITY,
    _BalanceSheetColumns.NONCONTROLLING_INTEREST_IN_CONSOLIDATED_ENTITY,
    _BalanceSheetColumns.TEMPORARY_EQUITY_REDEEMABLE_NONCONTROLLING_INTERESTS,
    _BalanceSheetColumns.ACCUMULATED_OTHER_COMPREHENSIVE_INCOME,
    _BalanceSheetColumns.ADDITIONAL_PAID_IN_CAPITAL,
    _BalanceSheetColumns.COMMON_STOCK_TOTAL_EQUITY,
    _BalanceSheetColumns.PREFERRED_STOCK_TOTAL_EQUITY,
    _BalanceSheetColumns.RETAINED_EARNINGS_TOTAL_EQUITY,
    _BalanceSheetColumns.TREASURY_STOCK,
    _BalanceSheetColumns.ACCUMULATED_AMORTIZATION,
    _BalanceSheetColumns.NON_CURRRENT_ASSETS_OTHER,
    _BalanceSheetColumns.DEFERRED_LONG_TERM_ASSET_CHARGES,
    _BalanceSheetColumns.NON_CURRENT_ASSETS_TOTAL,
    _BalanceSheetColumns.CAPITAL_LEASE_OBLIGATIONS,
    _BalanceSheetColumns.LONG_TERM_DEBT_TOTAL,
    _BalanceSheetColumns.NON_CURRENT_LIABILITIES_OTHER,
    _BalanceSheetColumns.NON_CURRENT_LIABILITIES_TOTAL,
    _BalanceSheetColumns.NEGATIVE_GOODWILL,
    _BalanceSheetColumns.WARRANTS,
    _BalanceSheetColumns.CAPITAL_SURPLUSE,
    _BalanceSheetColumns.LIABILITIES_AND_STOCKHOLDERS_EQUITY,
    _BalanceSheetColumns.CASH_AND_SHORT_TERM_INVESTMENTS,
    _BalanceSheetColumns.PROPERTY_PLANT_AND_EQUIPMENT_GROSS,
    _BalanceSheetColumns.PROPERTY_PLANT_AND_EQUIPMENT_NET,
    _BalanceSheetColumns.ACCUMULATED_DEPRECIATION,
    _BalanceSheetColumns.NET_WORKING_CAPITAL,
    _BalanceSheetColumns.NET_INVESTED_CAPITAL,
    _BalanceSheetColumns.COMMON_STOCK_SHARES_OUTSTANDING,
)


class _CashFlowColumns:
    """Column constants shared by cash_flow_quarterly and cash_flow_annually."""
    SYMBOL_CODE                             = "symbol_code"
    EXCHANGE_CODE                           = "exchange_code"
    DATE                                    = "date"
    FILING_DATE                             = "filing_date"
    CURRENCY_SYMBOL                         = "currency_symbol"
    INVESTMENTS                             = "investments"
    CHANGE_TO_LIABILITIES                   = "change_to_liabilities"
    TOTAL_CASHFLOWS_FROM_INVESTING_ACTIVITIES = "total_cashflows_from_investing_activities"
    NET_BORROWINGS                          = "net_borrowings"
    TOTAL_CASH_FROM_FINANCING_ACTIVITIES    = "total_cash_from_financing_activities"
    CHANGE_TO_OPERATING_ACTIVITIES          = "change_to_operating_activities"
    NET_INCOME                              = "net_income"
    CHANGE_IN_CASH                          = "change_in_cash"
    BEGIN_PERIOD_CASH_FLOW                  = "begin_period_cash_flow"
    END_PERIOD_CASH_FLOW                    = "end_period_cash_flow"
    TOTAL_CASH_FROM_OPERATING_ACTIVITIES    = "total_cash_from_operating_activities"
    ISSUANCE_OF_CAPITAL_STOCK               = "issuance_of_capital_stock"
    DEPRECIATION                            = "depreciation"
    OTHER_CASHFLOWS_FROM_INVESTING_ACTIVITIES = "other_cashflows_from_investing_activities"
    DIVIDENDS_PAID                          = "dividends_paid"
    CHANGE_TO_INVENTORY                     = "change_to_inventory"
    CHANGE_TO_ACCOUNT_RECEIVABLES           = "change_to_account_receivables"
    SALE_PURCHASE_OF_STOCK                  = "sale_purchase_of_stock"
    OTHER_CASHFLOWS_FROM_FINANCING_ACTIVITIES = "other_cashflows_from_financing_activities"
    CHANGE_TO_NETINCOME                     = "change_to_netincome"
    CAPITAL_EXPENDITURES                    = "capital_expenditures"
    CHANGE_RECEIVABLES                      = "change_receivables"
    CASH_FLOWS_OTHER_OPERATING              = "cash_flows_other_operating"
    EXCHANGE_RATE_CHANGES                   = "exchange_rate_changes"
    CASH_AND_CASH_EQUIVALENTS_CHANGES       = "cash_and_cash_equivalents_changes"
    CHANGE_IN_WORKING_CAPITAL               = "change_in_working_capital"
    STOCK_BASED_COMPENSATION                = "stock_based_compensation"
    OTHER_NON_CASH_ITEMS                    = "other_non_cash_items"
    FREE_CASH_FLOW                          = "free_cash_flow"

_CASH_FLOW_ALL_COLUMNS = (
    _CashFlowColumns.SYMBOL_CODE,
    _CashFlowColumns.EXCHANGE_CODE,
    _CashFlowColumns.DATE,
    _CashFlowColumns.FILING_DATE,
    _CashFlowColumns.CURRENCY_SYMBOL,
    _CashFlowColumns.INVESTMENTS,
    _CashFlowColumns.CHANGE_TO_LIABILITIES,
    _CashFlowColumns.TOTAL_CASHFLOWS_FROM_INVESTING_ACTIVITIES,
    _CashFlowColumns.NET_BORROWINGS,
    _CashFlowColumns.TOTAL_CASH_FROM_FINANCING_ACTIVITIES,
    _CashFlowColumns.CHANGE_TO_OPERATING_ACTIVITIES,
    _CashFlowColumns.NET_INCOME,
    _CashFlowColumns.CHANGE_IN_CASH,
    _CashFlowColumns.BEGIN_PERIOD_CASH_FLOW,
    _CashFlowColumns.END_PERIOD_CASH_FLOW,
    _CashFlowColumns.TOTAL_CASH_FROM_OPERATING_ACTIVITIES,
    _CashFlowColumns.ISSUANCE_OF_CAPITAL_STOCK,
    _CashFlowColumns.DEPRECIATION,
    _CashFlowColumns.OTHER_CASHFLOWS_FROM_INVESTING_ACTIVITIES,
    _CashFlowColumns.DIVIDENDS_PAID,
    _CashFlowColumns.CHANGE_TO_INVENTORY,
    _CashFlowColumns.CHANGE_TO_ACCOUNT_RECEIVABLES,
    _CashFlowColumns.SALE_PURCHASE_OF_STOCK,
    _CashFlowColumns.OTHER_CASHFLOWS_FROM_FINANCING_ACTIVITIES,
    _CashFlowColumns.CHANGE_TO_NETINCOME,
    _CashFlowColumns.CAPITAL_EXPENDITURES,
    _CashFlowColumns.CHANGE_RECEIVABLES,
    _CashFlowColumns.CASH_FLOWS_OTHER_OPERATING,
    _CashFlowColumns.EXCHANGE_RATE_CHANGES,
    _CashFlowColumns.CASH_AND_CASH_EQUIVALENTS_CHANGES,
    _CashFlowColumns.CHANGE_IN_WORKING_CAPITAL,
    _CashFlowColumns.STOCK_BASED_COMPENSATION,
    _CashFlowColumns.OTHER_NON_CASH_ITEMS,
    _CashFlowColumns.FREE_CASH_FLOW,
)


class _IncomeStatementColumns:
    """Column constants shared by income_statement_quarterly and income_statement_annually."""
    SYMBOL_CODE                             = "symbol_code"
    EXCHANGE_CODE                           = "exchange_code"
    DATE                                    = "date"
    FILING_DATE                             = "filing_date"
    CURRENCY_SYMBOL                         = "currency_symbol"
    RESEARCH_DEVELOPMENT                    = "research_development"
    EFFECT_OF_ACCOUNTING_CHARGES            = "effect_of_accounting_charges"
    INCOME_BEFORE_TAX                       = "income_before_tax"
    MINORITY_INTEREST                       = "minority_interest"
    NET_INCOME                              = "net_income"
    SELLING_GENERAL_ADMINISTRATIVE          = "selling_general_administrative"
    SELLING_AND_MARKETING_EXPENSES          = "selling_and_marketing_expenses"
    GROSS_PROFIT                            = "gross_profit"
    RECONCILED_DEPRECIATION                 = "reconciled_depreciation"
    EBIT                                    = "ebit"
    EBITDA                                  = "ebitda"
    DEPRECIATION_AND_AMORTIZATION           = "depreciation_and_amortization"
    NON_OPERATING_INCOME_NET_OTHER          = "non_operating_income_net_other"
    OPERATING_INCOME                        = "operating_income"
    OTHER_OPERATING_EXPENSES                = "other_operating_expenses"
    INTEREST_EXPENSE                        = "interest_expense"
    TAX_PROVISION                           = "tax_provision"
    INTEREST_INCOME                         = "interest_income"
    NET_INTEREST_INCOME                     = "net_interest_income"
    EXTRAORDINARY_ITEMS                     = "extraordinary_items"
    NON_RECURRING                           = "non_recurring"
    OTHER_ITEMS                             = "other_items"
    INCOME_TAX_EXPENSE                      = "income_tax_expense"
    TOTAL_REVENUE                           = "total_revenue"
    TOTAL_OPERATING_EXPENSES                = "total_operating_expenses"
    COST_OF_REVENUE                         = "cost_of_revenue"
    TOTAL_OTHER_INCOME_EXPENSE_NET          = "total_other_income_expense_net"
    DISCONTINUED_OPERATIONS                 = "discontinued_operations"
    NET_INCOME_FROM_CONTINUING_OPS          = "net_income_from_continuing_ops"
    NET_INCOME_APPLICABLE_TO_COMMON_SHARES  = "net_income_applicable_to_common_shares"

_INCOME_STATEMENT_ALL_COLUMNS = (
    _IncomeStatementColumns.SYMBOL_CODE,
    _IncomeStatementColumns.EXCHANGE_CODE,
    _IncomeStatementColumns.DATE,
    _IncomeStatementColumns.FILING_DATE,
    _IncomeStatementColumns.CURRENCY_SYMBOL,
    _IncomeStatementColumns.RESEARCH_DEVELOPMENT,
    _IncomeStatementColumns.EFFECT_OF_ACCOUNTING_CHARGES,
    _IncomeStatementColumns.INCOME_BEFORE_TAX,
    _IncomeStatementColumns.MINORITY_INTEREST,
    _IncomeStatementColumns.NET_INCOME,
    _IncomeStatementColumns.SELLING_GENERAL_ADMINISTRATIVE,
    _IncomeStatementColumns.SELLING_AND_MARKETING_EXPENSES,
    _IncomeStatementColumns.GROSS_PROFIT,
    _IncomeStatementColumns.RECONCILED_DEPRECIATION,
    _IncomeStatementColumns.EBIT,
    _IncomeStatementColumns.EBITDA,
    _IncomeStatementColumns.DEPRECIATION_AND_AMORTIZATION,
    _IncomeStatementColumns.NON_OPERATING_INCOME_NET_OTHER,
    _IncomeStatementColumns.OPERATING_INCOME,
    _IncomeStatementColumns.OTHER_OPERATING_EXPENSES,
    _IncomeStatementColumns.INTEREST_EXPENSE,
    _IncomeStatementColumns.TAX_PROVISION,
    _IncomeStatementColumns.INTEREST_INCOME,
    _IncomeStatementColumns.NET_INTEREST_INCOME,
    _IncomeStatementColumns.EXTRAORDINARY_ITEMS,
    _IncomeStatementColumns.NON_RECURRING,
    _IncomeStatementColumns.OTHER_ITEMS,
    _IncomeStatementColumns.INCOME_TAX_EXPENSE,
    _IncomeStatementColumns.TOTAL_REVENUE,
    _IncomeStatementColumns.TOTAL_OPERATING_EXPENSES,
    _IncomeStatementColumns.COST_OF_REVENUE,
    _IncomeStatementColumns.TOTAL_OTHER_INCOME_EXPENSE_NET,
    _IncomeStatementColumns.DISCONTINUED_OPERATIONS,
    _IncomeStatementColumns.NET_INCOME_FROM_CONTINUING_OPS,
    _IncomeStatementColumns.NET_INCOME_APPLICABLE_TO_COMMON_SHARES,
)


# ---------------------------------------------------------------------------
# Earnings tables
# ---------------------------------------------------------------------------

class TableEarningsQuarterly(Table):
    """Constants for the 'earnings_quarterly' table."""
    NAME = "earnings_quarterly"

    class Columns:
        SYMBOL_CODE         = "symbol_code"
        EXCHANGE_CODE       = "exchange_code"
        REPORT_DATE         = "report_date"
        DATE                = "date"
        BEFORE_AFTER_MARKET = "before_after_market"
        CURRENCY            = "currency"
        EPS_ACTUAL          = "eps_actual"
        EPS_ESTIMATE        = "eps_estimate"
        EPS_DIFFERENCE      = "eps_difference"
        SURPRISE_PERCENT    = "surprise_percent"

    TIMESTAMP_COLUMN = Columns.REPORT_DATE

    UNIQUE_KEY_COLUMNS = (
        Columns.SYMBOL_CODE,
        Columns.EXCHANGE_CODE,
        Columns.REPORT_DATE,
    )

    ALL_COLUMNS = (
        Columns.SYMBOL_CODE,
        Columns.EXCHANGE_CODE,
        Columns.REPORT_DATE,
        Columns.DATE,
        Columns.BEFORE_AFTER_MARKET,
        Columns.CURRENCY,
        Columns.EPS_ACTUAL,
        Columns.EPS_ESTIMATE,
        Columns.EPS_DIFFERENCE,
        Columns.SURPRISE_PERCENT,
    )


class TableEarningsAnnually(Table):
    """Constants for the 'earnings_annually' table."""
    NAME = "earnings_annually"

    class Columns:
        SYMBOL_CODE     = "symbol_code"
        EXCHANGE_CODE   = "exchange_code"
        DATE            = "date"
        EPS_ACTUAL      = "eps_actual"

    TIMESTAMP_COLUMN = Columns.DATE

    UNIQUE_KEY_COLUMNS = (
        Columns.SYMBOL_CODE,
        Columns.EXCHANGE_CODE,
        Columns.DATE,
    )

    ALL_COLUMNS = (
        Columns.SYMBOL_CODE,
        Columns.EXCHANGE_CODE,
        Columns.DATE,
        Columns.EPS_ACTUAL,
    )


# ---------------------------------------------------------------------------
# Balance sheet tables
# ---------------------------------------------------------------------------

class TableBalanceSheetQuarterly(Table):
    """Constants for the 'balance_sheet_quarterly' table."""
    NAME = "balance_sheet_quarterly"
    Columns = _BalanceSheetColumns
    TIMESTAMP_COLUMN = _BalanceSheetColumns.FILING_DATE
    UNIQUE_KEY_COLUMNS = (
        _BalanceSheetColumns.SYMBOL_CODE,
        _BalanceSheetColumns.EXCHANGE_CODE,
        _BalanceSheetColumns.FILING_DATE,
    )
    ALL_COLUMNS = _BALANCE_SHEET_ALL_COLUMNS


class TableBalanceSheetAnnually(Table):
    """Constants for the 'balance_sheet_annually' table."""
    NAME = "balance_sheet_annually"
    Columns = _BalanceSheetColumns
    TIMESTAMP_COLUMN = _BalanceSheetColumns.FILING_DATE
    UNIQUE_KEY_COLUMNS = (
        _BalanceSheetColumns.SYMBOL_CODE,
        _BalanceSheetColumns.EXCHANGE_CODE,
        _BalanceSheetColumns.FILING_DATE,
    )
    ALL_COLUMNS = _BALANCE_SHEET_ALL_COLUMNS


# ---------------------------------------------------------------------------
# Cash flow tables
# ---------------------------------------------------------------------------

class TableCashFlowQuarterly(Table):
    """Constants for the 'cash_flow_quarterly' table."""
    NAME = "cash_flow_quarterly"
    Columns = _CashFlowColumns
    TIMESTAMP_COLUMN = _CashFlowColumns.FILING_DATE
    UNIQUE_KEY_COLUMNS = (
        _CashFlowColumns.SYMBOL_CODE,
        _CashFlowColumns.EXCHANGE_CODE,
        _CashFlowColumns.FILING_DATE,
    )
    ALL_COLUMNS = _CASH_FLOW_ALL_COLUMNS


class TableCashFlowAnnually(Table):
    """Constants for the 'cash_flow_annually' table."""
    NAME = "cash_flow_annually"
    Columns = _CashFlowColumns
    TIMESTAMP_COLUMN = _CashFlowColumns.FILING_DATE
    UNIQUE_KEY_COLUMNS = (
        _CashFlowColumns.SYMBOL_CODE,
        _CashFlowColumns.EXCHANGE_CODE,
        _CashFlowColumns.FILING_DATE,
    )
    ALL_COLUMNS = _CASH_FLOW_ALL_COLUMNS


# ---------------------------------------------------------------------------
# Income statement tables
# ---------------------------------------------------------------------------

class TableIncomeStatementQuarterly(Table):
    """Constants for the 'income_statement_quarterly' table."""
    NAME = "income_statement_quarterly"
    Columns = _IncomeStatementColumns
    TIMESTAMP_COLUMN = _IncomeStatementColumns.FILING_DATE
    UNIQUE_KEY_COLUMNS = (
        _IncomeStatementColumns.SYMBOL_CODE,
        _IncomeStatementColumns.EXCHANGE_CODE,
        _IncomeStatementColumns.FILING_DATE,
    )
    ALL_COLUMNS = _INCOME_STATEMENT_ALL_COLUMNS


class TableIncomeStatementAnnually(Table):
    """Constants for the 'income_statement_annually' table."""
    NAME = "income_statement_annually"
    Columns = _IncomeStatementColumns
    TIMESTAMP_COLUMN = _IncomeStatementColumns.FILING_DATE
    UNIQUE_KEY_COLUMNS = (
        _IncomeStatementColumns.SYMBOL_CODE,
        _IncomeStatementColumns.EXCHANGE_CODE,
        _IncomeStatementColumns.FILING_DATE,
    )
    ALL_COLUMNS = _INCOME_STATEMENT_ALL_COLUMNS


# Type Hint for tables in this class
FundamentalTableType = (TableEarningsQuarterly | TableEarningsAnnually |
                        TableBalanceSheetQuarterly | TableBalanceSheetAnnually |
                        TableCashFlowQuarterly | TableCashFlowAnnually |
                        TableIncomeStatementQuarterly | TableIncomeStatementAnnually)
# Table names
TABLE_NAMES_FUNDAMENTAL = [TableEarningsQuarterly.NAME, TableEarningsAnnually.NAME,
                           TableBalanceSheetQuarterly.NAME, TableBalanceSheetAnnually.NAME,
                           TableCashFlowQuarterly.NAME, TableCashFlowAnnually.NAME,
                           TableIncomeStatementQuarterly.NAME, TableIncomeStatementAnnually.NAME]