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
numeric_cols = master_df.select_dtypes(include=[np.number]).columns.tolist()
stock_col = next((c for c in master_df.columns if 'stock' in str(c).lower() or 'ticker' in str(c).lower()), master_df.columns[0])
valid_stocks = master_df[stock_col].dropna().unique().tolist()

# Find the Target Price column to use as our baseline for the math
target_col = next((c for c in master_df.columns if 'target' in str(c).lower()), None)

# --- 4. SIDEBAR CHECKBOXES ---
st.sidebar.header("1. Select Stocks")
selected_stocks = []

# Create a checkbox for every stock. We default to checking the first one.
for i, stock in enumerate(valid_stocks):
    if st.sidebar.checkbox(str(stock), value=(i == 0)):
        selected_stocks.append(stock)

st.sidebar.divider()

st.sidebar.header("2. Select Metrics to Plot")
selected_metrics = []

# Create a checkbox for every numeric column. Default to checking price and target.
for col in numeric_cols:
    is_default = 'price' in str(col).lower() or 'target' in str(col).lower()
    if st.sidebar.checkbox(str(col), value=is_default):
        selected_metrics.append(col)

# --- 5. BUILD CHARTS & CALCULATE COEFFICIENTS ---
if not selected_stocks:
    st.warning("👈 Please select at least one stock from the sidebar.")
elif not selected_metrics:
    st.warning("👈 Please select at least one metric to plot from the sidebar.")
else:
    if not target_col:
        st.warning("Note: Could not find a 'Target' column to calculate correlation coefficients against.")

    # Loop through every stock the user checked
    for stock in selected_stocks:
        st.subheader(f"📊 Performance: {stock}")
        
        # Filter data for this specific stock
        stock_data = master_df[master_df[stock_col] == stock].sort_values(by='File_Date')

        # --- COEFFICIENT SCORECARDS ---
        if target_col:
            st.write(f"**Correlation Coefficient (*r*) vs {target_col}:**")
            # Create a clean row of metrics
            metric_columns = st.columns(len(selected_metrics))
            
            for idx, metric in enumerate(selected_metrics):
                if metric == target_col:
                    metric_columns[idx].metric(label=f"{metric}", value="1.00", help="Target compared to itself.")
                    continue
                
                # Drop empty rows so the math works
                clean_data = stock_data.dropna(subset=[metric, target_col])
                
                # Check if we have enough varying data points to calculate correlation
                if len(clean_data) > 1 and clean_data[metric].nunique() > 1 and clean_data[target_col].nunique() > 1:
                    # Calculate Pearson's r
                    r = np.corrcoef(clean_data[metric], clean_data[target_col])[0, 1]
                    metric_columns[idx].metric(label=f"{metric}", value=f"{r:.3f}")
                else:
                    metric_columns[idx].metric(label=f"{metric}", value="N/A", help="Not enough variance.")

        # --- PLOT THE CHART ---
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        for metric in selected_metrics:
            is_large_number = 'cap' in str(metric).lower() or 'market' in str(metric).lower()
            
            fig.add_trace(go.Scatter(
                x=stock_data['File_Date'],
                y=stock_data[metric],
                mode='lines+markers',
                name=metric
            ), secondary_y=is_large_number)

        fig.update_layout(
            template="plotly_white", 
            hovermode="x unified",
            height=500,
            margin=dict(t=30, b=30) # Tidy up the margins
        )
        
        # Keep Market Cap on the right-hand side so it doesn't crush the price lines
        fig.update_yaxes(title_text="Standard Metrics", secondary_y=False)
        fig.update_yaxes(title_text="Large Metrics (Cap)", secondary_y=True, showgrid=False)
        
        st.plotly_chart(fig, use_container_width=True)
        st.divider() # Adds a clean horizontal line between stocks
