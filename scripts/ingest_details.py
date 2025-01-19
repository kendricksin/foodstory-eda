# foodstory-eda/dashboard/scripts/ingest_details.py

import sys
import os
from pathlib import Path
import argparse
import logging
import pandas as pd
from typing import Optional, Dict, Any
from tqdm import tqdm
import sqlite3

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from dashboard.utils.data_cleaning import (
    clean_column_name, clean_monetary_columns,
    clean_datetime_cols, remove_duplicates,
    validate_dataframe
)
from dashboard.utils.db_utils import (
    DatabaseConnection, create_indices,
    validate_db_path, table_exists
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('ingest_details.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

def process_csv_file(file_path: Path) -> Optional[pd.DataFrame]:
    """
    Process a single CSV file of detailed bill data.
    
    Args:
        file_path: Path to CSV file
        
    Returns:
        Optional[pd.DataFrame]: Processed DataFrame or None if error
    """
    try:
        logger.info(f"Processing: {file_path.name}")
        
        # Try different encodings
        for encoding in ['utf-8', 'utf-8-sig', 'cp1252']:
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise ValueError(f"Could not read file with any encoding: {file_path}")
        
        # Validate required columns
        required_columns = {
            'Payment Date', 'Payment Time', 'Receipt Number',
            'Menu Code', 'Menu Name', 'Quantity',
            'Price per unit', 'Summary Price', 'Category'
        }
        validate_dataframe(df, required_columns)
        
        # Clean column names
        df.columns = [clean_column_name(col) for col in df.columns]
        
        # Convert datetime
        df['datetime'] = clean_datetime_cols(df)
        
        # Clean monetary columns
        df = clean_monetary_columns(df)
        
        # Convert quantity to numeric
        df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce')
        
        # Clean menu data
        df['menu_name'] = df['menu_name'].fillna('Unknown')
        df['category'] = df['category'].fillna('Uncategorized')
        df['menu_code'] = pd.to_numeric(df['menu_code'], errors='coerce')
        
        # Calculate additional metrics
        df['revenue'] = df['quantity'] * df['price_per_unit']
        df['discount_amount'] = df['revenue'] - df['summary_price']
        
        # Remove duplicates
        df = remove_duplicates(df, ['receipt_number', 'menu_code', 'menu_name', 'datetime'])
        
        logger.info(f"Successfully processed {len(df):,} records from {file_path.name}")
        return df
        
    except Exception as e:
        logger.error(f"Error processing {file_path}: {str(e)}")
        return None

def create_summary_tables(df: pd.DataFrame, conn: sqlite3.Connection) -> None:
    """
    Create summary tables from detailed sales data.
    
    Args:
        df: Processed sales detail DataFrame
        conn: Database connection
    """
    # Menu summary
    logger.info("Creating menu summary table...")
    menu_summary = df.groupby(['menu_code', 'menu_name', 'category']).agg({
        'quantity': 'sum',
        'revenue': 'sum',
        'discount_amount': 'sum',
        'receipt_number': 'count'
    }).reset_index()
    
    menu_summary.columns = [
        'menu_code', 'menu_name', 'category',
        'total_quantity', 'total_revenue',
        'total_discount', 'times_ordered'
    ]
    
    menu_summary.to_sql('menu_summary', conn, if_exists='replace', index=False)
    
    # Monthly summary
    logger.info("Creating monthly summary table...")
    monthly_summary = df.groupby([
        df['datetime'].dt.strftime('%Y-%m'),
        'menu_code',
        'menu_name',
        'category'
    ]).agg({
        'quantity': 'sum',
        'revenue': 'sum',
        'discount_amount': 'sum',
        'receipt_number': 'nunique'
    }).reset_index()
    
    monthly_summary.columns = [
        'year_month', 'menu_code', 'menu_name', 'category',
        'quantity', 'revenue', 'discount_amount', 'orders'
    ]
    
    monthly_summary.to_sql('monthly_summary', conn, if_exists='replace', index=False)

def create_indices(conn: sqlite3.Connection) -> None:
    """Create all necessary indices."""
    try:
        cursor = conn.cursor()
        
        # Sales detail indices
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_detail_datetime ON sales_detail(datetime)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_detail_receipt ON sales_detail(receipt_number)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_detail_menu ON sales_detail(menu_code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_detail_category ON sales_detail(category)')
        
        # Menu summary indices
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_menu_code ON menu_summary(menu_code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_category_summary ON menu_summary(category)')
        
        # Monthly summary indices
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_year_month ON monthly_summary(year_month)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_menu_monthly ON monthly_summary(menu_code)')
        
        conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Error creating index: {str(e)}")
        raise

def load_and_clean_data(path: Path) -> pd.DataFrame:
    """
    Load and clean detailed bill data from file or directory.
    
    Args:
        path: Path to CSV file or directory
        
    Returns:
        pd.DataFrame: Cleaned and combined data
    """
    if path.is_dir():
        csv_files = list(path.glob('*.csv'))
        if not csv_files:
            raise ValueError(f"No CSV files found in directory: {path}")
            
        logger.info(f"Found {len(csv_files)} CSV files")
        all_data = []
        
        for file in tqdm(csv_files, desc="Processing files"):
            df = process_csv_file(file)
            if df is not None:
                all_data.append(df)
        
        if not all_data:
            raise ValueError("No valid data was processed from any files")
            
        df = pd.concat(all_data, ignore_index=True)
        logger.info(f"Total records loaded: {len(df):,}")
        
    else:
        df = process_csv_file(path)
        if df is None:
            raise ValueError(f"Failed to process file: {path}")
    
    return df

def main():
    parser = argparse.ArgumentParser(
        description='Load detailed bill data into SQLite database'
    )
    parser.add_argument('path', type=Path,
                       help='Path to CSV file or directory')
    parser.add_argument('--db', type=Path,
                       default=Path('database/restaurant_sales.db'),
                       help='Path to SQLite database')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Validate inputs
        if not args.path.exists():
            raise FileNotFoundError(f"Input path does not exist: {args.path}")
        
        if not args.db.exists():
            raise FileNotFoundError(
                f"Database not found: {args.db}\n"
                "Please run ingest_bills.py first to create the database."
            )
        
        validate_db_path(args.db)
        
        # Process data
        df = load_and_clean_data(args.path)
        
        # Update database
        with DatabaseConnection(args.db) as conn:
            logger.info(f"Writing {len(df):,} records to database")
            df.to_sql('sales_detail', conn, if_exists='replace', index=False)
            
            # Create summary tables
            create_summary_tables(df, conn)
            
            # Create indices
            create_indices(conn)
            
            # Log summary statistics
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(DISTINCT menu_code) FROM sales_detail')
            unique_items = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(DISTINCT category) FROM sales_detail')
            unique_categories = cursor.fetchone()[0]
            
            cursor.execute('SELECT MIN(datetime), MAX(datetime) FROM sales_detail')
            date_range = cursor.fetchone()
        
        logger.info("\nIngestion complete!")
        logger.info(f"Unique menu items: {unique_items:,}")
        logger.info(f"Menu categories: {unique_categories}")
        logger.info(f"Date range: {date_range[0]} to {date_range[1]}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        if args.verbose:
            logger.exception("Full traceback:")
        return 1

if __name__ == "__main__":
    sys.exit(main())