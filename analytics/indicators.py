"""Technical indicators as derived columns.

Pure functions (testable) plus an opt-in Streamlit step that appends the
chosen indicators to the DataFrame so they flow into the table, charts
(price-scale ones overlay automatically), and export.
"""
import numpy as np
import pandas as pd
import streamlit as st

from analytics.stats import PRICE_PREFERENCE

# Column-name prefixes the price chart overlays on the price axis.
OVERLAY_PREFIXES = ("sma_", "ema_", "bb_")


# ----- pure indicator math -------------------------------------------------

def sma(series, window):
    return series.rolling(window).mean()


def ema(series, span):
    return series.ewm(span=span, adjust=False).mean()


def returns(series):
    return series.pct_change()


def log_returns(series):
    return np.log(series / series.shift(1))


def cumulative_return(series):
    return series / series.iloc[0] - 1.0


def rolling_volatility(series, window, periods_per_year=252):
    return series.pct_change().rolling(window).std() * np.sqrt(periods_per_year)


def rsi(series, window=14):
    """Wilder's RSI (0–100)."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - 100 / (1 + rs)


def bollinger(series, window=20, k=2.0):
    """Return (mid, upper, lower) Bollinger Bands."""
    mid = series.rolling(window).mean()
    std = series.rolling(window).std()
    return mid, mid + k * std, mid - k * std


# ----- helpers -------------------------------------------------------------

def _pick_price_column(df, numeric_cols):
    lowered = {str(c).lower(): c for c in numeric_cols}
    for pref in PRICE_PREFERENCE:
        if pref in lowered:
            return lowered[pref]
    return numeric_cols[0] if numeric_cols else None


def _parse_windows(text, fallback):
    """Parse a comma-separated list of positive ints, e.g. '20, 50, 200'."""
    out = []
    for part in text.split(","):
        part = part.strip()
        if part.isdigit() and int(part) > 0:
            out.append(int(part))
    return out or fallback


# ----- UI ------------------------------------------------------------------

def render_indicators(df):
    """Render the opt-in indicators step; return ``df`` with chosen columns added."""
    st.markdown("---")
    with st.expander("Technical Indicators"):
        if not st.checkbox("Add technical indicators", value=False, key="ind_enabled"):
            st.markdown("---")
            return df

        numeric_cols = df.select_dtypes("number").columns.tolist()
        if not numeric_cols:
            st.info("No numeric price column found. Run the normalizer first.")
            st.markdown("---")
            return df

        default_price = _pick_price_column(df, numeric_cols)
        price_col = st.selectbox(
            "Price column",
            options=numeric_cols,
            index=numeric_cols.index(default_price) if default_price in numeric_cols else 0,
            key="ind_price_col",
        )
        price = df[price_col]

        chosen = st.multiselect(
            "Indicators",
            options=["SMA", "EMA", "Returns", "Log returns", "Cumulative return",
                     "Rolling volatility", "RSI", "Bollinger Bands"],
            default=["SMA"],
            key="ind_choice",
        )

        out = df.copy()

        if "SMA" in chosen:
            for w in _parse_windows(st.text_input("SMA windows", "20, 50", key="ind_sma"), [20, 50]):
                out[f"sma_{w}"] = sma(price, w)
        if "EMA" in chosen:
            for w in _parse_windows(st.text_input("EMA spans", "12, 26", key="ind_ema"), [12, 26]):
                out[f"ema_{w}"] = ema(price, w)
        if "Returns" in chosen:
            out["ret"] = returns(price)
        if "Log returns" in chosen:
            out["logret"] = log_returns(price)
        if "Cumulative return" in chosen:
            out["cumret"] = cumulative_return(price)
        if "Rolling volatility" in chosen:
            w = st.number_input("Volatility window", min_value=2, value=20, step=1, key="ind_vol_w")
            out[f"vol_{int(w)}"] = rolling_volatility(price, int(w))
        if "RSI" in chosen:
            w = st.number_input("RSI window", min_value=2, value=14, step=1, key="ind_rsi_w")
            out[f"rsi_{int(w)}"] = rsi(price, int(w))
        if "Bollinger Bands" in chosen:
            c1, c2 = st.columns(2)
            w = c1.number_input("Bollinger window", min_value=2, value=20, step=1, key="ind_bb_w")
            k = c2.number_input("Std multiplier (k)", min_value=0.5, value=2.0, step=0.5, key="ind_bb_k")
            mid, up, lo = bollinger(price, int(w), float(k))
            out[f"bb_mid_{int(w)}"], out[f"bb_upper_{int(w)}"], out[f"bb_lower_{int(w)}"] = mid, up, lo

        added = [c for c in out.columns if c not in df.columns]
        if added:
            st.success(f"Added: {', '.join(added)}")
        st.markdown("---")
        return out
