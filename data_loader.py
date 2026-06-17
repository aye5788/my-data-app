import pandas as pd
import os

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
