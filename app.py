import streamlit as st
import pandas as pd
import plotly.express as px
from data_loader import load_data_file

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

if df is not None:

        st.subheader("Interactive Line Chart")

        numerical_cols = df.select_dtypes(include=['number']).columns.tolist()

        if len(numerical_cols) >= 1:
            # For simplicity, plot all numerical columns against the DataFrame index.
            # Users can customize axis selection if more detailed charting is needed.
            fig = px.line(df, y=numerical_cols, title="Data Trends Over Index")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.write("No numerical columns found to create a line chart.")

    # This else block is now implicitly handled by df being None
    pass
