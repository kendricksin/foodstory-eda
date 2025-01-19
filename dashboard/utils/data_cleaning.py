# foodstory-eda/src/utils/data_cleaning.py
"""
Utility functions for cleaning and preprocessing restaurant sales data.
"""
import pandas as pd
from typing import Union, List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def clean_column_name(name: str) -> str:
    """
    Clean column names to be SQLite and Python friendly.
    
    Args:
        name (str): Original column name
        
    Returns:
        str: Cleaned column name
    """
    return (name.lower()
            .replace(' ', '_')
            .replace('-', '_')
            .replace('.', '')
            .replace('(', '')
            .replace(')', '')
            .strip())

def clean_monetary_value(value: Union[str, float]) -> float:
    """
    Clean monetary values by removing currency symbols and converting to float.
    
    Args:
        value: Value to clean, can be string with currency symbol or float
        
    Returns:
        float: Cleaned monetary value
    """
    if pd.isna(value):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    return float(str(value).replace('฿', '').replace(',', '').strip() or 0)

def clean_datetime_cols(df: pd.DataFrame, date_col: str = 'payment_date', 
                       time_col: str = 'payment_time') -> pd.Series:
    """
    Convert separate date and time columns to datetime.
    
    Args:
        df: DataFrame containing the columns
        date_col: Name of the date column
        time_col: Name of the time column
        
    Returns:
        pd.Series: Combined datetime series
    """
    try:
        return pd.to_datetime(
            df[date_col] + ' ' + df[time_col],
            format='%d/%m/%Y %H:%M',
            dayfirst=True
        )
    except Exception as e:
        logger.error(f"Error converting datetime: {str(e)}")
        raise

def clean_monetary_columns(df: pd.DataFrame, 
                         columns: List[str] = None) -> pd.DataFrame:
    """
    Clean multiple monetary columns in a DataFrame.
    
    Args:
        df: Input DataFrame
        columns: List of column names to clean. If None, uses default set.
        
    Returns:
        pd.DataFrame: DataFrame with cleaned monetary columns
    """
    if columns is None:
        columns = [
            'summary_price',
            'subtotal_bill_discount',
            'subtotal_summary_price_discount_by_item',
            'ex_vat',
            'before_vat_subtotal_service_charge',
            'price_per_unit',
            'discounted_price'
        ]
    
    df_cleaned = df.copy()
    for col in columns:
        if col in df_cleaned.columns:
            df_cleaned[col] = df_cleaned[col].apply(clean_monetary_value)
    
    return df_cleaned

def validate_dataframe(df: pd.DataFrame, required_columns: List[str]) -> bool:
    """
    Validate that DataFrame has required columns.
    
    Args:
        df: DataFrame to validate
        required_columns: List of required column names
        
    Returns:
        bool: True if valid, raises ValueError if not
    """
    missing_cols = set(required_columns) - set(df.columns)
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    return True

def remove_duplicates(df: pd.DataFrame, subset: List[str] = None) -> pd.DataFrame:
    """
    Remove duplicate rows from DataFrame.
    
    Args:
        df: Input DataFrame
        subset: Columns to consider for duplicates. If None, uses receipt_number
        
    Returns:
        pd.DataFrame: DataFrame with duplicates removed
    """
    if subset is None:
        subset = ['receipt_number']
    
    initial_rows = len(df)
    df_cleaned = df.drop_duplicates(subset=subset)
    
    if len(df_cleaned) < initial_rows:
        logger.info(f"Removed {initial_rows - len(df_cleaned):,} duplicate records")
    
    return df_cleaned

def clean_group_size(df: pd.DataFrame, col: str = 'seat_amount') -> pd.DataFrame:
    """
    Clean and validate group size data.
    
    Args:
        df: Input DataFrame
        col: Column name for group size
        
    Returns:
        pd.DataFrame: DataFrame with cleaned group size
    """
    df_cleaned = df.copy()
    df_cleaned[col] = pd.to_numeric(df_cleaned[col], errors='coerce')
    
    # Remove invalid group sizes (e.g., negative or unreasonably large)
    mask = (df_cleaned[col] > 0) & (df_cleaned[col] <= 50)  # Adjust max as needed
    invalid_count = (~mask).sum()
    
    if invalid_count > 0:
        logger.warning(f"Found {invalid_count} invalid group sizes")
        df_cleaned.loc[~mask, col] = None
    
    return df_cleaned