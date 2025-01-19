"""
Script to initialize the SQLite database schema.
"""
import sqlite3
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def get_db_path() -> Path:
    """Get the database path."""
    return Path(__file__).parent / 'restaurant_sales.db'

def init_db():
    """Initialize the database with required schema."""
    db_path = get_db_path()
    
    # Create database directory if it doesn't exist
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Initializing database at: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create sales table
        logger.info("Creating sales table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            datetime TIMESTAMP NOT NULL,
            receipt_number TEXT PRIMARY KEY,
            payment_type TEXT,
            table_number TEXT,
            seat_amount INTEGER,
            summary_price REAL,
            subtotal_bill_discount REAL,
            subtotal_summary_price_discount_by_item REAL,
            ex_vat REAL,
            before_vat_subtotal_service_charge REAL,
            customer_name TEXT,
            phone_number TEXT,
            remark TEXT,
            bill_open_by TEXT,
            bill_close_by TEXT,
            branch TEXT
        )
        """)
        
        # Create sales_detail table
        logger.info("Creating sales_detail table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales_detail (
            datetime TIMESTAMP NOT NULL,
            receipt_number TEXT,
            menu_code INTEGER,
            menu_name TEXT,
            category TEXT,
            quantity REAL,
            price_per_unit REAL,
            summary_price REAL,
            revenue REAL,
            discount_amount REAL,
            order_type TEXT,
            channel TEXT,
            table_number TEXT,
            bill_open_by TEXT,
            bill_close_by TEXT,
            branch TEXT,
            FOREIGN KEY (receipt_number) REFERENCES sales(receipt_number)
        )
        """)
        
        # Create menu_summary table
        logger.info("Creating menu_summary table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS menu_summary (
            menu_code INTEGER PRIMARY KEY,
            menu_name TEXT NOT NULL,
            category TEXT,
            total_quantity REAL,
            total_revenue REAL,
            total_discount REAL,
            times_ordered INTEGER
        )
        """)
        
        # Create monthly_summary table
        logger.info("Creating monthly_summary table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS monthly_summary (
            year_month TEXT,
            menu_code INTEGER,
            menu_name TEXT,
            category TEXT,
            quantity REAL,
            revenue REAL,
            discount_amount REAL,
            orders INTEGER,
            PRIMARY KEY (year_month, menu_code),
            FOREIGN KEY (menu_code) REFERENCES menu_summary(menu_code)
        )
        """)
        
        # Create indices
        logger.info("Creating indices...")
        
        # Sales indices
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sales_datetime ON sales(datetime)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sales_payment_type ON sales(payment_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sales_branch ON sales(branch)")
        
        # Sales detail indices
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_detail_datetime ON sales_detail(datetime)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_detail_receipt ON sales_detail(receipt_number)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_detail_menu ON sales_detail(menu_code)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_detail_category ON sales_detail(category)")
        
        # Menu summary indices
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_menu_category ON menu_summary(category)")
        
        # Monthly summary indices
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_monthly_year_month ON monthly_summary(year_month)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_monthly_category ON monthly_summary(category)")
        
        conn.commit()
        logger.info("Database initialization completed successfully!")
        
    except sqlite3.Error as e:
        logger.error(f"SQLite error: {str(e)}")
        raise
        
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise
        
    finally:
        conn.close()

def check_db_exists() -> bool:
    """Check if database exists and has required tables."""
    db_path = get_db_path()
    if not db_path.exists():
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check for required tables
        cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name IN ('sales', 'sales_detail', 'menu_summary', 'monthly_summary')
        """)
        
        tables = cursor.fetchall()
        return len(tables) == 4
        
    except sqlite3.Error:
        return False
        
    finally:
        conn.close()

def main():
    """Main entry point for database initialization."""
    if check_db_exists():
        logger.info("Database already exists and has required tables.")
        user_input = input("Do you want to reinitialize the database? (y/N): ")
        if user_input.lower() != 'y':
            logger.info("Database initialization skipped.")
            return
    
    try:
        init_db()
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        return 1
    return 0

if __name__ == "__main__":
    exit(main())