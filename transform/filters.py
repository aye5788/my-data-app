"""Interactive filtering workspace (sidebar)."""
import pandas as pd
import streamlit as st


def render_filters(df):
    """Render sidebar filter controls and return the filtered DataFrame."""
    filtered_df = df.copy()

    st.sidebar.header("Filter Workspace")
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
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
            unique_values = df[col].astype(str).unique().tolist()
            unique_values.sort()
            selected_values = st.sidebar.multiselect(
                f"Filter {col}",
                options=unique_values,
                default=unique_values,
                key=f"multiselect_{col}",
            )
            if selected_values:
                filtered_df = filtered_df[filtered_df[col].astype(str).isin(selected_values)]

    return filtered_df


def render_export(filtered_df):
    """Render the CSV export button for the filtered data."""
    st.markdown("---")
    st.subheader("Export Workspace")
    csv_export = filtered_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download Filtered Data as CSV",
        data=csv_export,
        file_name="cleansed_data_export.csv",
        mime="text/csv",
    )
