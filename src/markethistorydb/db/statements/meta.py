#!/usr/bin/env python12.9


class StatementsMeta:
    SELECT_SCHEMA = "SELECT * FROM INFORMATION_SCHEMA.columns WHERE table_name = %s AND column_name = %s"

    # Which of a table and its copy exist; a copy is left over when deleting a symbol was
    # interrupted before the copy took the table's name
    SELECT_TABLE_AND_COPY = "SELECT table_name FROM tables() WHERE table_name IN (%s, %s)"
    DROP_COPY = "DROP TABLE {table_name_copy};"
    RENAME_COPY_TO_TABLE = "RENAME TABLE {table_name_copy} TO {table_name};"
