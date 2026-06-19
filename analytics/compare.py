"""Multi-symbol comparison.

Accumulate price series from *any* source (upload, FRED, custom REST, SQL —
not tied to one API) into a session-held store, then compare them on one
chart rebased to a common base of 100, plus a correlation heatmap of their
returns. Each series is added from the currently active dataset, so the
workflow is: load symbol A -> add, load symbol B -> add, compare.
"""
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from analytics.stats import _pick_price_column
from transform.normalize import clean_numeric, time_axis

# session_state key: dict[label] -> date-indexed price Series
_STORE_KEY = "compare_store"


def _series_from_df(df, price_col):
    """Extract a sorted, date-indexed price Series from ``df``.

    Uses the frame's time axis (DatetimeIndex or a detected datetime column).
    Returns ``None`` if no usable datetime axis is present.
    """
    kind, name = time_axis(df)
    if kind == "index":
        idx = pd.to_datetime(df.index, errors="coerce")
    elif kind == "column":
        idx = pd.to_datetime(df[name], errors="coerce")
    else:
        return None
    s = pd.Series(clean_numeric(df[price_col]).values, index=idx)
    s = s[~s.index.isna()].dropna().sort_index()
    # collapse any duplicate timestamps (keep last)
    s = s[~s.index.duplicated(keep="last")]
    return s if not s.empty else None


def _rebased(frame):
    """Rebase each column to 100 at its own first valid observation."""
    def scale(col):
        valid = col.dropna()
        return col / valid.iloc[0] * 100 if not valid.empty else col
    return frame.apply(scale)


def render_multi_symbol(df, asset_name=""):
    """Render the opt-in multi-symbol comparison workspace."""
    st.markdown("---")
    with st.expander("Multi-Symbol Comparison"):
        store = st.session_state.setdefault(_STORE_KEY, {})

        numeric_cols = df.select_dtypes("number").columns.tolist()
        if not numeric_cols:
            st.info("No numeric column found in the active dataset to add.")
        else:
            kind, _ = time_axis(df)
            if kind is None:
                st.caption(
                    "No datetime axis detected — run the normalizer (set a date "
                    "column / index) so this series can align by date."
                )
            default_price = _pick_price_column(df, numeric_cols)
            c1, c2, c3 = st.columns([2, 2, 1])
            price_col = c1.selectbox(
                "Price column",
                options=numeric_cols,
                index=numeric_cols.index(default_price) if default_price in numeric_cols else 0,
                key="cmp_price_col",
            )
            label = c2.text_input(
                "Label", value=asset_name or price_col, key="cmp_label"
            )
            c3.markdown("<div style='height:1.8em'></div>", unsafe_allow_html=True)
            if c3.button("Add ↗", key="cmp_add", use_container_width=True):
                s = _series_from_df(df, price_col)
                if s is None:
                    st.warning("Couldn't add — no datetime axis or no valid numbers.")
                else:
                    store[(label or price_col)] = s
                    st.success(f"Added '{label or price_col}' ({len(s)} points).")

        if not store:
            st.caption("No series added yet. Load a symbol, then click **Add ↗**.")
            st.markdown("---")
            return

        shown = st.multiselect(
            "Series to compare",
            options=list(store),
            default=list(store),
            key="cmp_shown",
        )
        cols = st.columns(2)
        if cols[0].button("Remove unselected", key="cmp_prune"):
            for lbl in list(store):
                if lbl not in shown:
                    store.pop(lbl, None)
            st.rerun()
        if cols[1].button("Clear all", key="cmp_clear"):
            store.clear()
            st.rerun()

        selected = [l for l in shown if l in store]
        if not selected:
            st.markdown("---")
            return

        frame = pd.concat({l: store[l] for l in selected}, axis=1).sort_index()

        st.markdown("**Rebased performance** (each starts at 100)")
        rebased = _rebased(frame)
        fig = px.line(rebased, labels={"value": "Index (=100 at start)", "index": "date",
                                       "variable": "symbol"})
        fig.update_layout(height=450, legend_title_text="symbol")
        st.plotly_chart(fig, use_container_width=True)

        if len(selected) >= 2:
            st.markdown("**Return correlation** (aligned daily returns)")
            corr = frame.pct_change().corr()
            heat = px.imshow(
                corr, text_auto=".2f", zmin=-1, zmax=1, aspect="auto",
                color_continuous_scale="RdBu_r",
            )
            heat.update_layout(height=110 + 60 * len(selected))
            st.plotly_chart(heat, use_container_width=True)

        st.markdown("---")
