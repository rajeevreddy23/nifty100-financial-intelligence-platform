"""FastAPI server for Nifty 100 Financial Intelligence Platform (16 REST Endpoints)."""
import os
import time
import sqlite3
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np

app = FastAPI(
    title="Nifty 100 Financial Intelligence API",
    description="REST API service providing fundamental data, ratio analytics, screener queries, peer benchmarking, and automated reports for 92 Nifty 100 companies.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

START_TIME = time.time()
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
DB_PATH = os.path.join(BASE_DIR, 'data/nifty100.db')
REPORTS_DIR = os.path.join(BASE_DIR, 'reports/tearsheets')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# 1. Health check
@app.get("/api/v1/health", tags=["System"])
def health_check():
    """Returns database status, row counts for all 10 tables, uptime, and platform version."""
    uptime = int(time.time() - START_TIME)
    try:
        conn = get_db()
        tables = [
            'companies', 'profitandloss', 'balancesheet', 'cashflow',
            'analysis', 'documents', 'prosandcons', 'sectors',
            'stock_prices', 'market_cap'
        ]
        counts = {}
        for t in tables:
            r = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()
            counts[t] = r[0]
        conn.close()
        return {
            "status": "ok",
            "uptime_seconds": uptime,
            "version": "1.0.0",
            "db_row_counts": counts
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {str(e)}")

# 2. Companies list
@app.get("/api/v1/companies", tags=["Companies"])
def list_companies(sector: Optional[str] = None, market_cap_category: Optional[str] = None, search: Optional[str] = None):
    """List all 92 companies with id, name, sector, sub-sector, ROE %, ROCE %."""
    conn = get_db()
    q = """
    SELECT c.id, c.company_name, s.broad_sector, s.sub_sector, s.market_cap_category,
           c.roe_percentage, c.roce_percentage, c.company_logo
    FROM companies c
    LEFT JOIN sectors s ON c.id = s.company_id
    WHERE 1=1
    """
    params = []
    if sector:
        q += " AND LOWER(s.broad_sector) = LOWER(?)"
        params.append(sector)
    if market_cap_category:
        q += " AND LOWER(s.market_cap_category) = LOWER(?)"
        params.append(market_cap_category)
    if search:
        q += " AND (LOWER(c.id) LIKE LOWER(?) OR LOWER(c.company_name) LIKE LOWER(?))"
        params.extend([f"%{search}%", f"%{search}%"])
    q += " ORDER BY c.id ASC"

    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# 3. Company Profile
@app.get("/api/v1/companies/{ticker}", tags=["Companies"])
def get_company_profile(ticker: str, year: Optional[str] = None):
    """Full company profile: master data, latest ratios, pros/cons, sector, and capital pattern."""
    ticker = ticker.strip().upper()
    conn = get_db()
    comp = conn.execute("SELECT * FROM companies WHERE id = ?", (ticker,)).fetchone()
    if not comp:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Company '{ticker}' not found")

    sec = conn.execute("SELECT * FROM sectors WHERE company_id = ?", (ticker,)).fetchone()
    
    # Ratios
    if year:
        ratio = conn.execute("SELECT * FROM financial_ratios WHERE company_id = ? AND year = ?", (ticker, year)).fetchone()
    else:
        ratio = conn.execute("SELECT * FROM financial_ratios WHERE company_id = ? AND net_profit_margin_pct IS NOT NULL ORDER BY year DESC LIMIT 1", (ticker,)).fetchone()

    # Pros and Cons from generated CSV or DB
    pc_rows = conn.execute("SELECT * FROM prosandcons WHERE company_id = ?", (ticker,)).fetchall()
    
    conn.close()
    return {
        "company": dict(comp),
        "sector": dict(sec) if sec else {},
        "ratios": dict(ratio) if ratio else {},
        "pros_and_cons": [dict(p) for p in pc_rows]
    }

# 4. P&L History
@app.get("/api/v1/companies/{ticker}/pl", tags=["Financials"])
def get_company_pl(ticker: str, from_year: Optional[str] = None, to_year: Optional[str] = None):
    """P&L history for a company across all available years."""
    ticker = ticker.strip().upper()
    conn = get_db()
    c_check = conn.execute("SELECT id FROM companies WHERE id = ?", (ticker,)).fetchone()
    if not c_check:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Company '{ticker}' not found")

    q = "SELECT * FROM profitandloss WHERE company_id = ?"
    params = [ticker]
    if from_year:
        q += " AND year >= ?"
        params.append(from_year)
    if to_year:
        q += " AND year <= ?"
        params.append(to_year)
    q += " ORDER BY year ASC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# 5. Balance Sheet History
@app.get("/api/v1/companies/{ticker}/bs", tags=["Financials"])
def get_company_bs(ticker: str, from_year: Optional[str] = None, to_year: Optional[str] = None):
    """Balance Sheet history for a company."""
    ticker = ticker.strip().upper()
    conn = get_db()
    c_check = conn.execute("SELECT id FROM companies WHERE id = ?", (ticker,)).fetchone()
    if not c_check:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Company '{ticker}' not found")

    q = "SELECT * FROM balancesheet WHERE company_id = ?"
    params = [ticker]
    if from_year:
        q += " AND year >= ?"
        params.append(from_year)
    if to_year:
        q += " AND year <= ?"
        params.append(to_year)
    q += " ORDER BY year ASC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# 6. Cash Flow History
@app.get("/api/v1/companies/{ticker}/cashflow", tags=["Financials"])
def get_company_cashflow(ticker: str, from_year: Optional[str] = None, to_year: Optional[str] = None):
    """Cash Flow history for a company."""
    ticker = ticker.strip().upper()
    conn = get_db()
    c_check = conn.execute("SELECT id FROM companies WHERE id = ?", (ticker,)).fetchone()
    if not c_check:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Company '{ticker}' not found")

    q = "SELECT * FROM cashflow WHERE company_id = ?"
    params = [ticker]
    if from_year:
        q += " AND year >= ?"
        params.append(from_year)
    if to_year:
        q += " AND year <= ?"
        params.append(to_year)
    q += " ORDER BY year ASC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# 7. Ratios History
@app.get("/api/v1/companies/{ticker}/ratios", tags=["Financials"])
def get_company_ratios(ticker: str, year: Optional[str] = None):
    """All 14 pre-computed KPIs per year for one company."""
    ticker = ticker.strip().upper()
    conn = get_db()
    c_check = conn.execute("SELECT id FROM companies WHERE id = ?", (ticker,)).fetchone()
    if not c_check:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Company '{ticker}' not found")

    if year:
        rows = conn.execute("SELECT * FROM financial_ratios WHERE company_id = ? AND year = ?", (ticker, year)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM financial_ratios WHERE company_id = ? ORDER BY year ASC", (ticker,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# 8. Company Tearsheet PDF download
@app.get("/api/v1/companies/{ticker}/tearsheet", tags=["Reports"])
def get_tearsheet_pdf(ticker: str):
    """Returns pre-generated 2-page tearsheet PDF as a binary stream."""
    ticker = ticker.strip().upper()
    pdf_file = os.path.join(REPORTS_DIR, f"{ticker}_tearsheet.pdf")
    if not os.path.exists(pdf_file):
        raise HTTPException(status_code=404, detail=f"Tearsheet PDF for '{ticker}' not found")
    return FileResponse(pdf_file, media_type='application/pdf', filename=f"{ticker}_tearsheet.pdf")

# 9. Investment Screener
@app.get("/api/v1/screener", tags=["Screener"])
def run_screener_api(
    min_roe: Optional[float] = None,
    max_de: Optional[float] = None,
    min_fcf: Optional[float] = None,
    sector: Optional[str] = None,
    min_rev_cagr_5yr: Optional[float] = None,
    min_pat_cagr_5yr: Optional[float] = None,
    max_pe: Optional[float] = None
):
    """Multi-criteria screener returning ranked list of matching companies."""
    from src.analytics.screener.engine import get_latest_screener_dataset, apply_filters
    df = get_latest_screener_dataset()
    filters = {
        'min_roe': min_roe,
        'max_de': max_de,
        'min_fcf': min_fcf,
        'sector': sector,
        'min_rev_cagr_5yr': min_rev_cagr_5yr,
        'min_pat_cagr_5yr': min_pat_cagr_5yr,
        'max_pe': max_pe
    }
    filtered = apply_filters(df, filters)
    filtered = filtered.sort_values('composite_score', ascending=False)
    cols = [
        'id', 'company_name', 'broad_sector', 'sub_sector', 'return_on_equity_pct',
        'return_on_capital_pct', 'net_profit_margin_pct', 'debt_to_equity',
        'free_cash_flow_cr', 'revenue_cagr_5yr', 'pat_cagr_5yr', 'pe_ratio', 'composite_score'
    ]
    cols = [c for c in cols if c in filtered.columns]
    res_df = filtered[cols].replace({np.nan: None})
    return res_df.to_dict(orient='records')

# 10. Sectors summary
@app.get("/api/v1/sectors", tags=["Sectors"])
def list_sectors():
    """List all sectors with company count, median ROE, median P/E, and median D/E."""
    conn = get_db()
    q = """
    SELECT s.broad_sector as sector_name,
           COUNT(DISTINCT s.company_id) as company_count,
           ROUND(AVG(r.return_on_equity_pct), 1) as median_roe,
           ROUND(AVG(m.pe_ratio), 1) as median_pe,
           ROUND(AVG(r.debt_to_equity), 2) as median_de
    FROM sectors s
    LEFT JOIN (
        SELECT r1.* FROM financial_ratios r1
        INNER JOIN (
            SELECT company_id, MAX(year) as max_year FROM financial_ratios WHERE net_profit_margin_pct IS NOT NULL GROUP BY company_id
        ) l ON r1.company_id = l.company_id AND r1.year = l.max_year
    ) r ON s.company_id = r.company_id
    LEFT JOIN (
        SELECT m1.* FROM market_cap m1
        INNER JOIN (
            SELECT company_id, MAX(year) as max_year FROM market_cap GROUP BY company_id
        ) l2 ON m1.company_id = l2.company_id AND m1.year = l2.max_year
    ) m ON s.company_id = m.company_id
    GROUP BY s.broad_sector
    ORDER BY company_count DESC
    """
    rows = conn.execute(q).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# 11. Companies in sector
@app.get("/api/v1/sectors/{sector}/companies", tags=["Sectors"])
def get_sector_companies(sector: str):
    """List all companies in a sector with top 8 KPIs."""
    conn = get_db()
    q = """
    SELECT s.company_id, c.company_name, s.sub_sector, s.index_weight_pct,
           r.return_on_equity_pct, r.return_on_capital_pct, r.net_profit_margin_pct,
           r.debt_to_equity, r.free_cash_flow_cr, r.revenue_cagr_5yr, r.composite_score
    FROM sectors s
    JOIN companies c ON s.company_id = c.id
    LEFT JOIN (
        SELECT r1.* FROM financial_ratios r1
        INNER JOIN (
            SELECT company_id, MAX(year) as max_year FROM financial_ratios WHERE net_profit_margin_pct IS NOT NULL GROUP BY company_id
        ) l ON r1.company_id = l.company_id AND r1.year = l.max_year
    ) r ON s.company_id = r.company_id
    WHERE LOWER(s.broad_sector) = LOWER(?)
    ORDER BY r.composite_score DESC
    """
    rows = conn.execute(q, (sector,)).fetchall()
    conn.close()
    if not rows:
        raise HTTPException(status_code=404, detail=f"Sector '{sector}' not found")
    return [dict(r) for r in rows]

# 12. Peer group members
@app.get("/api/v1/peers/{group_name}", tags=["Peers"])
def get_peer_group(group_name: str):
    """All companies in a peer group with percentile ranks."""
    conn = get_db()
    q = "SELECT * FROM peer_percentiles WHERE LOWER(peer_group_name) = LOWER(?) ORDER BY company_id, metric"
    rows = conn.execute(q, (group_name,)).fetchall()
    conn.close()
    if not rows:
        raise HTTPException(status_code=404, detail=f"Peer group '{group_name}' not found")
    return [dict(r) for r in rows]

# 13. Radar data: company vs peer group average
@app.get("/api/v1/companies/{ticker}/peers/compare", tags=["Peers"])
def compare_company_peers(ticker: str):
    """Radar data: 8 axis metrics for company + group average + benchmark."""
    ticker = ticker.strip().upper()
    conn = get_db()
    pg_match = conn.execute("SELECT peer_group_name FROM peer_groups WHERE company_id = ?", (ticker,)).fetchone()
    if not pg_match:
        conn.close()
        raise HTTPException(status_code=404, detail=f"No peer group assigned for '{ticker}'")
    
    gname = pg_match[0]
    bench_row = conn.execute("SELECT company_id FROM peer_groups WHERE peer_group_name = ? AND is_benchmark = 1", (gname,)).fetchone()
    bench_ticker = bench_row[0] if bench_row else ticker
    conn.close()

    return {
        "ticker": ticker,
        "peer_group": gname,
        "benchmark": bench_ticker,
        "radar_image_url": f"/reports/radar_charts/{ticker}_radar.png"
    }

# 14. Market Cap & Valuation History
@app.get("/api/v1/market-cap/{ticker}", tags=["Valuation"])
def get_market_cap_history(ticker: str, from_year: Optional[int] = None, to_year: Optional[int] = None):
    """Historical valuation multiples (P/E, P/B, EV/EBITDA) 2019-2024."""
    ticker = ticker.strip().upper()
    conn = get_db()
    c_check = conn.execute("SELECT id FROM companies WHERE id = ?", (ticker,)).fetchone()
    if not c_check:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Company '{ticker}' not found")

    q = "SELECT * FROM market_cap WHERE company_id = ?"
    params = [ticker]
    if from_year:
        q += " AND year >= ?"
        params.append(from_year)
    if to_year:
        q += " AND year <= ?"
        params.append(to_year)
    q += " ORDER BY year ASC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# 15. Portfolio Stats
@app.get("/api/v1/portfolio/stats", tags=["Portfolio"])
def get_portfolio_stats():
    """Portfolio-level statistics: P10-P90 for all core KPIs across all 92 companies."""
    stats_file = os.path.join(OUTPUT_DIR, 'portfolio_stats.csv')
    if os.path.exists(stats_file):
        df = pd.read_csv(stats_file)
        return df.to_dict(orient='records')
    return []

# 16. Documents (Annual Reports)
@app.get("/api/v1/companies/{ticker}/documents", tags=["Documents"])
def get_company_documents(ticker: str, from_year: Optional[int] = None, to_year: Optional[int] = None):
    """Annual report links and validation status for a company."""
    ticker = ticker.strip().upper()
    conn = get_db()
    c_check = conn.execute("SELECT id FROM companies WHERE id = ?", (ticker,)).fetchone()
    if not c_check:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Company '{ticker}' not found")

    q = "SELECT year, annual_report, is_url_valid FROM documents WHERE company_id = ?"
    params = [ticker]
    if from_year:
        q += " AND year >= ?"
        params.append(from_year)
    if to_year:
        q += " AND year <= ?"
        params.append(to_year)
    q += " ORDER BY year DESC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]
