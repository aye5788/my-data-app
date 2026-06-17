import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai # Import for Gemini API
import os # To potentially read API key from environment
import json # Import for reading JSON config
from openai import OpenAI # Import for OpenAI API
from data_loader import load_data_file, get_data_profile, load_from_gcs, list_gcs_bucket_files, list_all_gcs_buckets

st.set_page_config(layout="wide")

st.title("Personal Data Analysis Application")

# Initialize OpenAI client for DeepSeek
try:
    openai_client = OpenAI(
        base_url='https://api.deepseek.com',
        api_key=st.secrets['DEEPSEEK_API_KEY']
    )
except KeyError:
    st.error("DEEPSEEK_API_KEY not found in Streamlit secrets. Please add it to your `.streamlit/secrets.toml` or set the environment variable.")
    openai_client = None # Set to None if key is missing

# Helper function to get the current context for the AI
def get_current_context(df_arg):
    context_parts = []

    # Add app.py snippet
    try:
        with open("app.py", "r") as f:
            app_snippet_lines = f.read().splitlines()[:50] # Get first 50 lines as a snippet
            app_snippet = "\n".join(app_snippet_lines)
        context_parts.append("--- app.py snippet ---\n" + app_snippet + "\n--- End of app.py snippet ---")
    except FileNotFoundError:
        context_parts.append("`app.py` file not found for context.")

    if df_arg is not None and not df_arg.empty:
        context_parts.append("\n--- Active DataFrame Context ---")
        context_parts.append(f"DataFrame Shape: {df_arg.shape}")
        context_parts.append("DataFrame Columns and dtypes:")
        for col, dtype in df_arg.dtypes.items():
            context_parts.append(f"- {col}: {dtype}")
        context_parts.append("--- End of DataFrame Context ---")
    else:
        context_parts.append("\nNo active DataFrame loaded yet.")

    return "\n".join(context_parts)

st.sidebar.header("Select Data Source")

# Load data sources from config file
try:
    with open("sources_config.json", "r") as f:
        data_sources_config = json.load(f)
    source_names = list(data_sources_config.keys())
except FileNotFoundError:
    st.error("`sources_config.json` not found. Please create it with data source configurations.")
    source_names = []
except json.JSONDecodeError:
    st.error("Error decoding `sources_config.json`. Please check its format.")
    source_names = []

if source_names:
    selected_source_name = st.sidebar.selectbox(
        "Choose your data source",
        source_names
    )
    selected_source_type = data_sources_config.get(selected_source_name)
else:
    selected_source_name = None
    selected_source_type = None

df = None # Initialize df to None

if selected_source_type == "file_upload":
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
elif selected_source_type == "gcs_bucket":
    available_buckets = list_all_gcs_buckets()
    
    if available_buckets:
        selected_bucket_name = st.sidebar.selectbox(
            "Select GCS Bucket",
            options=[""] + sorted(available_buckets), # Add empty option and sort for UI
            key="gcs_bucket_selector"
        )

        if selected_bucket_name:
            bucket_files = list_gcs_bucket_files(selected_bucket_name)

            st.subheader(f"Bucket File Explorer: `{selected_bucket_name}`")
            if bucket_files:
                # Create a dictionary to map display names (basename) back to full GCS paths
                file_paths_map = {os.path.basename(f): f for f in bucket_files}
                display_file_names = sorted(list(file_paths_map.keys())) # Sort for better UI
                
                selected_file_display_name = st.radio(
                    "Select a file from the bucket to load",
                    options=display_file_names,
                    index=0 if display_file_names else None, # Default to the first file if available
                    key="gcs_file_radio_selector"
                )

                if selected_file_display_name:
                    # Retrieve the full GCS path using the map
                    selected_gcs_file_path = file_paths_map[selected_file_display_name]
                    
                    st.info(f"Attempting to load data from: `{selected_gcs_file_path}`")
                    try:
                        df = load_from_gcs(selected_gcs_file_path)
                        if df is None:
                            st.error(f"Could not load data from '{selected_gcs_file_path}'. Check path and permissions.")
                    except Exception as e:
                        st.error(f"Error loading from GCS: {e}")
                else:
                    st.info("Please select a file from the bucket explorer.")
            else:
                st.warning(f"No files found in bucket '{selected_bucket_name}' or an error occurred. Ensure you have read permissions.")
        else:
            st.sidebar.info("Please select a GCS bucket.")
    else:
        st.sidebar.warning("No GCS buckets found or accessible. Ensure your service account has appropriate permissions.")
else: # No source selected or config error
    if source_names: # If there are options but none selected (e.g., initial load)
        st.sidebar.info("Please select a data source or configure `sources_config.json`.") # Added a hint for config


data_studio_tab, ai_workspace_tab = st.tabs(["📊 Data Studio", "🤖 AI Workspace"])

with data_studio_tab:
    # --- Main application logic when df is loaded ---
    filtered_df = None
    if df is not None:
        # --- Modify Column Data Types Section ---
        st.markdown("---")
        with st.expander("Modify Column Data Types"):
            st.write("Review and adjust data types for columns if needed. Changes here will affect filtering and visualizations.")

            for col in df.columns:
                current_type = str(df[col].dtype)
                
                # Options for type conversion
                options = ["No Change", "Text", "Integer", "Float", "Datetime"]
                
                # Determine default selection based on current type
                default_index = 0 # Default to "No Change"
                if pd.api.types.is_integer_dtype(df[col]):
                    default_index = options.index("Integer")
                elif pd.api.types.is_float_dtype(df[col]):
                    default_index = options.index("Float")
                elif pd.api.types.is_datetime64_any_dtype(df[col]):
                    default_index = options.index("Datetime")
                elif pd.api.types.is_object_dtype(df[col]):
                    # Heuristic: try to infer type for object columns
                    inferred_dtype = pd.api.types.infer_dtype(df[col])
                    if inferred_dtype == 'integer':
                        default_index = options.index("Integer")
                    elif inferred_dtype == 'floating':
                        default_index = options.index("Float")
                    elif inferred_dtype == 'datetime64':
                        default_index = options.index("Datetime")
                    else: # Fallback to text for other objects (strings, mixed, etc.)
                        default_index = options.index("Text")

                selected_type = st.selectbox(
                    f"Column '{col}' (Current: {current_type})",
                    options=options,
                    index=default_index,
                    key=f"type_select_{col}" # Unique key for each selectbox
                )

                if selected_type != "No Change":
                    try:
                        if selected_type == "Text":
                            df[col] = df[col].astype(str)
                        elif selected_type == "Integer":
                            # Convert to float first to handle NaNs, then to Int64 (pandas nullable integer type)
                            df[col] = pd.to_numeric(df[col], errors='coerce').astype(pd.Int64Dtype())
                        elif selected_type == "Float":
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                        elif selected_type == "Datetime":
                            df[col] = pd.to_datetime(df[col], errors='coerce')
                        st.success(f"Column '{col}' converted to {selected_type}. New type: {df[col].dtype}")
                    except Exception as type_e:
                        st.error(f"Could not convert column '{col}' to {selected_type}: {type_e}. Data might contain incompatible values. Consider cleaning data first.")
        st.markdown("---") # Separator after the expander

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

        # --- Export Workspace Section ---
        st.markdown("---")
        st.subheader("Export Workspace")
        
        # Convert DataFrame to CSV
        csv_export = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Filtered Data as CSV",
            data=csv_export,
            file_name='cleansed_data_export.csv',
            mime='text/csv',
        )

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
                st.info("No missing values found!")
        st.markdown("---")

        # --- Visualization Studio Section ---
        st.markdown("---")
        st.subheader("Visualization Studio")

        all_columns = filtered_df.columns.tolist()

        if not all_columns:
            st.info("Upload data to see visualization options.")
        else:
            col_x, col_y = st.columns(2)
            with col_x:
                x_axis = st.selectbox("Select X-Axis", options=all_columns, index=0 if all_columns else None)
            with col_y:
                y_axis = st.selectbox("Select Y-Axis", options=all_columns, index=1 if len(all_columns) > 1 else (0 if all_columns else None))

            chart_type = st.selectbox(
                "Select Chart Type",
                options=["Line", "Bar", "Scatter"],
                index=0
            )

            if x_axis and y_axis:
                try:
                    if chart_type == "Line":
                        fig = px.line(filtered_df, x=x_axis, y=y_axis, title=f"{y_axis} vs {x_axis} (Line Chart)")
                    elif chart_type == "Bar":
                        fig = px.bar(filtered_df, x=x_axis, y=y_axis, title=f"{y_axis} vs {x_axis} (Bar Chart)")
                    elif chart_type == "Scatter":
                        fig = px.scatter(filtered_df, x=x_axis, y=y_axis, title=f"{y_axis} vs {x_axis} (Scatter Plot)")

                    st.plotly_chart(fig, use_container_width=True)
                except Exception as chart_e:
                    st.error(f"Error creating chart: {chart_e}. Please check your axis selections and data types.")
            else:
                st.info("Please select both X and Y axes to generate a chart.")

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

with ai_workspace_tab:
    st.header("🤖 AI Workspace (DeepSeek)")
    
    if openai_client:
        # Initialize chat history
        if "messages" not in st.session_state:
            initial_context = get_current_context(df)
            st.session_state.messages = [
                {"role": "system", "content": f"You are a helpful AI assistant. Here is the current application and data context:\n{initial_context}"}
            ]

        # Display chat messages from history
        for message in st.session_state.messages:
            if message["role"] != "system": # Don't display system message in the UI
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        # Accept user input
        if prompt := st.chat_input("Ask me anything about the data or app..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = ""
                
                # Prepare messages for API call, ensuring system message is at the beginning
                messages_for_api = []
                system_message_content = next((msg["content"] for msg in st.session_state.messages if msg["role"] == "system"), None)
                if system_message_content:
                    messages_for_api.append({"role": "system", "content": system_message_content})
                
                # Add user and assistant messages (excluding the system message if already added)
                for msg in st.session_state.messages:
                    if msg["role"] != "system":
                        messages_for_api.append(msg)

                try:
                    for response in openai_client.chat.completions.create(
                        model="deepseek-v4-flash",
                        messages=messages_for_api,
                        stream=True,
                    ):
                        full_response += (response.choices[0].delta.content or "")
                        message_placeholder.markdown(full_response + "▌")
                    message_placeholder.markdown(full_response)
                except Exception as e:
                    st.error(f"Error communicating with DeepSeek API: {e}")
                    full_response = "I'm sorry, I couldn't get a response from the AI."
                    message_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
    else:
        st.warning("DeepSeek AI Workspace is not configured. Please ensure `DEEPSEEK_API_KEY` is set in your Streamlit secrets.")

