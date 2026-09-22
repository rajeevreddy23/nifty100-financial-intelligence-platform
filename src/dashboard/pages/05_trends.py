import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from utils.db import load_companies, load_company_history

st.title("📈 10-Year Financial Trend Analysis")

companies = load_companies()
ticker_list = sorted(companies['id'].tolist())
selected_ticker = st.selectbox("Select Company", ticker_list, index=ticker_list.index("INFY") if "INFY" in ticker_list else 0)

hist = load_company_history(selected_ticker)
pl = hist['pl']
ratios = hist['ratios']

merged = pd.merge(pl, ratios, on=['company_id', 'year'], suffixes=('_pl', '_rat'))

metric_options = {
    'Sales (₹ Cr)': 'sales',
    'Net Profit (₹ Cr)': 'net_profit',
    'Operating Profit (₹ Cr)': 'operating_profit',
    'Return on Equity (%)': 'return_on_equity_pct',
    'Return on Capital (%)': 'return_on_capital_pct',
    'Free Cash Flow (₹ Cr)': 'free_cash_flow_cr',
    'Debt to Equity (x)': 'debt_to_equity'
}

selected_metrics = st.multiselect("Select Metrics to Overlay (Up to 3)", list(metric_options.keys()), default=['Sales (₹ Cr)', 'Net Profit (₹ Cr)'])

if selected_metrics and len(merged) > 0:
    fig = go.Figure()
    for m_label in selected_metrics:
        col_name = metric_options[m_label]
        if col_name in merged.columns:
            fig.add_trace(go.Scatter(x=merged['year'], y=merged[col_name], mode='lines+markers', name=m_label, line=dict(width=2.5)))
    fig.update_layout(title=f"{selected_ticker} — Multi-Year Trend Progression", height=450)
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Historical Data Points")
st.dataframe(merged[['year'] + [metric_options[m] for m in selected_metrics if metric_options[m] in merged.columns]], use_container_width=True, hide_index=True)
