import os
import streamlit as st
import pandas as pd
from PIL import Image
from utils.db import load_peer_groups, load_latest_universe

st.title("👥 Peer Group Benchmarking & Comparison")

pg = load_peer_groups()
group_names = sorted(list(pg['peer_group_name'].unique()))
selected_group = st.selectbox("Select Peer Group", group_names)

group_members = pg[pg['peer_group_name'] == selected_group]
benchmark_row = group_members[group_members['is_benchmark'] == 1]
benchmark_ticker = benchmark_row['company_id'].values[0] if len(benchmark_row) > 0 else group_members['company_id'].iloc[0]

st.info(f"Group: **{selected_group}** ({len(group_members)} constituents) | Designated Benchmark Leader: **{benchmark_ticker}**")

univ = load_latest_universe()
comp_data = univ[univ['id'].isin(group_members['company_id'])].copy()

cols = ['id', 'company_name', 'return_on_equity_pct', 'return_on_capital_pct', 'net_profit_margin_pct', 'debt_to_equity', 'free_cash_flow_cr', 'revenue_cagr_5yr', 'pe_ratio', 'composite_score']
st.subheader("Peer Comparison Matrix")
st.dataframe(comp_data[cols], use_container_width=True, hide_index=True)

selected_member = st.selectbox("Select Company for Radar Analysis", group_members['company_id'].tolist())
radar_path = os.path.abspath(os.path.join(os.path.dirname(__file__), f"../../../reports/radar_charts/{selected_member}_radar.png"))
if os.path.exists(radar_path):
    img = Image.open(radar_path)
    st.image(img, caption=f"{selected_member} Performance vs Peer Average", width=550)
else:
    st.warning("Radar chart image not available.")
