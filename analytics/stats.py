"""Returns & risk metrics for a price series."""
import numpy as np
import pandas as pd
import streamlit as st

from transform.normalize import time_axis

# Preferred price columns, best first.
PRICE_PREFERENCE = ["adj_close", "close", "price", "value"]


def _periods_per_year(dates: pd.Series) -> int:
    """Infer the annualization factor from the median spacing of ``dates``."""
    if dates is None or len(dates) < 3:
        return 252
    med_days = pd.Series(pd.to_datetime(dates)).sort_values().diff().dropna().dt.days.median()
    if med_days is None or np.isnan(med_days):
        return 252
    if med_days <= 3:
        return 252      # daily (trading)
    if med_days <= 10:
        return 52       # weekly
    if med_days <= 45:
        return 12       # monthly
    return 1            # annual-ish


def compute_stats(prices, dates=None) -> dict:
    """Compute return/risk metrics from a price series.

    ``prices`` is array-like; ``dates`` (optional, aligned) enables CAGR and a
    frequency-aware annualization. Returns a dict of metrics (values may be NaN
    when there isn't enough data).
    """
    prices = pd.Series(prices, dtype="float64")
    # Order oldest→newest so returns/drawdown are correct even when the source
    # is newest-first (common in price exports).
    if dates is not None and len(dates) == len(prices):
        order = pd.to_datetime(pd.Series(dates).reset_index(drop=True), errors="coerce").argsort()
        prices = prices.reset_index(drop=True).iloc[order.values]
    prices = prices.dropna().reset_index(drop=True)
    if len(prices) < 2:
        return {}

    returns = prices.pct_change().dropna()
    total_return = prices.iloc[-1] / prices.iloc[0] - 1.0
    ppy = _periods_per_year(dates)

    cagr = np.nan
    if dates is not None and len(dates) >= 2:
        d = pd.to_datetime(pd.Series(dates)).sort_values()
        span_days = (d.iloc[-1] - d.iloc[0]).days
        if span_days > 0:
            cagr = (prices.iloc[-1] / prices.iloc[0]) ** (365.25 / span_days) - 1.0

    vol = returns.std() * np.sqrt(ppy) if len(returns) > 1 else np.nan
    ann_return = returns.mean() * ppy if len(returns) else np.nan
    sharpe = ann_return / vol if vol and not np.isnan(vol) and vol != 0 else np.nan
    drawdown = (prices / prices.cummax() - 1.0).min()

    return {
        "total_return": total_return,
        "cagr": cagr,
        "ann_volatility": vol,
        "sharpe": sharpe,
        "max_drawdown": drawdown,
        "best_day": returns.max() if len(returns) else np.nan,
        "worst_day": returns.min() if len(returns) else np.nan,
        "observations": len(prices),
    }


def _pick_price_column(df, numeric_cols):
    lowered = {str(c).lower(): c for c in numeric_cols}
    for pref in PRICE_PREFERENCE:
        if pref in lowered:
            return lowered[pref]
    return numeric_cols[0] if numeric_cols else None


def _pct(x):
    return "—" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x * 100:.2f}%"


def render_returns_panel(df):
    """Render the 'Returns & Risk' panel for the active DataFrame."""
    st.markdown("---")
    if not st.checkbox("Show Returns & Risk", key="returns_panel"):
        return

    st.subheader("Returns & Risk")

    numeric_cols = df.select_dtypes("number").columns.tolist()
    if not numeric_cols:
        st.info("No numeric price column available. Try the normalizer to coerce prices.")
        return

    default_price = _pick_price_column(df, numeric_cols)
    price_col = st.selectbox(
        "Price column",
        options=numeric_cols,
        index=numeric_cols.index(default_price) if default_price in numeric_cols else 0,
        key="returns_price_col",
    )

    kind, name = time_axis(df)
    if kind == "index":
        dates = df.index.to_series()
    elif kind == "column":
        dates = df[name]
    else:
        dates = None
        st.caption("No datetime axis found — CAGR/annualization use a daily assumption.")

    stats = compute_stats(df[price_col], dates)
    if not stats:
        st.info("Not enough data points to compute statistics.")
        return

    row1 = st.columns(4)
    row1[0].metric("Total Return", _pct(stats["total_return"]))
    row1[1].metric("CAGR", _pct(stats["cagr"]))
    row1[2].metric("Annual Volatility", _pct(stats["ann_volatility"]))
    row1[3].metric("Max Drawdown", _pct(stats["max_drawdown"]))

    row2 = st.columns(4)
    sharpe = stats["sharpe"]
    row2[0].metric("Sharpe (rf=0)", "—" if np.isnan(sharpe) else f"{sharpe:.2f}")
    row2[1].metric("Best Day", _pct(stats["best_day"]))
    row2[2].metric("Worst Day", _pct(stats["worst_day"]))
    row2[3].metric("Observations", stats["observations"])
