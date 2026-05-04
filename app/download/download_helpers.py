#!/usr/bin/env python12.9

"""Helper functions for download module"""

import pandas as pd


def convert_df_column_names_from_camel_to_snake_case(df: pd.DataFrame) -> pd.DataFrame:
    """Converts column names of dataframe from camel case to snake case"""
    df.columns = (df.columns.str.replace('(?<=[a-z])(?=[A-Z])', '_', regex=True).str.lower())
    return df
