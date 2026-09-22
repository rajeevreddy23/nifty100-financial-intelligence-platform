import os
import sqlite3
import pandas as pd
import streamlit as st

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
DB_PATH = os.path.join(BASE_DIR, 'data/nifty100.db')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')

@st.cache_data(ttl=600)
def load_companies():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT c.*, s.broad_sector, s.sub_sector, s.market_cap_category FROM companies c LEFT JOIN sectors s ON c.id = s.company_id", conn)
    conn.close()
    return df

@st.cache_data(ttl=600)
def load_latest_universe():
    conn = sqlite3.connect(DB_PATH)
    q = """
    SELECT c.id, c.company_name, s.broad_sector, s.sub_sector,
           r.year, r.return_on_equity_pct, r.return_on_capital_pct, r.net_profit_margin_pct,
           r.operating_profit_margin_pct, r.debt_to_equity, r.interest_coverage,
           r.free_cash_flow_cr, r.revenue_cagr_5yr, r.pat_cagr_5yr, r.composite_score,
           m.market_cap_crore, m.pe_ratio, m.pb_ratio, m.ev_ebitda, m.dividend_yield_pct,
           p.sales, p.net_profit, ca.pattern_label
    FROM companies c
    LEFT JOIN sectors s ON c.id = s.company_id
    INNER JOIN (
        SELECT company_id, MAX(year) as max_year
        FROM financial_ratios
        WHERE net_profit_margin_pct IS NOT NULL
        GROUP BY company_id
    ) latest ON c.id = latest.company_id
    LEFT JOIN financial_ratios r ON c.id = r.company_id AND r.year = latest.max_year
    LEFT JOIN market_cap m ON c.id = m.company_id AND m.year = CAST(SUBSTR(latest.max_year, 1, 4) AS INTEGER)
    LEFT JOIN profitandloss p ON c.id = p.company_id AND p.year = latest.max_year
    LEFT JOIN capital_allocation ca ON c.id = ca.company_id AND ca.year = latest.max_year
    ORDER BY r.composite_score DESC
    """
    df = pd.read_sql_query(q, conn)
    conn.close()
    return df

@st.cache_data(ttl=600)
def load_company_history(ticker: str):
    conn = sqlite3.connect(DB_PATH)
    pl = pd.read_sql_query(f"SELECT * FROM profitandloss WHERE company_id = '{ticker}' ORDER BY year ASC", conn)
    bs = pd.read_sql_query(f"SELECT * FROM balancesheet WHERE company_id = '{ticker}' ORDER BY year ASC", conn)
    cf = pd.read_sql_query(f"SELECT * FROM cashflow WHERE company_id = '{ticker}' ORDER BY year ASC", conn)
    ratios = pd.read_sql_query(f"SELECT * FROM financial_ratios WHERE company_id = '{ticker}' ORDER BY year ASC", conn)
    mc = pd.read_sql_query(f"SELECT * FROM market_cap WHERE company_id = '{ticker}' ORDER BY year ASC", conn)
    pc = pd.read_sql_query(f"SELECT * FROM prosandcons WHERE company_id = '{ticker}'", conn)
    docs = pd.read_sql_query(f"SELECT * FROM documents WHERE company_id = '{ticker}' ORDER BY year DESC", conn)
    conn.close()
    return {'pl': pl, 'bs': bs, 'cf': cf, 'ratios': ratios, 'mc': mc, 'pc': pc, 'docs': docs}

@st.cache_data(ttl=600)
def load_peer_groups():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM peer_groups ORDER BY peer_group_name, company_id", conn)
    conn.close()
    return df
