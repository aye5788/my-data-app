"""Shared, source-agnostic loading helpers used by individual connectors."""
import io
import os
from collections import Counter

import pandas as pd
import streamlit as st


def _csv_preamble_rows(text, sniff_lines=10):
    """Count leading lines that are *preamble* (fewer fields than the data).

    Many price exports (e.g. CryptoDataDownload) prepend an attribution line
    like ``https://www.CryptoDataDownload.com`` above the real header. Such a
    line has fewer delimiters than the header/data rows; skipping it lets the
    true header be read correctly.
    """
    lines = [ln for ln in text.splitlines() if ln.strip()][:sniff_lines]
    if len(lines) < 2:
        return 0
    counts = [ln.count(",") for ln in lines]
    dominant = Counter(counts).most_common(1)[0][0]
    skip = 0
    for c in counts:
        if c < dominant:
            skip += 1
        else:
            break
    return skip


def _read_csv(file_object):
    """Read a CSV, skipping any attribution/preamble lines, and keep all
    columns out of the index (pandas auto-promotes unlabeled leading columns
    to a (Multi)Index when the header is short)."""
    raw = file_object.read()
    text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
    skip = _csv_preamble_rows(text)
    df = pd.read_csv(io.StringIO(text), skiprows=skip)
    if not isinstance(df.index, pd.RangeIndex):
        df = df.reset_index()
    return df


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
            return _read_csv(file_object)
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
