import os
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="Stock Analysis Dashboard", layout="wide")
st.title("Interactive Stock Analysis Dashboard")

# --- 2. LOAD DATA ---
# st.cache_data prevents the app from reloading the Excel file every time you click a button
@st.cache_data
def load_data():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, "Master_Dataset.xlsx")
    
    if not os.path.exists(file_path):
        return None
        
    df = pd.read_excel(file_path)
    df['File_Date'] = pd.to_datetime(df['File_Date'], errors='coerce')
    return df.dropna(subset=['File_Date'])

master_df = load_data()

if master_df is None:
    st.error("Error: 'Master_Dataset.xlsx' not found! Please run your first script to compile the data.")
    st.stop()

# --- 3. DYNAMIC COLUMN DETECTION ---
# Find all columns that contain numbers (so you can plot any of them)
numeric_cols = master_df.select_dtypes(include=[np.number]).columns.tolist()
# Find the stock name column
stock_col = next((c for c in master_df.columns if 'stock' in str(c).lower() or 'ticker' in str(c).lower()), master_df.columns[0])
valid_stocks = master_df[stock_col].dropna().unique().tolist()

# --- 4. INTERACTIVE DROPDOWNS ---
# Create two columns at the top of the page for our dropdowns
col1, col2 = st.columns(2)

with col1:
    # Dropdown 1: Pick the stock
    selected_stock = st.selectbox("Select a Stock:", valid_stocks)

with col2:
    # Dropdown 2: Multi-select columns to plot
    # We pre-select Price and Target by default if they exist
    default_cols = [c for c in numeric_cols if 'price' in str(c).lower() or 'target' in str(c).lower()]
    selected_metrics = st.multiselect("Select columns to plot:", numeric_cols, default=default_cols)

# --- 5. FILTER DATA & CALCULATE R² ---
# Filter data to only the selected stock
stock_data = master_df[master_df[stock_col] == selected_stock].sort_values(by='File_Date')

# Dynamically find which selected metrics are Price and Target for the R² math
price_col = next((c for c in selected_metrics if 'price' in str(c).lower() and 'target' not in str(c).lower()), None)
target_col = next((c for c in selected_metrics if 'target' in str(c).lower()), None)

# Calculate and display R² right above the chart
if price_col and target_col:
    clean_data = stock_data.dropna(subset=[price_col, target_col])
    if len(clean_data) > 1 and clean_data[price_col].nunique() > 1 and clean_data[target_col].nunique() > 1:
        r2 = np.corrcoef(clean_data[price_col], clean_data[target_col])[0, 1] ** 2
        st.metric(label=f"R² Correlation ({price_col} vs {target_col})", value=f"{r2:.3f}")
    else:
        st.metric(label="R² Correlation", value="N/A", help="Not enough variance to calculate.")
else:
    st.info("Select both a Price and Target column to see the R² correlation.")

# --- 6. BUILD AND DISPLAY CHART ---
if selected_metrics:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    for metric in selected_metrics:
        # If the metric is market cap, put it on the right-hand Y-axis
        is_large_number = 'cap' in str(metric).lower() or 'market' in str(metric).lower()
        
        fig.add_trace(go.Scatter(
            x=stock_data['File_Date'],
            y=stock_data[metric],
            mode='lines+markers',
            name=metric
        ), secondary_y=is_large_number)

    fig.update_layout(
        title=f"Performance: {selected_stock}",
        template="plotly_white", 
        hovermode="x unified",
        height=600 # Makes the chart nice and tall
    )
    
    # Render the chart in the web app
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Please select at least one column to plot.")
