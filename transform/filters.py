"""Interactive filtering workspace (sidebar)."""
import pandas as pd
import streamlit as st

# Above this many distinct values, a categorical column gets a substring
# "contains" filter instead of an unwieldy multiselect of every value.
MAX_CATEGORICAL_OPTIONS = 50


def _date_range_filter(label, series, filtered_df, mask_target, key):
    """Render a from/to date picker; return a boolean mask over ``mask_target``."""
    valid = series.dropna()
    if valid.empty:
        return None
    lo, hi = valid.min(), valid.max()
    chosen = st.sidebar.date_input(
        f"Filter {label}",
        value=(lo.date(), hi.date()),
        min_value=lo.date(),
        max_value=hi.date(),
        key=key,
    )
    if not (isinstance(chosen, (tuple, list)) and len(chosen) == 2):
        return None
    start = pd.Timestamp(chosen[0])
    # include the whole end day
    end = pd.Timestamp(chosen[1]) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    return (mask_target >= start) & (mask_target <= end)


def render_filters(df):
    """Render sidebar filter controls and return the filtered DataFrame."""
    filtered_df = df.copy()

    st.sidebar.header("Filter Workspace")

    # Datetime index gets its own date-range filter (e.g. after normalization).
    if isinstance(df.index, pd.DatetimeIndex):
        mask = _date_range_filter(
            "date (index)", df.index.to_series(), filtered_df,
            filtered_df.index.to_series(), key="date_filter_index",
        )
        if mask is not None:
            filtered_df = filtered_df[mask.values]

    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            mask = _date_range_filter(
                col, df[col], filtered_df, filtered_df[col], key=f"date_filter_{col}"
            )
            if mask is not None:
                filtered_df = filtered_df[mask]
        elif pd.api.types.is_numeric_dtype(df[col]):
            min_val = float(df[col].min())
            max_val = float(df[col].max())

            if min_val == max_val:
                st.sidebar.write(f"Column '{col}' has a constant value: {min_val}")
                current_min, current_max = min_val, max_val
            else:
                current_min, current_max = st.sidebar.slider(
                    f"Filter {col}",
                    min_value=min_val,
                    max_value=max_val,
                    value=(min_val, max_val),
                    key=f"slider_{col}",
                )
            filtered_df = filtered_df[
                (filtered_df[col] >= current_min) & (filtered_df[col] <= current_max)
            ]
        elif df[col].dtype == "object" or pd.api.types.is_categorical_dtype(df[col]):
            unique_values = sorted(df[col].astype(str).unique().tolist())
            # A multiselect of hundreds of values is a wall of noise. Above a
            # threshold, offer a substring "contains" filter instead.
            if len(unique_values) > MAX_CATEGORICAL_OPTIONS:
                term = st.sidebar.text_input(
                    f"Filter {col} (contains)",
                    key=f"contains_{col}",
                    help=f"{len(unique_values)} unique values — type to match a substring.",
                ).strip()
                if term:
                    filtered_df = filtered_df[
                        filtered_df[col].astype(str).str.contains(term, case=False, na=False)
                    ]
            else:
                selected_values = st.sidebar.multiselect(
                    f"Filter {col}",
                    options=unique_values,
                    default=unique_values,
                    key=f"multiselect_{col}",
                )
                if selected_values:
                    filtered_df = filtered_df[filtered_df[col].astype(str).isin(selected_values)]

    return filtered_df


def _column_config(df):
    """Build st.column_config for nicer number/date formatting."""
    cfg = {}
    try:
        for col in df.columns:
            if pd.api.types.is_float_dtype(df[col]):
                cfg[col] = st.column_config.NumberColumn(format="%.2f")
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                cfg[col] = st.column_config.DatetimeColumn(format="YYYY-MM-DD")
    except Exception:
        pass
    return cfg


def render_table(filtered_df):
    """Render the filtered data as an editable, formatted table; return edits."""
    st.subheader("Data Table (Filtered & Editable)")
    # st.data_editor can't render a MultiIndex; flatten it into columns so the
    # data stays visible/editable and flows downstream intact.
    if isinstance(filtered_df.index, pd.MultiIndex):
        filtered_df = filtered_df.reset_index()
        st.caption("Note: a multi-level index was flattened into columns for editing.")
    edited = st.data_editor(
        filtered_df,
        use_container_width=True,
        num_rows="dynamic",
        column_config=_column_config(filtered_df),
        key="data_editor",
    )
    return edited


def render_export(filtered_df):
    """Render a single CSV download button for the current data."""
    csv_export = filtered_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇ Download CSV",
        data=csv_export,
        file_name="data_export.csv",
        mime="text/csv",
    )
