"""
Sales Overview Dashboard Page
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

from utils.data_loader import load_sales_data, get_date_range
from utils.analysis import (
    calculate_key_metrics,
    analyze_time_patterns,
    calculate_group_metrics
)

# Page config
st.set_page_config(page_title="Sales Overview", page_icon="📊", layout="wide")

# Title
st.title("📊 Sales Overview")

# Sidebar filters
st.sidebar.header("Filters")

# Date range selector with presets
min_date, max_date = get_date_range()
date_presets = {
    "All Time": (min_date.date(), max_date.date()),
    "Last 7 Days": (max_date.date() - timedelta(days=7), max_date.date()),
    "Last 30 Days": (max_date.date() - timedelta(days=30), max_date.date()),
    "Last 90 Days": (max_date.date() - timedelta(days=90), max_date.date()),
    "Custom Range": None
}

selected_preset = st.sidebar.selectbox(
    "Select Date Range",
    options=list(date_presets.keys())
)

if selected_preset == "Custom Range":
    date_range = st.sidebar.date_input(
        "Select Custom Date Range",
        value=(min_date.date(), max_date.date()),
        min_value=min_date.date(),
        max_value=max_date.date()
    )
else:
    date_range = date_presets[selected_preset]

# Time period selector
time_period = st.sidebar.selectbox(
    "Select Time Period for Analysis",
    options=["Hourly", "Daily", "Weekly", "Monthly"],
    index=2
)

# Load and filter data
@st.cache_data
def load_filtered_data(start_date, end_date):
    df = load_sales_data(start_date, end_date)
    return df

df = load_filtered_data(date_range[0], date_range[1])

# Calculate key metrics
metrics = calculate_key_metrics(df)

# Display key metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Total Revenue",
        f"฿{metrics['total_revenue']:,.0f}",
        f"฿{metrics['avg_daily_revenue']:,.0f}/day"
    )

with col2:
    st.metric(
        "Total Transactions",
        f"{metrics['total_transactions']:,}",
        f"{metrics['avg_daily_transactions']:.1f}/day"
    )

with col3:
    st.metric(
        "Average Bill",
        f"฿{metrics['avg_transaction']:,.0f}",
        f"฿{df['summary_price'].median():,.0f} median"
    )

with col4:
    st.metric(
        "Average Group Size",
        f"{metrics['avg_group_size']:.1f}",
        f"{df['seat_amount'].median():.0f} median"
    )

# Revenue Analysis
st.header("Revenue Analysis")
tab1, tab2 = st.tabs(["Trend Analysis", "Time Distribution"])

with tab1:
    # Prepare data based on selected time period
    if time_period == "Hourly":
        df['period'] = df['datetime'].dt.floor('H')
    elif time_period == "Daily":
        df['period'] = df['datetime'].dt.date
    elif time_period == "Weekly":
        df['period'] = df['datetime'].dt.strftime('%Y-W%U')
    else:  # Monthly
        df['period'] = df['datetime'].dt.strftime('%Y-%m')

    trend_data = df.groupby('period').agg({
        'summary_price': ['sum', 'mean', 'count']
    }).reset_index()
    trend_data.columns = ['period', 'revenue', 'avg_bill', 'transactions']

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=trend_data['period'],
        y=trend_data['revenue'],
        name='Revenue',
        line=dict(color='#2E86C1')
    ))
    fig.add_trace(go.Scatter(
        x=trend_data['period'],
        y=trend_data['transactions'] * trend_data['revenue'].mean(),
        name='Transactions',
        line=dict(color='#E67E22', dash='dot')
    ))

    fig.update_layout(
        title=f'{time_period} Revenue and Transaction Trends',
        xaxis_title='Period',
        yaxis_title='Amount (฿)',
        hovermode='x unified'
    )
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    # Time distribution analysis
    time_patterns = analyze_time_patterns(df, time_period.lower())
    time_patterns = time_patterns.reset_index()
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=time_patterns['index'],
        y=time_patterns[('summary_price', 'sum')],
        name='Total Revenue',
        marker_color='#2E86C1'
    ))
    fig.add_trace(go.Scatter(
        x=time_patterns['index'],
        y=time_patterns[('summary_price', 'mean')],
        name='Average Bill',
        yaxis='y2',
        line=dict(color='#E67E22')
    ))

    fig.update_layout(
        title=f'Revenue Distribution by {time_period}',
        xaxis_title=time_period,
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
    fig = px.histogram(
        df,
        x='seat_amount',
        nbins=20,
        title='Distribution of Group Sizes',
        labels={'seat_amount': 'Group Size', 'count': 'Number of Visits'}
    )
    fig.update_traces(marker_color='#2E86C1')
    st.plotly_chart(fig, use_container_width=True)

with col2:
    # Revenue by group size
    group_metrics = calculate_group_metrics(df)
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=group_metrics['seat_amount'],
        y=group_metrics['total_revenue'],
        name='Total Revenue',
        marker_color='#2E86C1'
    ))
    fig.add_trace(go.Scatter(
        x=group_metrics['seat_amount'],
        y=group_metrics['revenue_per_person'],
        name='Revenue per Person',
        yaxis='y2',
        line=dict(color='#E67E22')
    ))

    fig.update_layout(
        title='Revenue Analysis by Group Size',
        xaxis_title='Group Size',
        yaxis_title='Total Revenue (฿)',
        yaxis2=dict(
            title='Revenue per Person (฿)',
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
    monthly_stats = df.groupby(df['datetime'].dt.strftime('%Y-%m')).agg({
        'summary_price': ['count', 'sum', 'mean'],
        'seat_amount': ['mean', 'sum']
    }).round(2)
    
    monthly_stats.columns = [
        'transaction_count', 'total_revenue', 'avg_bill',
        'avg_group_size', 'total_seats'
    ]
    monthly_stats = monthly_stats.reset_index()
    
    # Calculate growth rates
    monthly_stats['revenue_growth'] = monthly_stats['total_revenue'].pct_change() * 100
    monthly_stats['transaction_growth'] = monthly_stats['transaction_count'].pct_change() * 100
    
    st.subheader("Monthly Performance")
    st.dataframe(
        monthly_stats.style.format({
            'total_revenue': '฿{:,.2f}',
            'avg_bill': '฿{:,.2f}',
            'avg_group_size': '{:.1f}',
            'revenue_growth': '{:+.1f}%',
            'transaction_growth': '{:+.1f}%'
        }),
        hide_index=True
    )