-- Menu summary table schema
CREATE TABLE IF NOT EXISTS menu_summary (
    menu_code INTEGER PRIMARY KEY,
    menu_name TEXT NOT NULL,
    category TEXT,
    total_quantity REAL,
    total_revenue REAL,
    total_discount REAL,
    times_ordered INTEGER
);

-- Create indices for menu_summary table
CREATE INDEX IF NOT EXISTS idx_menu_category ON menu_summary(category);

-- Monthly summary table schema
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
);

-- Create indices for monthly_summary table
CREATE INDEX IF NOT EXISTS idx_monthly_year_month ON monthly_summary(year_month);
CREATE INDEX IF NOT EXISTS idx_monthly_category ON monthly_summary(category);