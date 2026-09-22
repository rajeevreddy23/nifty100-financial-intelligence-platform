"""NLP Module: Regex parser for analysis.xlsx compounded growth strings."""
import os
import re
import sqlite3
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
DB_PATH = os.path.join(BASE_DIR, 'data/nifty100.db')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')

def parse_analysis_text():
    logger.info("Parsing analysis.xlsx qualitative text fields...")
    conn = sqlite3.connect(DB_PATH)
    df_ana = pd.read_sql_query("SELECT * FROM analysis", conn)
    conn.close()

    pattern = re.compile(r'(\d+)\s*Years?:?\s*([\d.]+)%?', re.IGNORECASE)
    parsed_rows = []

    for _, r in df_ana.iterrows():
        cid = r['company_id']
        for col in ['compounded_sales_growth', 'compounded_profit_growth', 'stock_price_cagr', 'roe']:
            text = str(r.get(col, ''))
            if text and text != 'None' and text != 'nan':
                # Split multiple items if present (e.g. newline or comma separated)
                parts = text.split('\n')
                for part in parts:
                    matches = pattern.findall(part)
                    for period, val in matches:
                        parsed_rows.append({
                            'company_id': cid,
                            'metric_type': col,
                            'period_years': int(period),
                            'value_pct': float(val)
                        })

    df_parsed = pd.DataFrame(parsed_rows)
    out_path = os.path.join(OUTPUT_DIR, 'analysis_parsed.csv')
    df_parsed.to_csv(out_path, index=False)
    logger.info(f"Parsed {len(df_parsed)} growth metrics from analysis.xlsx saved to {out_path}")
    return df_parsed

if __name__ == '__main__':
    parse_analysis_text()
