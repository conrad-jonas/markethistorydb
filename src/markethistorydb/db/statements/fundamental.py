#!/usr/bin/env python12.9

import markethistorydb.db.tables as tables


class StatementsFundamental:
    SELECT_ALL_FROM_EARNINGS_QUARTERLY = (
        f"SELECT {', '.join(tables.EarningsQuarterly.ALL_COLUMNS)} FROM {tables.EarningsQuarterly.NAME} "
        f"WHERE {tables.EarningsQuarterly.Columns.SYMBOL_CODE}=%s")
    SELECT_ALL_FROM_EARNINGS_ANNUALLY = (
        f"SELECT {', '.join(tables.EarningsAnnually.ALL_COLUMNS)} FROM {tables.EarningsAnnually.NAME} "
        f"WHERE {tables.EarningsAnnually.Columns.SYMBOL_CODE}=%s")
    SELECT_ALL_FROM_BALANCE_SHEET_QUARTERLY = (
        f"SELECT {', '.join(tables.BalanceSheetQuarterly.ALL_COLUMNS)} FROM {tables.BalanceSheetQuarterly.NAME} "
        f"WHERE {tables.BalanceSheetQuarterly.Columns.SYMBOL_CODE}=%s")
    SELECT_ALL_FROM_BALANCE_SHEET_ANNUALLY = (
        f"SELECT {', '.join(tables.BalanceSheetAnnually.ALL_COLUMNS)} FROM {tables.BalanceSheetAnnually.NAME} "
        f"WHERE {tables.BalanceSheetAnnually.Columns.SYMBOL_CODE}=%s")
    SELECT_ALL_FROM_CASH_FLOW_QUARTERLY = (
        f"SELECT {', '.join(tables.CashFlowQuarterly.ALL_COLUMNS)} FROM {tables.CashFlowQuarterly.NAME} "
        f"WHERE {tables.CashFlowQuarterly.Columns.SYMBOL_CODE}=%s")
    SELECT_ALL_FROM_CASH_FLOW_ANNUALLY = (
        f"SELECT {', '.join(tables.CashFlowAnnually.ALL_COLUMNS)} FROM {tables.CashFlowAnnually.NAME} "
        f"WHERE {tables.CashFlowAnnually.Columns.SYMBOL_CODE}=%s")
    SELECT_ALL_FROM_INCOME_STATEMENT_QUARTERLY = (
        f"SELECT {', '.join(tables.IncomeStatementQuarterly.ALL_COLUMNS)} "
        f"FROM {tables.IncomeStatementQuarterly.NAME} WHERE {tables.IncomeStatementQuarterly.Columns.SYMBOL_CODE}=%s")
    SELECT_ALL_FROM_INCOME_STATEMENT_ANNUALLY = (
        f"SELECT {', '.join(tables.IncomeStatementAnnually.ALL_COLUMNS)} "
        f"FROM {tables.IncomeStatementAnnually.NAME} WHERE {tables.IncomeStatementAnnually.Columns.SYMBOL_CODE}=%s")

    # Each element is a separate statement (QuestDB executes one statement per query); {table_name_copy}
    # is a distinct placeholder from {table_name} so sql.Identifier() quoting isn't glued to literal "_copy" text
    DROP_SYMBOL_FROM_TABLE: tuple[str, ...] = (
        "CREATE TABLE {table_name_copy} AS (SELECT * FROM {table_name} WHERE NOT (symbol_code = %s AND exchange_code = %s)) "
        "TIMESTAMP({timestamp_column}) PARTITION BY YEAR WAL DEDUP UPSERT KEYS({unique_key_columns});",
        "DROP TABLE {table_name};",
        "RENAME TABLE {table_name_copy} TO {table_name};")
