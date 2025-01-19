# foodstory-eda/src/dashboard/db_utils.py

import sqlite3
import pandas as pd
import logging
from typing import List, Optional, Union
from pathlib import Path
import os

logger = logging.getLogger(__name__)

class DatabaseConnection:
    """Context manager for database connections."""
    
    def __init__(self, db_path: Union[str, Path]):
        self.db_path = Path(db_path)
        
    def __enter__(self) -> sqlite3.Connection:
        if not self.db_path.parent.exists():
            raise FileNotFoundError(f"Database directory does not exist: {self.db_path.parent}")
        
        self.conn = sqlite3.connect(self.db_path)
        return self.conn
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()

def create_indices(conn: sqlite3.Connection, table_name: str, 
                  columns: List[str]) -> None:
    """
    Create indices on specified columns.
    
    Args:
        conn: Database connection
        table_name: Name of the table
        columns: List of columns to index
    """
    cursor = conn.cursor()
    for column in columns:
        index_name = f"idx_{table_name}_{column}"
        try:
            cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS {index_name}
            ON {table_name} ({column})
            """)
        except sqlite3.Error as e:
            logger.error(f"Error creating index on {column}: {str(e)}")
            raise

def get_table_info(conn: sqlite3.Connection, table_name: str) -> pd.DataFrame:
    """
    Get information about table structure.
    
    Args:
        conn: Database connection
        table_name: Name of the table
        
    Returns:
        pd.DataFrame: Table information
    """
    return pd.read_sql_query(f"PRAGMA table_info({table_name})", conn)

def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    """
    Check if a table exists in the database.
    
    Args:
        conn: Database connection
        table_name: Name of the table to check
        
    Returns:
        bool: True if table exists
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?
    """, (table_name,))
    return cursor.fetchone() is not None

def safe_write_to_db(df: pd.DataFrame, db_path: Union[str, Path], 
                    table_name: str, if_exists: str = 'replace',
                    index: bool = False) -> None:
    """
    Safely write DataFrame to database with error handling.
    
    Args:
        df: DataFrame to write
        db_path: Path to database
        table_name: Name of the table
        if_exists: How to behave if table exists ('fail', 'replace', 'append')
        index: Whether to write index as a column
    """
    try:
        with DatabaseConnection(db_path) as conn:
            df.to_sql(table_name, conn, if_exists=if_exists, index=index)
            logger.info(f"Successfully wrote {len(df):,} rows to {table_name}")
    except Exception as e:
        logger.error(f"Error writing to database: {str(e)}")
        raise

def read_query(db_path: Union[str, Path], query: str, 
               params: Optional[tuple] = None) -> pd.DataFrame:
    """
    Execute SQL query and return results as DataFrame.
    
    Args:
        db_path: Path to database
        query: SQL query string
        params: Optional tuple of parameters for query
        
    Returns:
        pd.DataFrame: Query results
    """
    try:
        with DatabaseConnection(db_path) as conn:
            if params:
                return pd.read_sql_query(query, conn, params=params)
            return pd.read_sql_query(query, conn)
    except Exception as e:
        logger.error(f"Error executing query: {str(e)}")
        raise

def get_date_range(db_path: Union[str, Path], 
                  table_name: str, 
                  date_column: str = 'datetime') -> tuple:
    """
    Get the date range from a table.
    
    Args:
        db_path: Path to database
        table_name: Name of the table
        date_column: Name of the date column
        
    Returns:
        tuple: (min_date, max_date)
    """
    query = f"""
    SELECT MIN({date_column}), MAX({date_column})
    FROM {table_name}
    """
    try:
        with DatabaseConnection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            return cursor.fetchone()
    except Exception as e:
        logger.error(f"Error getting date range: {str(e)}")
        raise

def validate_db_path(db_path: Union[str, Path]) -> bool:
    """
    Validate database path and permissions.
    
    Args:
        db_path: Path to database
        
    Returns:
        bool: True if valid and accessible
    """
    db_path = Path(db_path)
    
    # Check if directory exists and is writable
    if not db_path.parent.exists():
        raise FileNotFoundError(f"Database directory does not exist: {db_path.parent}")
    
    if not os.access(db_path.parent, os.W_OK):
        raise PermissionError(f"No write permission for directory: {db_path.parent}")
    
    # If database exists, check if it's readable
    if db_path.exists() and not os.access(db_path, os.R_OK):
        raise PermissionError(f"No read permission for database: {db_path}")
    
    return True