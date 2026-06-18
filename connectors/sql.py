"""SQL database connector.

Connects to any SQLAlchemy-supported database (Postgres, MySQL, SQLite,
DuckDB) and loads data by table (with a row limit) or via a custom query.
Work is pushed *down* to the database so we never pull whole tables into
the limited memory of the Cloud instance.

Reachability note: on Streamlit Community Cloud the database must be
reachable from the public internet. Run the app locally/desktop to reach
a database on your own machine or LAN.
"""
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL

NAME = "SQL Database"

# Friendly name -> SQLAlchemy dialect+driver.
DIALECTS = {
    "PostgreSQL": "postgresql+psycopg2",
    "MySQL": "mysql+pymysql",
    "SQLite": "sqlite",
    "DuckDB": "duckdb",
}
FILE_BASED = {"SQLite", "DuckDB"}


@st.cache_resource(show_spinner=False)
def _get_engine(url: str):
    """One pooled engine per connection URL (cached across reruns)."""
    return create_engine(url)


@st.cache_data(show_spinner=False)
def _list_tables(url: str):
    return inspect(_get_engine(url)).get_table_names()


@st.cache_data(show_spinner="Running query...")
def _run_query(url: str, sql: str) -> pd.DataFrame:
    return pd.read_sql(text(sql), _get_engine(url))


def _quote(url: str, identifier: str) -> str:
    """Quote a table identifier using the target dialect's rules."""
    return _get_engine(url).dialect.identifier_preparer.quote(identifier)


def _build_url() -> str:
    """Render connection widgets and return a SQLAlchemy URL string (or "")."""
    # Prefill a full URL from secrets if the user configured one there.
    secret_url = ""
    try:
        secret_url = st.secrets["connections"]["sql"]["url"]
    except Exception:
        secret_url = ""

    mode = st.sidebar.radio(
        "Connection input",
        ["Build from fields", "Full URL / secret"],
        key="sql_mode",
        index=1 if secret_url else 0,
    )

    if mode == "Full URL / secret":
        url = st.sidebar.text_input(
            "SQLAlchemy URL",
            value=secret_url,
            type="password",
            help="e.g. postgresql+psycopg2://user:pass@host:5432/dbname",
            key="sql_url",
        )
        return url.strip()

    dialect_name = st.sidebar.selectbox("Database type", list(DIALECTS), key="sql_dialect")
    driver = DIALECTS[dialect_name]

    if dialect_name in FILE_BASED:
        path = st.sidebar.text_input(
            "Database file path",
            help="Absolute path to the .db / .duckdb file. Reachable only when running locally.",
            key="sql_path",
        ).strip()
        return f"{driver}:///{path}" if path else ""

    host = st.sidebar.text_input("Host", key="sql_host").strip()
    port = st.sidebar.text_input("Port", key="sql_port").strip()
    database = st.sidebar.text_input("Database", key="sql_db").strip()
    user = st.sidebar.text_input("User", key="sql_user").strip()
    password = st.sidebar.text_input("Password", type="password", key="sql_pw")

    if not (host and database and user):
        return ""

    # URL.create handles escaping of special characters in credentials.
    return URL.create(
        driver,
        username=user or None,
        password=password or None,
        host=host or None,
        port=int(port) if port.isdigit() else None,
        database=database or None,
    ).render_as_string(hide_password=False)


def render():
    """Render the SQL connector UI; return ``(df_or_None, asset_name)``."""
    st.sidebar.markdown("**SQL connection**")
    url = _build_url()

    if not url:
        st.sidebar.info("Enter connection details to connect.")
        return None, ""

    # Establish the connection by listing tables.
    try:
        tables = _list_tables(url)
    except Exception as e:
        st.sidebar.error(f"Connection failed: {e}")
        return None, ""

    st.subheader("SQL Query Builder")
    query_mode = st.radio("Load by", ["Table", "Custom SQL"], horizontal=True, key="sql_query_mode")

    if query_mode == "Table":
        if not tables:
            st.warning("Connected, but no tables were found in this database.")
            return None, ""
        table = st.selectbox("Table", tables, key="sql_table")
        limit = st.number_input(
            "Row limit", min_value=1, max_value=1_000_000, value=1000, step=100, key="sql_limit"
        )
        if not table:
            return None, ""
        sql = f"SELECT * FROM {_quote(url, table)} LIMIT {int(limit)}"
        asset = table
    else:
        sql = st.text_area(
            "SQL query",
            value="SELECT 1",
            help="Use LIMIT to keep result sizes manageable.",
            key="sql_custom",
        ).strip()
        asset = "custom query"
        if not sql:
            st.info("Enter a SQL query to run.")
            return None, ""

    st.caption(f"Query: `{sql}`")
    try:
        df = _run_query(url, sql)
        return df, asset
    except Exception as e:
        st.error(f"Query failed: {e}")
        return None, ""
