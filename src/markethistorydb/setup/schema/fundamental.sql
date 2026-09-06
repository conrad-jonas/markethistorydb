DROP TABLE IF EXISTS earnings_quarterly;
DROP TABLE IF EXISTS earnings_annually;
DROP TABLE IF EXISTS balance_sheet_quarterly;
DROP TABLE IF EXISTS balance_sheet_annually;
DROP TABLE IF EXISTS cash_flow_quarterly;
DROP TABLE IF EXISTS cash_flow_annually;
DROP TABLE IF EXISTS income_statement_quarterly;
DROP TABLE IF EXISTS income_statement_annually;

CREATE TABLE IF NOT EXISTS earnings_quarterly (
    symbol_code         SYMBOL,
    exchange_code       SYMBOL,
    report_date         TIMESTAMP, -- the date of the actual report. It should be noted that for US stocks specifically, this is the date of the 8K report, not of the 10K/10Q one (for those reports' dates, please see the Financials section). For major companies, such as e. g. AAPL, this might be just the day before the earnings call, while for lesser companies, such as e. g. SCCO, the difference in days between the two reports may be longer
    date                TIMESTAMP, -- the end of the reported period.
	before_after_market SYMBOL,    -- beforeMarket: earnings reported before market opened; AfterMarket: earnings reported after market closed; null: unknown.
	currency            SYMBOL,    -- currency
	eps_actual          DOUBLE,    -- the actual non-GAAP EPS reported by the company.
	eps_estimate        DOUBLE,    -- the EPS that was estimated to happen prior to the earnings release.
	eps_difference      DOUBLE,    -- epsActual - epsEstimate.
	surprise_percent    DOUBLE     -- (epsActual - epsEstimate) / epsEstimate.
) TIMESTAMP(report_date) PARTITION BY YEAR WAL
DEDUP UPSERT KEYS(symbol_code, exchange_code, report_date);

CREATE TABLE IF NOT EXISTS earnings_annually (
    symbol_code         SYMBOL,
    exchange_code       SYMBOL,
    date                TIMESTAMP, -- the end of the reported period.
	eps_actual          DOUBLE     -- the sum of the 4 quarterly EPS of the calendar year.
) TIMESTAMP(date) PARTITION BY YEAR WAL
DEDUP UPSERT KEYS(symbol_code, exchange_code, date);

CREATE TABLE IF NOT EXISTS balance_sheet_quarterly (
    symbol_code                                             SYMBOL,
    exchange_code                                           SYMBOL,
    date                                                    TIMESTAMP, -- the end of the reported period.
    filing_date                                             TIMESTAMP, -- the filing date of the financial report.
    currency_symbol                                         SYMBOL,    -- currency
    total_assets                                            DOUBLE,    -- the total amount of assets owned by a company.
    intangible_assets                                       DOUBLE,    -- assets that have no physical form. These are long-term assets that accrue value year over year. Examples of intangible assets include intellectual property, brand recognition and reputation, relationships, and goodwill.
    earning_assets                                          DOUBLE,    -- income-producing investments that are owned or held by a business, institution, or individual. Earning assets include stocks, bonds, rental property income, CDs, and other interest or dividend-earning accounts.
    other_current_assets                                    DOUBLE,    -- a category of things of value that a company owns, benefits from, or uses to generate income that can be converted into cash within one business cycle.
    total_liab                                              DOUBLE,    -- the combined debts and obligations that a company owes to outside parties. totalLiab = totalCurrentLiabilities + nonCurrentLiabilitiesTotal.
    total_stockholder_equity                                DOUBLE,    -- assets remaining in a business once all liabilities have been settled. totalStockholderEquity = totalAssets - totalLiab.
    deferred_long_term_liab                                 DOUBLE,    -- deferred tax liability is a type of long-term liability incurred when a company postpones paying taxes on certain types of accounting income. The amount of the liability is the difference between a company's taxable income and its accounting or book income.
    other_current_liab                                      DOUBLE,    -- the current liabilities (due within 12 months) that are insignificant separately, but are clumped together on the company's liabilities.
    common_stock                                            DOUBLE,    -- same as capitalStock.
    capital_stock                                           DOUBLE,    -- the total amount of common and preferred shares that a company is authorized to issue, according to its corporate charter. Capital stock can only be issued by the company and is the maximum number of shares that can ever be outstanding.
    retained_earnings                                       DOUBLE,    -- same as retainedEarningsTotalEquity. The amount of profit a company has left over after paying all its direct costs, indirect costs, income taxes and its dividends to shareholders.
    other_liab                                              DOUBLE,    -- all balance sheet liability accounts not covered specifically in other areas of the supervisory activity.
    good_will                                               DOUBLE,    -- an intangible asset that is associated with the purchase of one company by another. It represents value that can give the acquiring company a competitive advantage. The value of a company's name, brand reputation, loyal customer base, solid customer service, good employee relations, and proprietary technology represent aspects of goodwill. This value is why one company may pay a premium for another.
    other_assets                                            DOUBLE,    -- same as nonCurrentAssetsOther.
    cash                                                    DOUBLE,    -- the fields cash and cashAndEquivalents are interchangeable for US tickers, the latter being a later addition to the template. For other exchanges, this may differ in some cases, and "cash" will only have the cash figure.
    cash_and_equivalents                                    DOUBLE,    -- the fields cash and cashAndEquivalents are interchangeable for US tickers, the latter being a later addition to the template. For other exchanges, this may differ in some cases, and "cashAndEquivalents" will have the figure corresponding to cash and its equivalents from the financial report.
    total_current_liabilities                               DOUBLE,    -- the current liabilities (due within 12 months). accountsPayable + shortLongTermDebt + otherCurrentLiab + (Current portion of operating lease liabilities - not yet available) + (Income taxes payable - not available). OR: shortTermDebt + shortLongTermDebtTotal + otherCurrentLiab. OR: totalCurrentLiabilities = totalLiab - nonCurrentLiabilitiesTotal.
    current_deferred_revenue                                DOUBLE,    -- the deferred revenue liability, current to the period. It can be used in place of deferred liability.
    net_debt                                                DOUBLE,    -- a metric that shows how much debt a company has on its balance sheet compared to its liquid assets. netDebt = shortTermDebt + longTermDebtTotal - cash.
    short_term_debt                                         DOUBLE,    -- Short-term debt refers to any debt that is due within one year or less. This may include loans, credit card balances, and other obligations that are expected to be paid off within the next 12 months. For some companies, this number represents the current capital lease obligations.
    short_long_term_debt                                    DOUBLE,    -- the Short/Current Long-Term Debt (current portion of the long term debt).
    short_long_term_debt_total                              DOUBLE,    -- may differ between companies: longTermDebt/longTermDebtTotal +  shortTermDebt / + shortLongTermDebt / = shortLongTermDebtTotal.
    other_stockholder_equity                                DOUBLE,    -- may correspond to accumulatedOtherComprehensiveIncome with some companies, or may differ for others.
    property_plant_equipment                                DOUBLE,    -- same as propertyPlantAndEquipmentNet.
    total_current_assets                                    DOUBLE,    -- the sum of all current assets. totalCurrentAssets = cashAndEquivalents + shortTermInvestments + netReceivables +inventory + otherCurrentAssets.
    long_term_investments                                   DOUBLE,    -- marketable securities.
    net_tangible_assets                                     DOUBLE,    -- the total physical assets of a company minus all intangible assets and liabilities.
    short_term_investments                                  DOUBLE,    -- marketable securities.
    net_receivables                                         DOUBLE,    -- the total money owed to a company by its customers minus the money owed that will likely never be paid.
    long_term_debt                                          DOUBLE,    -- any debt that is due in more than one year.
    inventory                                               DOUBLE,    -- raw materials used to produce goods as well as the goods that are available for sale.
    accounts_payable                                        DOUBLE,    -- amounts due to vendors or suppliers for goods or services received that have not yet been paid for.
    total_permanent_equity                                  DOUBLE,    -- the sum of paid in capital and net income less any distributions.
    noncontrolling_interest_in_consolidated_entity          DOUBLE,    -- minority interest in the balance sheet.
    temporary_equity_redeemable_noncontrolling_interests    DOUBLE,    -- an ownership stake in a corporation, with the investors owning a minority interest and having less influence over how the company is managed.
    accumulated_other_comprehensive_income                  DOUBLE,    -- same as otherStockholderEquity.
    additional_paid_in_capital                              DOUBLE,    -- the difference between the par value of a stock and the price that investors actually pay for it.
    common_stock_total_equity                               DOUBLE,    -- the total amount of all investments in a company made by common equity investors, including the total value of all shares of common stock, plus retained earnings and additional paid-in capital.
    preferred_stock_total_equity                            DOUBLE,    -- the total amount of all investments in a company made by preferred equity investors.
    retained_earnings_total_equity                          DOUBLE,    -- same as retainedEarnings.
    treasury_stock                                          DOUBLE,    -- the portion of a company's shares that are held by its treasury and not available to the public.
    accumulated_amortization                                DOUBLE,    -- the cumulative amount of all amortization expenses that has been charged against an intangible asset.
    non_currrent_assets_other                               DOUBLE,    -- same as otherAssets. noncurrent assets are long-term and have a useful life of more than a year.
    deferred_long_term_asset_charges                        DOUBLE,    -- long-term prepaid expenses that are carried as an asset on a balance sheet until used/consumed.
    non_current_assets_total                                DOUBLE,    -- noncurrent assets are long-term and have a useful life of more than a year.
    capital_lease_obligations                               DOUBLE,    -- long-term (non-current) amount of hire charges or rent owed by the lessee to the lessor for taking capital assets on hire under a capital lease.
    long_term_debt_total                                    DOUBLE,    -- may be same as longTermDebt for some companies, or longTermDebt + capitalLeaseObligations for others.
    non_current_liabilities_other                           DOUBLE,    -- a part of non-current liabilities that is not directly classifiable.
    non_current_liabilities_total                           DOUBLE,    -- the debts that a business owes, but isn't due to pay for at least 12 months. nonCurrentLiabilitiesTotal = totalLiab - totalCurrentLiabilities.
    negative_goodwill                                       DOUBLE,    -- negative goodwill, also known as bargain purchase gain, occurs when the fair value of the net assets acquired in a merger or acquisition exceeds the purchase price.
    warrants                                                DOUBLE,    -- the amount of derivatives that give the right, but not the obligation, to buy or sell a security - most commonly an equity - at a certain price before expiration.
    capital_surpluse                                        DOUBLE,    -- the surplus resulting after common stock is sold for more than its par value.
    liabilities_and_stockholders_equity                     DOUBLE,    -- same as totalAssets: liabilitiesAndStockholdersEquity = totalLiab + totalStockholderEquity.
    cash_and_short_term_investments                         DOUBLE,    -- cash and short term investments.
    property_plant_and_equipment_gross                      DOUBLE,    -- gross PPE,
    property_plant_and_equipment_net                        DOUBLE,    -- net PPE, same as propertyPlantEquipment.
    accumulated_depreciation                                DOUBLE,    -- the total amount an asset has been depreciated up until a single point.
    net_working_capital                                     DOUBLE,    -- (totalCurrentAssets - cash)  - (totalCurrentLiabilities - shortLongTermDebtTotal).
    net_invested_capital                                    DOUBLE,    -- the total amount of money that a company spends on capital assets, minus the cost of the depreciation of those assets.
    common_stock_shares_outstanding                         DOUBLE    -- the shares of common stock that have been issued minus any shares of common stock known as treasury stock. This is the weighted average diluted number (the total number of shares if the convertible securities of a company were exercised) used for EPS calculations.
) TIMESTAMP(filing_date) PARTITION BY YEAR WAL
DEDUP UPSERT KEYS(symbol_code, exchange_code, filing_date);

CREATE TABLE IF NOT EXISTS balance_sheet_annually (
    symbol_code                                             SYMBOL,
    exchange_code                                           SYMBOL,
    date                                                    TIMESTAMP, -- the end of the reported period.
    filing_date                                             TIMESTAMP, -- the filing date of the financial report.
    currency_symbol                                         SYMBOL,    -- currency
    total_assets                                            DOUBLE,    -- the total amount of assets owned by a company.
    intangible_assets                                       DOUBLE,    -- assets that have no physical form. These are long-term assets that accrue value year over year. Examples of intangible assets include intellectual property, brand recognition and reputation, relationships, and goodwill.
    earning_assets                                          DOUBLE,    -- income-producing investments that are owned or held by a business, institution, or individual. Earning assets include stocks, bonds, rental property income, CDs, and other interest or dividend-earning accounts.
    other_current_assets                                    DOUBLE,    -- a category of things of value that a company owns, benefits from, or uses to generate income that can be converted into cash within one business cycle.
    total_liab                                              DOUBLE,    -- the combined debts and obligations that a company owes to outside parties. totalLiab = totalCurrentLiabilities + nonCurrentLiabilitiesTotal.
    total_stockholder_equity                                DOUBLE,    -- assets remaining in a business once all liabilities have been settled. totalStockholderEquity = totalAssets - totalLiab.
    deferred_long_term_liab                                 DOUBLE,    -- deferred tax liability is a type of long-term liability incurred when a company postpones paying taxes on certain types of accounting income. The amount of the liability is the difference between a company's taxable income and its accounting or book income.
    other_current_liab                                      DOUBLE,    -- the current liabilities (due within 12 months) that are insignificant separately, but are clumped together on the company's liabilities.
    common_stock                                            DOUBLE,    -- same as capitalStock.
    capital_stock                                           DOUBLE,    -- the total amount of common and preferred shares that a company is authorized to issue, according to its corporate charter. Capital stock can only be issued by the company and is the maximum number of shares that can ever be outstanding.
    retained_earnings                                       DOUBLE,    -- same as retainedEarningsTotalEquity. The amount of profit a company has left over after paying all its direct costs, indirect costs, income taxes and its dividends to shareholders.
    other_liab                                              DOUBLE,    -- all balance sheet liability accounts not covered specifically in other areas of the supervisory activity.
    good_will                                               DOUBLE,    -- an intangible asset that is associated with the purchase of one company by another. It represents value that can give the acquiring company a competitive advantage. The value of a company's name, brand reputation, loyal customer base, solid customer service, good employee relations, and proprietary technology represent aspects of goodwill. This value is why one company may pay a premium for another.
    other_assets                                            DOUBLE,    -- same as nonCurrentAssetsOther.
    cash                                                    DOUBLE,    -- the fields cash and cashAndEquivalents are interchangeable for US tickers, the latter being a later addition to the template. For other exchanges, this may differ in some cases, and "cash" will only have the cash figure.
    cash_and_equivalents                                    DOUBLE,    -- the fields cash and cashAndEquivalents are interchangeable for US tickers, the latter being a later addition to the template. For other exchanges, this may differ in some cases, and "cashAndEquivalents" will have the figure corresponding to cash and its equivalents from the financial report.
    total_current_liabilities                               DOUBLE,    -- the current liabilities (due within 12 months). accountsPayable + shortLongTermDebt + otherCurrentLiab + (Current portion of operating lease liabilities - not yet available) + (Income taxes payable - not available). OR: shortTermDebt + shortLongTermDebtTotal + otherCurrentLiab. OR: totalCurrentLiabilities = totalLiab - nonCurrentLiabilitiesTotal.
    current_deferred_revenue                                DOUBLE,    -- the deferred revenue liability, current to the period. It can be used in place of deferred liability.
    net_debt                                                DOUBLE,    -- a metric that shows how much debt a company has on its balance sheet compared to its liquid assets. netDebt = shortTermDebt + longTermDebtTotal - cash.
    short_term_debt                                         DOUBLE,    -- Short-term debt refers to any debt that is due within one year or less. This may include loans, credit card balances, and other obligations that are expected to be paid off within the next 12 months. For some companies, this number represents the current capital lease obligations.
    short_long_term_debt                                    DOUBLE,    -- the Short/Current Long-Term Debt (current portion of the long term debt).
    short_long_term_debt_total                              DOUBLE,    -- may differ between companies: longTermDebt/longTermDebtTotal +  shortTermDebt / + shortLongTermDebt / = shortLongTermDebtTotal.
    other_stockholder_equity                                DOUBLE,    -- may correspond to accumulatedOtherComprehensiveIncome with some companies, or may differ for others.
    property_plant_equipment                                DOUBLE,    -- same as propertyPlantAndEquipmentNet.
    total_current_assets                                    DOUBLE,    -- the sum of all current assets. totalCurrentAssets = cashAndEquivalents + shortTermInvestments + netReceivables +inventory + otherCurrentAssets.
    long_term_investments                                   DOUBLE,    -- marketable securities.
    net_tangible_assets                                     DOUBLE,    -- the total physical assets of a company minus all intangible assets and liabilities.
    short_term_investments                                  DOUBLE,    -- marketable securities.
    net_receivables                                         DOUBLE,    -- the total money owed to a company by its customers minus the money owed that will likely never be paid.
    long_term_debt                                          DOUBLE,    -- any debt that is due in more than one year.
    inventory                                               DOUBLE,    -- raw materials used to produce goods as well as the goods that are available for sale.
    accounts_payable                                        DOUBLE,    -- amounts due to vendors or suppliers for goods or services received that have not yet been paid for.
    total_permanent_equity                                  DOUBLE,    -- the sum of paid in capital and net income less any distributions.
    noncontrolling_interest_in_consolidated_entity          DOUBLE,    -- minority interest in the balance sheet.
    temporary_equity_redeemable_noncontrolling_interests    DOUBLE,    -- an ownership stake in a corporation, with the investors owning a minority interest and having less influence over how the company is managed.
    accumulated_other_comprehensive_income                  DOUBLE,    -- same as otherStockholderEquity.
    additional_paid_in_capital                              DOUBLE,    -- the difference between the par value of a stock and the price that investors actually pay for it.
    common_stock_total_equity                               DOUBLE,    -- the total amount of all investments in a company made by common equity investors, including the total value of all shares of common stock, plus retained earnings and additional paid-in capital.
    preferred_stock_total_equity                            DOUBLE,    -- the total amount of all investments in a company made by preferred equity investors.
    retained_earnings_total_equity                          DOUBLE,    -- same as retainedEarnings.
    treasury_stock                                          DOUBLE,    -- the portion of a company's shares that are held by its treasury and not available to the public.
    accumulated_amortization                                DOUBLE,    -- the cumulative amount of all amortization expenses that has been charged against an intangible asset.
    non_currrent_assets_other                               DOUBLE,    -- same as otherAssets. noncurrent assets are long-term and have a useful life of more than a year.
    deferred_long_term_asset_charges                        DOUBLE,    -- long-term prepaid expenses that are carried as an asset on a balance sheet until used/consumed.
    non_current_assets_total                                DOUBLE,    -- noncurrent assets are long-term and have a useful life of more than a year.
    capital_lease_obligations                               DOUBLE,    -- long-term (non-current) amount of hire charges or rent owed by the lessee to the lessor for taking capital assets on hire under a capital lease.
    long_term_debt_total                                    DOUBLE,    -- may be same as longTermDebt for some companies, or longTermDebt + capitalLeaseObligations for others.
    non_current_liabilities_other                           DOUBLE,    -- a part of non-current liabilities that is not directly classifiable.
    non_current_liabilities_total                           DOUBLE,    -- the debts that a business owes, but isn't due to pay for at least 12 months. nonCurrentLiabilitiesTotal = totalLiab - totalCurrentLiabilities.
    negative_goodwill                                       DOUBLE,    -- negative goodwill, also known as bargain purchase gain, occurs when the fair value of the net assets acquired in a merger or acquisition exceeds the purchase price.
    warrants                                                DOUBLE,    -- the amount of derivatives that give the right, but not the obligation, to buy or sell a security - most commonly an equity - at a certain price before expiration.
    capital_surpluse                                        DOUBLE,    -- the surplus resulting after common stock is sold for more than its par value.
    liabilities_and_stockholders_equity                     DOUBLE,    -- same as totalAssets: liabilitiesAndStockholdersEquity = totalLiab + totalStockholderEquity.
    cash_and_short_term_investments                         DOUBLE,    -- cash and short term investments.
    property_plant_and_equipment_gross                      DOUBLE,    -- gross PPE,
    property_plant_and_equipment_net                        DOUBLE,    -- net PPE, same as propertyPlantEquipment.
    accumulated_depreciation                                DOUBLE,    -- the total amount an asset has been depreciated up until a single point.
    net_working_capital                                     DOUBLE,    -- (totalCurrentAssets - cash)  - (totalCurrentLiabilities - shortLongTermDebtTotal).
    net_invested_capital                                    DOUBLE,    -- the total amount of money that a company spends on capital assets, minus the cost of the depreciation of those assets.
    common_stock_shares_outstanding                         DOUBLE    -- the shares of common stock that have been issued minus any shares of common stock known as treasury stock. This is the weighted average diluted number (the total number of shares if the convertible securities of a company were exercised) used for EPS calculations.
) TIMESTAMP(filing_date) PARTITION BY YEAR WAL
DEDUP UPSERT KEYS(symbol_code, exchange_code, filing_date);

CREATE TABLE IF NOT EXISTS cash_flow_quarterly (
    symbol_code                                 SYMBOL,
    exchange_code                               SYMBOL,
    date                                        TIMESTAMP, -- the end of the reported period.
    filing_date                                 TIMESTAMP, -- the filing date of the financial report.
    currency_symbol                             SYMBOL,    -- currency
    investments                                 DOUBLE,
    change_to_liabilities                       DOUBLE,    -- the increase or decrease in liabilities from one period to the next.
    total_cashflows_from_investing_activities   DOUBLE,
    net_borrowings                              DOUBLE,    -- total debt borrowed during the year minus total debt repaid in the year.
    total_cash_from_financing_activities        DOUBLE,
    change_to_operating_activities              DOUBLE,    -- a change (positive or negative) to operating activities, not to be confused with totalCashFromOperatingActivities.
    net_income                                  DOUBLE,    -- see the same field on the income statement.
    change_in_cash                              DOUBLE,    -- changeInCash = endPeriodCashFlow - beginPeriodCashFlow. Same as cashAndCashEquivalentsChanges for tickers where cash = cashAndEquivalents.
    begin_period_cash_flow                      DOUBLE,    -- how much cash was available at the start of the period.
    end_period_cash_flow                        DOUBLE,    -- how much cash was available at the end of the period.
    total_cash_from_operating_activities        DOUBLE,    -- cash from operations, not to be confused with changeToOperatingActivities.
    issuance_of_capital_stock                   DOUBLE,    -- the amount of income from the process through which a company offers and sells its shares of stock to investors in order to raise capital.
    depreciation                                DOUBLE,    -- depreciation and amortization, same as reconciledDepreciation and depreciationAndAmortization from the income statement.
    other_cashflows_from_investing_activities   DOUBLE,    -- a non-classified part of investing activities cash flow.
    dividends_paid                              DOUBLE,    -- the sum of all cash dividends paid during the period.
    change_to_inventory                         DOUBLE,    -- the difference between additions to and withdrawals from inventories.
    change_to_account_receivables               DOUBLE,    -- increase or decrease in the account receivables during the period.
    sale_purchase_of_stock                      DOUBLE,    -- cash flow generated from the sale of securities, such as stocks and bonds (positive), or repurchases of stock (negative).
    other_cashflows_from_financing_activities   DOUBLE,    -- a non-classified part of financing activities cash flow.
    change_to_netincome                         DOUBLE,    -- increase or decrease of the net income during the period.
    capital_expenditures                        DOUBLE,    -- funds used by a company to acquire, upgrade, and maintain physical assets such as property, plants, buildings, technology, or equipment.
    change_receivables                          DOUBLE,    -- increase or decrease in the cash that customers owe the company.
    cash_flows_other_operating                  DOUBLE,    -- a non-classified part of operating activities cash flow.
    exchange_rate_changes                       DOUBLE,    -- changes in the value of a company's cash balance due to fluctuations in foreign currency exchange rates.
    cash_and_cash_equivalents_changes           DOUBLE,    -- the change in the cashAndCashEquivalents field during the period. Same as changeInCash for tickers where cash = cashAndEquivalents.
    change_in_working_capital                   DOUBLE,    -- The excess of current assets over current liabilities is referred to as the company's working capital; the difference between the working capital for two given reporting periods is called the change in working capital. changeInWorkingCapital = changeToAccountReceivables + changeToInventory + changeToLiabilities + changeToOperatingActivities.
    stock_based_compensation                    DOUBLE,    -- a kind of compensation given by companies to their employees in the form of equity shares besides the regular cash or salary and bonuses they receive.
    other_non_cash_items                        DOUBLE,    -- expenses listed on an income statement, such as capital depreciation, investment gains, or losses, that do not involve a cash payment. Examples of non-cash items include depreciation, amortization, deferred income tax, stock based compensation that is provided to employees.
    free_cash_flow                              DOUBLE     -- the money a company has left over after paying its operating expenses (OpEx) and capital expenditures (CapEx). totalCashFromOperatingActivities - capitalExpenditures = freeCashFlow.
) TIMESTAMP(filing_date) PARTITION BY YEAR WAL
DEDUP UPSERT KEYS(symbol_code, exchange_code, filing_date);

CREATE TABLE IF NOT EXISTS cash_flow_annually (
    symbol_code                                 SYMBOL,
    exchange_code                               SYMBOL,
    date                                        TIMESTAMP, -- the end of the reported period.
    filing_date                                 TIMESTAMP, -- the filing date of the financial report.
    currency_symbol                             SYMBOL,    -- currency
    investments                                 DOUBLE,
    change_to_liabilities                       DOUBLE,    -- the increase or decrease in liabilities from one period to the next.
    total_cashflows_from_investing_activities   DOUBLE,
    net_borrowings                              DOUBLE,    -- total debt borrowed during the year minus total debt repaid in the year.
    total_cash_from_financing_activities        DOUBLE,
    change_to_operating_activities              DOUBLE,    -- a change (positive or negative) to operating activities, not to be confused with totalCashFromOperatingActivities.
    net_income                                  DOUBLE,    -- see the same field on the income statement.
    change_in_cash                              DOUBLE,    -- changeInCash = endPeriodCashFlow - beginPeriodCashFlow. Same as cashAndCashEquivalentsChanges for tickers where cash = cashAndEquivalents.
    begin_period_cash_flow                      DOUBLE,    -- how much cash was available at the start of the period.
    end_period_cash_flow                        DOUBLE,    -- how much cash was available at the end of the period.
    total_cash_from_operating_activities        DOUBLE,    -- cash from operations, not to be confused with changeToOperatingActivities.
    issuance_of_capital_stock                   DOUBLE,    -- the amount of income from the process through which a company offers and sells its shares of stock to investors in order to raise capital.
    depreciation                                DOUBLE,    -- depreciation and amortization, same as reconciledDepreciation and depreciationAndAmortization from the income statement.
    other_cashflows_from_investing_activities   DOUBLE,    -- a non-classified part of investing activities cash flow.
    dividends_paid                              DOUBLE,    -- the sum of all cash dividends paid during the period.
    change_to_inventory                         DOUBLE,    -- the difference between additions to and withdrawals from inventories.
    change_to_account_receivables               DOUBLE,    -- increase or decrease in the account receivables during the period.
    sale_purchase_of_stock                      DOUBLE,    -- cash flow generated from the sale of securities, such as stocks and bonds (positive), or repurchases of stock (negative).
    other_cashflows_from_financing_activities   DOUBLE,    -- a non-classified part of financing activities cash flow.
    change_to_netincome                         DOUBLE,    -- increase or decrease of the net income during the period.
    capital_expenditures                        DOUBLE,    -- funds used by a company to acquire, upgrade, and maintain physical assets such as property, plants, buildings, technology, or equipment.
    change_receivables                          DOUBLE,    -- increase or decrease in the cash that customers owe the company.
    cash_flows_other_operating                  DOUBLE,    -- a non-classified part of operating activities cash flow.
    exchange_rate_changes                       DOUBLE,    -- changes in the value of a company's cash balance due to fluctuations in foreign currency exchange rates.
    cash_and_cash_equivalents_changes           DOUBLE,    -- the change in the cashAndCashEquivalents field during the period. Same as changeInCash for tickers where cash = cashAndEquivalents.
    change_in_working_capital                   DOUBLE,    -- The excess of current assets over current liabilities is referred to as the company's working capital; the difference between the working capital for two given reporting periods is called the change in working capital. changeInWorkingCapital = changeToAccountReceivables + changeToInventory + changeToLiabilities + changeToOperatingActivities.
    stock_based_compensation                    DOUBLE,    -- a kind of compensation given by companies to their employees in the form of equity shares besides the regular cash or salary and bonuses they receive.
    other_non_cash_items                        DOUBLE,    -- expenses listed on an income statement, such as capital depreciation, investment gains, or losses, that do not involve a cash payment. Examples of non-cash items include depreciation, amortization, deferred income tax, stock based compensation that is provided to employees.
    free_cash_flow                              DOUBLE     -- the money a company has left over after paying its operating expenses (OpEx) and capital expenditures (CapEx). totalCashFromOperatingActivities - capitalExpenditures = freeCashFlow.
) TIMESTAMP(filing_date) PARTITION BY YEAR WAL
DEDUP UPSERT KEYS(symbol_code, exchange_code, filing_date);

CREATE TABLE IF NOT EXISTS income_statement_quarterly (
    symbol_code                             SYMBOL,
    exchange_code                           SYMBOL,
    date                                    TIMESTAMP, -- the end of the reported period.
    filing_date                             TIMESTAMP, -- the filing date of the financial report.
    currency_symbol                         SYMBOL,    -- currency
    research_development                    DOUBLE,    -- R&D expenses.
    effect_of_accounting_charges            DOUBLE,    -- charges that include items such as depreciation, amortization, bad debt, and other expenses that are associated with the normal operations of a business.
    income_before_tax                       DOUBLE,    -- self-explanatory. incomeBeforeTax = operatingIncome - nonOperatingIncomeNetOther.
    minority_interest                       DOUBLE,    -- a minority interest refers to a stake in a company that is otherwise controlled by a parent company. On the income statement, minority interest is recorded as a share of the minority shareholders' profit.
    net_income                              DOUBLE,    -- self-explanatory. netIncome = incomeBeforeTax - incomeTaxExpense - minorityInterest OR netIncome = operatingIncome - interestExpense - incomeTaxExpense OR netIncome = operatingIncome - incomeTaxExpense, depending on how it was reported.
    selling_general_administrative          DOUBLE,    -- selling, general, and administrative expenses (SG&A) - all general and administrative expenses (G&A) as well as the direct and indirect selling expenses of a business.
    selling_and_marketing_expenses          DOUBLE,    -- may be a component of sellingGeneralAdministrative, not reported in that case; or a field of its own, reported separately.
    gross_profit                            DOUBLE,    -- self-explanatory: the gross profit. grossProfit = totalRevenue - costOfRevenue.
    reconciled_depreciation                 DOUBLE,    -- same as depreciationAndAmortization for US tickers.
    ebit                                    DOUBLE,    -- ebit = totalRevenue - costOfRevenue - totalOperatingExpenses. In most cases this should be the same as operatingIncome, if the companies report it as such. In other cases, it may be operatingIncome + netInterestIncome + totalOtherIncomeExpenseNet.
    ebitda                                  DOUBLE,    -- earnings before interest, taxes, depreciation, amortization; ebit + depreciationAndAmortization.
    depreciation_and_amortization           DOUBLE,    -- depreciation and amortization, same as reconciledDepreciation for US tickers.
    non_operating_income_net_other          DOUBLE,    -- income (loss) not attributable to operating income.
    operating_income                        DOUBLE,    -- self-explanatory. operatingIncome = totalRevenue - totalOperatingExpenses OR operatingIncome = totalRevenue - totalOperatingExpenses - costOfRevenue, depending on how it was reported. In most cases this should be the same as ebit.
    other_operating_expenses                DOUBLE,    -- the total expenses / cost and expenses field.
    interest_expense                        DOUBLE,    -- the cost incurred by an entity for borrowed funds.
    tax_provision                           DOUBLE,    -- the reporting period's total income tax expense.
    interest_income                         DOUBLE,    -- income incurred from interest-related operations, a banking sphere field.
    net_interest_income                     DOUBLE,    -- net interest income incurred from interest-related operations, a banking sphere field.
    extraordinary_items                     DOUBLE,    -- obsolete: International Financial Reporting Standards (IFRS) does not recognize the concept of an extraordinary item, which has led to the practice of classifying extraordinary items as separate from nonrecurring items to become obsolete.
    non_recurring                           DOUBLE,    -- income received which is not anticipated to continue in future months.
    other_items                             DOUBLE,    -- other possible income.
    income_tax_expense                      DOUBLE,    -- the expenses incurred by tax paying.
    total_revenue                           DOUBLE,    -- self-explanatory, a reported figure. totalRevenue = operatingIncome + totalOperatingExpenses. For banks, totalRevenue can be calculated as interestIncome + totalOtherIncomeExpenseNet.
    total_operating_expenses                DOUBLE,    -- companies apply their own logic to calculating expenses. It may be: researchDevelopment + sellingGeneralAdministrative + sellingAndMarketingExpenses + depreciationAndAmortization (some tickers include D&A, some do not); it may be different. Check the companies' original report to see how exactly they calculate their expenses.
    cost_of_revenue                         DOUBLE,    -- otherwise known as "cost of goods sold", a reported figure. costOfRevenue = totalOperatingExpenses - sellingGeneralAdministrative.
    total_other_income_expense_net          DOUBLE,    -- nonOperatingIncomeNetOther + netInterestIncome.
    discontinued_operations                 DOUBLE,    -- net income (loss) from discontinued operations, not a subcomponent of extraordinaryItems or nonRecurring.
    net_income_from_continuing_ops          DOUBLE,
    net_income_applicable_to_common_shares  DOUBLE     -- the portion of net income that should be used in calculations where only the common shares are applicable, if a company has more than one class of shares.
    -- preferred_stock_and_other_adjustments   REAL    -- the aggregate value of preferred stock dividends and other adjustments necessary to derive net income apportioned to common stockholders.
) TIMESTAMP(filing_date) PARTITION BY YEAR WAL
DEDUP UPSERT KEYS(symbol_code, exchange_code, filing_date);

CREATE TABLE IF NOT EXISTS income_statement_annually (
    symbol_code                             SYMBOL,
    exchange_code                           SYMBOL,
    date                                    TIMESTAMP, -- the end of the reported period.
    filing_date                             TIMESTAMP, -- the filing date of the financial report.
    currency_symbol                         SYMBOL,    -- currency
    research_development                    DOUBLE,    -- R&D expenses.
    effect_of_accounting_charges            DOUBLE,    -- charges that include items such as depreciation, amortization, bad debt, and other expenses that are associated with the normal operations of a business.
    income_before_tax                       DOUBLE,    -- self-explanatory. incomeBeforeTax = operatingIncome - nonOperatingIncomeNetOther.
    minority_interest                       DOUBLE,    -- a minority interest refers to a stake in a company that is otherwise controlled by a parent company. On the income statement, minority interest is recorded as a share of the minority shareholders' profit.
    net_income                              DOUBLE,    -- self-explanatory. netIncome = incomeBeforeTax - incomeTaxExpense - minorityInterest OR netIncome = operatingIncome - interestExpense - incomeTaxExpense OR netIncome = operatingIncome - incomeTaxExpense, depending on how it was reported.
    selling_general_administrative          DOUBLE,    -- selling, general, and administrative expenses (SG&A) - all general and administrative expenses (G&A) as well as the direct and indirect selling expenses of a business.
    selling_and_marketing_expenses          DOUBLE,    -- may be a component of sellingGeneralAdministrative, not reported in that case; or a field of its own, reported separately.
    gross_profit                            DOUBLE,    -- self-explanatory: the gross profit. grossProfit = totalRevenue - costOfRevenue.
    reconciled_depreciation                 DOUBLE,    -- same as depreciationAndAmortization for US tickers.
    ebit                                    DOUBLE,    -- ebit = totalRevenue - costOfRevenue - totalOperatingExpenses. In most cases this should be the same as operatingIncome, if the companies report it as such. In other cases, it may be operatingIncome + netInterestIncome + totalOtherIncomeExpenseNet.
    ebitda                                  DOUBLE,    -- earnings before interest, taxes, depreciation, amortization; ebit + depreciationAndAmortization.
    depreciation_and_amortization           DOUBLE,    -- depreciation and amortization, same as reconciledDepreciation for US tickers.
    non_operating_income_net_other          DOUBLE,    -- income (loss) not attributable to operating income.
    operating_income                        DOUBLE,    -- self-explanatory. operatingIncome = totalRevenue - totalOperatingExpenses OR operatingIncome = totalRevenue - totalOperatingExpenses - costOfRevenue, depending on how it was reported. In most cases this should be the same as ebit.
    other_operating_expenses                DOUBLE,    -- the total expenses / cost and expenses field.
    interest_expense                        DOUBLE,    -- the cost incurred by an entity for borrowed funds.
    tax_provision                           DOUBLE,    -- the reporting period's total income tax expense.
    interest_income                         DOUBLE,    -- income incurred from interest-related operations, a banking sphere field.
    net_interest_income                     DOUBLE,    -- net interest income incurred from interest-related operations, a banking sphere field.
    extraordinary_items                     DOUBLE,    -- obsolete: International Financial Reporting Standards (IFRS) does not recognize the concept of an extraordinary item, which has led to the practice of classifying extraordinary items as separate from nonrecurring items to become obsolete.
    non_recurring                           DOUBLE,    -- income received which is not anticipated to continue in future months.
    other_items                             DOUBLE,    -- other possible income.
    income_tax_expense                      DOUBLE,    -- the expenses incurred by tax paying.
    total_revenue                           DOUBLE,    -- self-explanatory, a reported figure. totalRevenue = operatingIncome + totalOperatingExpenses. For banks, totalRevenue can be calculated as interestIncome + totalOtherIncomeExpenseNet.
    total_operating_expenses                DOUBLE,    -- companies apply their own logic to calculating expenses. It may be: researchDevelopment + sellingGeneralAdministrative + sellingAndMarketingExpenses + depreciationAndAmortization (some tickers include D&A, some do not); it may be different. Check the companies' original report to see how exactly they calculate their expenses.
    cost_of_revenue                         DOUBLE,    -- otherwise known as "cost of goods sold", a reported figure. costOfRevenue = totalOperatingExpenses - sellingGeneralAdministrative.
    total_other_income_expense_net          DOUBLE,    -- nonOperatingIncomeNetOther + netInterestIncome.
    discontinued_operations                 DOUBLE,    -- net income (loss) from discontinued operations, not a subcomponent of extraordinaryItems or nonRecurring.
    net_income_from_continuing_ops          DOUBLE,
    net_income_applicable_to_common_shares  DOUBLE     -- the portion of net income that should be used in calculations where only the common shares are applicable, if a company has more than one class of shares.
    -- preferred_stock_and_other_adjustments   REAL    -- the aggregate value of preferred stock dividends and other adjustments necessary to derive net income apportioned to common stockholders.
) TIMESTAMP(filing_date) PARTITION BY YEAR WAL
DEDUP UPSERT KEYS(symbol_code, exchange_code, filing_date);