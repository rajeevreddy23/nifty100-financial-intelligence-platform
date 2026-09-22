"""Peer Comparison Engine: percentile ranks, benchmark gaps, radar charts, and Excel export."""
import os
import sqlite3
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
DB_PATH = os.path.join(BASE_DIR, 'data/nifty100.db')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
RADAR_DIR = os.path.join(BASE_DIR, 'reports/radar_charts')

METRICS_20 = [
    'return_on_equity_pct', 'return_on_capital_pct', 'net_profit_margin_pct',
    'operating_profit_margin_pct', 'return_on_assets_pct', 'debt_to_equity',
    'interest_coverage', 'asset_turnover', 'fixed_asset_turnover',
    'working_capital_days', 'revenue_cagr_3yr', 'revenue_cagr_5yr',
    'pat_cagr_3yr', 'pat_cagr_5yr', 'eps_cagr_5yr', 'free_cash_flow_cr',
    'cfo_pat_ratio', 'capex_intensity_pct', 'fcf_conversion_pct', 'composite_score'
]

RADAR_8_AXES = [
    'return_on_equity_pct', 'return_on_capital_pct', 'net_profit_margin_pct',
    'debt_to_equity', 'free_cash_flow_cr', 'pat_cagr_5yr',
    'revenue_cagr_5yr', 'eps_cagr_5yr'
]

def generate_radar_chart(ticker: str, comp_data: dict, peer_avg: dict, save_path: str):
    """Generates an 8-axis polar radar chart for a company vs its peer group average."""
    categories = ['ROE', 'ROCE', 'NPM', 'Low D/E', 'FCF', 'PAT CAGR', 'Rev CAGR', 'EPS CAGR']
    num_vars = len(categories)

    # Compute values scaled 0-100 for radar plotting
    comp_vals = []
    peer_vals = []
    for metric in RADAR_8_AXES:
        cv = comp_data.get(metric, 0) or 0
        pv = peer_avg.get(metric, 0) or 0
        # For D/E: lower is better -> invert for visual plot
        if metric == 'debt_to_equity':
            cv = max(0, 100 - cv * 25)
            pv = max(0, 100 - pv * 25)
        else:
            cv = max(0, min(100, cv * 2 if 'cagr' in metric or 'pct' in metric else (cv/100 if metric == 'free_cash_flow_cr' else cv)))
            pv = max(0, min(100, pv * 2 if 'cagr' in metric or 'pct' in metric else (pv/100 if metric == 'free_cash_flow_cr' else pv)))
        comp_vals.append(cv)
        peer_vals.append(pv)

    comp_vals += comp_vals[:1]
    peer_vals += peer_vals[:1]

    angles = [n / float(num_vars) * 2 * np.pi for n in range(num_vars)]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    plt.xticks(angles[:-1], categories, color='grey', size=9)
    ax.plot(angles, comp_vals, linewidth=2, linestyle='solid', label=ticker, color='#1f77b4')
    ax.fill(angles, comp_vals, '#1f77b4', alpha=0.25)

    ax.plot(angles, peer_vals, linewidth=1.5, linestyle='dashed', label='Peer Average', color='#ff7f0e')
    ax.fill(angles, peer_vals, '#ff7f0e', alpha=0.1)

    plt.title(f"{ticker} vs Peer Average", size=12, color='#333333', y=1.08, fontweight='bold')
    plt.legend(loc='upper right', bbox_to_anchor=(0.1, 0.1), fontsize=8)
    plt.tight_layout()
    plt.savefig(save_path, dpi=120)
    plt.close()

def run_peer_comparison():
    """Computes intra-group percentiles, detects best-in-class / watchlist, and exports."""
    logger.info("Starting Peer Comparison Engine...")
    os.makedirs(RADAR_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    pg = pd.read_sql_query("SELECT peer_group_name, company_id, is_benchmark FROM peer_groups", conn)
    
    # Latest ratios
    q_r = """
    SELECT r.* 
    FROM financial_ratios r
    INNER JOIN (
        SELECT company_id, MAX(year) as max_year 
        FROM financial_ratios 
        GROUP BY company_id
    ) latest ON r.company_id = latest.company_id AND r.year = latest.max_year
    """
    ratios = pd.read_sql_query(q_r, conn)
    comp_names = pd.read_sql_query("SELECT id, company_name FROM companies", conn)

    merged = pd.merge(pg, ratios, on='company_id', how='inner')
    merged = pd.merge(merged, comp_names, left_on='company_id', right_on='id', how='left')

    peer_excel_path = os.path.join(OUTPUT_DIR, 'peer_comparison.xlsx')
    percentile_records = []

    with pd.ExcelWriter(peer_excel_path, engine='openpyxl') as writer:
        for gname, group in merged.groupby('peer_group_name'):
            group = group.copy().reset_index(drop=True)
            bench_row = group[group['is_benchmark'] == 1]
            bench_ticker = bench_row['company_id'].values[0] if len(bench_row) > 0 else group['company_id'].iloc[0]

            # Compute percentiles for each metric
            top_q_counts = {cid: 0 for cid in group['company_id']}
            bot_q_counts = {cid: 0 for cid in group['company_id']}

            pctile_cols = {}
            for metric in METRICS_20:
                if metric in group.columns:
                    s = group[metric].fillna(group[metric].median())
                    # For debt_to_equity and working_capital_days: lower is better
                    ascending = False if metric in ['debt_to_equity', 'working_capital_days'] else True
                    ranks = s.rank(pct=True, ascending=ascending)
                    pctile_cols[f"{metric}_pctile"] = (ranks * 100).round(1)

                    # Track top / bottom quartile counts
                    for cid, rval in zip(group['company_id'], ranks):
                        if rval >= 0.75:
                            top_q_counts[cid] += 1
                        elif rval <= 0.25:
                            bot_q_counts[cid] += 1

                        percentile_records.append({
                            'company_id': cid,
                            'peer_group_name': gname,
                            'metric': metric,
                            'value': float(group[group['company_id'] == cid][metric].values[0]) if pd.notna(group[group['company_id'] == cid][metric].values[0]) else None,
                            'percentile_rank': round(float(rval * 100), 1),
                            'year': str(group[group['company_id'] == cid]['year'].values[0])
                        })

            group_pct = pd.DataFrame(pctile_cols)
            group_out = pd.concat([group[['company_id', 'company_name', 'is_benchmark'] + [m for m in METRICS_20 if m in group.columns]], group_pct], axis=1)

            # Add Badges: Best in Class (top quartile on >= 6 of 10), Watch List (bottom quartile on >= 4 of 10)
            badges = []
            for cid in group['company_id']:
                if top_q_counts[cid] >= 6:
                    badges.append("Best in Class")
                elif bot_q_counts[cid] >= 4:
                    badges.append("Watch List")
                else:
                    badges.append("Neutral")
            group_out['peer_status'] = badges

            sheet_title = gname[:31]
            group_out.to_excel(writer, sheet_name=sheet_title, index=False)

            # Generate radar charts for all members in this peer group
            peer_avg_dict = {m: group[m].mean() for m in RADAR_8_AXES if m in group.columns}
            for _, r in group.iterrows():
                cid = r['company_id']
                comp_dict = {m: r.get(m) for m in RADAR_8_AXES}
                radar_file = os.path.join(RADAR_DIR, f"{cid}_radar.png")
                generate_radar_chart(cid, comp_dict, peer_avg_dict, radar_file)

    # Also generate radar chart for non-peer-group companies against Nifty 100 universe average
    univ_avg_dict = {m: ratios[m].mean() for m in RADAR_8_AXES if m in ratios.columns}
    for _, r in ratios.iterrows():
        cid = r['company_id']
        radar_file = os.path.join(RADAR_DIR, f"{cid}_radar.png")
        if not os.path.exists(radar_file):
            comp_dict = {m: r.get(m) for m in RADAR_8_AXES}
            generate_radar_chart(cid, comp_dict, univ_avg_dict, radar_file)

    # Save peer_percentiles to SQLite
    df_pctile = pd.DataFrame(percentile_records)
    df_pctile.to_sql('peer_percentiles', conn, if_exists='replace', index=False)
    conn.close()

    logger.info(f"Peer comparison completed. Output written to {peer_excel_path}")
    logger.info(f"Radar charts generated in {RADAR_DIR}")

if __name__ == '__main__':
    run_peer_comparison()
