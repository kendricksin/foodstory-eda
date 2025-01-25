# foodstory-eda/dashboard/pages/2_menu_analysis.py

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd
import sqlite3

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
    analyze_menu_combinations
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

# Load base data
@st.cache_data
def load_base_menu_data(start_date, end_date, category):
    df = load_menu_data(start_date, end_date)
    if category != 'All':
        df = df[df['category'] == category]
    return df

# Load initial data
df = load_base_menu_data(date_range[0], date_range[1], selected_category)

# Menu item filters
st.sidebar.markdown("---")
st.sidebar.subheader("Menu Item Filters")

# Get unique menu items for filter
all_menu_items = sorted(df['menu_name'].unique().tolist())

# Custom item exclusion
excluded_items = st.sidebar.multiselect(
    "Exclude Specific Items",
    options=all_menu_items,
    default=['ข้าวเหนียว ขาว','น้ำเปล่า'],
    help="Select items to exclude from analysis"
)

# Minimum order threshold
min_order_count = st.sidebar.number_input(
    "Minimum Order Count",
    min_value=1,
    max_value=1000,
    value=10,
    help="Only include items ordered at least this many times"
)

# Apply filters
df = df[~df['menu_name'].isin(excluded_items)]
order_counts = df.groupby('menu_name')['quantity'].sum()
valid_items = order_counts[order_counts >= min_order_count].index
df = df[df['menu_name'].isin(valid_items)]

# Top-level metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_items = float(df['quantity'].sum())
    avg_items = float(df['quantity'].mean())
    st.metric(
        "Total Items Sold",
        f"{total_items:,.0f}",
        f"{avg_items:.1f} avg per order"
    )

with col2:
    total_revenue = float(df['revenue'].sum())
    avg_revenue = float(df['revenue'].mean())
    st.metric(
        "Total Revenue",
        f"฿{total_revenue:,.0f}",
        f"฿{avg_revenue:,.0f} avg per item"
    )

with col3:
    unique_items = int(df['menu_code'].nunique())
    unique_cats = int(df['category'].nunique())
    st.metric(
        "Unique Items",
        f"{unique_items:,}",
        f"{unique_cats} categories"
    )

with col4:
    total_discount = float(df['discount_amount'].sum())
    discount_rate = (total_discount / total_revenue * 100) if total_revenue > 0 else 0
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

# Get combination matrices
top_vs_top, top_vs_bottom, bottom_vs_bottom = analyze_menu_combinations(df)

# Create tabs for different matrices
tab1, tab2, tab3 = st.tabs([
    "Top 20 vs Top 20",
    "Top 20 vs Bottom 20",
    "Bottom 20 vs Bottom 20"
])

def plot_heatmap(matrix, title):
    """Helper function to plot heatmap with consistent styling"""
    fig = go.Figure(data=go.Heatmap(
        z=matrix.values,
        x=matrix.columns,
        y=matrix.index,
        colorscale='Blues',
        hoverongaps=False,
        hovertemplate='%{y} + %{x}<br>Orders: %{z}<extra></extra>'
    ))
    
    fig.update_layout(
        title=title,
        height=800,
        xaxis=dict(
            tickangle=45,
            title='Second Item'
        ),
        yaxis=dict(
            title='First Item'
        )
    )
    
    return fig

with tab1:
    st.markdown("""
    This heatmap shows how frequently the top 20 menu items are ordered together.
    Darker colors indicate more frequent combinations.
    """)
    
    fig = plot_heatmap(
        top_vs_top,
        'Combination Frequency: Top 20 Items'
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Show top combinations as text
    st.subheader("Most Common Combinations")
    top_combos = []
    for i in range(len(top_vs_top.index)):
        for j in range(i+1, len(top_vs_top.columns)):
            count = top_vs_top.iloc[i, j]
            if count > 0:
                top_combos.append({
                    'Item 1': top_vs_top.index[i],
                    'Item 2': top_vs_top.columns[j],
                    'Orders': int(count)
                })
    
    top_combos_df = pd.DataFrame(top_combos).sort_values('Orders', ascending=False).head(10)
    st.dataframe(top_combos_df, hide_index=True)

with tab2:
    st.markdown("""
    This heatmap shows combinations between top 20 and bottom 20 items.
    It can help identify if any low-performing items are frequently paired with popular items.
    """)
    
    fig = plot_heatmap(
        top_vs_bottom,
        'Combination Frequency: Top 20 vs Bottom 20 Items'
    )
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.markdown("""
    This heatmap shows combinations among the bottom 20 items.
    This can help identify if certain low-performing items tend to be ordered together.
    """)
    
    fig = plot_heatmap(
        bottom_vs_bottom,
        'Combination Frequency: Bottom 20 Items'
    )
    st.plotly_chart(fig, use_container_width=True)

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