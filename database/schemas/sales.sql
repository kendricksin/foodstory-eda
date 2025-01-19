-- Sales table schema
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
);

-- Create indices for sales table
CREATE INDEX IF NOT EXISTS idx_sales_datetime ON sales(datetime);
CREATE INDEX IF NOT EXISTS idx_sales_payment_type ON sales(payment_type);
CREATE INDEX IF NOT EXISTS idx_sales_branch ON sales(branch);

-- Sales detail table schema
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
);

-- Create indices for sales_detail table
CREATE INDEX IF NOT EXISTS idx_detail_datetime ON sales_detail(datetime);
CREATE INDEX IF NOT EXISTS idx_detail_receipt ON sales_detail(receipt_number);
CREATE INDEX IF NOT EXISTS idx_detail_menu ON sales_detail(menu_code);
CREATE INDEX IF NOT EXISTS idx_detail_category ON sales_detail(category);