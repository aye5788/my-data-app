"""Data profiling / health-check layer.

Phase 0 ports the existing health check unchanged. Phase 2 will grow this into
the full profiling dashboard + on-demand ydata-profiling report.
"""
import streamlit as st


def get_data_profile(df):
    """Compute summary metrics for a DataFrame."""
    if df is None or df.empty:
        return {
            "total_rows": 0,
            "total_columns": 0,
            "duplicate_rows": 0,
            "missing_values_percentage": {},
        }

    total_rows = df.shape[0]
    total_columns = df.shape[1]
    duplicate_rows = df.duplicated().sum()
    missing_values_percentage = (df.isnull().sum() / total_rows * 100).to_dict()

    return {
        "total_rows": total_rows,
        "total_columns": total_columns,
        "duplicate_rows": duplicate_rows,
        "missing_values_percentage": {
            col: f"{val:.2f}%"
            for col, val in missing_values_percentage.items()
            if val > 0
        },
    }


def render_health_check(df):
    """Render the optional 'Data Health Check' section for ``df``."""
    st.markdown("---")
    show_health_check = st.checkbox("Show Data Health Check")

    if not show_health_check:
        st.markdown("---")
        return

    profile = get_data_profile(df)
    st.subheader("Data Health Check")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Rows (Filtered)", profile["total_rows"])
    with col2:
        st.metric("Total Columns", profile["total_columns"])
    with col3:
        st.metric("Duplicate Rows (Filtered)", profile["duplicate_rows"])

    if profile["missing_values_percentage"]:
        st.markdown("##### Missing Values Per Column:")
        missing_cols = list(profile["missing_values_percentage"].keys())
        missing_vals = list(profile["missing_values_percentage"].values())

        if len(missing_cols) <= 4:
            cols_missing = st.columns(len(missing_cols))
            for i, col_name in enumerate(missing_cols):
                with cols_missing[i]:
                    st.metric(col_name, missing_vals[i])
    else:
        st.info("No missing values found!")
    st.markdown("---")
