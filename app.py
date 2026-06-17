import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(layout="wide")

st.title("Personal Data Analysis Application")

st.sidebar.header("Upload your Data")
uploaded_file = st.sidebar.file_uploader("Upload a CSV file", type=["csv"])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        st.subheader("Raw Data Table")
        st.dataframe(df)

        st.subheader("Interactive Line Chart")

        numerical_cols = df.select_dtypes(include=['number']).columns.tolist()

        if len(numerical_cols) >= 1:
            # For simplicity, plot all numerical columns against the DataFrame index.
            # Users can customize axis selection if more detailed charting is needed.
            fig = px.line(df, y=numerical_cols, title="Data Trends Over Index")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.write("No numerical columns found to create a line chart.")

    except Exception as e:
        st.error(f"Error loading or processing file: {e}")
else:
    st.info("Please upload a CSV file to begin analysis.")
