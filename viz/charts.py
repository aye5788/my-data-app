"""Visualization studio (generic charts + price charts)."""
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from transform.normalize import time_axis
from analytics.stats import _pick_price_column

OHLC = ["open", "high", "low", "close"]


def _time_values(df):
    """Return the x-axis (time) values and a label, from index or a column."""
    kind, name = time_axis(df)
    if kind == "index":
        return df.index, df.index.name or "date"
    if kind == "column":
        return df[name], name
    return None, None


def _render_price_chart(df, chart_type):
    x, x_label = _time_values(df)
    if x is None:
        st.info("No datetime axis found — a candlestick/OHLC chart needs a date column or index.")
        return
    if not all(c in df.columns for c in OHLC):
        st.info("Need canonical `open/high/low/close` columns — run the normalizer to map them.")
        return

    has_volume = "volume" in df.columns
    log_scale = st.checkbox("Log price scale", value=False, key="price_log_scale")

    rows = 2 if has_volume else 1
    fig = make_subplots(
        rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.03,
        row_heights=[0.75, 0.25] if has_volume else [1.0],
    )

    if chart_type == "Candlestick":
        price_trace = go.Candlestick(
            x=x, open=df["open"], high=df["high"], low=df["low"], close=df["close"], name="Price",
        )
    else:  # OHLC bars
        price_trace = go.Ohlc(
            x=x, open=df["open"], high=df["high"], low=df["low"], close=df["close"], name="Price",
        )
    fig.add_trace(price_trace, row=1, col=1)

    # Overlay any price-scale indicator columns (sma_/ema_/bb_) as lines.
    overlay_cols = [c for c in df.columns if str(c).startswith(("sma_", "ema_", "bb_"))]
    for c in overlay_cols:
        fig.add_trace(go.Scatter(x=x, y=df[c], name=c, mode="lines"), row=1, col=1)

    if has_volume:
        fig.add_trace(go.Bar(x=x, y=df["volume"], name="Volume", marker_color="#888"), row=2, col=1)
        fig.update_yaxes(title_text="Volume", row=2, col=1)

    fig.update_yaxes(title_text="Price", type="log" if log_scale else "linear", row=1, col=1)
    fig.update_xaxes(title_text=x_label, rangeslider_visible=False, row=rows, col=1)
    fig.update_layout(height=600, title=f"Price ({chart_type})", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)


def _xy_defaults(df):
    """Smart default (x, y) for a generic chart: time on X, a price on Y."""
    cols = df.columns.tolist()
    kind, name = time_axis(df)
    x_options = (["(index)"] if kind == "index" else []) + cols
    if kind == "index":
        default_x = "(index)"
    elif kind == "column" and name in cols:
        default_x = name
    else:
        default_x = cols[0] if cols else None
    numeric = [c for c in df.select_dtypes("number").columns if c != default_x]
    default_y = _pick_price_column(df, numeric) or (
        next((c for c in cols if c != default_x), default_x)
    )
    return x_options, default_x, default_y


def _render_xy_chart(df, chart_type):
    cols = df.columns.tolist()
    if not cols:
        st.info("No columns to plot.")
        return

    x_options, default_x, default_y = _xy_defaults(df)
    with st.expander("Chart options"):
        x_axis = st.selectbox(
            "X-Axis", x_options,
            index=x_options.index(default_x) if default_x in x_options else 0,
            key="primary_x",
        )
        y_axis = st.selectbox(
            "Y-Axis", cols,
            index=cols.index(default_y) if default_y in cols else 0,
            key="primary_y",
        )

    x_data = df.index if x_axis == "(index)" else df[x_axis]
    x_label = "date" if x_axis == "(index)" else x_axis
    try:
        builder = {"Line": px.line, "Bar": px.bar, "Scatter": px.scatter}[chart_type]
        fig = builder(df, x=x_data, y=y_axis, title=f"{y_axis} vs {x_label}")
        fig.update_xaxes(title_text=x_label)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as chart_e:
        st.error(
            f"Error creating chart: {chart_e}. "
            "Open **Chart options** and check your axis selections and data types."
        )


def _default_chart_type(df):
    """Candlestick when this looks like OHLC price data on a time axis, else Line."""
    kind, _ = time_axis(df)
    if kind is not None and all(c in df.columns for c in OHLC):
        return "Candlestick"
    return "Line"


def render_visualization(df):
    """Render the primary chart for ``df`` (auto-defaulted, shown first)."""
    if df is None or (not df.columns.tolist() and not len(df.index)):
        st.info("Load data to see a chart.")
        return

    types = ["Line", "Bar", "Scatter", "Candlestick", "OHLC"]
    default = _default_chart_type(df)
    chart_type = st.selectbox(
        "Chart type", options=types, index=types.index(default), key="primary_chart_type"
    )

    if chart_type in ("Candlestick", "OHLC"):
        _render_price_chart(df, chart_type)
    else:
        _render_xy_chart(df, chart_type)
