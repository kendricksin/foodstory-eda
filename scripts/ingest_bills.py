# foodstory-eda/dashboard/scripts/ingest_bills.py

import sys
import os
from pathlib import Path
import argparse
import logging
import pandas as pd
from glob import glob
from typing import Optional
import sqlite3

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from dashboard.utils.data_cleaning import (
    clean_column_name, clean_monetary_columns,
    clean_datetime_cols, remove_duplicates,
    clean_group_size, validate_dataframe
)
from dashboard.utils.db_utils import (
    DatabaseConnection, create_indices,
    validate_db_path, safe_write_to_db
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('ingest_bills.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

def process_csv_file(file_path: Path) -> Optional[pd.DataFrame]:
    """
    Process a single CSV file of bill data.
    
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
            'Summary Price', 'Seat Amount'
        }
        validate_dataframe(df, required_columns)
        
        # Clean column names
        df.columns = [clean_column_name(col) for col in df.columns]
        
        # Convert datetime
        df['datetime'] = clean_datetime_cols(df)
        
        # Clean monetary columns
        df = clean_monetary_columns(df)
        
        # Clean group size
        df = clean_group_size(df)
        
        # Remove duplicates
        df = remove_duplicates(df)
        
        logger.info(f"Successfully processed {len(df):,} records from {file_path.name}")
        return df
        
    except Exception as e:
        logger.error(f"Error processing {file_path}: {str(e)}")
        return None

def load_and_clean_data(path: Path) -> pd.DataFrame:
    """
    Load and clean bill data from file or directory.
    
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
        
        for file in csv_files:
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

def create_sales_indices(conn: sqlite3.Connection) -> None:
    """Create indices for the sales table."""
    try:
        cursor = conn.cursor()
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sales_datetime ON sales(datetime)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sales_receipt ON sales(receipt_number)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sales_payment ON sales(payment_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sales_seats ON sales(seat_amount)')
        conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Error creating index: {str(e)}")
        raise

def main():
    parser = argparse.ArgumentParser(description='Load restaurant bill data into SQLite')
    parser.add_argument('path', type=Path, help='Path to CSV file or directory')
    parser.add_argument('--db', type=Path, default=Path('database/restaurant_sales.db'),
                       help='Path for the SQLite database')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Validate inputs
        if not args.path.exists():
            raise FileNotFoundError(f"Input path does not exist: {args.path}")
            
        validate_db_path(args.db)
        
        # Process data
        df = load_and_clean_data(args.path)
        
        # Ensure database directory exists
        args.db.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to database
        with DatabaseConnection(args.db) as conn:
            logger.info(f"Writing {len(df):,} records to database")
            df.to_sql('sales', conn, if_exists='replace', index=False)
            
            # Create indices
            create_sales_indices(conn)
            
            # Log summary statistics
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(DISTINCT receipt_number) FROM sales')
            unique_receipts = cursor.fetchone()[0]
            
            cursor.execute('SELECT MIN(datetime), MAX(datetime) FROM sales')
            date_range = cursor.fetchone()
            
        logger.info("\nIngestion complete!")
        logger.info(f"Total rows: {len(df):,}")
        logger.info(f"Unique receipts: {unique_receipts:,}")
        logger.info(f"Date range: {date_range[0]} to {date_range[1]}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        if args.verbose:
            logger.exception("Full traceback:")
        return 1

if __name__ == "__main__":
    sys.exit(main())