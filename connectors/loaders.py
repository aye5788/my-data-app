"""Shared, source-agnostic loading helpers used by individual connectors."""
import os

import pandas as pd
import streamlit as st


@st.cache_data
def load_data_file(file_object, file_name):
    """Load a file-like object into a DataFrame based on its extension.

    Returns the DataFrame, or ``None`` for an unsupported extension. Errors
    during parsing are surfaced as ``None`` so the caller can show a message.
    """
    _, file_extension = os.path.splitext(file_name)
    file_extension = file_extension.lower()

    try:
        if file_extension == ".csv":
            df = pd.read_csv(file_object)
            # When a CSV header has fewer names than the rows have fields,
            # pandas promotes the leading column(s) into the (Multi)Index —
            # common in price exports where the date/ticker column is unlabeled.
            # Pull them back into real columns so the rest of the app sees them.
            if not isinstance(df.index, pd.RangeIndex):
                df = df.reset_index()
            return df
        elif file_extension == ".xlsx":
            return pd.read_excel(file_object)
        elif file_extension == ".json":
            return pd.read_json(file_object)
        elif file_extension == ".parquet":
            return pd.read_parquet(file_object)
        else:
            return None
    except Exception as e:
        print(f"Error loading file of type {file_extension}: {e}")
        return None
