"""Valuation & Market Data Module: historical multiples, overvaluation flags, and exports."""
import os
import sqlite3
import pandas as pd
import numpy as np
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
DB_PATH = os.path.join(BASE_DIR, 'data/nifty100.db')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')

def run_valuation_module():
    logger.info("Running Valuation Module...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)

    # Core data
    mc = pd.read_sql_query("SELECT * FROM market_cap", conn)
    sec = pd.read_sql_query("SELECT company_id, broad_sector, sub_sector FROM sectors", conn)
    comp = pd.read_sql_query("SELECT id, company_name FROM companies", conn)
    
    # Latest ratios per company
    q_r = """
    SELECT r.company_id, r.year, r.return_on_equity_pct, r.free_cash_flow_cr, r.composite_score
    FROM financial_ratios r
    INNER JOIN (
        SELECT company_id, MAX(year) as max_year
        FROM financial_ratios
        WHERE net_profit_margin_pct IS NOT NULL
        GROUP BY company_id
    ) latest ON r.company_id = latest.company_id AND r.year = latest.max_year
    """
    ratios = pd.read_sql_query(q_r, conn)
    conn.close()

    # Get latest market cap row per company
    latest_mc = mc.sort_values('year').groupby('company_id').last().reset_index()
    # Compute 5-year median multiples
    five_yr_mc = mc[mc['year'] >= 2020].groupby('company_id').agg({
        'pe_ratio': 'median',
        'pb_ratio': 'median',
        'ev_ebitda': 'median',
        'dividend_yield_pct': 'mean'
    }).rename(columns={
        'pe_ratio': 'pe_5yr_median',
        'pb_ratio': 'pb_5yr_median',
        'ev_ebitda': 'ev_ebitda_5yr_median',
        'dividend_yield_pct': 'div_yield_5yr_avg'
    }).reset_index()

    val = pd.merge(comp, sec, left_on='id', right_on='company_id', how='inner')
    val = pd.merge(val, latest_mc, on='company_id', how='left')
    val = pd.merge(val, five_yr_mc, on='company_id', how='left')
    val = pd.merge(val, ratios, on='company_id', how='left', suffixes=('', '_ratio'))

    # FCF Yield
    val['fcf_yield_pct'] = np.where(
        (val['market_cap_crore'] > 0) & (val['free_cash_flow_cr'].notna()),
        (val['free_cash_flow_cr'] / val['market_cap_crore']) * 100.0,
        0.0
    ).round(2)

    # Sector median P/E and EV/EBITDA
    sector_medians = val.groupby('broad_sector')[['pe_ratio', 'ev_ebitda']].median().rename(
        columns={'pe_ratio': 'sector_pe_median', 'ev_ebitda': 'sector_ev_ebitda_median'}
    ).reset_index()

    val = pd.merge(val, sector_medians, on='broad_sector', how='left')

    # Overvaluation / Undervaluation flags
    # P/E > (sector_median * 1.5) -> 'Caution' badge
    # P/E < (sector_median * 0.7) -> 'Discount' badge
    flags = []
    reasons = []
    for _, r in val.iterrows():
        pe = r.get('pe_ratio')
        sec_pe = r.get('sector_pe_median')
        if pd.notna(pe) and pd.notna(sec_pe) and sec_pe > 0:
            if pe > sec_pe * 1.5:
                flags.append("Caution (Overvalued)")
                reasons.append(f"P/E {pe:.1f}x > 1.5x sector median ({sec_pe:.1f}x)")
            elif pe < sec_pe * 0.7 and pe > 0:
                flags.append("Discount (Undervalued)")
                reasons.append(f"P/E {pe:.1f}x < 0.7x sector median ({sec_pe:.1f}x)")
            else:
                flags.append("Fair Value")
                reasons.append("Within normal sector range")
        else:
            flags.append("N/A")
            reasons.append("Missing multiple")

    val['valuation_badge'] = flags
    val['valuation_reason'] = reasons

    # Export valuation_summary.xlsx
    summary_path = os.path.join(OUTPUT_DIR, 'valuation_summary.xlsx')
    val_cols = [
        'company_id', 'company_name', 'broad_sector', 'sub_sector',
        'market_cap_crore', 'enterprise_value_crore', 'pe_ratio', 'pe_5yr_median',
        'sector_pe_median', 'pb_ratio', 'pb_5yr_median', 'ev_ebitda',
        'ev_ebitda_5yr_median', 'sector_ev_ebitda_median', 'dividend_yield_pct',
        'fcf_yield_pct', 'valuation_badge', 'valuation_reason'
    ]
    cols = [c for c in val_cols if c in val.columns]
    val[cols].to_excel(summary_path, index=False)
    logger.info(f"Valuation summary written to {summary_path}")

    # Export valuation_flags.csv
    flags_path = os.path.join(OUTPUT_DIR, 'valuation_flags.csv')
    val[val['valuation_badge'].isin(['Caution (Overvalued)', 'Discount (Undervalued)'])][
        ['company_id', 'company_name', 'broad_sector', 'pe_ratio', 'sector_pe_median', 'valuation_badge', 'valuation_reason']
    ].to_csv(flags_path, index=False)
    logger.info(f"Valuation flags saved to {flags_path}")
    return val

if __name__ == '__main__':
    run_valuation_module()
