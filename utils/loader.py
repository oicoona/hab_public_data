"""
Data loading utilities with encoding fallback and caching.
"""
import io
import os
import pandas as pd
import streamlit as st
from typing import BinaryIO


def read_csv_safe(file_path: str) -> pd.DataFrame:
    """
    Read CSV file with automatic encoding detection (UTF-8 → UTF-8-SIG → CP949).

    Parameters:
        file_path (str): Absolute or relative path to CSV file

    Returns:
        pd.DataFrame: Loaded dataset

    Raises:
        FileNotFoundError: If file_path does not exist
        ValueError: If file cannot be decoded with any supported encoding
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"CSV file not found: {file_path}")

    encodings = ['utf-8', 'utf-8-sig', 'cp949']
    last_error = None

    for enc in encodings:
        try:
            df = pd.read_csv(file_path, encoding=enc)
            return df
        except UnicodeDecodeError as e:
            last_error = e
            continue

    raise ValueError(
        f"Could not decode {file_path} with any supported encoding (tried: {', '.join(encodings)}). "
        f"Last error: {last_error}"
    )


def read_uploaded_csv(uploaded_file: BinaryIO) -> pd.DataFrame:
    """
    Read uploaded CSV file with automatic encoding detection.

    Parameters:
        uploaded_file: Streamlit UploadedFile object (file-like binary object)

    Returns:
        pd.DataFrame: Loaded dataset

    Raises:
        ValueError: If file cannot be decoded with any supported encoding
    """
    encodings = ['utf-8', 'utf-8-sig', 'cp949']
    last_error = None

    # Read file content once
    content = uploaded_file.read()

    for enc in encodings:
        try:
            df = pd.read_csv(io.BytesIO(content), encoding=enc)
            return df
        except UnicodeDecodeError as e:
            last_error = e
            continue

    raise ValueError(
        f"Could not decode uploaded file with any supported encoding (tried: {', '.join(encodings)}). "
        f"Last error: {last_error}"
    )


def load_dataset_from_session(dataset_name: str) -> pd.DataFrame | None:
    """
    Load dataset from session_state.

    Parameters:
        dataset_name (str): Dataset key (e.g., 'cctv', 'lights', etc.)

    Returns:
        pd.DataFrame | None: Dataset if uploaded, None otherwise
    """
    if 'datasets' not in st.session_state:
        return None
    return st.session_state.datasets.get(dataset_name)


@st.cache_data
def load_dataset(dataset_name: str) -> pd.DataFrame:
    """
    Load predefined dataset by name with caching and date parsing.

    Parameters:
        dataset_name (str): One of ['cctv', 'lights', 'zones', 'parking', 'accident', 'train', 'test']

    Returns:
        pd.DataFrame: Cached dataset with parsed date columns

    Raises:
        ValueError: If dataset_name not recognized
        FileNotFoundError: If corresponding CSV file missing
    """
    # Dataset name to file path mapping
    dataset_map = {
        'cctv': 'data/대구 CCTV 정보.csv',
        'lights': 'data/대구 보안등 정보.csv',
        'zones': 'data/대구 어린이 보호 구역 정보.csv',
        'parking': 'data/대구 주차장 정보.csv',
        'accident': 'data/countrywide_accident.csv',
        'train': 'data/train.csv',
        'test': 'data/test.csv'
    }

    # Dataset-specific date columns mapping
    date_columns = {
        'cctv': ['설치연도'],
        'lights': ['설치연도'],
        'accident': ['사고일시'],
        'train': ['사고일시'],
        'test': ['사고일시']
    }

    if dataset_name not in dataset_map:
        valid_names = ', '.join(dataset_map.keys())
        raise ValueError(
            f"Unknown dataset name: '{dataset_name}'. "
            f"Valid options: {valid_names}"
        )

    file_path = dataset_map[dataset_name]
    df = read_csv_safe(file_path)

    # Convert date columns to datetime
    if dataset_name in date_columns:
        for col in date_columns[dataset_name]:
            if col in df.columns:
                try:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                except Exception as e:
                    print(f"Warning: Could not convert {col} to datetime: {e}")

    return df


def get_dataset_info(df: pd.DataFrame) -> dict:
    """
    Generate comprehensive dataset summary statistics.

    Parameters:
        df (pd.DataFrame): Input dataset

    Returns:
        dict: Summary statistics with keys:
            - row_count (int): Number of rows
            - column_count (int): Number of columns
            - dtypes (dict): {col_name: dtype_str}
            - missing_ratios (dict): {col_name: float 0-1}
            - numeric_summary (pd.DataFrame): describe() for numeric cols
            - categorical_summary (dict): {col_name: value_counts dict}
    """
    # Handle empty DataFrame
    if df.empty:
        return {
            'row_count': 0,
            'column_count': 0,
            'dtypes': {},
            'missing_ratios': {},
            'numeric_summary': pd.DataFrame(),
            'categorical_summary': {}
        }

    # Basic info
    row_count = len(df)
    column_count = len(df.columns)

    # Data types
    dtypes = {col: str(dtype) for col, dtype in df.dtypes.items()}

    # Missing value ratios
    missing_ratios = {col: df[col].isnull().sum() / row_count for col in df.columns}

    # Numeric column summary
    numeric_cols = df.select_dtypes(include=['number']).columns
    if len(numeric_cols) > 0:
        numeric_summary = df[numeric_cols].describe()
    else:
        numeric_summary = pd.DataFrame()

    # Categorical column summary
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns
    categorical_summary = {}
    for col in categorical_cols:
        value_counts = df[col].value_counts().head(20)  # Top 20 values
        categorical_summary[col] = value_counts.to_dict()

    return {
        'row_count': row_count,
        'column_count': column_count,
        'dtypes': dtypes,
        'missing_ratios': missing_ratios,
        'numeric_summary': numeric_summary,
        'categorical_summary': categorical_summary
    }
