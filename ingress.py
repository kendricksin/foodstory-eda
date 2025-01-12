import pandas as pd
import sqlite3
from pathlib import Path
import argparse
from datetime import datetime
import os
import glob

def clean_column_name(name):
    """Clean column names to be SQLite friendly."""
    return name.lower().replace(' ', '_').replace('-', '_')

def load_and_clean_data(path):
    """Load and clean the restaurant sales data."""
    all_data = []
    
    try:
        if os.path.isdir(path):
            # If path is a directory, process all CSV files
            if not os.access(path, os.R_OK):
                raise PermissionError(f"No read permission for directory: {path}")
                
            csv_files = glob.glob(os.path.join(path, '*.csv'))
            if not csv_files:
                raise ValueError(f"No CSV files found in directory: {path}")
            
            print(f"Found {len(csv_files)} CSV files")
            for file in csv_files:
                if os.access(file, os.R_OK):
                    print(f"Processing: {os.path.basename(file)}")
                    df = pd.read_csv(file)
                    all_data.append(df)
                else:
                    print(f"Warning: No read permission for {file}, skipping")
            
            if not all_data:
                raise PermissionError("No readable CSV files found")
                
            df = pd.concat(all_data, ignore_index=True)
            print(f"Total records loaded: {len(df):,}")
        else:
            # If path is a file, process single file
            if not os.access(path, os.R_OK):
                raise PermissionError(f"No read permission for file: {path}")
                
            print(f"Processing single file: {path}")
            df = pd.read_csv(path)
            print(f"Records loaded: {len(df):,}")
    
        # Convert Payment Date and Time columns to datetime
        df['datetime'] = pd.to_datetime(df['Payment Date'] + ' ' + df['Payment Time'], 
                                      format='%d/%m/%Y %H:%M', 
                                      dayfirst=True)
        
        # Clean monetary columns
        monetary_columns = ['Summary Price', 'Subtotal Bill Discount', 
                          'Subtotal Summary Price - Discount By Item',
                          'Ex. VAT', 'Before Vat Subtotal + Service charge']
        
        for col in monetary_columns:
            df[col] = df[col].str.replace('฿', '').str.replace(',', '').astype(float)
        
        # Convert Seat Amount to numeric
        df['Seat Amount'] = pd.to_numeric(df['Seat Amount'], errors='coerce')
        
        # Clean column names
        df.columns = [clean_column_name(col) for col in df.columns]
        
        # Remove duplicates
        initial_rows = len(df)
        df = df.drop_duplicates(subset=['receipt_number'])
        if initial_rows > len(df):
            print(f"Removed {initial_rows - len(df):,} duplicate records")
        
        return df
        
    except PermissionError as e:
        raise PermissionError(f"Permission error: {str(e)}")
    except Exception as e:
        raise Exception(f"Error processing data: {str(e)}")

def create_database(df, db_path):
    """Create SQLite database and load the data."""
    # Check if we have write permission in the target directory
    db_dir = os.path.dirname(os.path.abspath(db_path)) or '.'
    if not os.access(db_dir, os.W_OK):
        raise PermissionError(f"No write permission in directory: {db_dir}")
    
    print(f"Creating database at: {db_path}")
    
    # Create database connection
    conn = sqlite3.connect(db_path)
    
    try:
        # Create the sales table
        df.to_sql('sales', conn, if_exists='replace', index=False)
        
        # Create some useful indices
        cursor = conn.cursor()
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_datetime ON sales(datetime)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_receipt ON sales(receipt_number)')
        
        # Get some basic stats
        cursor.execute('SELECT COUNT(*) FROM sales')
        total_rows = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT receipt_number) FROM sales')
        unique_receipts = cursor.fetchone()[0]
        
        cursor.execute('SELECT MIN(datetime), MAX(datetime) FROM sales')
        date_range = cursor.fetchone()
        
        print("\nDatabase creation successful!")
        print(f"Total rows: {total_rows:,}")
        print(f"Unique receipts: {unique_receipts:,}")
        print(f"Date range: {date_range[0]} to {date_range[1]}")
        
    finally:
        conn.close()

def main():
    parser = argparse.ArgumentParser(description='Load restaurant sales data into SQLite')
    parser.add_argument('path', help='Path to CSV file or directory containing CSV files')
    parser.add_argument('--db', default='restaurant_sales.db',
                       help='Path for the output SQLite database (default: restaurant_sales.db)')
    
    args = parser.parse_args()
    
    # Validate input path exists
    if not os.path.exists(args.path):
        print(f"Error: Path does not exist: {args.path}")
        return 1
    
    try:
        # Load and clean the data
        df = load_and_clean_data(args.path)
        
        # Create the database
        create_database(df, args.db)
        
        return 0
        
    except PermissionError as e:
        print(f"Permission error: {str(e)}")
        print("\nTry running with appropriate permissions:")
        print("- Make sure you have read access to the CSV file(s)")
        print("- Make sure you have write access to the database directory")
        print("- On Unix-like systems, you might need to use 'sudo' or adjust file permissions")
        return 1
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())