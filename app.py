"""Personal Data Analysis Application — navigation shell.

Wires together the connect → transform → quality → visualize → AI stages.
Each stage lives in its own module; the active dataset flows through
``state`` so every stage operates on the same in-memory DataFrame.
"""
import streamlit as st

import state
from connectors import render_source_selector
from transform.typing import render_type_editor
from transform.filters import render_filters, render_export
from quality.profiling import render_health_check
from viz.charts import render_visualization
from ai.deepseek import render_ai_workspace

st.set_page_config(layout="wide")
st.title("Personal Data Analysis Application")

# --- Connect: pick a source and load the active dataset (sidebar + GCS explorer). ---
df, source_name, asset_name = render_source_selector()
if df is not None:
    state.set_dataset(df, source=source_name, asset=asset_name)

data_studio_tab, ai_workspace_tab = st.tabs(["📊 Data Studio", "🤖 AI Workspace"])

with data_studio_tab:
    if df is not None:
        df = render_type_editor(df)            # may recast column dtypes
        filtered_df = render_filters(df)        # sidebar filters -> filtered view

        st.subheader("Raw Data Table (Filtered)")
        st.dataframe(filtered_df)

        render_export(filtered_df)
        render_health_check(filtered_df)
        render_visualization(filtered_df)
    else:
        st.info("Please upload a file or specify a GCS path to begin analysis.")

with ai_workspace_tab:
    render_ai_workspace(df)
