"""Personal Data Analysis Application — navigation shell.

Layout: the sidebar holds the *inputs* (data source, prep tools, filters); the
main canvas leads with the **chart**, then the analysis (metrics, table, export,
comparison). The active dataset flows through ``state`` so every stage operates
on the same in-memory DataFrame.
"""
import pandas as pd
import streamlit as st

import state
from connectors import render_source_selector
from transform.typing import render_type_editor
from transform.normalize import render_normalizer, time_axis
from transform.filters import render_filters, render_table, render_export
from quality.profiling import render_health_check
from analytics.stats import render_returns_panel
from analytics.indicators import render_indicators
from analytics.compare import render_multi_symbol
from viz.charts import render_visualization
from ai.deepseek import render_ai_workspace

st.set_page_config(layout="wide")
st.title("Personal Data Analysis Application")


def _summary(df, asset):
    """A one-line caption: name · size · date range (when there's a time axis)."""
    bits = [asset or "Dataset", f"{df.shape[0]:,} rows × {df.shape[1]} cols"]
    kind, name = time_axis(df)
    try:
        s = df.index.to_series() if kind == "index" else (
            pd.to_datetime(df[name], errors="coerce") if kind == "column" else None
        )
        if s is not None and s.notna().any():
            bits.append(f"{s.min():%Y-%m-%d} → {s.max():%Y-%m-%d}")
    except Exception:
        pass
    return "  ·  ".join(bits)


# --- Connect: pick a source and load the active dataset (sidebar). ---
df, source_name, asset_name = render_source_selector()
if df is not None:
    state.set_dataset(df, source=source_name, asset=asset_name)

data_studio_tab, ai_workspace_tab = st.tabs(["📊 Data Studio", "🤖 AI Workspace"])

with data_studio_tab:
    if df is not None:
        # --- Inputs live in the sidebar; the canvas stays for analysis. ---
        with st.sidebar:
            st.markdown("---")
            st.header("Prepare Data")
            df = render_type_editor(df)        # may recast column dtypes
            df = render_normalizer(df)         # opt-in time-series/price standardization
            df = render_indicators(df)         # opt-in technical indicators (full series)
        filtered_df = render_filters(df)        # draws its own sidebar "Filter Workspace"

        # --- Canvas: chart first (hero), then analysis organized into tabs. ---
        st.caption(_summary(filtered_df, asset_name))
        render_visualization(filtered_df)       # the hero chart, auto-defaulted

        tab_table, tab_returns, tab_health, tab_compare = st.tabs(
            ["📋 Table", "📈 Returns & Risk", "🩺 Health", "🔀 Compare"]
        )
        with tab_table:
            edited = render_table(filtered_df)   # editable view
            render_export(edited)                # download button
        with tab_returns:
            render_returns_panel(filtered_df)
        with tab_health:
            render_health_check(filtered_df)
        with tab_compare:
            render_multi_symbol(df, asset_name)  # compares across symbols (full series)
    else:
        st.info("Pick a data source in the sidebar to begin.")

with ai_workspace_tab:
    render_ai_workspace(df)
