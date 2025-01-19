# foodstory-eda/dashboard/app.py

import streamlit as st
from pathlib import Path
from utils.data_loader import get_date_range

# Configure the default settings
st.set_page_config(
    page_title="Restaurant Analytics Dashboard",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title and description
st.title("🍽️ Restaurant Analytics Dashboard")
st.markdown("""
This dashboard provides comprehensive analytics for restaurant operations,
including sales trends, menu performance, and customer behavior analysis.
""")

# Get available date range
min_date, max_date = get_date_range()

# Show basic information in the main page
st.info(f"""
#### Available Data Range
- **Start Date:** {min_date.date()}
- **End Date:** {max_date.date()}
- **Total Days:** {(max_date - min_date).days + 1:,}

Use the pages in the sidebar to explore different aspects of the restaurant's performance:

1. **Sales Overview**: Analyze revenue trends, group sizes, and time patterns
2. **Menu Analysis**: Investigate item performance, category analysis, and popular combinations
""")

# Footer with database info
st.sidebar.markdown("---")
st.sidebar.markdown("##### Dashboard Info")
db_path = Path(__file__).parent.parent / 'database' / 'restaurant_sales.db'
st.sidebar.text(f"Database: {db_path.name}")
st.sidebar.text(f"Last Updated: {db_path.stat().st_mtime:.10}")