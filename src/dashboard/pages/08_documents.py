import sqlite3
import streamlit as st
import pandas as pd
from utils.db import DB_PATH

st.title("📑 Annual Reports & Filings Repository")

conn = sqlite3.connect(DB_PATH)
df_docs = pd.read_sql_query("SELECT d.company_id, c.company_name, d.year, d.annual_report FROM documents d JOIN companies c ON d.company_id = c.id ORDER BY d.year DESC", conn)
conn.close()

st.caption(f"Repository contains {len(df_docs)} annual filing links across Nifty 100 constituent universe.")

search_txt = st.text_input("Search by Ticker or Company Name", "")
if search_txt:
    df_docs = df_docs[
        df_docs['company_id'].str.contains(search_txt, case=False) |
        df_docs['company_name'].str.contains(search_txt, case=False)
    ]

years = sorted(list(df_docs['year'].unique()), reverse=True)
sel_yr = st.selectbox("Filter by Financial Year", ["All Years"] + years)
if sel_yr != "All Years":
    df_docs = df_docs[df_docs['year'] == sel_yr]

st.dataframe(
    df_docs,
    column_config={
        "annual_report": st.column_config.LinkColumn("BSE India Filing PDF")
    },
    use_container_width=True,
    hide_index=True
)
