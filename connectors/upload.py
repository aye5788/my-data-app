"""Local file-upload connector."""
import streamlit as st

from .loaders import load_data_file

NAME = "Local Upload"


def render():
    """Draw the upload widget and return a (df, asset_name) tuple.

    Returns ``(None, "")`` when nothing has been uploaded yet.
    """
    uploaded_file = st.sidebar.file_uploader(
        "Upload a file",
        type=["csv", "xlsx", "json", "parquet"],
    )

    if uploaded_file is None:
        return None, ""

    try:
        df = load_data_file(uploaded_file, uploaded_file.name)
        if df is None:
            st.error(
                "Unsupported file type or error loading file. "
                "Please upload a CSV, XLSX, JSON, or Parquet file."
            )
        return df, uploaded_file.name
    except Exception as e:
        st.error(f"Error loading or processing file: {e}")
        return None, ""
