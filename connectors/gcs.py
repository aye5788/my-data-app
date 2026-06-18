"""Google Cloud Storage connector."""
import os

import streamlit as st
from st_files_connection import FilesConnection
from google.cloud import storage

from .loaders import load_data_file

NAME = "Google Cloud Storage (GCS)"


@st.cache_data
def list_all_gcs_buckets():
    """List all GCS bucket names accessible by the service account."""
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
        return [bucket.name for bucket in client.list_buckets()]
    except Exception as e:
        st.error(f"Error listing all GCS buckets: {e}. Check permissions and authentication.")
        return []


@st.cache_data
def list_gcs_bucket_files(bucket_name):
    """List full ``gs://`` paths for the files in a bucket."""
    if not bucket_name:
        return []
    try:
        conn = st.connection("gcs", type=FilesConnection)
        files_info = conn.fs.ls(f"gs://{bucket_name}/", detail=True)
        return [
            f"gs://{bucket_name}/{item['name']}"
            for item in files_info
            if item["type"] == "file"
        ]
    except Exception as e:
        st.error(f"Error listing files in GCS bucket '{bucket_name}': {e}")
        return []


def load_from_gcs(bucket_path):
    """Load a ``gs://bucket/path`` object into a DataFrame."""
    try:
        conn = st.connection("gcs", type=FilesConnection)
        with conn.open(bucket_path, "rb") as file_object:
            file_name = os.path.basename(bucket_path)
            return load_data_file(file_object, file_name)
    except Exception as e:
        st.error(f"Error connecting to GCS or loading file from '{bucket_path}': {e}")
        return None


def render():
    """Draw the GCS bucket/file pickers and return a (df, asset_name) tuple."""
    available_buckets = list_all_gcs_buckets()
    if not available_buckets:
        st.sidebar.warning(
            "No GCS buckets found or accessible. Ensure your service account "
            "has appropriate permissions."
        )
        return None, ""

    selected_bucket_name = st.sidebar.selectbox(
        "Select GCS Bucket",
        options=[""] + sorted(available_buckets),
        key="gcs_bucket_selector",
    )

    if not selected_bucket_name:
        st.sidebar.info("Please select a GCS bucket.")
        return None, ""

    bucket_files = list_gcs_bucket_files(selected_bucket_name)
    st.subheader(f"Bucket File Explorer: `{selected_bucket_name}`")

    if not bucket_files:
        st.warning(
            f"No files found in bucket '{selected_bucket_name}' or an error occurred. "
            "Ensure you have read permissions."
        )
        return None, ""

    # Map display names (basename) back to full GCS paths.
    file_paths_map = {os.path.basename(f): f for f in bucket_files}
    display_file_names = sorted(file_paths_map.keys())

    selected_file_display_name = st.radio(
        "Select a file from the bucket to load",
        options=display_file_names,
        index=0 if display_file_names else None,
        key="gcs_file_radio_selector",
    )

    if not selected_file_display_name:
        st.info("Please select a file from the bucket explorer.")
        return None, ""

    selected_gcs_file_path = file_paths_map[selected_file_display_name]
    st.info(f"Attempting to load data from: `{selected_gcs_file_path}`")
    try:
        df = load_from_gcs(selected_gcs_file_path)
        if df is None:
            st.error(
                f"Could not load data from '{selected_gcs_file_path}'. "
                "Check path and permissions."
            )
        return df, selected_gcs_file_path
    except Exception as e:
        st.error(f"Error loading from GCS: {e}")
        return None, ""
