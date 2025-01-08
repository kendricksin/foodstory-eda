import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import numpy as np
import os
import argparse
import sys
import glob

def load_and_clean_data(path):
    """
    Load and clean the restaurant sales data.
    
    Args:
        path (str): Path to the CSV file or directory containing CSV files
        
    Returns:
        pd.DataFrame: Cleaned dataframe with properly formatted columns
    """
    all_data = []
    
    try:
        if os.path.isdir(path):
            # If path is a directory, process all CSV files
            csv_files = glob.glob(os.path.join(path, '*.csv'))
            if not csv_files:
                raise ValueError(f"No CSV files found in directory: {path}")
            
            print(f"Found {len(csv_files)} CSV files")
            for file in csv_files:
                print(f"Processing: {os.path.basename(file)}")
                df = pd.read_csv(file)
                all_data.append(df)
            df = pd.concat(all_data, ignore_index=True)
            print(f"Total records loaded: {len(df):,}")
        else:
            # If path is a file, process single file
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
        
        # Remove duplicates if any
        initial_rows = len(df)
        df = df.drop_duplicates(subset=['Receipt Number'])
        if initial_rows > len(df):
            print(f"Removed {initial_rows - len(df):,} duplicate records")
        
        return df
        
    except FileNotFoundError:
        print(f"Error: Could not find {path}")
        raise
    except pd.errors.EmptyDataError:
        print(f"Error: No data found in {path}")
        raise
    except Exception as e:
        print(f"Error occurred while processing {path}: {str(e)}")
        raise

def analyze_group_sizes(df):
    # Group size distribution
    group_size_stats = df['Seat Amount'].describe()
    
    # Calculate total visitors and revenue per group size
    group_analysis = df.groupby('Seat Amount').agg({
        'Summary Price': ['mean', 'sum', 'count'],
        'Seat Amount': 'count'
    }).reset_index()
    
    # Flatten column names
    group_analysis.columns = ['group_size', 'avg_bill', 'total_revenue', 'visit_count', 'group_count']
    
    # Calculate total visitors per group size
    group_analysis['total_visitors'] = group_analysis['group_size'] * group_analysis['visit_count']
    
    # Calculate percentage of total visitors
    total_visitors = group_analysis['total_visitors'].sum()
    group_analysis['visitor_percentage'] = (group_analysis['total_visitors'] / total_visitors) * 100
    
    # Calculate average spend per person
    group_analysis['spend_per_person'] = group_analysis['avg_bill'] / group_analysis['group_size']
    
    return group_size_stats, group_analysis

def analyze_dwell_time(df):
    # Calculate time difference between consecutive orders at same table
    df_sorted = df.sort_values(['Table', 'datetime'])
    df_sorted['next_order_time'] = df_sorted.groupby('Table')['datetime'].shift(-1)
    df_sorted['time_between_orders'] = (df_sorted['next_order_time'] - df_sorted['datetime']).dt.total_seconds() / 3600
    
    # Filter out unreasonable times (e.g., > 4 hours probably means different customers)
    dwell_time = df_sorted[df_sorted['time_between_orders'] <= 4]['time_between_orders']
    
    return dwell_time.describe()

def analyze_revenue_patterns(df):
    # Add time-based columns
    df['hour'] = df['datetime'].dt.hour
    df['month'] = df['datetime'].dt.strftime('%Y-%m')
    
    # Revenue by hour of day
    hourly_revenue = df.groupby('hour')['Summary Price'].agg(['mean', 'count', 'sum'])
    
    # Monthly analysis
    monthly_analysis = df.groupby('month').agg({
        'Summary Price': ['count', 'sum', 'mean'],
        'Seat Amount': ['mean', 'sum'],
        'Receipt Number': 'count'
    }).round(2)
    
    # Flatten column names
    monthly_analysis.columns = ['transaction_count', 'total_revenue', 'avg_bill',
                              'avg_group_size', 'total_seats', 'receipt_count']
    
    # Calculate month-over-month growth
    monthly_analysis['revenue_growth'] = monthly_analysis['total_revenue'].pct_change() * 100
    monthly_analysis['transaction_growth'] = monthly_analysis['transaction_count'].pct_change() * 100
    
    # Revenue by group size
    revenue_by_group = df.groupby('Seat Amount')['Summary Price'].agg(['mean', 'count', 'sum'])
    
    return hourly_revenue, revenue_by_group, monthly_analysis

def plot_insights(df, group_analysis, hourly_revenue, monthly_analysis):
    # Set the backend to non-interactive
    plt.switch_backend('Agg')
    
    # Plot 1: Group Size Distribution with Visitor Percentage
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Raw visit counts
    sns.histplot(data=df, x='Seat Amount', bins=20, ax=ax1)
    ax1.set_title('Distribution of Group Sizes\n(Visit Counts)')
    ax1.set_xlabel('Number of Customers')
    ax1.set_ylabel('Number of Visits')
    
    # Visitor percentage
    sns.barplot(data=group_analysis, x='group_size', y='visitor_percentage', ax=ax2)
    ax2.set_title('Distribution of Total Visitors\n(% of Total Customers)')
    ax2.set_xlabel('Group Size')
    ax2.set_ylabel('Percentage of Total Visitors')
    plt.tight_layout()
    plt.savefig('group_size_analysis.png')
    plt.close()
    
    # Plot 2: Revenue Analysis by Group Size
    plt.figure(figsize=(10, 6))
    ax = plt.gca()
    
    # Plot average spend per person
    line1 = ax.plot(group_analysis['group_size'], 
                   group_analysis['spend_per_person'], 
                   marker='o', label='Spend per Person')
    ax.set_xlabel('Group Size')
    ax.set_ylabel('Average Spend per Person (฿)')
    
    # Plot total revenue on secondary y-axis
    ax2 = ax.twinx()
    line2 = ax2.plot(group_analysis['group_size'], 
                    group_analysis['total_revenue'], 
                    marker='s', color='red', label='Total Revenue')
    ax2.set_ylabel('Total Revenue (฿)')
    
    # Combine legends
    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax.legend(lines, labels, loc='upper right')
    
    plt.title('Revenue Analysis by Group Size')
    plt.tight_layout()
    plt.savefig('revenue_analysis.png')
    plt.close()
    
    # Plot 3: Monthly Trends
    plt.figure(figsize=(12, 6))
    ax = plt.gca()
    
    # Plot total revenue
    line1 = ax.plot(monthly_analysis.index, 
                    monthly_analysis['total_revenue'], 
                    marker='o', label='Total Revenue')
    ax.set_xlabel('Month')
    ax.set_ylabel('Total Revenue (฿)')
    
    # Plot average bill on secondary y-axis
    ax2 = ax.twinx()
    line2 = ax2.plot(monthly_analysis.index, 
                     monthly_analysis['avg_bill'], 
                     marker='s', color='red', label='Average Bill')
    ax2.set_ylabel('Average Bill (฿)')
    
    # Combine legends
    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax.legend(lines, labels, loc='upper right')
    
    plt.title('Monthly Revenue Trends')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('monthly_trends.png')
    plt.close()
    
    # Plot 4: Revenue by Hour
    plt.figure(figsize=(10, 6))
    hourly_revenue['sum'].plot(kind='bar')
    plt.title('Total Revenue by Hour of Day')
    plt.xlabel('Hour')
    plt.ylabel('Total Revenue')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('revenue_by_hour.png')
    plt.close()
    
    print("\nPlots have been saved as PNG files in the current directory.")

def main():
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description='Analyze restaurant sales data')
    parser.add_argument('data_path', help='Path to CSV file or directory containing CSV files')
    parser.add_argument('--output', '-o', default='analysis_output',
                       help='Directory to save output files (default: analysis_output)')
    
    args = parser.parse_args()
    
    # Validate input path
    if not os.path.exists(args.data_path):
        print(f"Error: Path does not exist: {args.data_path}")
        sys.exit(1)
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output, exist_ok=True)
    print(f"\nOutput directory: {args.output}")
    
    # Change working directory to output directory for saving files
    original_dir = os.getcwd()
    os.chdir(args.output)
    
    try:
        # Load and process data
        df = load_and_clean_data(os.path.join(original_dir, args.data_path))
        
        # Perform analyses
        group_size_stats, group_analysis = analyze_group_sizes(df)
        dwell_time_stats = analyze_dwell_time(df)
        hourly_revenue, revenue_by_group, monthly_analysis = analyze_revenue_patterns(df)
        
        # Save detailed analysis to a text file
        with open('analysis_results.txt', 'w', encoding='utf-8') as f:
            f.write("=== Restaurant Sales Analysis ===\n\n")
            
            f.write("Dataset Overview:\n")
            f.write(f"Total transactions analyzed: {len(df):,}\n")
            f.write(f"Date range: {df['datetime'].min().date()} to {df['datetime'].max().date()}\n")
            
            f.write("\n=== Group Size Analysis ===\n")
            f.write(f"Average group size: {group_size_stats['mean']:.2f} people\n")
            f.write(f"Most common group size: {group_size_stats['50%']:.0f} people\n")
            f.write(f"Range: {group_size_stats['min']:.0f} to {group_size_stats['max']:.0f} people\n")
            
            f.write("\n=== Revenue Insights ===\n")
            f.write("\nTop 5 most profitable group sizes:\n")
            top_groups = revenue_by_group.sort_values('sum', ascending=False).head()
            for size, row in top_groups.iterrows():
                f.write(f"\nGroup Size {size:.0f}:\n")
                f.write(f"  Average bill: ฿{row['mean']:,.2f}\n")
                f.write(f"  Number of visits: {row['count']:,}\n")
                f.write(f"  Total revenue: ฿{row['sum']:,.2f}\n")
            
            f.write("\n=== Average Dwell Time ===\n")
            f.write(f"Mean stay duration: {dwell_time_stats['mean']:.2f} hours\n")
            f.write(f"Median stay duration: {dwell_time_stats['50%']:.2f} hours\n")
            
            f.write("\n=== Peak Hours ===\n")
            peak_hours = hourly_revenue.sort_values('sum', ascending=False).head(3)
            for hour in peak_hours.index:
                f.write(f"Hour {hour:02f}:00: ฿{peak_hours.loc[hour, 'sum']:,.2f} ")
                f.write(f"(avg ฿{peak_hours.loc[hour, 'mean']:,.2f} per bill)\n")
        
            # Add monthly analysis to the report
            f.write("\n=== Monthly Trends ===\n")
            f.write("\nRevenue trends by month:\n")
            for month, row in monthly_analysis.iterrows():
                f.write(f"\n{month}:\n")
                f.write(f"  Total Revenue: ฿{row['total_revenue']:,.2f}\n")
                f.write(f"  Average Bill: ฿{row['avg_bill']:,.2f}\n")
                f.write(f"  Number of Transactions: {row['transaction_count']:,}\n")
                if not pd.isna(row['revenue_growth']):
                    f.write(f"  Revenue Growth: {row['revenue_growth']:+.1f}%\n")
                if not pd.isna(row['transaction_growth']):
                    f.write(f"  Transaction Growth: {row['transaction_growth']:+.1f}%\n")

        # Generate and save plots
        plot_insights(df, group_analysis, hourly_revenue, monthly_analysis)
        
        print(f"\nAnalysis complete! Results have been saved to {args.output}/")
        print("Generated files:")
        print("- analysis_results.txt (Detailed analysis)")
        print("- group_size_analysis.png (Distribution and normalized visitor counts)")
        print("- revenue_analysis.png (Revenue metrics by group size)")
        print("- monthly_trends.png (Revenue trends over time)")
        print("- revenue_by_hour.png (Hourly revenue distribution)")
        
    finally:
        # Change back to original directory
        os.chdir(original_dir)

if __name__ == "__main__":
    main()