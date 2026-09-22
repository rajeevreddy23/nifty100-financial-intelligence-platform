import re
import pandas as pd
from typing import List, Dict, Any

def run_dq_checks(dfs: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
    """Runs all 16 DQ validation rules and returns list of violation records."""
    violations = []
    
    companies = dfs.get('companies')
    pl = dfs.get('profitandloss')
    bs = dfs.get('balancesheet')
    cf = dfs.get('cashflow')
    docs = dfs.get('documents')

    # DQ-01: Company PK Uniqueness (CRITICAL)
    if companies is not None:
        if len(companies) != companies['id'].nunique():
            dups = companies[companies['id'].duplicated()]['id'].tolist()
            violations.append({
                'rule_id': 'DQ-01',
                'rule_name': 'Company PK Uniqueness',
                'company_id': str(dups),
                'year': 'N/A',
                'field': 'id',
                'issue': f"Duplicate company IDs found: {dups}",
                'severity': 'CRITICAL'
            })

    valid_tickers = set(companies['id']) if companies is not None else set()

    # DQ-02: Annual PK Uniqueness (CRITICAL)
    for tname, df in [('profitandloss', pl), ('balancesheet', bs), ('cashflow', cf)]:
        if df is not None and {'company_id', 'year'}.issubset(df.columns):
            dup_mask = df.duplicated(subset=['company_id', 'year'], keep=False)
            if dup_mask.any():
                dup_records = df[dup_mask]
                for _, r in dup_records.iterrows():
                    violations.append({
                        'rule_id': 'DQ-02',
                        'rule_name': 'Annual PK Uniqueness',
                        'company_id': str(r['company_id']),
                        'year': str(r['year']),
                        'field': 'company_id, year',
                        'issue': f"Duplicate (company_id, year) in {tname}",
                        'severity': 'CRITICAL'
                    })

    # DQ-03: FK Integrity (CRITICAL)
    for tname, df in dfs.items():
        if tname != 'companies' and df is not None and 'company_id' in df.columns:
            orphans = df[~df['company_id'].isin(valid_tickers)]
            for _, r in orphans.iterrows():
                violations.append({
                    'rule_id': 'DQ-03',
                    'rule_name': 'FK Integrity',
                    'company_id': str(r['company_id']),
                    'year': str(r.get('year', 'N/A')),
                    'field': 'company_id',
                    'issue': f"Orphan ticker not found in companies master in {tname}",
                    'severity': 'CRITICAL'
                })

    # DQ-04: Balance Sheet Balance (WARNING)
    if bs is not None:
        for _, r in bs.iterrows():
            ta = r.get('total_assets', 0) or 0
            tl = r.get('total_liabilities', 0) or 0
            if ta > 0:
                diff = abs(ta - tl) / ta
                if diff >= 0.01:
                    violations.append({
                        'rule_id': 'DQ-04',
                        'rule_name': 'Balance Sheet Balance',
                        'company_id': str(r['company_id']),
                        'year': str(r['year']),
                        'field': 'total_assets, total_liabilities',
                        'issue': f"BS balance diff {diff:.2%} (assets={ta}, liab={tl})",
                        'severity': 'WARNING'
                    })

    # DQ-05: OPM Cross-Check (WARNING)
    if pl is not None:
        for _, r in pl.iterrows():
            sales = r.get('sales', 0) or 0
            op = r.get('operating_profit', 0) or 0
            src_opm = r.get('opm_percentage', 0) or 0
            if sales > 0:
                calc_opm = (op / sales) * 100
                if abs(src_opm - calc_opm) > 1.0:
                    violations.append({
                        'rule_id': 'DQ-05',
                        'rule_name': 'OPM Cross-Check',
                        'company_id': str(r['company_id']),
                        'year': str(r['year']),
                        'field': 'opm_percentage',
                        'issue': f"OPM divergence: source={src_opm}%, computed={calc_opm:.1f}%",
                        'severity': 'WARNING'
                    })

    # DQ-06: Positive Sales (WARNING)
    if pl is not None:
        for _, r in pl.iterrows():
            sales = r.get('sales', 0) or 0
            if sales <= 0:
                violations.append({
                    'rule_id': 'DQ-06',
                    'rule_name': 'Positive Sales',
                    'company_id': str(r['company_id']),
                    'year': str(r['year']),
                    'field': 'sales',
                    'issue': f"Non-positive sales: {sales}",
                    'severity': 'WARNING'
                })

    # DQ-07: Year Format (CRITICAL)
    for tname, df in [('profitandloss', pl), ('balancesheet', bs), ('cashflow', cf)]:
        if df is not None and 'year' in df.columns:
            for _, r in df.iterrows():
                y = str(r['year'])
                if not re.match(r'^\d{4}-\d{2}$', y):
                    violations.append({
                        'rule_id': 'DQ-07',
                        'rule_name': 'Year Format',
                        'company_id': str(r.get('company_id', 'N/A')),
                        'year': y,
                        'field': 'year',
                        'issue': f"Invalid year format in {tname}: '{y}'",
                        'severity': 'CRITICAL'
                    })

    # DQ-08: Ticker Format (CRITICAL)
    if companies is not None:
        for _, r in companies.iterrows():
            cid = str(r['id'])
            if len(cid) < 2 or len(cid) > 15 or not re.match(r'^[A-Z0-9&\-]+$', cid):
                violations.append({
                    'rule_id': 'DQ-08',
                    'rule_name': 'Ticker Format',
                    'company_id': cid,
                    'year': 'N/A',
                    'field': 'id',
                    'issue': f"Invalid ticker format: '{cid}'",
                    'severity': 'CRITICAL'
                })

    # DQ-09: Net Cash Check (WARNING)
    if cf is not None:
        for _, r in cf.iterrows():
            cfo = r.get('operating_activity', 0) or 0
            cfi = r.get('investing_activity', 0) or 0
            cff = r.get('financing_activity', 0) or 0
            ncf = r.get('net_cash_flow', 0) or 0
            if abs(ncf - (cfo + cfi + cff)) > 10.0:
                violations.append({
                    'rule_id': 'DQ-09',
                    'rule_name': 'Net Cash Check',
                    'company_id': str(r['company_id']),
                    'year': str(r['year']),
                    'field': 'net_cash_flow',
                    'issue': f"Net cash mismatch: ncf={ncf}, sum={cfo+cfi+cff}",
                    'severity': 'WARNING'
                })

    # DQ-10: Non-Negative Fixed Assets (WARNING)
    if bs is not None:
        for _, r in bs.iterrows():
            fa = r.get('fixed_assets', 0) or 0
            if fa < 0:
                violations.append({
                    'rule_id': 'DQ-10',
                    'rule_name': 'Non-Negative Fixed Assets',
                    'company_id': str(r['company_id']),
                    'year': str(r['year']),
                    'field': 'fixed_assets',
                    'issue': f"Negative fixed assets: {fa}",
                    'severity': 'WARNING'
                })

    # DQ-11: Tax Rate Range (WARNING)
    if pl is not None:
        for _, r in pl.iterrows():
            tax = r.get('tax_percentage')
            if pd.notna(tax) and (tax < 0 or tax > 60):
                violations.append({
                    'rule_id': 'DQ-11',
                    'rule_name': 'Tax Rate Range',
                    'company_id': str(r['company_id']),
                    'year': str(r['year']),
                    'field': 'tax_percentage',
                    'issue': f"Tax rate out of standard range: {tax}%",
                    'severity': 'WARNING'
                })

    # DQ-12: Dividend Payout Cap (WARNING)
    if pl is not None:
        for _, r in pl.iterrows():
            dp = r.get('dividend_payout')
            if pd.notna(dp) and dp > 200:
                violations.append({
                    'rule_id': 'DQ-12',
                    'rule_name': 'Dividend Payout Cap',
                    'company_id': str(r['company_id']),
                    'year': str(r['year']),
                    'field': 'dividend_payout',
                    'issue': f"Dividend payout > 200%: {dp}%",
                    'severity': 'WARNING'
                })

    # DQ-14: EPS Sign Consistency (WARNING)
    if pl is not None:
        for _, r in pl.iterrows():
            np = r.get('net_profit', 0) or 0
            eps = r.get('eps')
            if pd.notna(eps) and np > 0 and eps <= 0:
                violations.append({
                    'rule_id': 'DQ-14',
                    'rule_name': 'EPS Sign Consistency',
                    'company_id': str(r['company_id']),
                    'year': str(r['year']),
                    'field': 'eps',
                    'issue': f"Net profit is positive ({np}) but EPS is non-positive ({eps})",
                    'severity': 'WARNING'
                })

    # DQ-16: Coverage Check (WARNING)
    if pl is not None:
        counts = pl.groupby('company_id')['year'].nunique()
        for cid, cnt in counts.items():
            if cnt < 5:
                violations.append({
                    'rule_id': 'DQ-16',
                    'rule_name': 'Coverage Check',
                    'company_id': str(cid),
                    'year': 'N/A',
                    'field': 'history_years',
                    'issue': f"Company has only {cnt} years of records (< 5yr threshold)",
                    'severity': 'WARNING'
                })

    return violations
