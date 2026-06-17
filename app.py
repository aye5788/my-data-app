import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai # Import for Gemini API
import os # To potentially read API key from environment
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

    # --- AI Data Assistant Section ---
    st.markdown("---")
    st.subheader("Ask Gemini about this data")
    gemini_query = st.text_input(
        "Enter your question about the data (e.g., 'What is the average of column X?', 'How many unique values in column Y?')",
        key="gemini_query_input"
    )

    if st.button("Get Answer from Gemini") and gemini_query:
        if "GEMINI_API_KEY" not in st.secrets:
            st.error("Gemini API key not found. Please add it to your `.streamlit/secrets.toml` or set the `GEMINI_API_KEY` environment variable.")
        else:
            try:
                # Configure Gemini
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                model = genai.GenerativeModel('gemini-pro')

                # Prepare data schema for the prompt
                schema_string = "\n".join([f"- {col}: {filtered_df[col].dtype}" for col in filtered_df.columns])

                # Construct the prompt for Gemini
                prompt_parts = [
                    "You are a helpful data analysis assistant. Your task is to generate a single line of Python code using Pandas "
                    "on a DataFrame named `df` (which is already defined and loaded in the environment) to answer the user's question. "
                    "The DataFrame `df` has the following columns and data types:\n"
                    f"{schema_string}\n\n"
                    "Return ONLY the Python code string. Do not include `print()`, any explanatory text, or code block delimiters (e.g., ```python). "
                    "Ensure the code is a single executable line that directly computes the answer or value. For example, if asked 'What is the average of column A?', return 'df[\"A\"].mean()'.\n\n"
                    f"User question: {gemini_query}"
                ]

                with st.spinner("Asking Gemini..."):
                    response = model.generate_content(prompt_parts)
                    pandas_code = response.text.strip()

                    st.markdown(f"**Gemini's suggested code:** `{pandas_code}`")

                    # Safely execute the generated Pandas code
                    try:
                        # Define a restricted execution environment
                        safe_globals = {'pd': pd, 'df': filtered_df}
                        safe_locals = {}
                        # Only allow a very limited set of built-in functions
                        safe_globals['__builtins__'] = {
                            'abs': abs, 'round': round, 'len': len, 'str': str, 'int': int, 'float': float, 'bool': bool,
                            'max': max, 'min': min, 'sum': sum, 'list': list, 'tuple': tuple, 'dict': dict, 'set': set
                        }

                        # Execute the code
                        result = eval(pandas_code, safe_globals, safe_locals)
                        st.success(f"**Gemini's Answer:** {result}")
                    except SyntaxError as se:
                        st.error(f"Gemini returned invalid Python syntax: `{pandas_code}`. Error: {se}")
                    except NameError as ne:
                        st.error(f"Gemini used an undefined name in its code: `{pandas_code}`. Error: {ne}")
                    except KeyError as ke:
                        st.error(f"Gemini referenced a non-existent column: `{pandas_code}`. Error: {ke}")
                    except Exception as exec_e:
                        st.error(f"Error executing Gemini's code: `{pandas_code}`. Error: {exec_e}")

            except Exception as api_e:
                st.error(f"Error communicating with Gemini API: {api_e}")
else: # If df is None, display initial prompt for the entire app
    st.info("Please upload a file or specify a GCS path to begin analysis.")

