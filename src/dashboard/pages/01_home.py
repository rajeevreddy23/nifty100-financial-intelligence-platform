import streamlit as st
import plotly.express as px
from utils.db import load_latest_universe

st.title("📊 Universe Overview & Sector Health")
df = load_latest_universe()

selected_sector = st.selectbox("Filter by Sector", ["All Sectors"] + sorted(list(df['broad_sector'].dropna().unique())))
if selected_sector != "All Sectors":
    df_show = df[df['broad_sector'] == selected_sector]
else:
    df_show = df

c1, c2, c3, c4 = st.columns(4)
c1.metric("Companies Shown", len(df_show))
c2.metric("Median ROE", f"{df_show['return_on_equity_pct'].median():.1f}%")
c3.metric("Median ROCE", f"{df_show['return_on_capital_pct'].median():.1f}%")
c4.metric("Median P/E", f"{df_show['pe_ratio'].median():.1f}x")

st.subheader("Profitability vs Scale")
fig = px.scatter(
    df_show, x="sales", y="return_on_equity_pct",
    size="market_cap_crore", color="broad_sector",
    hover_name="company_name", text="id",
    labels={"sales": "Sales / Revenue (₹ Cr)", "return_on_equity_pct": "ROE %", "market_cap_crore": "Market Cap"},
    height=480
)
fig.update_traces(textposition='top center')
st.plotly_chart(fig, use_container_width=True)

st.subheader("Constituents Table")
cols = ['id', 'company_name', 'broad_sector', 'return_on_equity_pct', 'return_on_capital_pct', 'debt_to_equity', 'free_cash_flow_cr', 'pe_ratio', 'composite_score']
st.dataframe(df_show[cols], use_container_width=True, hide_index=True)
