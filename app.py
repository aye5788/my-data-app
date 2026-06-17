import streamlit as st
import pandas as pd
import plotly.express as px
from data_loader import load_data_file, get_data_profile

st.set_page_config(layout="wide")

st.title("Personal Data Analysis Application")

st.sidebar.header("Select Data Source")
data_source = st.sidebar.selectbox(
    "Choose your data source",
    ("Local Upload", "Google Cloud Storage (GCS)")
)

df = None # Initialize df to None

if data_source == "Local Upload":
    uploaded_file = st.sidebar.file_uploader(
        "Upload a file",
        type=["csv", "xlsx", "json", "parquet"]
    )

    if uploaded_file is not None:
        try:
            df = load_data_file(uploaded_file, uploaded_file.name)
            if df is None: # Only show error if df is explicitly None after attempting to load
                st.error("Unsupported file type or error loading file. Please upload a CSV, XLSX, JSON, or Parquet file.")
        except Exception as e:
            st.error(f"Error loading or processing file: {e}")
elif data_source == "Google Cloud Storage (GCS)":
    st.sidebar.info("GCS integration will be added here.")


# --- Main application logic when df is loaded ---
filtered_df = None
if df is not None:
    filtered_df = df.copy() # Start with a copy of the original data

    st.sidebar.header("Filter Workspace")
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            min_val = float(df[col].min())
            max_val = float(df[col].max())

            # Handle constant value columns or very small ranges
            if min_val == max_val:
                st.sidebar.write(f"Column '{col}' has a constant value: {min_val}")
                # For a single unique value, filtering effectively doesn't change anything
                current_min, current_max = min_val, max_val
            else:
                current_min, current_max = st.sidebar.slider(
                    f"Filter {col}",
                    min_value=min_val,
                    max_value=max_val,
                    value=(min_val, max_val), # Default to full range
                    key=f"slider_{col}"
                )
            filtered_df = filtered_df[
                (filtered_df[col] >= current_min) & (filtered_df[col] <= current_max)
            ]
        elif df[col].dtype == 'object' or pd.api.types.is_categorical_dtype(df[col]):
            unique_values = df[col].astype(str).unique().tolist()
            unique_values.sort() # Sort for better UI
            selected_values = st.sidebar.multiselect(
                f"Filter {col}",
                options=unique_values,
                default=unique_values, # Default to all selected
                key=f"multiselect_{col}"
            )
            if selected_values:
                filtered_df = filtered_df[filtered_df[col].astype(str).isin(selected_values)]

    # Display Filtered Data Table
    st.subheader("Raw Data Table (Filtered)")
    st.dataframe(filtered_df)

    # Data Health Check Section
    st.markdown("---")
    show_health_check = st.checkbox("Show Data Health Check")

    if show_health_check:
        profile = get_data_profile(filtered_df) # Use filtered_df for health check
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

            if len(missing_cols) <= 4: # Display up to 4 in columns, otherwise a dataframe
                cols_missing = st.columns(len(missing_cols))
                for i, col_name in enumerate(missing_cols):
                    with cols_missing[i]:
                        st.metric(col_name, missing_vals[i])
            else:
                st.dataframe(pd.DataFrame({"Column": missing_cols, "Missing %": missing_vals}))
        else:
            st.info("No missing values found!")
    st.markdown("---")

    # Interactive Line Chart Section
    st.subheader("Interactive Line Chart (Filtered)") # Update subheader
    numerical_cols = filtered_df.select_dtypes(include=['number']).columns.tolist() # Use filtered_df

    if len(numerical_cols) >= 1:
        # For simplicity, plot all numerical columns against the DataFrame index.
        # Users can customize axis selection if more detailed charting is needed.
        fig = px.line(filtered_df, y=numerical_cols, title="Data Trends Over Index") # Use filtered_df
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.write("No numerical columns found to create a line chart.")
else: # If df is None, display initial prompt
    st.info("Please upload a file or specify a GCS path to begin analysis.")

