"""Visualization studio (generic charts + price charts)."""
import math

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from transform.normalize import time_axis
from analytics.stats import _pick_price_column
from viz.tv_charts import build_price_payload

try:
    from streamlit_lightweight_charts import renderLightweightCharts
    _HAS_TV = True
except Exception:  # component missing -> Plotly fallback
    _HAS_TV = False

# Hide Plotly's floating modebar (camera/zoom/pan toolbar) everywhere.
PLOTLY_CONFIG = {"displayModeBar": False}

OHLC = ["open", "high", "low", "close"]

# Render caps that keep the browser responsive on large files. Plotly draws
# every point; past these counts it freezes, so we aggregate/downsample first.
MAX_CANDLES = 2000      # candlesticks are bucket-aggregated to this many bars
MAX_LINE_POINTS = 8000  # line/scatter are strided to this many points (+ WebGL)


def _time_values(df):
    """Return the x-axis (time) values and a label, from index or a column."""
    kind, name = time_axis(df)
    if kind == "index":
        return df.index, df.index.name or "date"
    if kind == "column":
        return df[name], name
    return None, None


def _sort_by_time(df):
    """Return ``df`` ordered oldest→newest by its time axis (charts expect this).

    Many price exports are newest-first; an unsorted x-axis renders as broken
    line/candle segments. Sorting a copy leaves the source table untouched.
    """
    kind, name = time_axis(df)
    if kind == "index":
        return df.sort_index()
    if kind == "column":
        key = pd.to_datetime(df[name], errors="coerce")
        return df.assign(_sort_key=key).sort_values("_sort_key").drop(columns="_sort_key")
    return df


def _aggregate_candles(df, x, max_bars):
    """Bucket consecutive rows into ``<= max_bars`` groups, aggregating OHLCV
    correctly (open=first, high=max, low=min, close=last, volume=sum). Returns
    ``(x_values, frame, downsampled?)``. Keeps real candles at any file size.
    """
    n = len(df)
    work = df.copy()
    work["__x"] = list(x)
    if n <= max_bars:
        return work["__x"], work, False

    groups = np.arange(n) // math.ceil(n / max_bars)
    agg = {"__x": "first"}
    for c in df.columns:
        cl = str(c).lower()
        agg[c] = ("first" if cl == "open" else "max" if cl == "high"
                  else "min" if cl == "low" else "sum" if cl == "volume" else "last")
    out = work.groupby(groups, sort=True).agg(agg)
    return out["__x"], out, True


def _render_price_chart(df, chart_type, log_scale=None):
    x, x_label = _time_values(df)
    if x is None:
        st.info("No datetime axis found — a candlestick/OHLC chart needs a date column or index.")
        return
    if not all(c in df.columns for c in OHLC):
        st.info("Need canonical `open/high/low/close` columns — run the normalizer to map them.")
        return

    has_volume = "volume" in df.columns
    if log_scale is None:
        log_scale = st.checkbox("Log price scale", value=False, key="price_log_scale")

    # Keep the browser responsive: aggregate to a drawable number of bars.
    x, pdf, downsampled = _aggregate_candles(df, x, MAX_CANDLES)
    if downsampled:
        st.caption(f"Aggregated {len(df):,} rows into {len(pdf):,} bars for a responsive chart.")

    rows = 2 if has_volume else 1
    fig = make_subplots(
        rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.03,
        row_heights=[0.75, 0.25] if has_volume else [1.0],
    )

    if chart_type == "Candlestick":
        price_trace = go.Candlestick(
            x=x, open=pdf["open"], high=pdf["high"], low=pdf["low"], close=pdf["close"], name="Price",
        )
    else:  # OHLC bars
        price_trace = go.Ohlc(
            x=x, open=pdf["open"], high=pdf["high"], low=pdf["low"], close=pdf["close"], name="Price",
        )
    fig.add_trace(price_trace, row=1, col=1)

    # Overlay any price-scale indicator columns (sma_/ema_/bb_) as lines.
    overlay_cols = [c for c in pdf.columns if str(c).startswith(("sma_", "ema_", "bb_"))]
    for c in overlay_cols:
        fig.add_trace(go.Scatter(x=x, y=pdf[c], name=c, mode="lines"), row=1, col=1)

    if has_volume:
        fig.add_trace(go.Bar(x=x, y=pdf["volume"], name="Volume", marker_color="#888"), row=2, col=1)
        fig.update_yaxes(title_text="Volume", row=2, col=1)

    fig.update_yaxes(title_text="Price", type="log" if log_scale else "linear", row=1, col=1)
    fig.update_xaxes(title_text=x_label, rangeslider_visible=False, row=rows, col=1)
    fig.update_layout(height=600, title=f"Price ({chart_type})", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)


def _render_price_chart_tv(df, chart_type):
    """Render the price chart with TradingView Lightweight Charts; fall back to
    Plotly if the component is missing or errors."""
    x, _ = _time_values(df)
    if x is None or not all(c in df.columns for c in OHLC):
        _render_price_chart(df, chart_type)   # shows the right info message
        return
    if not _HAS_TV:
        _render_price_chart(df, chart_type)
        return

    log_scale = st.checkbox("Log price scale", value=False, key="price_log_scale")
    x_agg, pdf, downsampled = _aggregate_candles(df, x, MAX_CANDLES)
    if downsampled:
        st.caption(f"Aggregated {len(df):,} rows into {len(pdf):,} bars for a responsive chart.")
    try:
        payload = build_price_payload(pdf, x_agg, chart_type)
        if payload is None:
            raise ValueError("no OHLC payload")
        if log_scale:
            payload[0]["chart"]["rightPriceScale"]["mode"] = 1   # logarithmic
        renderLightweightCharts(payload, key="tv_price")
    except Exception as e:
        st.caption(f"Refined chart unavailable ({e}); showing fallback.")
        _render_price_chart(df, chart_type, log_scale=log_scale)


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

    # Downsample large series so the browser doesn't freeze rendering points.
    plot_df = df
    if len(df) > MAX_LINE_POINTS:
        step = math.ceil(len(df) / MAX_LINE_POINTS)
        plot_df = df.iloc[::step]
        st.caption(f"Showing {len(plot_df):,} of {len(df):,} points (every {step}th) for a responsive chart.")

    x_data = plot_df.index if x_axis == "(index)" else plot_df[x_axis]
    x_label = "date" if x_axis == "(index)" else x_axis
    title = f"{y_axis} vs {x_label}"
    try:
        # WebGL ("webgl") handles far more points than SVG for line/scatter.
        if chart_type == "Line":
            fig = px.line(plot_df, x=x_data, y=y_axis, title=title, render_mode="webgl")
        elif chart_type == "Scatter":
            fig = px.scatter(plot_df, x=x_data, y=y_axis, title=title, render_mode="webgl")
        else:  # Bar
            fig = px.bar(plot_df, x=x_data, y=y_axis, title=title)
        fig.update_xaxes(title_text=x_label)
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
    except Exception as chart_e:
        st.error(
            f"Error creating chart: {chart_e}. "
            "Open **Chart options** and check your axis selections and data types."
        )


# Above this many rows, candlesticks become an unreadable smear — default to a
# line instead (the user can still pick Candlestick explicitly).
CANDLE_DENSITY_LIMIT = 1500


def _default_chart_type(df):
    """Candlestick for daily-ish OHLC price data, Line for dense/intraday or
    non-price data."""
    kind, _ = time_axis(df)
    if kind is not None and all(c in df.columns for c in OHLC):
        return "Candlestick" if len(df) <= CANDLE_DENSITY_LIMIT else "Line"
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

    plot_df = _sort_by_time(df)   # charts read left→right oldest→newest
    if chart_type in ("Candlestick", "OHLC"):
        _render_price_chart_tv(plot_df, chart_type)
    else:
        _render_xy_chart(plot_df, chart_type)
