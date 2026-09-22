import os
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from utils.db import load_companies, load_company_history

st.title("🏢 Company Intelligence Profile")

companies = load_companies()
ticker_options = sorted(companies['id'].tolist())
selected_ticker = st.selectbox("Search / Select NSE Ticker", ticker_options, index=ticker_options.index("TCS") if "TCS" in ticker_options else 0)

comp_row = companies[companies['id'] == selected_ticker].iloc[0]
hist = load_company_history(selected_ticker)

st.subheader(f"{comp_row['company_name']} ({selected_ticker})")
st.caption(f"Sector: **{comp_row.get('broad_sector', 'N/A')}** | Sub-Sector: **{comp_row.get('sub_sector', 'N/A')}** | Market Cap Tier: **{comp_row.get('market_cap_category', 'Large Cap')}**")

tearsheet_path = os.path.abspath(os.path.join(os.path.dirname(__file__), f"../../../reports/tearsheets/{selected_ticker}_tearsheet.pdf"))
if os.path.exists(tearsheet_path):
    with open(tearsheet_path, "rb") as pdf_file:
        st.download_button(
            label="📄 Download 2-Page Tearsheet PDF",
            data=pdf_file,
            file_name=f"{selected_ticker}_tearsheet.pdf",
            mime="application/pdf"
        )

r_latest = hist['ratios'].iloc[-1] if len(hist['ratios']) > 0 else {}
mc_latest = hist['mc'].iloc[-1] if len(hist['mc']) > 0 else {}

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("ROE %", f"{r_latest.get('return_on_equity_pct', 0):.1f}%" if pd.notna(r_latest.get('return_on_equity_pct')) else "-")
c2.metric("ROCE %", f"{r_latest.get('return_on_capital_pct', 0):.1f}%" if pd.notna(r_latest.get('return_on_capital_pct')) else "-")
c3.metric("Net Margin", f"{r_latest.get('net_profit_margin_pct', 0):.1f}%" if pd.notna(r_latest.get('net_profit_margin_pct')) else "-")
c4.metric("D/E Ratio", f"{r_latest.get('debt_to_equity', 0):.2f}x" if pd.notna(r_latest.get('debt_to_equity')) else "0.0x")
c5.metric("Free Cash Flow", f"₹{r_latest.get('free_cash_flow_cr', 0):,.0f} Cr" if pd.notna(r_latest.get('free_cash_flow_cr')) else "-")
c6.metric("P/E Multiple", f"{mc_latest.get('pe_ratio', 0):.1f}x" if pd.notna(mc_latest.get('pe_ratio')) else "-")

st.markdown("---")

t1, t2, t3 = st.tabs(["Profit & Loss Trend", "Cash Flow Breakdown", "Pros & Cons Insights"])
with t1:
    pl = hist['pl']
    if len(pl) > 0:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=pl['year'], y=pl['sales'], name="Sales (₹ Cr)", marker_color='#1f77b4'))
        fig.add_trace(go.Bar(x=pl['year'], y=pl['net_profit'], name="Net Profit (PAT ₹ Cr)", marker_color='#2ca02c'))
        fig.update_layout(barmode='group', title="Revenue & Net Profit History", height=380)
        st.plotly_chart(fig, use_container_width=True)

with t2:
    cf = hist['cf']
    if len(cf) > 0:
        fig_cf = go.Figure()
        fig_cf.add_trace(go.Bar(x=cf['year'], y=cf['operating_activity'], name="Cash from Operations (CFO)", marker_color='#2ca02c'))
        fig_cf.add_trace(go.Bar(x=cf['year'], y=cf['investing_activity'], name="Cash from Investing (CFI)", marker_color='#d62728'))
        fig_cf.add_trace(go.Bar(x=cf['year'], y=cf['financing_activity'], name="Cash from Financing (CFF)", marker_color='#ff7f0e'))
        fig_cf.update_layout(barmode='relative', title="Cash Flow Statement Dynamics", height=380)
        st.plotly_chart(fig_cf, use_container_width=True)

with t3:
    pc_csv = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../output/pros_cons_generated.csv"))
    if os.path.exists(pc_csv):
        df_pc_all = pd.read_csv(pc_csv)
        comp_pc = df_pc_all[df_pc_all['company_id'] == selected_ticker]
        col_p, col_c = st.columns(2)
        with col_p:
            st.markdown("### 🟢 Strengths (Pros)")
            for _, r in comp_pc[comp_pc['type'] == 'pro'].iterrows():
                st.success(f"**{r['rule_triggered']}**: {r['text']}")
        with col_c:
            st.markdown("### 🔴 Risks & Considerations (Cons)")
            for _, r in comp_pc[comp_pc['type'] == 'con'].iterrows():
                st.error(f"**{r['rule_triggered']}**: {r['text']}")
