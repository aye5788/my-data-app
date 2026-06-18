"""Shared application state.

The whole platform operates on a single "active dataset" that lives in
``st.session_state`` so every stage (connect, quality, transform, viz, AI)
reads and writes the same in-memory DataFrame instead of recomputing it.
"""
from dataclasses import dataclass
from typing import Optional

import pandas as pd
import streamlit as st


@dataclass
class Dataset:
    df: pd.DataFrame
    source: str = ""   # connector name, e.g. "Local Upload"
    asset: str = ""     # file name / table name the data came from


def set_dataset(df: pd.DataFrame, source: str = "", asset: str = "") -> None:
    st.session_state["dataset"] = Dataset(df=df, source=source, asset=asset)


def get_dataset() -> Optional[Dataset]:
    return st.session_state.get("dataset")


def clear_dataset() -> None:
    st.session_state.pop("dataset", None)
