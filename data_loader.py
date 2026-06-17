import pandas as pd
import os
import streamlit as st
from st_files_connection import FilesConnection

def load_data_file(file_object, file_name):
    """
    Loads data from a file object into a Pandas DataFrame based on file extension.

    Args:
        file_object: A file-like object (e.g., uploaded by Streamlit).
        file_name (str): The name of the file, including its extension.

    Returns:
        pandas.DataFrame or None: A Pandas DataFrame if successful, None otherwise.
    """
    _, file_extension = os.path.splitext(file_name)
    file_extension = file_extension.lower()

    try:
        if file_extension == '.csv':
            return pd.read_csv(file_object)
        elif file_extension == '.xlsx':
            return pd.read_excel(file_object)
        elif file_extension == '.json':
            return pd.read_json(file_object)
        elif file_extension == '.parquet':
            return pd.read_parquet(file_object)
        else:
            return None # Indicate unsupported file type
    except Exception as e:
        # Re-raise or log the specific error for detailed debugging if needed.
        # For a user-friendly message, we'll let the caller handle the display.
        print(f"Error loading file of type {file_extension}: {e}")
        return None

def load_from_gcs(bucket_path):
    """
    Loads data from a Google Cloud Storage bucket path into a Pandas DataFrame.

    Args:
        bucket_path (str): The full path to the file in GCS (e.g., "gs://my-bucket/data/file.csv").

    Returns:
        pandas.DataFrame or None: A Pandas DataFrame if successful, None otherwise.
    """
    try:
        # Establish GCS connection using st.connection
        # Streamlit handles credentials via st.secrets or environment variables
        # The type='st_files_connection.FilesConnection' requires the package to be installed.
        conn = st.connection('gcs', type=FilesConnection)

        # Open the file from GCS as a file-like object
        with conn.open(bucket_path, 'rb') as file_object:
            # Extract file name from bucket_path
            file_name = os.path.basename(bucket_path)
            return load_data_file(file_object, file_name)

    except Exception as e:
        st.error(f"Error connecting to GCS or loading file from '{bucket_path}': {e}")
        return None
