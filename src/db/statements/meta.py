#!/usr/bin/env python12.9


class StatementsMeta:
    SELECT_SCHEMA = "SELECT * FROM INFORMATION_SCHEMA.columns WHERE table_name = %s AND column_name = %s"