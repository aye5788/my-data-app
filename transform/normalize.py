"""Time-series / price-data normalizer.

Price data arrives in inconsistent shapes (date vs timestamp, Close vs
adjClose, "$1,234.50" strings, ascending vs descending). This step
standardizes any imported or uploaded frame into a clean, sorted time series
with canonical OHLCV column names where they can be found.
"""
import pandas as pd
import streamlit as st

# Column-name aliases (compared case-insensitively, stripped).
DATE_ALIASES = ["date", "datetime", "time", "timestamp", "ds", "period", "date_time"]
OHLCV_ALIASES = {
    "open": ["open", "o", "1. open"],
    "high": ["high", "h", "2. high"],
    "low": ["low", "l", "3. low"],
    "close": ["close", "c", "price", "value", "close_last", "4. close", "last"],
    "adj_close": ["adj_close", "adjclose", "adj close", "adjusted_close", "5. adjusted close"],
    "volume": ["volume", "vol", "v", "6. volume"],
}


def detect_datetime_col(df):
    """Best-effort guess of the datetime column (by name, then parseability)."""
    lowered = {str(c).strip().lower(): c for c in df.columns}
    for alias in DATE_ALIASES:
        if alias in lowered:
            return lowered[alias]
    for c in df.columns:
        if df[c].dtype == object:
            parsed = pd.to_datetime(df[c], errors="coerce")
            if parsed.notna().mean() > 0.8:
                return c
    return None


def time_axis(df):
    """Locate the time axis of ``df``.

    Returns ``("index", None)`` if the index is a DatetimeIndex,
    ``("column", name)`` if a datetime column is found, else ``(None, None)``.
    """
    if isinstance(df.index, pd.DatetimeIndex):
        return "index", None
    for c in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[c]):
            return "column", c
    detected = detect_datetime_col(df)
    if detected is not None:
        return "column", detected
    return None, None


def suggest_mapping(df):
    """Map canonical OHLCV names -> source columns found in ``df``."""
    lowered = {str(c).strip().lower(): c for c in df.columns}
    mapping = {}
    for canon, aliases in OHLCV_ALIASES.items():
        for a in aliases:
            if a in lowered:
                mapping[canon] = lowered[a]
                break
    return mapping


def clean_numeric(series):
    """Strip currency/percent/thousands formatting and coerce to numbers."""
    cleaned = (
        series.astype(str)
        .str.replace(r"[$,%\s]", "", regex=True)
        .str.replace(",", "", regex=False)
    )
    return pd.to_numeric(cleaned, errors="coerce")


def normalize(df, dt_col, mapping, clean_other_numeric=False, set_index=False,
              resample_rule=None):
    """Return a standardized copy of ``df``.

    - parse ``dt_col`` to datetime and sort ascending
    - rename mapped source columns to canonical OHLCV names
    - coerce mapped (and optionally other object) columns to numeric
    - optionally set the datetime as index and resample (OHLC aware)
    """
    out = df.copy()

    if dt_col and dt_col in out.columns:
        out[dt_col] = pd.to_datetime(out[dt_col], errors="coerce")
        out = out.sort_values(dt_col).reset_index(drop=True)

    rename = {src: canon for canon, src in mapping.items() if src in out.columns}
    out = out.rename(columns=rename)

    numeric_targets = list(rename.values())
    if clean_other_numeric:
        numeric_targets += [
            c for c in out.columns if c != dt_col and out[c].dtype == object
        ]
    for c in set(numeric_targets):
        if c in out.columns:
            out[c] = clean_numeric(out[c])

    if set_index and dt_col and dt_col in out.columns:
        out = out.set_index(dt_col)
        if resample_rule:
            agg = {}
            for canon, how in [("open", "first"), ("high", "max"), ("low", "min"),
                               ("close", "last"), ("adj_close", "last"), ("volume", "sum")]:
                if canon in out.columns:
                    agg[canon] = how
            # fall back to mean for any other numeric columns
            for c in out.select_dtypes("number").columns:
                agg.setdefault(c, "mean")
            if agg:
                out = out.resample(resample_rule).agg(agg).dropna(how="all")

    return out


def render_normalizer(df):
    """Render the opt-in normalization expander; return the (possibly) new df."""
    with st.expander("Normalize price / time-series data"):
        enabled = st.checkbox(
            "Standardize as time-series / price data",
            value=False,
            key="normalize_enabled",
            help="Parse the date column, rename OHLCV columns, and clean numeric formatting.",
        )
        if not enabled:
            return df

        cols = list(df.columns)
        detected = detect_datetime_col(df)
        dt_col = st.selectbox(
            "Datetime column",
            options=cols,
            index=cols.index(detected) if detected in cols else 0,
            key="normalize_dtcol",
        )

        st.markdown("**Map price columns** (leave as `—` if absent):")
        mapping = {}
        suggested = suggest_mapping(df)
        opts = ["—"] + cols
        for canon in ["open", "high", "low", "close", "adj_close", "volume"]:
            default = suggested.get(canon, "—")
            choice = st.selectbox(
                canon,
                options=opts,
                index=opts.index(default) if default in opts else 0,
                key=f"normalize_map_{canon}",
            )
            if choice != "—":
                mapping[canon] = choice

        clean_other = st.checkbox(
            "Also clean other numeric-looking text columns", value=False, key="normalize_cleanother"
        )
        set_index = st.checkbox("Set datetime as index", value=False, key="normalize_setindex")
        resample_label = st.selectbox(
            "Resample frequency",
            options=["None", "Daily", "Weekly", "Monthly"],
            index=0,
            key="normalize_resample",
            disabled=not set_index,
        )
        rule = {"Daily": "D", "Weekly": "W", "Monthly": "ME"}.get(resample_label)

        try:
            result = normalize(
                df,
                dt_col=dt_col,
                mapping=mapping,
                clean_other_numeric=clean_other,
                set_index=set_index,
                resample_rule=rule,
            )
            st.success(f"Normalized: {result.shape[0]} rows × {result.shape[1]} columns.")
            return result
        except Exception as e:
            st.error(f"Normalization failed: {e}")
            return df
