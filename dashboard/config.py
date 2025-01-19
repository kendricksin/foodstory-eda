"""
Configuration settings for the dashboard application.
"""
from pathlib import Path

# Database settings
DB_PATH = Path(__file__).parent.parent / 'database' / 'restaurant_sales.db'

# Plot settings
COLORS = {
    'primary': '#2E86C1',    # Blue
    'secondary': '#E67E22',  # Orange
    'success': '#27AE60',    # Green
    'warning': '#F1C40F',    # Yellow
    'danger': '#E74C3C'      # Red
}

# Analysis settings
MIN_ORDERS_FOR_ANALYSIS = 10
MAX_GROUP_SIZE = 50  # Filter out unreasonable group sizes
MAX_DWELL_TIME_HOURS = 4  # Maximum reasonable dwell time

# Time periods
TIME_PERIODS = {
    'hour': 'Hourly',
    'day': 'Daily',
    'week': 'Weekly',
    'month': 'Monthly'
}

# Date range presets
DATE_RANGE_PRESETS = [
    "All Time",
    "Last 7 Days",
    "Last 30 Days",
    "Last 90 Days",
    "Custom Range"
]

# Chart defaults
CHART_HEIGHT = 500
CHART_HEIGHT_LARGE = 600
CHART_MARGIN = dict(l=50, r=50, t=50, b=50)

# Format strings
CURRENCY_FORMAT = "฿{:,.2f}"
PERCENT_FORMAT = "{:.1f}%"
COUNT_FORMAT = "{:,}"

# Category display names
CATEGORY_NAMES = {
    'main_course': 'Main Course',
    'appetizer': 'Appetizer',
    'dessert': 'Dessert',
    'beverage': 'Beverage',
    'alcohol': 'Alcoholic Drinks',
    'side_dish': 'Side Dish'
}