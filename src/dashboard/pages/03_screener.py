import streamlit as st
import pandas as pd
from utils.db import load_latest_universe

st.title("🔍 Multi-Criteria Financial Screener")

df = load_latest_universe()

preset = st.selectbox(
    "Select Screening Preset",
    ["Custom Filters", "Quality Compounder", "Value Pick", "Growth Accelerator", "Dividend Champion", "Debt-Free Blue Chip", "Turnaround Watch"]
)

st.sidebar.header("Filter Criteria")

if preset == "Quality Compounder":
    default_roe, default_de, default_fcf, default_cagr = 15.0, 1.0, 0.0, 10.0
elif preset == "Value Pick":
    default_roe, default_de, default_fcf, default_cagr = 0.0, 2.0, 0.0, 0.0
elif preset == "Debt-Free Blue Chip":
    default_roe, default_de, default_fcf, default_cagr = 12.0, 0.0, -1000.0, 0.0
else:
    default_roe, default_de, default_fcf, default_cagr = 0.0, 5.0, -50000.0, 0.0

min_roe = st.sidebar.slider("Minimum ROE (%)", -10.0, 50.0, float(default_roe), 1.0)
max_de = st.sidebar.slider("Maximum Debt-to-Equity (x)", 0.0, 10.0, float(default_de), 0.1)
min_fcf = st.sidebar.slider("Minimum Free Cash Flow (₹ Cr)", -5000.0, 20000.0, float(default_fcf), 500.0)
min_cagr = st.sidebar.slider("Minimum 5Y Revenue CAGR (%)", -10.0, 40.0, float(default_cagr), 1.0)
max_pe = st.sidebar.slider("Maximum P/E Ratio", 5.0, 120.0, 80.0, 5.0)

cond = (
    (df['return_on_equity_pct'].fillna(-999) >= min_roe) &
    ((df['debt_to_equity'].fillna(999) <= max_de) | (df['broad_sector'].str.lower().isin(['financials', 'financial services']))) &
    (df['free_cash_flow_cr'].fillna(-999999) >= min_fcf) &
    (df['revenue_cagr_5yr'].fillna(-999) >= min_cagr) &
    (df['pe_ratio'].fillna(999) <= max_pe)
)
filtered = df[cond].sort_values('composite_score', ascending=False)

st.subheader(f"Screening Results: {len(filtered)} Qualified Companies")

csv_bytes = filtered.to_csv(index=False).encode('utf-8')
st.download_button(
    "📥 Export Filtered Results (CSV)",
    data=csv_bytes,
    file_name="screener_results.csv",
    mime="text/csv"
)

cols_show = [
    'id', 'company_name', 'broad_sector', 'return_on_equity_pct', 'return_on_capital_pct',
    'debt_to_equity', 'free_cash_flow_cr', 'revenue_cagr_5yr', 'pe_ratio', 'composite_score'
]
st.dataframe(filtered[cols_show], use_container_width=True, hide_index=True)
