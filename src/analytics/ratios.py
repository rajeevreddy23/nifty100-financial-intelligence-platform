"""Financial Ratio Engine: Computes 50+ KPIs across all company-years and updates SQLite."""
import os
import sqlite3
import pandas as pd
import numpy as np
import logging
from cagr import compute_cagr
from cashflow_kpis import classify_capital_allocation, check_distress_pattern

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
DB_PATH = os.path.join(BASE_DIR, 'data/nifty100.db')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')

def compute_ratios():
    """Extract financial statements from SQLite, compute all KPIs, and store in financial_ratios table."""
    logger.info("Starting Ratio Engine computation...")
    conn = sqlite3.connect(DB_PATH)
    
    companies = pd.read_sql_query("SELECT id, face_value, book_value, roce_percentage, roe_percentage FROM companies", conn)
    pl = pd.read_sql_query("SELECT * FROM profitandloss ORDER BY company_id, year", conn)
    bs = pd.read_sql_query("SELECT * FROM balancesheet ORDER BY company_id, year", conn)
    cf = pd.read_sql_query("SELECT * FROM cashflow ORDER BY company_id, year", conn)
    sec = pd.read_sql_query("SELECT company_id, broad_sector FROM sectors", conn)
    mc = pd.read_sql_query("SELECT company_id, year, market_cap_crore, pe_ratio, pb_ratio, ev_ebitda, dividend_yield_pct FROM market_cap", conn)
    
    # Merge core statements on company_id and year
    merged = pd.merge(pl, bs, on=['company_id', 'year'], suffixes=('_pl', '_bs'), how='outer')
    merged = pd.merge(merged, cf, on=['company_id', 'year'], suffixes=('', '_cf'), how='outer')
    merged = pd.merge(merged, sec, on='company_id', how='left')
    merged = pd.merge(merged, companies, left_on='company_id', right_on='id', how='left')

    edge_case_logs = []
    capital_allocation_records = []
    ratio_rows = []

    # Group by company to compute multi-year CAGR and time-series ratios
    grouped = merged.groupby('company_id')

    for cid, group in grouped:
        group = group.sort_values('year').reset_index(drop=True)
        n_rows = len(group)
        is_financial = str(group['broad_sector'].iloc[0]).strip().lower() in ['financials', 'financial services']

        for i, row in group.iterrows():
            yr = row['year']
            sales = row.get('sales') or 0.0
            expenses = row.get('expenses') or 0.0
            op = row.get('operating_profit')
            if op is None or pd.isna(op):
                op = sales - expenses
            dep = row.get('depreciation') or 0.0
            ebit = op - dep
            other_inc = row.get('other_income') or 0.0
            interest = row.get('interest') or 0.0
            net_profit = row.get('net_profit') or 0.0
            eps = row.get('eps')
            div_payout = row.get('dividend_payout')

            eq_cap = row.get('equity_capital') or 0.0
            reserves = row.get('reserves') or 0.0
            total_equity = eq_cap + reserves
            borrowings = row.get('borrowings') or 0.0
            total_assets = row.get('total_assets') or 0.0
            fixed_assets = row.get('fixed_assets') or 0.0
            investments = row.get('investments') or 0.0
            other_asset = row.get('other_asset') or 0.0
            other_liab = row.get('other_liabilities') or 0.0

            cfo = row.get('operating_activity') or 0.0
            cfi = row.get('investing_activity') or 0.0
            cff = row.get('financing_activity') or 0.0
            fcf = cfo + cfi
            capex = abs(cfi)

            # Profitability Ratios
            npm = (net_profit / sales * 100.0) if sales > 0 else None
            opm = (op / sales * 100.0) if sales > 0 else None
            ebit_margin = (ebit / sales * 100.0) if sales > 0 else None

            # Returns Ratios
            if total_equity > 0:
                roe = (net_profit / total_equity) * 100.0
            else:
                roe = None
                edge_case_logs.append(f"{cid} {yr}: Negative or zero equity ({total_equity}), ROE set to None")

            capital_employed = total_equity + borrowings
            if capital_employed > 0:
                roce = (ebit / capital_employed) * 100.0
            else:
                roce = None

            roa = (net_profit / total_assets * 100.0) if total_assets > 0 else None

            # Leverage Ratios
            if total_equity > 0:
                de = borrowings / total_equity
            else:
                de = None
            if borrowings == 0:
                de = 0.0

            if interest == 0 or pd.isna(interest):
                icr = 999.0  # Displayed as Debt Free
                edge_case_logs.append(f"{cid} {yr}: Zero interest expense, ICR set to 999 (Debt Free)")
            else:
                icr = (op + other_inc) / interest

            net_debt = borrowings - investments
            net_debt_ebitda = (net_debt / op) if op > 0 else None

            # Efficiency Ratios
            asset_turnover = (sales / total_assets) if total_assets > 0 else None
            fixed_asset_turnover = (sales / fixed_assets) if fixed_assets > 0 else None
            working_cap_days = ((other_asset - other_liab) / sales * 365.0) if sales > 0 else None

            # Cash Flow Ratios
            cfo_pat = (cfo / net_profit) if net_profit != 0 else None
            capex_intensity = (capex / sales * 100.0) if sales > 0 else None
            fcf_conv = (fcf / op * 100.0) if op != 0 else None

            # Multi-Year CAGRs (3yr, 5yr, 10yr)
            rev_cagr_3yr, pat_cagr_3yr = None, None
            rev_cagr_5yr, pat_cagr_5yr, eps_cagr_5yr = None, None, None
            rev_cagr_10yr = None
            turnaround_flag = None

            if i >= 3:
                r3_base_sales = group.loc[i - 3, 'sales']
                r3_end_sales = sales
                rev_cagr_3yr, flag = compute_cagr(r3_base_sales, r3_end_sales, 3)
                if flag: turnaround_flag = flag

                r3_base_pat = group.loc[i - 3, 'net_profit']
                r3_end_pat = net_profit
                pat_cagr_3yr, flag = compute_cagr(r3_base_pat, r3_end_pat, 3)
                if flag and not turnaround_flag: turnaround_flag = flag

            if i >= 5:
                r5_base_sales = group.loc[i - 5, 'sales']
                r5_end_sales = sales
                rev_cagr_5yr, flag = compute_cagr(r5_base_sales, r5_end_sales, 5)
                if flag and not turnaround_flag: turnaround_flag = flag

                r5_base_pat = group.loc[i - 5, 'net_profit']
                r5_end_pat = net_profit
                pat_cagr_5yr, flag = compute_cagr(r5_base_pat, r5_end_pat, 5)
                if flag and not turnaround_flag: turnaround_flag = flag

                r5_base_eps = group.loc[i - 5, 'eps']
                r5_end_eps = eps
                eps_cagr_5yr, _ = compute_cagr(r5_base_eps, r5_end_eps, 5)

            if i >= 10:
                r10_base_sales = group.loc[i - 10, 'sales']
                r10_end_sales = sales
                rev_cagr_10yr, _ = compute_cagr(r10_base_sales, r10_end_sales, 10)

            # Capital Allocation Classification
            cfo_sign, cfi_sign, cff_sign, pattern_label = classify_capital_allocation(cfo, cfi, cff, cfo_pat or 1.0)
            capital_allocation_records.append({
                'company_id': cid,
                'year': yr,
                'cfo_sign': cfo_sign,
                'cfi_sign': cfi_sign,
                'cff_sign': cff_sign,
                'pattern_label': pattern_label
            })

            # Get market cap for FCF Yield
            yr_int = int(str(yr)[:4])
            mc_match = mc[(mc['company_id'] == cid) & (mc['year'] == yr_int)]
            mkt_cap_val = mc_match['market_cap_crore'].values[0] if len(mc_match) > 0 else None
            fcf_yield = (fcf / mkt_cap_val * 100.0) if mkt_cap_val and mkt_cap_val > 0 else None

            ratio_rows.append({
                'company_id': cid,
                'year': yr,
                'net_profit_margin_pct': round(npm, 2) if npm is not None else None,
                'operating_profit_margin_pct': round(opm, 2) if opm is not None else None,
                'return_on_equity_pct': round(roe, 2) if roe is not None else None,
                'return_on_capital_pct': round(roce, 2) if roce is not None else None,
                'return_on_assets_pct': round(roa, 2) if roa is not None else None,
                'debt_to_equity': round(de, 2) if de is not None else None,
                'interest_coverage': round(icr, 2) if icr is not None else None,
                'asset_turnover': round(asset_turnover, 2) if asset_turnover is not None else None,
                'fixed_asset_turnover': round(fixed_asset_turnover, 2) if fixed_asset_turnover is not None else None,
                'working_capital_days': round(working_cap_days, 1) if working_cap_days is not None else None,
                'revenue_cagr_3yr': rev_cagr_3yr,
                'revenue_cagr_5yr': rev_cagr_5yr,
                'revenue_cagr_10yr': rev_cagr_10yr,
                'pat_cagr_3yr': pat_cagr_3yr,
                'pat_cagr_5yr': pat_cagr_5yr,
                'eps_cagr_5yr': eps_cagr_5yr,
                'free_cash_flow_cr': round(fcf, 2),
                'cfo_pat_ratio': round(cfo_pat, 2) if cfo_pat is not None else None,
                'capex_intensity_pct': round(capex_intensity, 2) if capex_intensity is not None else None,
                'fcf_conversion_pct': round(fcf_conv, 2) if fcf_conv is not None else None,
                'fcf_yield_pct': round(fcf_yield, 2) if fcf_yield is not None else None,
                'total_debt_cr': round(borrowings, 2),
                'cash_from_operations_cr': round(cfo, 2),
                'capex_cr': round(capex, 2),
                'composite_score': None,  # Computed in next step
                'turnaround_flag': turnaround_flag
            })

    df_ratios = pd.DataFrame(ratio_rows)
    df_cap = pd.DataFrame(capital_allocation_records)

    # Compute Composite Quality Score across all companies
    # 35% Profitability (ROE 15, ROCE 10, NPM 10)
    # 30% Cash Quality (FCF CAGR 15, CFO/PAT 10, FCF > 0 flag 5)
    # 20% Growth (Revenue CAGR 5yr 10, PAT CAGR 5yr 10)
    # 15% Leverage (D/E score 10, ICR score 5)
    def normalize_min_max(s):
        p10 = s.quantile(0.10)
        p90 = s.quantile(0.90)
        s_clipped = s.clip(lower=p10, upper=p90)
        rng = p90 - p10
        if rng == 0:
            return pd.Series(50.0, index=s.index)
        return ((s_clipped - p10) / rng) * 100.0

    roe_score = normalize_min_max(df_ratios['return_on_equity_pct'].fillna(0))
    roce_score = normalize_min_max(df_ratios['return_on_capital_pct'].fillna(0))
    npm_score = normalize_min_max(df_ratios['net_profit_margin_pct'].fillna(0))
    prof_score = 0.15 * roe_score + 0.10 * roce_score + 0.10 * npm_score

    cfo_pat_score = normalize_min_max(df_ratios['cfo_pat_ratio'].fillna(0))
    fcf_flag_score = (df_ratios['free_cash_flow_cr'] > 0).astype(float) * 100.0
    fcf_cagr_score = normalize_min_max(df_ratios['pat_cagr_5yr'].fillna(0)) # proxy
    cash_score = 0.15 * fcf_cagr_score + 0.10 * cfo_pat_score + 0.05 * fcf_flag_score

    rev_g_score = normalize_min_max(df_ratios['revenue_cagr_5yr'].fillna(0))
    pat_g_score = normalize_min_max(df_ratios['pat_cagr_5yr'].fillna(0))
    growth_score = 0.10 * rev_g_score + 0.10 * pat_g_score

    # Leverage score: lower D/E is better. ICR: higher is better
    de_vals = df_ratios['debt_to_equity'].fillna(1.0)
    de_score = de_vals.apply(lambda x: 100.0 if x == 0 else (85.0 if x <= 0.5 else (70.0 if x <= 1.0 else (50.0 if x <= 2.0 else 0.0))))
    icr_vals = df_ratios['interest_coverage'].fillna(3.0)
    icr_score = icr_vals.apply(lambda x: 100.0 if x >= 10 else (75.0 if x >= 5 else (50.0 if x >= 3 else 0.0)))
    lev_score = 0.10 * de_score + 0.05 * icr_score

    df_ratios['composite_score'] = (prof_score + cash_score + growth_score + lev_score).round(1)

    # Save to SQLite
    df_ratios.to_sql('financial_ratios', conn, if_exists='replace', index=False)
    df_cap.to_sql('capital_allocation', conn, if_exists='replace', index=False)
    conn.close()

    # Save outputs
    cap_csv_path = os.path.join(OUTPUT_DIR, 'capital_allocation.csv')
    df_cap.to_csv(cap_csv_path, index=False)

    edge_log_path = os.path.join(OUTPUT_DIR, 'ratio_edge_cases.log')
    with open(edge_log_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(edge_case_logs[:200]))

    logger.info(f"Ratio Engine finished. Populated {len(df_ratios)} rows in financial_ratios table.")
    logger.info(f"Capital allocation patterns saved to {cap_csv_path}")
    logger.info(f"Edge case logs saved to {edge_log_path}")

if __name__ == '__main__':
    compute_ratios()
