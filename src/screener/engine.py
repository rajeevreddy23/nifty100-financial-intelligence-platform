"""Multi-criteria stock screener and ranking engine with 6 presets and custom filter builder."""
import os
import sqlite3
import yaml
import pandas as pd
import numpy as np
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
DB_PATH = os.path.join(BASE_DIR, 'data/nifty100.db')
CONFIG_PATH = os.path.join(BASE_DIR, 'config/screener_config.yaml')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')

def load_screener_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def get_latest_screener_dataset():
    """Builds a unified dataframe for all 92 companies using their latest fiscal year data."""
    conn = sqlite3.connect(DB_PATH)
    
    # Latest ratios per company where annual financial statements exist
    q_ratios = """
    SELECT r.* 
    FROM financial_ratios r
    INNER JOIN (
        SELECT company_id, MAX(year) as max_year 
        FROM financial_ratios 
        WHERE net_profit_margin_pct IS NOT NULL
        GROUP BY company_id
    ) latest ON r.company_id = latest.company_id AND r.year = latest.max_year
    """
    df_r = pd.read_sql_query(q_ratios, conn)

    # Core company master
    df_c = pd.read_sql_query("SELECT id, company_name, book_value, face_value FROM companies", conn)
    # Sectors
    df_s = pd.read_sql_query("SELECT company_id, broad_sector, sub_sector, index_weight_pct, market_cap_category FROM sectors", conn)
    
    # Latest Market Cap & Multiples
    q_mc = """
    SELECT m.* 
    FROM market_cap m
    INNER JOIN (
        SELECT company_id, MAX(year) as max_year 
        FROM market_cap 
        GROUP BY company_id
    ) latest ON m.company_id = latest.company_id AND m.year = latest.max_year
    """
    df_mc = pd.read_sql_query(q_mc, conn)

    # Latest P&L sales & net profit & dividend payout
    q_pl = """
    SELECT p.company_id, p.year, p.sales, p.operating_profit, p.net_profit, p.eps, p.dividend_payout
    FROM profitandloss p
    INNER JOIN (
        SELECT company_id, MAX(year) as max_year 
        FROM profitandloss 
        GROUP BY company_id
    ) latest ON p.company_id = latest.company_id AND p.year = latest.max_year
    """
    df_pl = pd.read_sql_query(q_pl, conn)

    conn.close()

    # Merge into single table
    res = pd.merge(df_c, df_s, left_on='id', right_on='company_id', how='inner')
    res = pd.merge(res, df_r, left_on='id', right_on='company_id', suffixes=('', '_ratio'), how='inner')
    res = pd.merge(res, df_mc, left_on='id', right_on='company_id', suffixes=('', '_mc'), how='left')
    res = pd.merge(res, df_pl, left_on='id', right_on='company_id', suffixes=('', '_pl'), how='left')

    # Re-calculate FCF yield with market cap if needed
    if 'market_cap_crore' in res.columns:
        res['fcf_yield'] = np.where(
            (res['market_cap_crore'] > 0) & (res['free_cash_flow_cr'].notna()),
            (res['free_cash_flow_cr'] / res['market_cap_crore']) * 100.0,
            0.0
        )
    return res

def apply_filters(df, filters):
    """Filters dataframe based on dictionary of criteria."""
    filtered = df.copy()

    if 'min_roe' in filters and filters['min_roe'] is not None:
        filtered = filtered[filtered['return_on_equity_pct'] >= filters['min_roe']]

    if 'max_de' in filters and filters['max_de'] is not None:
        max_de_val = filters['max_de']
        is_fin = filtered['broad_sector'].str.lower().isin(['financials', 'financial services'])
        cond_de = (filtered['debt_to_equity'] <= max_de_val) | is_fin
        filtered = filtered[cond_de]

    if 'min_fcf' in filters and filters['min_fcf'] is not None:
        filtered = filtered[filtered['free_cash_flow_cr'] >= filters['min_fcf']]

    if 'min_rev_cagr_5yr' in filters and filters['min_rev_cagr_5yr'] is not None:
        filtered = filtered[filtered['revenue_cagr_5yr'] >= filters['min_rev_cagr_5yr']]

    if 'min_rev_cagr_3yr' in filters and filters['min_rev_cagr_3yr'] is not None:
        filtered = filtered[filtered['revenue_cagr_3yr'] >= filters['min_rev_cagr_3yr']]

    if 'min_pat_cagr_5yr' in filters and filters['min_pat_cagr_5yr'] is not None:
        filtered = filtered[filtered['pat_cagr_5yr'] >= filters['min_pat_cagr_5yr']]

    if 'max_pe' in filters and filters['max_pe'] is not None:
        filtered = filtered[(filtered['pe_ratio'] > 0) & (filtered['pe_ratio'] <= filters['max_pe'])]

    if 'max_pb' in filters and filters['max_pb'] is not None:
        filtered = filtered[(filtered['pb_ratio'] > 0) & (filtered['pb_ratio'] <= filters['max_pb'])]

    if 'min_div_yield' in filters and filters['min_div_yield'] is not None:
        filtered = filtered[filtered['dividend_yield_pct'] >= filters['min_div_yield']]

    if 'max_payout_ratio' in filters and filters['max_payout_ratio'] is not None:
        filtered = filtered[filtered['dividend_payout'] <= filters['max_payout_ratio']]

    if 'min_sales' in filters and filters['min_sales'] is not None:
        filtered = filtered[filtered['sales'] >= filters['min_sales']]

    if 'sector' in filters and filters['sector']:
        filtered = filtered[filtered['broad_sector'].str.lower() == filters['sector'].lower()]

    return filtered

def run_screeners():
    """Runs all 6 preset screeners and saves results to screener_output.xlsx."""
    df_all = get_latest_screener_dataset()
    config = load_screener_config()
    presets = config['presets']

    output_path = os.path.join(OUTPUT_DIR, 'screener_output.xlsx')
    logger.info(f"Writing screener results to {output_path}...")

    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        for pkey, pval in presets.items():
            filtered = apply_filters(df_all, pval['filters'])
            rank_col = pval['ranking_metric']
            asc = pval.get('ascending', False)
            if rank_col in filtered.columns:
                filtered = filtered.sort_values(rank_col, ascending=asc)
            
            # Select display columns
            cols_to_show = [
                'id', 'company_name', 'broad_sector', 'sub_sector',
                'return_on_equity_pct', 'return_on_capital_pct', 'net_profit_margin_pct',
                'debt_to_equity', 'interest_coverage', 'free_cash_flow_cr',
                'revenue_cagr_5yr', 'pat_cagr_5yr', 'pe_ratio', 'pb_ratio',
                'dividend_yield_pct', 'composite_score', 'sales', 'net_profit'
            ]
            cols = [c for c in cols_to_show if c in filtered.columns]
            sheet_name = pval['name'][:31] # Excel sheet name limit
            filtered[cols].to_excel(writer, sheet_name=sheet_name, index=False)
            logger.info(f"Preset '{pval['name']}': {len(filtered)} companies matched")

        # Full Universe Sheet
        df_all_sorted = df_all.sort_values('composite_score', ascending=False)
        df_all_sorted.to_excel(writer, sheet_name="All 92 Universe", index=False)

    logger.info("Screener execution complete.")
    return df_all

if __name__ == '__main__':
    run_screeners()
