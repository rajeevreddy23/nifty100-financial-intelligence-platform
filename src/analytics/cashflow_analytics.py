"""Cash Flow Intelligence Module: CFO quality, CapEx intensity, FCF compounding, distress flags."""
import os
import sqlite3
import pandas as pd
import numpy as np
import logging
import sys
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
ANALYTICS_DIR = os.path.dirname(__file__)
if ANALYTICS_DIR not in sys.path:
    sys.path.insert(0, ANALYTICS_DIR)

from src.analytics.cashflow_kpis import get_cfo_quality, get_capex_intensity_label

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
DB_PATH = os.path.join(BASE_DIR, 'data/nifty100.db')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')

def run_cashflow_intelligence():
    logger.info("Running Cash Flow Intelligence Module...")
    conn = sqlite3.connect(DB_PATH)

    q = """
    SELECT r.*, c.company_name, s.broad_sector, ca.pattern_label, ca.cfo_sign, ca.cfi_sign, ca.cff_sign
    FROM financial_ratios r
    JOIN companies c ON r.company_id = c.id
    JOIN sectors s ON r.company_id = s.company_id
    LEFT JOIN capital_allocation ca ON r.company_id = ca.company_id AND r.year = ca.year
    INNER JOIN (
        SELECT company_id, MAX(year) as max_year
        FROM financial_ratios
        WHERE net_profit_margin_pct IS NOT NULL
        GROUP BY company_id
    ) latest ON r.company_id = latest.company_id AND r.year = latest.max_year
    """
    df = pd.read_sql_query(q, conn)

    # Also get 5-year average CFO/PAT and 5-year FCF sum
    q_5yr = """
    SELECT company_id,
           AVG(cfo_pat_ratio) as cfo_pat_5yr_avg,
           SUM(free_cash_flow_cr) as fcf_5yr_sum,
           SUM(CASE WHEN free_cash_flow_cr > 0 THEN 1 ELSE 0 END) as positive_fcf_yrs
    FROM financial_ratios
    WHERE year >= '2020-03'
    GROUP BY company_id
    """
    df_5yr = pd.read_sql_query(q_5yr, conn)
    conn.close()

    merged = pd.merge(df, df_5yr, on='company_id', how='left')

    # CFO Quality Badge
    merged['cfo_quality_score'] = merged['cfo_pat_5yr_avg'].apply(get_cfo_quality)
    # CapEx Intensity Tier
    merged['capex_intensity_tier'] = merged['capex_intensity_pct'].apply(get_capex_intensity_label)

    # Distress detection: CFO < 0 and CFF > 0 in latest year
    merged['is_distressed'] = (merged['cash_from_operations_cr'] < 0) & (merged['cff_sign'] == '+')
    distress_list = merged[merged['is_distressed']][
        ['company_id', 'company_name', 'broad_sector', 'cash_from_operations_cr', 'total_debt_cr', 'pattern_label']
    ]

    # Save distress alerts
    distress_path = os.path.join(OUTPUT_DIR, 'distress_alerts.csv')
    distress_list.to_csv(distress_path, index=False)
    logger.info(f"Distress alerts ({len(distress_list)} companies) saved to {distress_path}")

    # Export cashflow_intelligence.xlsx
    cf_intel_path = os.path.join(OUTPUT_DIR, 'cashflow_intelligence.xlsx')
    out_cols = [
        'company_id', 'company_name', 'broad_sector', 'year',
        'cash_from_operations_cr', 'capex_cr', 'free_cash_flow_cr',
        'cfo_pat_ratio', 'cfo_pat_5yr_avg', 'cfo_quality_score',
        'capex_intensity_pct', 'capex_intensity_tier', 'fcf_conversion_pct',
        'fcf_5yr_sum', 'positive_fcf_yrs', 'pattern_label', 'is_distressed'
    ]
    cols = [c for c in out_cols if c in merged.columns]
    merged[cols].to_excel(cf_intel_path, index=False)
    logger.info(f"Cash flow intelligence written to {cf_intel_path}")

if __name__ == '__main__':
    run_cashflow_intelligence()
