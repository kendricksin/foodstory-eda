# foodstory-eda/dashboard/utils/analysis.py

from typing import Dict, Tuple, List
import pandas as pd
from datetime import datetime, timedelta
import streamlit as st

def calculate_key_metrics(df: pd.DataFrame) -> Dict[str, float]:
    """
    Calculate key business metrics from sales data.
    
    Args:
        df: Sales DataFrame
        
    Returns:
        Dictionary of key metrics
    """
    days = (df['datetime'].max() - df['datetime'].min()).days + 1
    
    return {
        'total_revenue': df['summary_price'].sum(),
        'avg_daily_revenue': df['summary_price'].sum() / days,
        'total_transactions': len(df),
        'avg_daily_transactions': len(df) / days,
        'avg_transaction': df['summary_price'].mean(),
        'avg_group_size': df['seat_amount'].mean(),
        'total_customers': (df['seat_amount'] * len(df)).sum()
    }

def analyze_time_patterns(df: pd.DataFrame, 
                        period: str = 'hour') -> pd.DataFrame:
    """
    Analyze sales patterns over different time periods.
    
    Args:
        df: Sales DataFrame
        period: Time period for analysis ('hour', 'day', 'month')
        
    Returns:
        DataFrame with time-based analysis
    """
    if period == 'hour':
        group_col = df['datetime'].dt.hour
    elif period == 'day':
        group_col = df['datetime'].dt.dayofweek
    elif period == 'week':
        group_col = df['datetime'].dt.strftime('%Y-W%U')
    else:  # month
        group_col = df['datetime'].dt.strftime('%Y-%m')
    
    result = df.groupby(group_col).agg({
        'receipt_number': 'count',  # transaction count
        'summary_price': ['sum', 'mean'],  # revenue and average bill
        'seat_amount': 'mean'  # average group size
    }).round(2)
    
    return result

def analyze_menu_performance(df: pd.DataFrame, min_orders: int = 5) -> pd.DataFrame:
    """
    Analyze performance metrics for menu items with improved error handling.
    """
    try:
        # Ensure numeric columns
        df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0)
        df['revenue'] = pd.to_numeric(df['revenue'], errors='coerce').fillna(0)
        df['discount_amount'] = pd.to_numeric(df['discount_amount'], errors='coerce').fillna(0)
        
        # Group by menu items
        metrics = df.groupby(['menu_code', 'menu_name', 'category']).agg({
            'quantity': 'sum',
            'revenue': 'sum',
            'discount_amount': 'sum',
            'receipt_number': 'nunique'
        }).reset_index()
        
        # Filter by minimum orders
        metrics = metrics[metrics['receipt_number'] >= min_orders]
        
        # Calculate additional metrics
        metrics['avg_price'] = metrics['revenue'] / metrics['quantity'].where(metrics['quantity'] > 0, 1)
        total_revenue = metrics['revenue'].sum()
        metrics['revenue_share'] = (metrics['revenue'] / total_revenue * 100) if total_revenue > 0 else 0
        metrics['discount_rate'] = (metrics['discount_amount'] / metrics['revenue'] * 100).where(metrics['revenue'] > 0, 0)
        
        return metrics
    except Exception as e:
        st.error(f"Error in menu performance analysis: {str(e)}")
        return pd.DataFrame()

def analyze_category_trends(df: pd.DataFrame) -> pd.DataFrame:
    """
    Analyze sales trends by category.
    
    Args:
        df: Menu sales DataFrame
        
    Returns:
        DataFrame with category trends
    """
    monthly = df.groupby([
        df['datetime'].dt.strftime('%Y-%m'),
        'category'
    ]).agg({
        'quantity': 'sum',
        'revenue': 'sum',
        'receipt_number': 'nunique'
    }).reset_index()
    
    # Calculate growth rates
    monthly['prev_revenue'] = monthly.groupby('category')['revenue'].shift(1)
    monthly['revenue_growth'] = ((monthly['revenue'] - monthly['prev_revenue']) / 
                               monthly['prev_revenue'] * 100)
    
    return monthly

def create_combination_matrix(df, items_x, items_y):
    """
    Create a combination matrix for specified menu items.
    
    Args:
        df: Menu sales DataFrame
        items_x: List of menu items for x-axis
        items_y: List of menu items for y-axis
        
    Returns:
        DataFrame with combination matrix
    """
    import pandas as pd
    import numpy as np
    
    # Group orders by receipt
    order_groups = df.groupby('receipt_number')['menu_name'].agg(set).to_dict()
    
    # Initialize matrix
    matrix = pd.DataFrame(0, index=items_x, columns=items_y)
    
    # Count co-occurrences
    for items in order_groups.values():
        for item_x in items.intersection(items_x):
            for item_y in items.intersection(items_y):
                matrix.loc[item_x, item_y] += 1
    
    return matrix

def get_top_bottom_items(df, n=20):
    """
    Get top and bottom n menu items by revenue.
    
    Args:
        df: Menu sales DataFrame
        n: Number of items to return
        
    Returns:
        tuple: (top_n_items, bottom_n_items)
    """
    # Calculate total revenue per menu item
    item_revenue = df.groupby('menu_name')['revenue'].sum().sort_values(ascending=False)
    
    # Get top and bottom n items
    top_n = item_revenue.head(n).index.tolist()
    bottom_n = item_revenue.tail(n).index.tolist()
    
    return top_n, bottom_n

def analyze_menu_combinations(df):
    """
    Analyze menu combinations and create three matrices:
    - Top 20 vs Top 20
    - Top 20 vs Bottom 20
    - Bottom 20 vs Bottom 20
    
    Args:
        df: Menu sales DataFrame
        
    Returns:
        tuple: (top_vs_top, top_vs_bottom, bottom_vs_bottom)
    """
    # Get top and bottom items
    top_20, bottom_20 = get_top_bottom_items(df, n=20)
    
    # Create matrices
    top_vs_top = create_combination_matrix(df, top_20, top_20)
    top_vs_bottom = create_combination_matrix(df, top_20, bottom_20)
    bottom_vs_bottom = create_combination_matrix(df, bottom_20, bottom_20)
    
    return top_vs_top, top_vs_bottom, bottom_vs_bottom

def calculate_group_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate metrics by group size.
    
    Args:
        df: Sales DataFrame
        
    Returns:
        DataFrame with group size metrics
    """
    metrics = df.groupby('seat_amount').agg({
        'summary_price': ['count', 'sum', 'mean'],
        'receipt_number': 'nunique'
    })
    
    metrics.columns = ['visit_count', 'total_revenue', 'avg_bill', 'unique_receipts']
    metrics['revenue_per_person'] = metrics['avg_bill'] / metrics.index
    
    return metrics.reset_index()

def analyze_discounts(df: pd.DataFrame) -> pd.DataFrame:
    """
    Analyze discount patterns.
    
    Args:
        df: Menu sales DataFrame
        
    Returns:
        DataFrame with discount analysis
    """
    # Filter for items with discounts
    discount_data = df[df['discount_amount'] > 0]
    
    if not discount_data.empty:
        summary = discount_data.groupby(['category', 'menu_name']).agg({
            'discount_amount': ['sum', 'mean'],
            'revenue': 'sum',
            'quantity': 'sum'
        })
        
        # Add discount rate calculation
        summary['discount_rate'] = (summary[('discount_amount', 'sum')] / 
                                  summary['revenue'] * 100)
        
        return summary
    return pd.DataFrame()