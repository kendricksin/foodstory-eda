import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

# Set page config
st.set_page_config(
    page_title="Bandaidang Sales Analysis",
    page_icon="🍽️",
    layout="wide"
)

# Function to load data from SQLite
@st.cache_data
def load_data(db_path):
    conn = sqlite3.connect(db_path)
    query = """
    SELECT *
    FROM sales
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Convert datetime column
    df['datetime'] = pd.to_datetime(df['datetime'])
    return df

# Function to aggregate data by time period
def aggregate_by_period(df, period):
    if period == 'Hourly':
        return df.groupby(df['datetime'].dt.floor('h')).agg({
            'summary_price': ['sum', 'mean', 'count']
        }).reset_index()
    elif period == 'Daily':
        return df.groupby(df['datetime'].dt.date).agg({
            'summary_price': ['sum', 'mean', 'count']
        }).reset_index()
    elif period == 'Weekly':
        return df.groupby(pd.Grouper(key='datetime', freq='W-MON')).agg({
            'summary_price': ['sum', 'mean', 'count']
        }).reset_index()
    else:  # Monthly
        # Use strftime for monthly grouping instead of to_period
        df['month'] = df['datetime'].dt.strftime('%Y-%m')
        monthly = df.groupby('month').agg({
            'summary_price': ['sum', 'mean', 'count']
        }).reset_index()
        # Sort by month to ensure chronological order
        monthly['sort_key'] = pd.to_datetime(monthly['month'] + '-01')
        monthly = monthly.sort_values('sort_key').drop('sort_key', axis=1)
        return monthly

# Main title
st.title("🍽️ Restaurant Sales Analytics")

# Database connection
try:
    df = load_data('restaurant_sales.db')
    
    # Sidebar filters
    st.sidebar.header("Filters")

    # Date range selector with presets
    date_presets = {
        "All Time": (df['datetime'].min().date(), df['datetime'].max().date()),
        "Last 7 Days": (df['datetime'].max().date() - timedelta(days=7), df['datetime'].max().date()),
        "Last 30 Days": (df['datetime'].max().date() - timedelta(days=30), df['datetime'].max().date()),
        "Last 90 Days": (df['datetime'].max().date() - timedelta(days=90), df['datetime'].max().date()),
        "Custom Range": None
    }

    selected_preset = st.sidebar.selectbox(
        "Select Date Range Preset",
        options=list(date_presets.keys())
    )

    if selected_preset == "Custom Range":
        date_range = st.sidebar.date_input(
            "Select Custom Date Range",
            value=(df['datetime'].min().date(), df['datetime'].max().date()),
            min_value=df['datetime'].min().date(),
            max_value=df['datetime'].max().date()
        )
    else:
        date_range = date_presets[selected_preset]

    # Time period selector
    time_period = st.sidebar.selectbox(
        "Select Time Period",
        options=['Hourly', 'Daily', 'Weekly', 'Monthly']
    )
    
    # Group size filter
    group_size_range = st.sidebar.slider(
        "Filter by Group Size",
        min_value=int(df['seat_amount'].min()),
        max_value=int(df['seat_amount'].max()),
        value=(int(df['seat_amount'].min()), int(df['seat_amount'].max()))
    )
    
    # Filter data based on selections
    mask = (
        (df['datetime'].dt.date >= date_range[0]) & 
        (df['datetime'].dt.date <= date_range[1]) &
        (df['seat_amount'] >= group_size_range[0]) &
        (df['seat_amount'] <= group_size_range[1])
    )
    filtered_df = df[mask]
    
    # Key Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Revenue",
            f"฿{filtered_df['summary_price'].sum():,.0f}",
            f"฿{filtered_df['summary_price'].sum() / len(filtered_df):,.0f} per bill"
        )
    
    with col2:
        st.metric(
            "Total Transactions",
            f"{len(filtered_df):,}",
            f"{len(filtered_df) / (date_range[1] - date_range[0]).days:.1f} per day"
        )
    
    with col3:
        st.metric(
            "Average Group Size",
            f"{filtered_df['seat_amount'].mean():.1f}",
            f"Mode: {filtered_df['seat_amount'].mode().iloc[0]:.0f}"
        )
    
    with col4:
        st.metric(
            "Average Bill",
            f"฿{filtered_df['summary_price'].mean():,.0f}",
            f"฿{filtered_df['summary_price'].median():,.0f} median"
        )
    
    # Revenue Trends
    st.header("Revenue Analysis")
    tab1, tab2 = st.tabs(["Trend Analysis", "Time Distribution"])
    
    with tab1:
        # Aggregate data by selected time period
        period_data = aggregate_by_period(filtered_df, time_period)
        period_data.columns = ['date', 'revenue', 'avg_bill', 'transactions']
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=period_data['date'],
            y=period_data['revenue'],
            name='Revenue',
            line=dict(color='#2E86C1')
        ))
        fig.add_trace(go.Scatter(
            x=period_data['date'],
            y=period_data['transactions'] * period_data['revenue'].mean(),
            name='Transactions',
            line=dict(color='#E67E22', dash='dot')
        ))
        
        fig.update_layout(
            title=f'{time_period} Revenue and Transaction Trends',
            xaxis_title='Date',
            yaxis_title='Amount (฿)',
            hovermode='x unified'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        if time_period == 'Hourly':
            # Hourly distribution
            hourly_stats = filtered_df.groupby(filtered_df['datetime'].dt.hour).agg({
                'summary_price': ['mean', 'sum', 'count']
            }).round(2)
            x_values = hourly_stats.index
            x_title = 'Hour of Day'
        elif time_period == 'Daily':
            # Daily distribution
            hourly_stats = filtered_df.groupby(filtered_df['datetime'].dt.dayofweek).agg({
                'summary_price': ['mean', 'sum', 'count']
            }).round(2)
            x_values = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            x_title = 'Day of Week'
        else:
            # Monthly distribution
            hourly_stats = filtered_df.groupby(filtered_df['datetime'].dt.month).agg({
                'summary_price': ['mean', 'sum', 'count']
            }).round(2)
            x_values = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            x_title = 'Month'
            
        hourly_stats.columns = ['avg_bill', 'total_revenue', 'transaction_count']
        hourly_stats = hourly_stats.reset_index()
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=x_values,
            y=hourly_stats['total_revenue'],
            name='Total Revenue',
            marker_color='#2E86C1'
        ))
        fig.add_trace(go.Scatter(
            x=x_values,
            y=hourly_stats['avg_bill'],
            name='Average Bill',
            yaxis='y2',
            line=dict(color='#E67E22')
        ))
        
        fig.update_layout(
            title=f'Revenue Distribution by {x_title}',
            xaxis_title=x_title,
            yaxis_title='Total Revenue (฿)',
            yaxis2=dict(
                title='Average Bill (฿)',
                overlaying='y',
                side='right'
            ),
            hovermode='x unified'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Group Size Analysis
    st.header("Group Size Analysis")
    col1, col2 = st.columns(2)
    
    with col1:
        # Group size distribution
        group_dist = px.histogram(
            filtered_df,
            x='seat_amount',
            nbins=20,
            title='Distribution of Group Sizes',
            labels={'seat_amount': 'Group Size', 'count': 'Number of Visits'}
        )
        group_dist.update_traces(marker_color='#2E86C1')
        st.plotly_chart(group_dist, use_container_width=True)
    
    with col2:
        # Revenue by group size
        group_revenue = filtered_df.groupby('seat_amount').agg({
            'summary_price': ['mean', 'sum', 'count']
        }).round(2)
        group_revenue.columns = ['avg_bill', 'total_revenue', 'visit_count']
        group_revenue = group_revenue.reset_index()
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=group_revenue['seat_amount'],
            y=group_revenue['total_revenue'],
            name='Total Revenue',
            marker_color='#2E86C1'
        ))
        fig.add_trace(go.Scatter(
            x=group_revenue['seat_amount'],
            y=group_revenue['avg_bill'],
            name='Average Bill',
            yaxis='y2',
            line=dict(color='#E67E22')
        ))
        
        fig.update_layout(
            title='Revenue by Group Size',
            xaxis_title='Group Size',
            yaxis_title='Total Revenue (฿)',
            yaxis2=dict(
                title='Average Bill (฿)',
                overlaying='y',
                side='right'
            ),
            hovermode='x unified'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Detailed Statistics
    st.header("Detailed Statistics")
    with st.expander("View Detailed Statistics"):
        # Monthly statistics
        monthly_stats = filtered_df.groupby(filtered_df['datetime'].dt.strftime('%Y-%m')).agg({
            'summary_price': ['count', 'sum', 'mean'],
            'seat_amount': ['mean', 'sum']
        }).round(2)
        monthly_stats.columns = ['transaction_count', 'total_revenue', 'avg_bill', 'avg_group_size', 'total_seats']
        monthly_stats = monthly_stats.reset_index()
        
        # Calculate month-over-month growth
        monthly_stats['revenue_growth'] = monthly_stats['total_revenue'].pct_change() * 100
        monthly_stats['transaction_growth'] = monthly_stats['transaction_count'].pct_change() * 100
        
        st.subheader("Monthly Performance")
        st.dataframe(
            monthly_stats.style.format({
                'total_revenue': '฿{:,.2f}',
                'avg_bill': '฿{:,.2f}',
                'avg_group_size': '{:,.1f}',
                'revenue_growth': '{:+.1f}%',
                'transaction_growth': '{:+.1f}%'
            }),
            hide_index=True
        )

except Exception as e:
    st.error(f"Error loading data: {str(e)}")
    st.info("Please make sure the database file 'restaurant_sales.db' exists in the current directory.")