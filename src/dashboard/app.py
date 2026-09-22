import streamlit as st
import pandas as pd
import plotly.express as px
from utils.db import load_latest_universe

st.set_page_config(
    page_title="Nifty 100 Financial Intelligence",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.sidebar.title("📈 Nifty 100 Platform")
st.sidebar.markdown("**Institutional Fundamental Intelligence**")
st.sidebar.markdown("---")

st.title("🏛️ Nifty 100 Financial Intelligence Platform")
st.markdown("Welcome to the institutional equity intelligence platform covering **92 Nifty 100 constituents** across 10–14 years of financial statements.")

df_univ = load_latest_universe()

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.metric("Total Companies", f"{len(df_univ)}")
with c2:
    avg_roe = df_univ['return_on_equity_pct'].dropna().mean()
    st.metric("Average ROE", f"{avg_roe:.1f}%")
with c3:
    med_pe = df_univ['pe_ratio'].dropna().median()
    st.metric("Median P/E", f"{med_pe:.1f}x")
with c4:
    tot_mktcap = df_univ['market_cap_crore'].dropna().sum() / 100000
    st.metric("Total Market Cap", f"₹{tot_mktcap:.2f}L Cr")
with c5:
    qual_cnt = len(df_univ[df_univ['composite_score'] >= 70])
    st.metric("High Quality (Score ≥ 70)", f"{qual_cnt}")

st.markdown("---")

col_l, col_r = st.columns([1.2, 1])
with col_l:
    st.subheader("Top 10 High Quality Leaders (Composite Score)")
    top10 = df_univ[['id', 'company_name', 'broad_sector', 'return_on_equity_pct', 'debt_to_equity', 'free_cash_flow_cr', 'composite_score']].head(10)
    st.dataframe(
        top10.style.format({
            'return_on_equity_pct': '{:.1f}%',
            'debt_to_equity': '{:.2f}x',
            'free_cash_flow_cr': '₹{:,.0f} Cr',
            'composite_score': '{:.1f}'
        }),
        use_container_width=True,
        hide_index=True
    )

with col_r:
    st.subheader("Sector Allocation & Market Weight")
    sec_counts = df_univ.groupby('broad_sector')['market_cap_crore'].sum().reset_index()
    fig = px.pie(
        sec_counts, values='market_cap_crore', names='broad_sector',
        hole=0.45, color_discrete_sequence=px.colors.qualitative.Prism
    )
    fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=320)
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.info("👈 Use the left sidebar navigation to explore Company Profiles, Screener, Peer Comparison, Trends, Sectors, Capital Allocation, and Documents.")
