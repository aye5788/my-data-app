"""TradingView Lightweight Charts renderer for the price/candlestick view.

This is a *static* renderer — it takes a finite history of OHLC bars and draws a
refined, interactive (pan / zoom / crosshair) chart. No live feed is involved.
Used for the Candlestick / OHLC chart types; generic Line/Bar/Scatter stay on
Plotly. Falls back to the Plotly price chart if the component is unavailable.
"""
import pandas as pd

OHLC = ["open", "high", "low", "close"]

# Distinct colors cycled across SMA/EMA/Bollinger overlay lines.
_OVERLAY_COLORS = ["#2962FF", "#FF6D00", "#AB47BC", "#26C6DA", "#9CCC65", "#EC407A"]

_UP = "#26a69a"
_DOWN = "#ef5350"


def _tv_time(values):
    """Datetime-like -> integer UTC seconds (lightweight-charts time format)."""
    t = pd.to_datetime(pd.Series(list(values)), errors="coerce")
    # tz-naive values are treated as UTC; consistent with themselves.
    return (t.astype("int64") // 10**9)


def _is_intraday(times_seconds):
    """True if any bar falls off a midnight boundary (needs a visible clock)."""
    return bool((pd.Series(times_seconds) % 86400 != 0).any())


def build_price_payload(df, x, chart_type, height=520):
    """Build the renderLightweightCharts config for one price chart.

    ``x`` is the time axis (aligned to ``df``). Returns a list with a single
    ``{"chart": ..., "series": [...]}`` dict, or ``None`` if there's no
    plottable OHLC data.
    """
    if not all(c in df.columns for c in OHLC):
        return None

    work = pd.DataFrame({
        "time": _tv_time(x).values,
        "open": pd.to_numeric(df["open"], errors="coerce").values,
        "high": pd.to_numeric(df["high"], errors="coerce").values,
        "low": pd.to_numeric(df["low"], errors="coerce").values,
        "close": pd.to_numeric(df["close"], errors="coerce").values,
    })
    overlay_cols = [c for c in df.columns if str(c).startswith(("sma_", "ema_", "bb_"))]
    for c in overlay_cols:
        work[c] = pd.to_numeric(df[c], errors="coerce").values
    has_volume = "volume" in df.columns
    if has_volume:
        work["volume"] = pd.to_numeric(df["volume"], errors="coerce").values

    # lightweight-charts requires ascending, unique time values.
    work = (
        work.dropna(subset=["time"] + OHLC)
        .drop_duplicates("time", keep="last")
        .sort_values("time")
    )
    if work.empty:
        return None

    times = work["time"].astype(int).tolist()
    series = []

    main_type = "Candlestick" if chart_type == "Candlestick" else "Bar"
    candles = [
        {"time": int(t), "open": float(o), "high": float(h), "low": float(l), "close": float(c)}
        for t, o, h, l, c in zip(times, work["open"], work["high"], work["low"], work["close"])
    ]
    candle_opts = {"upColor": _UP, "downColor": _DOWN}
    if main_type == "Candlestick":
        candle_opts.update({"borderVisible": False, "wickUpColor": _UP, "wickDownColor": _DOWN})
    series.append({"type": main_type, "data": candles, "options": candle_opts})

    for i, c in enumerate(overlay_cols):
        line = [
            {"time": int(t), "value": float(v)}
            for t, v in zip(times, work[c]) if pd.notna(v)
        ]
        if line:
            series.append({
                "type": "Line",
                "data": line,
                "options": {"color": _OVERLAY_COLORS[i % len(_OVERLAY_COLORS)],
                            "lineWidth": 1, "priceLineVisible": False,
                            "lastValueVisible": False, "title": str(c)},
            })

    if has_volume:
        vol = [
            {"time": int(t), "value": float(v),
             "color": _UP if cl >= op else _DOWN}
            for t, v, op, cl in zip(times, work["volume"], work["open"], work["close"])
            if pd.notna(v)
        ]
        if vol:
            series.append({
                "type": "Histogram",
                "data": vol,
                "options": {"priceFormat": {"type": "volume"}, "priceScaleId": "",
                            "color": "#9598a1"},
                "priceScale": {"scaleMargins": {"top": 0.8, "bottom": 0}},
            })

    chart = {
        "height": height,
        "layout": {"background": {"type": "solid", "color": "white"}, "textColor": "#131722"},
        "grid": {"vertLines": {"color": "#f0f3fa"}, "horzLines": {"color": "#f0f3fa"}},
        "rightPriceScale": {"borderColor": "#d6dcde"},
        "timeScale": {
            "borderColor": "#d6dcde",
            "timeVisible": _is_intraday(times),
            "secondsVisible": False,
        },
        "crosshair": {"mode": 1},
    }
    return [{"chart": chart, "series": series}]
