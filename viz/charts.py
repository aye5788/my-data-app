"""Visualization studio (generic charts + price charts)."""
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from transform.normalize import time_axis

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

    if has_volume:
        fig.add_trace(go.Bar(x=x, y=df["volume"], name="Volume", marker_color="#888"), row=2, col=1)
        fig.update_yaxes(title_text="Volume", row=2, col=1)

    fig.update_yaxes(title_text="Price", type="log" if log_scale else "linear", row=1, col=1)
    fig.update_xaxes(title_text=x_label, rangeslider_visible=False, row=rows, col=1)
    fig.update_layout(height=600, title=f"Price ({chart_type})", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)


def _render_xy_chart(df, chart_type):
    all_columns = df.columns.tolist()
    col_x, col_y = st.columns(2)
    with col_x:
        x_axis = st.selectbox("Select X-Axis", options=all_columns, index=0)
    with col_y:
        y_axis = st.selectbox(
            "Select Y-Axis", options=all_columns, index=1 if len(all_columns) > 1 else 0
        )
    if not (x_axis and y_axis):
        st.info("Please select both X and Y axes to generate a chart.")
        return
    try:
        if chart_type == "Line":
            fig = px.line(df, x=x_axis, y=y_axis, title=f"{y_axis} vs {x_axis} (Line Chart)")
        elif chart_type == "Bar":
            fig = px.bar(df, x=x_axis, y=y_axis, title=f"{y_axis} vs {x_axis} (Bar Chart)")
        elif chart_type == "Scatter":
            fig = px.scatter(df, x=x_axis, y=y_axis, title=f"{y_axis} vs {x_axis} (Scatter Plot)")
        st.plotly_chart(fig, use_container_width=True)
    except Exception as chart_e:
        st.error(
            f"Error creating chart: {chart_e}. "
            "Please check your axis selections and data types."
        )


def render_visualization(df):
    """Render the chart builder for ``df``."""
    st.markdown("---")
    st.subheader("Visualization Studio")

    if not df.columns.tolist() and not len(df.index):
        st.info("Upload data to see visualization options.")
        return

    chart_type = st.selectbox(
        "Select Chart Type",
        options=["Line", "Bar", "Scatter", "Candlestick", "OHLC"],
        index=0,
    )

    if chart_type in ("Candlestick", "OHLC"):
        _render_price_chart(df, chart_type)
    else:
        _render_xy_chart(df, chart_type)
