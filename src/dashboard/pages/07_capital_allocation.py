import streamlit as st
import plotly.express as px
from utils.db import load_latest_universe

st.title("🧭 Capital Allocation Patterns & Health Matrix")

df = load_latest_universe()

alloc_counts = df['pattern_label'].value_counts().reset_index()
alloc_counts.columns = ['Pattern Label', 'Company Count']

c1, c2 = st.columns([1, 1.5])
with c1:
    st.subheader("Capital Pattern Distribution")
    fig = px.pie(alloc_counts, names='Pattern Label', values='Company Count', hole=0.4)
    st.plotly_chart(fig, use_container_width=True)

with c2:
    st.subheader("Constituents by Pattern")
    sel_pat = st.selectbox("Filter Pattern", ["All Patterns"] + alloc_counts['Pattern Label'].tolist())
    if sel_pat != "All Patterns":
        df_pat = df[df['pattern_label'] == sel_pat]
    else:
        df_pat = df
    st.dataframe(df_pat[['id', 'company_name', 'broad_sector', 'free_cash_flow_cr', 'debt_to_equity', 'pattern_label']], use_container_width=True, hide_index=True)
