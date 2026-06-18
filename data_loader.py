import pandas as pd
import os
import streamlit as st
from st_files_connection import FilesConnection
from google.cloud import storage # Import storage for GCS bucket listing

@st.cache_data
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

@st.cache_data
def list_all_gcs_buckets():
    """
    Lists all Google Cloud Storage bucket names accessible by the service account.

    Returns:
        list: A list of bucket names (strings) or an empty list if an error occurs.
    """
    try:
        # On Streamlit Community Cloud there is no key file on disk, so build the
        # client from the service-account stored in st.secrets["connections"]["gcs"].
        # Locally / on a VM, fall back to Application Default Credentials.
        if "connections" in st.secrets and "gcs" in st.secrets["connections"]:
            client = storage.Client.from_service_account_info(
                dict(st.secrets["connections"]["gcs"])
            )
        else:
            client = storage.Client()
        buckets = client.list_buckets()
        return [bucket.name for bucket in buckets]
    except Exception as e:
        st.error(f"Error listing all GCS buckets: {e}. Check permissions and authentication.")
        return []

@st.cache_data
def list_gcs_bucket_files(bucket_name):
    """
    Lists files (and folders) in a specified Google Cloud Storage bucket.

    Args:
        bucket_name (str): The name of the GCS bucket (e.g., "my-bucket").

    Returns:
        list: A list of full GCS file paths (e.g., "gs://my-bucket/folder/file.csv")
              or an empty list if an error occurs or no files are found.
    """
    if not bucket_name:
        return []

    try:
        conn = st.connection('gcs', type=FilesConnection)
        # fs.ls returns a list of dictionaries with 'name', 'type', 'size'
        # 'name' here is the path relative to the bucket root (e.g., 'file.csv' or 'folder/file.csv')
        files_info = conn.fs.ls(f"gs://{bucket_name}/", detail=True)
        
        # Construct full GCS paths for files only
        file_paths = []
        for item in files_info:
            if item['type'] == 'file':
                file_paths.append(f"gs://{bucket_name}/{item['name']}")
        return file_paths
    except Exception as e:
        st.error(f"Error listing files in GCS bucket '{bucket_name}': {e}")
        return []


def get_data_profile(df):
    """
    Calculates summary metrics for a Pandas DataFrame.

    Args:
        df (pandas.DataFrame): The input DataFrame.

    Returns:
        dict: A dictionary containing data profile metrics.
    """
    if df is None or df.empty:
        return {
            "total_rows": 0,
            "total_columns": 0,
            "duplicate_rows": 0,
            "missing_values_percentage": {}
        }

    total_rows = df.shape[0]
    total_columns = df.shape[1]
    duplicate_rows = df.duplicated().sum()
    missing_values_percentage = (df.isnull().sum() / total_rows * 100).to_dict()

    return {
        "total_rows": total_rows,
        "total_columns": total_columns,
        "duplicate_rows": duplicate_rows,
        "missing_values_percentage": {col: f"{val:.2f}%" for col, val in missing_values_percentage.items() if val > 0}
    }

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
