import streamlit as st
import plotly.express as px
from utils.db import load_latest_universe

st.title("🏭 Sector Intelligence & Benchmarking")

df = load_latest_universe()

sec_stats = df.groupby('broad_sector').agg({
    'id': 'count',
    'return_on_equity_pct': 'median',
    'return_on_capital_pct': 'median',
    'net_profit_margin_pct': 'median',
    'pe_ratio': 'median',
    'debt_to_equity': 'median',
    'market_cap_crore': 'sum'
}).rename(columns={'id': 'Companies', 'market_cap_crore': 'Total Market Cap (₹ Cr)'}).reset_index()

st.subheader("Sector Median Multiples & Returns")
st.dataframe(sec_stats.style.format({
    'return_on_equity_pct': '{:.1f}%',
    'return_on_capital_pct': '{:.1f}%',
    'net_profit_margin_pct': '{:.1f}%',
    'pe_ratio': '{:.1f}x',
    'debt_to_equity': '{:.2f}x',
    'Total Market Cap (₹ Cr)': '₹{:,.0f}'
}), use_container_width=True, hide_index=True)

fig = px.bar(
    sec_stats, x='broad_sector', y='return_on_equity_pct',
    title="Median ROE across Nifty 100 Broad Sectors",
    labels={'broad_sector': 'Sector', 'return_on_equity_pct': 'Median ROE %'},
    color='return_on_equity_pct', color_continuous_scale='Viridis', height=400
)
st.plotly_chart(fig, use_container_width=True)
