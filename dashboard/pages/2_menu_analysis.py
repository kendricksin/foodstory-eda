"""
Menu Analysis Dashboard Page
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

from utils.data_loader import (
    load_menu_data,
    get_date_range,
    get_categories,
    load_category_summary,
    load_monthly_trends
)
from utils.analysis import (
    analyze_menu_performance,
    analyze_category_trends,
    find_top_combinations,
    analyze_discounts
)

# Page config
st.set_page_config(page_title="Menu Analysis", page_icon="🍽️", layout="wide")

# Title
st.title("🍽️ Menu Analysis")

# Sidebar filters
st.sidebar.header("Filters")

# Date range selector
min_date, max_date = get_date_range()
date_range = st.sidebar.date_input(
    "Select Date Range",
    value=(min_date.date(), max_date.date()),
    min_value=min_date.date(),
    max_value=max_date.date()
)

# Category filter
categories = ['All'] + get_categories()
selected_category = st.sidebar.selectbox("Select Category", categories)

# Load and filter data
@st.cache_data
def load_filtered_menu_data(start_date, end_date, category):
    df = load_menu_data(start_date, end_date)
    if category != 'All':
        df = df[df['category'] == category]
    return df

df = load_filtered_menu_data(date_range[0], date_range[1], selected_category)

# Top-level metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Total Items Sold",
        f"{df['quantity'].sum():,.0f}",
        f"{df['quantity'].mean():.1f} avg per order"
    )

with col2:
    st.metric(
        "Total Revenue",
        f"฿{df['revenue'].sum():,.0f}",
        f"฿{df['revenue'].mean():,.0f} avg per item"
    )

with col3:
    st.metric(
        "Unique Items",
        f"{df['menu_code'].nunique():,}",
        f"{df['category'].nunique()} categories"
    )

with col4:
    total_discount = df['discount_amount'].sum()
    discount_rate = (total_discount / df['revenue'].sum()) * 100
    st.metric(
        "Total Discounts",
        f"฿{total_discount:,.0f}",
        f"{discount_rate:.1f}% of revenue"
    )

# Menu Performance Analysis
st.header("Menu Performance Analysis")

tab1, tab2, tab3 = st.tabs(["Top Items", "Category Analysis", "Trend Analysis"])

with tab1:
    # Get menu performance metrics
    menu_perf = analyze_menu_performance(df)
    top_items = menu_perf.nlargest(20, 'revenue')
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=top_items['menu_name'],
        y=top_items['revenue'],
        name='Revenue',
        marker_color='#2E86C1'
    ))
    fig.add_trace(go.Scatter(
        x=top_items['menu_name'],
        y=top_items['quantity'],
        name='Quantity Sold',
        yaxis='y2',
        line=dict(color='#E67E22')
    ))

    fig.update_layout(
        title='Top 20 Menu Items by Revenue',
        xaxis_title='Menu Item',
        yaxis_title='Revenue (฿)',
        yaxis2=dict(
            title='Quantity Sold',
            overlaying='y',
            side='right'
        ),
        showlegend=True,
        height=600
    )
    fig.update_xaxes(tickangle=45)
    st.plotly_chart(fig, use_container_width=True)

    # Show detailed metrics
    st.subheader("Top Items Details")
    detailed_view = top_items[['menu_name', 'category', 'quantity', 'revenue',
                              'avg_price', 'revenue_share', 'discount_rate']]
    st.dataframe(
        detailed_view.style.format({
            'revenue': '฿{:,.2f}',
            'avg_price': '฿{:,.2f}',
            'revenue_share': '{:.1f}%',
            'discount_rate': '{:.1f}%'
        }),
        hide_index=True
    )

with tab2:
    # Load category summary
    cat_summary = load_category_summary()
    
    # Create treemap
    fig = px.treemap(
        cat_summary,
        path=['category'],
        values='total_revenue',
        color='unique_items',
        color_continuous_scale='Viridis',
        title='Revenue Distribution by Category'
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Category performance table
    st.subheader("Category Performance Details")
    cat_summary['avg_revenue_per_item'] = cat_summary['total_revenue'] / cat_summary['unique_items']
    cat_summary['discount_rate'] = cat_summary['total_discount'] / cat_summary['total_revenue'] * 100
    
    st.dataframe(
        cat_summary.style.format({
            'total_revenue': '฿{:,.2f}',
            'total_discount': '฿{:,.2f}',
            'avg_revenue_per_item': '฿{:,.2f}',
            'discount_rate': '{:.1f}%'
        }),
        hide_index=True
    )

with tab3:
    # Time period selector for trends
    time_period = st.selectbox(
        "Select Time Period",
        options=['Daily', 'Weekly', 'Monthly'],
        index=2
    )
    
    # Get trend data
    trends = analyze_category_trends(df)
    
    fig = go.Figure()
    for cat in df['category'].unique():
        cat_data = trends[trends['category'] == cat]
        fig.add_trace(go.Scatter(
            x=cat_data['datetime'],
            y=cat_data['revenue'],
            name=cat,
            mode='lines+markers'
        ))
    
    fig.update_layout(
        title=f'Revenue Trends by Category',
        xaxis_title='Period',
        yaxis_title='Revenue (฿)',
        height=500,
        showlegend=True,
        hovermode='x unified'
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Show growth rates
    st.subheader("Category Growth Rates")
    growth_data = trends.pivot(
        index='datetime',
        columns='category',
        values='revenue_growth'
    ).fillna(0)
    
    st.dataframe(
        growth_data.style.format('{:+.1f}%')
                      .background_gradient(cmap='RdYlGn', vmin=-20, vmax=20),
        height=400
    )

# Menu Combinations Analysis
st.header("Menu Combinations Analysis")

# Find popular combinations
combinations = find_top_combinations(df)
combinations = combinations.sort_values('count', ascending=False).head(20)

fig = go.Figure(data=[
    go.Bar(
        x=[f"{row['item1']} + {row['item2']}" for _, row in combinations.iterrows()],
        y=combinations['count'],
        marker_color='#2E86C1'
    )
])

fig.update_layout(
    title='Top Menu Item Combinations',
    xaxis_title='Combination',
    yaxis_title='Number of Orders',
    height=500
)
fig.update_xaxes(tickangle=45)
st.plotly_chart(fig, use_container_width=True)

# Discount Analysis
st.header("Discount Analysis")
col1, col2 = st.columns(2)

with col1:
    # Distribution of discount rates
    discount_data = df[df['discount_amount'] > 0]
    if not discount_data.empty:
        fig = px.histogram(
            discount_data,
            x=discount_data['discount_amount'] / discount_data['revenue'] * 100,
            nbins=30,
            title='Distribution of Discount Rates',
            labels={'x': 'Discount Rate (%)', 'y': 'Count'}
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No discount data available for the selected period")

with col2:
    # Discount analysis by category
    discount_by_cat = analyze_discounts(df).reset_index()
    if not discount_by_cat.empty:
        fig = px.bar(
            discount_by_cat,
            x='category',
            y=('discount_amount', 'sum'),
            title='Total Discounts by Category',
            labels={'x': 'Category', 'y': 'Total Discount (฿)'}
        )
        fig.update_xaxes(tickangle=45)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No discount data available for the selected period")

# Detailed Menu Statistics
st.header("Detailed Menu Statistics")
with st.expander("View Detailed Menu Statistics"):
    # Show full menu performance data
    st.subheader("Menu Item Performance")
    menu_stats = analyze_menu_performance(df, min_orders=5)
    menu_stats = menu_stats.sort_values('revenue', ascending=False)
    
    st.dataframe(
        menu_stats.style.format({
            'revenue': '฿{:,.2f}',
            'discount_amount': '฿{:,.2f}',
            'avg_price': '฿{:,.2f}',
            'revenue_share': '{:.2f}%',
            'discount_rate': '{:.2f}%'
        }).background_gradient(subset=['revenue_share'], cmap='Blues'),
        height=400
    )