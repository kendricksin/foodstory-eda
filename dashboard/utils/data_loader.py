"""
Utility functions for loading and preprocessing data from SQLite database.
"""
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
from typing import Tuple, Dict, Optional
from pathlib import Path

def get_db_path() -> Path:
    """Get the path to the SQLite database."""
    return Path(__file__).parent.parent.parent / 'database' / 'restaurant_sales.db'

def load_sales_data(start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None) -> pd.DataFrame:
    """
    Load sales data from database with optional date filtering.
    
    Args:
        start_date: Optional start date for filtering
        end_date: Optional end date for filtering
        
    Returns:
        DataFrame with sales data
    """
    query = """
    SELECT *
    FROM sales
    WHERE 1=1
    """
    
    params = []
    if start_date:
        query += " AND datetime >= ?"
        params.append(start_date)
    if end_date:
        query += " AND datetime <= ?"
        params.append(end_date)
    
    with sqlite3.connect(get_db_path()) as conn:
        df = pd.read_sql_query(query, conn, params=params)
        df['datetime'] = pd.to_datetime(df['datetime'])
        
    return df

def load_menu_data(start_date: Optional[datetime] = None,
                  end_date: Optional[datetime] = None) -> pd.DataFrame:
    """
    Load detailed menu sales data from database.
    
    Args:
        start_date: Optional start date for filtering
        end_date: Optional end date for filtering
        
    Returns:
        DataFrame with menu sales data
    """
    query = """
    SELECT *
    FROM sales_detail
    WHERE 1=1
    """
    
    params = []
    if start_date:
        query += " AND datetime >= ?"
        params.append(start_date)
    if end_date:
        query += " AND datetime <= ?"
        params.append(end_date)
    
    with sqlite3.connect(get_db_path()) as conn:
        df = pd.read_sql_query(query, conn, params=params)
        df['datetime'] = pd.to_datetime(df['datetime'])
        
    return df

def load_category_summary() -> pd.DataFrame:
    """
    Load category-level summary data.
    
    Returns:
        DataFrame with category summary statistics
    """
    query = """
    SELECT 
        category,
        COUNT(DISTINCT menu_code) as unique_items,
        SUM(total_quantity) as total_quantity,
        SUM(total_revenue) as total_revenue,
        SUM(total_discount) as total_discount
    FROM menu_summary
    GROUP BY category
    """
    
    with sqlite3.connect(get_db_path()) as conn:
        return pd.read_sql_query(query, conn)

def load_monthly_trends(category: Optional[str] = None) -> pd.DataFrame:
    """
    Load monthly sales trends with optional category filtering.
    
    Args:
        category: Optional category to filter by
        
    Returns:
        DataFrame with monthly trends
    """
    query = """
    SELECT 
        year_month,
        SUM(quantity) as total_quantity,
        SUM(revenue) as total_revenue,
        COUNT(DISTINCT menu_code) as unique_items
    FROM monthly_summary
    """
    
    params = []
    if category:
        query += " WHERE category = ?"
        params.append(category)
    
    query += " GROUP BY year_month ORDER BY year_month"
    
    with sqlite3.connect(get_db_path()) as conn:
        return pd.read_sql_query(query, conn, params=params)

def get_date_range() -> Tuple[datetime, datetime]:
    """
    Get the full date range available in the database.
    
    Returns:
        Tuple of (min_date, max_date)
    """
    query = """
    SELECT MIN(datetime), MAX(datetime)
    FROM sales
    """
    
    with sqlite3.connect(get_db_path()) as conn:
        result = pd.read_sql_query(query, conn)
        return (pd.to_datetime(result.iloc[0, 0]),
                pd.to_datetime(result.iloc[0, 1]))

def get_categories() -> list:
    """
    Get list of all menu categories.
    
    Returns:
        List of category names
    """
    query = "SELECT DISTINCT category FROM menu_summary ORDER BY category"
    
    with sqlite3.connect(get_db_path()) as conn:
        return pd.read_sql_query(query, conn)['category'].tolist()