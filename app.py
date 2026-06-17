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
            if df is not None:
                st.subheader("Raw Data Table")
                st.dataframe(df)
            else:
                st.error("Unsupported file type or error loading file. Please upload a CSV, XLSX, JSON, or Parquet file.")
        except Exception as e:
            st.error(f"Error loading or processing file: {e}")
elif data_source == "Google Cloud Storage (GCS)":
    st.sidebar.info("GCS integration will be added here.")


# Data Health Check
if df is not None:
    st.markdown("---")
    show_health_check = st.checkbox("Show Data Health Check")

    if show_health_check:
        profile = get_data_profile(df)

        st.subheader("Data Health Check")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Rows", profile["total_rows"])
        with col2:
            st.metric("Total Columns", profile["total_columns"])
        with col3:
            st.metric("Duplicate Rows", profile["duplicate_rows"])

        if profile["missing_values_percentage"]:
            st.markdown("##### Missing Values Per Column:")
            missing_cols = list(profile["missing_values_percentage"].keys())
            missing_vals = list(profile["missing_values_percentage"].values())

            # Display missing values in a structured way (e.g., table or more columns)
            # Using columns for a few, or a dataframe for many
            if len(missing_cols) <= 4:
                cols_missing = st.columns(len(missing_cols))
                for i, col_name in enumerate(missing_cols):
                    with cols_missing[i]:
                        st.metric(col_name, missing_vals[i])
            else:
                st.dataframe(pd.DataFrame({"Column": missing_cols, "Missing %": missing_vals}))
        else:
            st.info("No missing values found!")
    st.markdown("---")


    st.subheader("Interactive Line Chart")

        numerical_cols = df.select_dtypes(include=['number']).columns.tolist()

        if len(numerical_cols) >= 1:
            # For simplicity, plot all numerical columns against the DataFrame index.
            # Users can customize axis selection if more detailed charting is needed.
            fig = px.line(df, y=numerical_cols, title="Data Trends Over Index")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.write("No numerical columns found to create a line chart.")

