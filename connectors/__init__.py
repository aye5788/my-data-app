"""Connector registry and the data-source selector.

Each connector module exposes ``NAME`` and a ``render()`` function that draws
its own widgets and returns ``(df_or_None, asset_name)``. To add a new source,
write a module with that contract and register it below.
"""
import streamlit as st

from . import upload, gcs

# Display name -> connector module. Order here drives the selectbox order.
REGISTRY = {
    upload.NAME: upload,
    gcs.NAME: gcs,
}


def render_source_selector():
    """Render the source picker + the active connector's UI.

    Returns ``(df_or_None, source_name, asset_name)``.
    """
    st.sidebar.header("Select Data Source")

    source_name = st.sidebar.selectbox(
        "Choose your data source",
        list(REGISTRY.keys()),
    )

    connector = REGISTRY.get(source_name)
    if connector is None:
        return None, source_name, ""

    df, asset = connector.render()
    return df, source_name, asset
