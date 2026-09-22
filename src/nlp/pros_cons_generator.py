"""Auto pros/cons generation using 12 pro + 12 con KPI threshold rules."""
import os
import sqlite3
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
DB_PATH = os.path.join(BASE_DIR, 'data/nifty100.db')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')

def generate_pros_cons():
    logger.info("Generating Pros & Cons for all 92 companies...")
    conn = sqlite3.connect(DB_PATH)
    
    # Existing hand-crafted pros/cons
    existing_pc = pd.read_sql_query("SELECT * FROM prosandcons", conn)
    
    # Latest ratios per company
    q = """
    SELECT r.*, c.company_name, s.broad_sector
    FROM financial_ratios r
    JOIN companies c ON r.company_id = c.id
    JOIN sectors s ON r.company_id = s.company_id
    INNER JOIN (
        SELECT company_id, MAX(year) as max_year
        FROM financial_ratios
        WHERE net_profit_margin_pct IS NOT NULL
        GROUP BY company_id
    ) latest ON r.company_id = latest.company_id AND r.year = latest.max_year
    """
    df = pd.read_sql_query(q, conn)
    conn.close()

    records = []

    for _, r in df.iterrows():
        cid = r['company_id']
        name = r['company_name']
        roe = r.get('return_on_equity_pct') or 0
        roce = r.get('return_on_capital_pct') or 0
        npm = r.get('net_profit_margin_pct') or 0
        de = r.get('debt_to_equity') if pd.notna(r.get('debt_to_equity')) else 1.0
        fcf = r.get('free_cash_flow_cr') or 0
        rev_cagr = r.get('revenue_cagr_5yr') or 0
        pat_cagr = r.get('pat_cagr_5yr') or 0
        icr = r.get('interest_coverage') or 0
        cfo_pat = r.get('cfo_pat_ratio') or 1.0
        is_financial = str(r['broad_sector']).lower() in ['financials', 'financial services']

        pros = []
        cons = []

        # 12 Pro Rules
        if roe >= 20.0:
            pros.append(("ROE > 20%", f"Company has delivered outstanding return on equity of {roe:.1f}%.", 95))
        elif roe >= 15.0:
            pros.append(("Healthy ROE", f"Consistent profitability with ROE of {roe:.1f}%.", 85))

        if not is_financial and de == 0:
            pros.append(("Debt Free", "Company is virtually debt-free with zero borrowings.", 95))
        elif not is_financial and de <= 0.3:
            pros.append(("Low Leverage", f"Conservative capital structure with D/E of {de:.2f}x.", 90))

        if fcf > 1000.0:
            pros.append(("Strong Free Cash Flow", f"Generates robust annual free cash flow of ₹{fcf:,.0f} Cr.", 90))
        elif fcf > 0:
            pros.append(("Positive FCF", "Maintains positive free cash flow after meeting capital expenditure.", 80))

        if rev_cagr >= 15.0:
            pros.append(("High Revenue Growth", f"Delivered 5-year revenue CAGR of {rev_cagr:.1f}%.", 85))
        if pat_cagr >= 20.0:
            pros.append(("Rapid Earnings Compounding", f"Compounded profit after tax at {pat_cagr:.1f}% over 5 years.", 90))

        if npm >= 20.0:
            pros.append(("High Margins", f"Enjoys robust net profit margin of {npm:.1f}%.", 85))
        if icr >= 10.0 or icr == 999:
            pros.append(("Comfortable Debt Servicing", "Superb interest coverage ratio indicating negligible solvency risk.", 90))
        if cfo_pat >= 1.0:
            pros.append(("High Quality Earnings", "Strong cash generation with operating cash flows exceeding reported PAT.", 85))

        # Default Pro if none triggered
        if not pros:
            pros.append(("Established Market Leader", f"Constituent of Nifty 100 index in {r['broad_sector']} sector.", 75))

        # 12 Con Rules
        if not is_financial and de >= 2.0:
            cons.append(("High Debt", f"Elevated debt-to-equity ratio of {de:.2f}x exceeds safe threshold.", 95))
        elif not is_financial and de >= 1.0:
            cons.append(("Moderate Leverage", f"Debt-to-equity ratio of {de:.2f}x requires monitoring.", 80))

        if fcf < 0:
            cons.append(("Negative Free Cash Flow", f"Free cash flow is currently negative at ₹{fcf:,.0f} Cr.", 90))

        if roe < 10.0 and roe > 0:
            cons.append(("Subdued ROE", f"Return on equity of {roe:.1f}% is below cost of capital.", 85))
        elif roe <= 0:
            cons.append(("Operating Losses", "Negative return on equity due to operational losses.", 95))

        if rev_cagr < 5.0 and rev_cagr != 0:
            cons.append(("Muted Topline Growth", f"5-year revenue CAGR is sluggish at {rev_cagr:.1f}%.", 80))

        if npm < 5.0:
            cons.append(("Thin Margins", f"Net profit margin is low at {npm:.1f}%, vulnerable to cost pressures.", 85))

        if icr < 2.0 and not is_financial and icr > 0:
            cons.append(("Weak Interest Coverage", f"Interest coverage ratio of {icr:.1f}x indicates debt servicing strain.", 90))

        if cfo_pat < 0.5 and cfo_pat > 0:
            cons.append(("Accrual Risk", "Operating cash flow is less than half of net profit, indicating working capital lockup.", 80))

        # Default Con if none triggered
        if not cons:
            cons.append(("Valuation Sensitivity", "High market expectations may cause volatility upon cyclical slowdowns.", 70))

        for rule, text, conf in pros:
            records.append({
                'company_id': cid,
                'company_name': name,
                'type': 'pro',
                'rule_triggered': rule,
                'text': text,
                'confidence_pct': conf
            })
        for rule, text, conf in cons:
            records.append({
                'company_id': cid,
                'company_name': name,
                'type': 'con',
                'rule_triggered': rule,
                'text': text,
                'confidence_pct': conf
            })

    df_pc = pd.DataFrame(records)
    out_path = os.path.join(OUTPUT_DIR, 'pros_cons_generated.csv')
    df_pc.to_csv(out_path, index=False)
    logger.info(f"Generated {len(df_pc)} pros/cons for all 92 companies saved to {out_path}")
    return df_pc

if __name__ == '__main__':
    generate_pros_cons()
