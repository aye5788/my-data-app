"""Generic REST / API connector.

There is no universal *importer* (every provider's endpoint differs), but
almost every data API is "HTTP GET -> JSON or CSV, with an API key." This
connector captures that shape with presets for common providers (FMP, FRED)
plus a Custom mode that can hit any URL. Pair it with the time-series
normalizer to standardize whatever comes back.

API keys are read from st.secrets["api_keys"][<name>] when present, otherwise
entered in the UI (and never persisted).
"""
import io

import pandas as pd
import requests
import streamlit as st

NAME = "API / REST"


# ----- response parsing (pure, unit-testable) -----------------------------

def _extract_records(data, records_path: str = ""):
    """Pull the list-of-records out of a decoded JSON payload.

    ``records_path`` is an optional dot-path (e.g. ``"data.results"``). When
    omitted we use the payload directly if it's a list, else the first list
    value found in the dict, else wrap the dict as a single record.
    """
    if records_path:
        for key in records_path.split("."):
            data = data[key]

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        nested = next((v for v in data.values() if isinstance(v, list)), None)
        return nested if nested is not None else [data]
    return [{"value": data}]


@st.cache_data(show_spinner="Fetching from API...")
def _fetch(url: str, params_items: tuple, records_path: str) -> pd.DataFrame:
    """GET ``url`` with ``params`` and return a DataFrame (JSON or CSV)."""
    params = dict(params_items)
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()

    ctype = resp.headers.get("content-type", "").lower()
    if "csv" in ctype or url.lower().endswith(".csv"):
        return pd.read_csv(io.StringIO(resp.text))

    return pd.DataFrame(_extract_records(resp.json(), records_path))


# ----- key handling --------------------------------------------------------

def _resolve_key(name: str, label: str) -> str:
    """Return an API key from secrets, or prompt for one in the sidebar."""
    try:
        secret = st.secrets["api_keys"][name]
    except Exception:
        secret = ""
    if secret:
        st.sidebar.caption(f"Using {label} key from secrets.")
        return secret
    return st.sidebar.text_input(
        f"{label} API key",
        type="password",
        help=f'Add to secrets as [api_keys] {name} = "..." to avoid re-entering.',
        key=f"rest_key_{name}",
    ).strip()


# ----- providers -----------------------------------------------------------

def _fmp():
    symbol = st.sidebar.text_input("Ticker symbol", value="AAPL", key="fmp_symbol").strip().upper()
    key = _resolve_key("fmp", "FMP")
    if not (symbol and key):
        return None, ""
    url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}"
    params = {"apikey": key}
    col1, col2 = st.columns(2)
    frm = col1.text_input("From (YYYY-MM-DD, optional)", key="fmp_from").strip()
    to = col2.text_input("To (YYYY-MM-DD, optional)", key="fmp_to").strip()
    if frm:
        params["from"] = frm
    if to:
        params["to"] = to
    return (url, params, "historical"), symbol


def _fred():
    series = st.sidebar.text_input("FRED series id", value="GDP", key="fred_series").strip().upper()
    key = _resolve_key("fred", "FRED")
    if not (series and key):
        return None, ""
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {"series_id": series, "api_key": key, "file_type": "json"}
    return (url, params, "observations"), series


def _custom():
    url = st.text_input(
        "Request URL",
        help="Full URL including any API key in the query string.",
        key="rest_custom_url",
    ).strip()
    records_path = st.text_input(
        "Records path (optional)",
        help="Dot-path to the list of records in the JSON, e.g. data.results. "
        "Leave blank to auto-detect.",
        key="rest_custom_path",
    ).strip()
    if not url:
        return None, ""
    return (url, {}, records_path), url


PROVIDERS = {
    "FMP – Historical Prices": _fmp,
    "FRED – Series Observations": _fred,
    "Custom URL": _custom,
}


def render():
    """Render the API connector UI; return ``(df_or_None, asset_name)``."""
    st.sidebar.markdown("**API source**")
    provider = st.sidebar.selectbox("Provider", list(PROVIDERS), key="rest_provider")

    request, asset = PROVIDERS[provider]()
    if request is None:
        st.sidebar.info("Enter the request details above.")
        return None, ""

    url, params, records_path = request
    st.caption(f"GET `{url}`")
    try:
        df = _fetch(url, tuple(sorted(params.items())), records_path)
        if df.empty:
            st.warning("The API returned no rows.")
        return df, asset
    except Exception as e:
        st.error(f"API request failed: {e}")
        return None, ""
