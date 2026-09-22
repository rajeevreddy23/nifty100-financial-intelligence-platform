"""ETL Ingestion Pipeline: loads all raw files, normalises, validates, and stores in SQLite."""
import os
import time
import sqlite3
import pandas as pd
import numpy as np
import logging
from normaliser import normalize_ticker, normalize_year
from validator import run_dq_checks

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
RAW_DIR = os.path.join(BASE_DIR, 'data/raw')
SUPP_DIR = os.path.join(BASE_DIR, 'data/supporting')
DB_PATH = os.path.join(BASE_DIR, 'data/nifty100.db')
SCHEMA_PATH = os.path.join(BASE_DIR, 'src/etl/schema.sql')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')

def init_database():
    """Initialise SQLite database with DDL schema."""
    logger.info(f"Initialising database at {DB_PATH}")
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
            conn.executescript(f.read())
    logger.info("Database schema initialized successfully.")

def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Strip whitespace and standardize column names."""
    df.columns = [str(c).strip() for c in df.columns]
    return df

def load_data():
    """Run full ETL pipeline and populate SQLite."""
    start_time = time.time()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    init_database()
    
    audit_records = []
    dfs = {}

    # 1. Companies (Core - header=1)
    t0 = time.time()
    comp_path = os.path.join(RAW_DIR, 'companies.xlsx')
    df_comp = pd.read_excel(comp_path, header=1)
    df_comp = clean_column_names(df_comp)
    rows_in = len(df_comp)
    df_comp['id'] = df_comp['id'].apply(normalize_ticker)
    df_comp = df_comp[df_comp['id'] != 'MISSING'].drop_duplicates(subset=['id'])
    df_comp['company_name'] = df_comp['company_name'].astype(str).str.replace('\n', ' ').str.strip()
    rows_out = len(df_comp)
    dfs['companies'] = df_comp
    audit_records.append({
        'table': 'companies', 'rows_in': rows_in, 'rows_out': rows_out,
        'rejected': rows_in - rows_out, 'timestamp': pd.Timestamp.now().isoformat(),
        'runtime_s': round(time.time() - t0, 3)
    })

    valid_company_ids = set(df_comp['id'])

    # 2. Profit & Loss (Core - header=1)
    t0 = time.time()
    pl_path = os.path.join(RAW_DIR, 'profitandloss.xlsx')
    df_pl = pd.read_excel(pl_path, header=1)
    df_pl = clean_column_names(df_pl)
    rows_in = len(df_pl)
    df_pl['company_id'] = df_pl['company_id'].apply(normalize_ticker)
    df_pl['year'] = df_pl['year'].apply(normalize_year)
    # Deduplicate: keep last occurrence as per DQ-02
    df_pl = df_pl[df_pl['company_id'].isin(valid_company_ids) & (df_pl['year'] != 'PARSE_ERROR')]
    df_pl = df_pl.drop_duplicates(subset=['company_id', 'year'], keep='last')
    rows_out = len(df_pl)
    dfs['profitandloss'] = df_pl
    audit_records.append({
        'table': 'profitandloss', 'rows_in': rows_in, 'rows_out': rows_out,
        'rejected': rows_in - rows_out, 'timestamp': pd.Timestamp.now().isoformat(),
        'runtime_s': round(time.time() - t0, 3)
    })

    # 3. Balance Sheet (Core - header=1)
    t0 = time.time()
    bs_path = os.path.join(RAW_DIR, 'balancesheet.xlsx')
    df_bs = pd.read_excel(bs_path, header=1)
    df_bs = clean_column_names(df_bs)
    rows_in = len(df_bs)
    df_bs['company_id'] = df_bs['company_id'].apply(normalize_ticker)
    df_bs['year'] = df_bs['year'].apply(normalize_year)
    # Coerce negative fixed assets to 0 as per DQ-10
    if 'fixed_assets' in df_bs.columns:
        df_bs['fixed_assets'] = df_bs['fixed_assets'].apply(lambda x: 0 if pd.notna(x) and x < 0 else x)
    df_bs = df_bs[df_bs['company_id'].isin(valid_company_ids) & (df_bs['year'] != 'PARSE_ERROR')]
    df_bs = df_bs.drop_duplicates(subset=['company_id', 'year'], keep='last')
    rows_out = len(df_bs)
    dfs['balancesheet'] = df_bs
    audit_records.append({
        'table': 'balancesheet', 'rows_in': rows_in, 'rows_out': rows_out,
        'rejected': rows_in - rows_out, 'timestamp': pd.Timestamp.now().isoformat(),
        'runtime_s': round(time.time() - t0, 3)
    })

    # 4. Cash Flow (Core - header=1)
    t0 = time.time()
    cf_path = os.path.join(RAW_DIR, 'cashflow.xlsx')
    df_cf = pd.read_excel(cf_path, header=1)
    df_cf = clean_column_names(df_cf)
    rows_in = len(df_cf)
    df_cf['company_id'] = df_cf['company_id'].apply(normalize_ticker)
    df_cf['year'] = df_cf['year'].apply(normalize_year)
    df_cf = df_cf[df_cf['company_id'].isin(valid_company_ids) & (df_cf['year'] != 'PARSE_ERROR')]
    df_cf = df_cf.drop_duplicates(subset=['company_id', 'year'], keep='last')
    rows_out = len(df_cf)
    dfs['cashflow'] = df_cf
    audit_records.append({
        'table': 'cashflow', 'rows_in': rows_in, 'rows_out': rows_out,
        'rejected': rows_in - rows_out, 'timestamp': pd.Timestamp.now().isoformat(),
        'runtime_s': round(time.time() - t0, 3)
    })

    # 5. Analysis (Core - header=1)
    t0 = time.time()
    ana_path = os.path.join(RAW_DIR, 'analysis.xlsx')
    df_ana = pd.read_excel(ana_path, header=1)
    df_ana = clean_column_names(df_ana)
    rows_in = len(df_ana)
    df_ana['company_id'] = df_ana['company_id'].apply(normalize_ticker)
    df_ana = df_ana[df_ana['company_id'].isin(valid_company_ids)]
    rows_out = len(df_ana)
    dfs['analysis'] = df_ana
    audit_records.append({
        'table': 'analysis', 'rows_in': rows_in, 'rows_out': rows_out,
        'rejected': rows_in - rows_out, 'timestamp': pd.Timestamp.now().isoformat(),
        'runtime_s': round(time.time() - t0, 3)
    })

    # 6. Documents (Core - header=1)
    t0 = time.time()
    doc_path = os.path.join(RAW_DIR, 'documents.xlsx')
    df_doc = pd.read_excel(doc_path, header=1)
    df_doc = clean_column_names(df_doc)
    rows_in = len(df_doc)
    df_doc['company_id'] = df_doc['company_id'].apply(normalize_ticker)
    df_doc['year'] = pd.to_numeric(df_doc['Year'], errors='coerce').fillna(0).astype(int)
    df_doc['annual_report'] = df_doc['Annual_Report']
    df_doc = df_doc[df_doc['company_id'].isin(valid_company_ids) & (df_doc['year'] > 0)]
    rows_out = len(df_doc)
    dfs['documents'] = df_doc
    audit_records.append({
        'table': 'documents', 'rows_in': rows_in, 'rows_out': rows_out,
        'rejected': rows_in - rows_out, 'timestamp': pd.Timestamp.now().isoformat(),
        'runtime_s': round(time.time() - t0, 3)
    })

    # 7. Pros & Cons (Core - header=1)
    t0 = time.time()
    pc_path = os.path.join(RAW_DIR, 'prosandcons.xlsx')
    df_pc = pd.read_excel(pc_path, header=1)
    df_pc = clean_column_names(df_pc)
    rows_in = len(df_pc)
    df_pc['company_id'] = df_pc['company_id'].apply(normalize_ticker)
    df_pc = df_pc[df_pc['company_id'].isin(valid_company_ids)]
    rows_out = len(df_pc)
    dfs['prosandcons'] = df_pc
    audit_records.append({
        'table': 'prosandcons', 'rows_in': rows_in, 'rows_out': rows_out,
        'rejected': rows_in - rows_out, 'timestamp': pd.Timestamp.now().isoformat(),
        'runtime_s': round(time.time() - t0, 3)
    })

    # 8. Sectors (Supporting - header=0)
    t0 = time.time()
    sec_path = os.path.join(SUPP_DIR, 'sectors.xlsx')
    df_sec = pd.read_excel(sec_path, header=0)
    df_sec = clean_column_names(df_sec)
    rows_in = len(df_sec)
    df_sec['company_id'] = df_sec['company_id'].apply(normalize_ticker)
    df_sec = df_sec[df_sec['company_id'].isin(valid_company_ids)].drop_duplicates(subset=['company_id'])
    rows_out = len(df_sec)
    dfs['sectors'] = df_sec
    audit_records.append({
        'table': 'sectors', 'rows_in': rows_in, 'rows_out': rows_out,
        'rejected': rows_in - rows_out, 'timestamp': pd.Timestamp.now().isoformat(),
        'runtime_s': round(time.time() - t0, 3)
    })

    # 9. Stock Prices (Supporting - header=0)
    t0 = time.time()
    sp_path = os.path.join(SUPP_DIR, 'stock_prices.xlsx')
    df_sp = pd.read_excel(sp_path, header=0)
    df_sp = clean_column_names(df_sp)
    rows_in = len(df_sp)
    df_sp['company_id'] = df_sp['company_id'].apply(normalize_ticker)
    df_sp = df_sp[df_sp['company_id'].isin(valid_company_ids)].drop_duplicates(subset=['company_id', 'date'])
    rows_out = len(df_sp)
    dfs['stock_prices'] = df_sp
    audit_records.append({
        'table': 'stock_prices', 'rows_in': rows_in, 'rows_out': rows_out,
        'rejected': rows_in - rows_out, 'timestamp': pd.Timestamp.now().isoformat(),
        'runtime_s': round(time.time() - t0, 3)
    })

    # 10. Market Cap (Supporting - header=0)
    t0 = time.time()
    mc_path = os.path.join(SUPP_DIR, 'market_cap.xlsx')
    df_mc = pd.read_excel(mc_path, header=0)
    df_mc = clean_column_names(df_mc)
    rows_in = len(df_mc)
    df_mc['company_id'] = df_mc['company_id'].apply(normalize_ticker)
    df_mc['year'] = df_mc['year'].astype(int)
    df_mc = df_mc[df_mc['company_id'].isin(valid_company_ids)].drop_duplicates(subset=['company_id', 'year'])
    rows_out = len(df_mc)
    dfs['market_cap'] = df_mc
    audit_records.append({
        'table': 'market_cap', 'rows_in': rows_in, 'rows_out': rows_out,
        'rejected': rows_in - rows_out, 'timestamp': pd.Timestamp.now().isoformat(),
        'runtime_s': round(time.time() - t0, 3)
    })

    # 11. Peer Groups (Supporting - header=0)
    t0 = time.time()
    pg_path = os.path.join(SUPP_DIR, 'peer_groups.xlsx')
    df_pg = pd.read_excel(pg_path, header=0)
    df_pg = clean_column_names(df_pg)
    rows_in = len(df_pg)
    df_pg['company_id'] = df_pg['company_id'].apply(normalize_ticker)
    df_pg = df_pg[df_pg['company_id'].isin(valid_company_ids)].drop_duplicates(subset=['peer_group_name', 'company_id'])
    rows_out = len(df_pg)
    dfs['peer_groups'] = df_pg
    audit_records.append({
        'table': 'peer_groups', 'rows_in': rows_in, 'rows_out': rows_out,
        'rejected': rows_in - rows_out, 'timestamp': pd.Timestamp.now().isoformat(),
        'runtime_s': round(time.time() - t0, 3)
    })

    # Execute Data Quality Checks
    logger.info("Running Data Quality validation rules...")
    violations = run_dq_checks(dfs)
    df_violations = pd.DataFrame(violations)
    val_fail_path = os.path.join(OUTPUT_DIR, 'validation_failures.csv')
    df_violations.to_csv(val_fail_path, index=False)
    logger.info(f"Saved {len(violations)} DQ rule findings to {val_fail_path}")

    # Load DataFrames into SQLite
    with sqlite3.connect(DB_PATH) as conn:
        # companies
        comp_cols = ['id', 'company_logo', 'company_name', 'chart_link', 'about_company',
                     'website', 'nse_profile', 'bse_profile', 'face_value', 'book_value',
                     'roce_percentage', 'roe_percentage']
        df_comp[comp_cols].to_sql('companies', conn, if_exists='append', index=False)
        
        # profitandloss
        pl_cols = ['company_id', 'year', 'sales', 'expenses', 'operating_profit',
                   'opm_percentage', 'other_income', 'interest', 'depreciation',
                   'profit_before_tax', 'tax_percentage', 'net_profit', 'eps', 'dividend_payout']
        df_pl[pl_cols].to_sql('profitandloss', conn, if_exists='append', index=False)
        
        # balancesheet
        bs_cols = ['company_id', 'year', 'equity_capital', 'reserves', 'borrowings',
                   'other_liabilities', 'total_liabilities', 'fixed_assets', 'cwip',
                   'investments', 'other_asset', 'total_assets']
        df_bs[bs_cols].to_sql('balancesheet', conn, if_exists='append', index=False)
        
        # cashflow
        cf_cols = ['company_id', 'year', 'operating_activity', 'investing_activity',
                   'financing_activity', 'net_cash_flow']
        df_cf[cf_cols].to_sql('cashflow', conn, if_exists='append', index=False)
        
        # analysis
        ana_cols = ['company_id', 'compounded_sales_growth', 'compounded_profit_growth',
                    'stock_price_cagr', 'roe']
        df_ana[ana_cols].to_sql('analysis', conn, if_exists='append', index=False)
        
        # documents
        doc_cols = ['company_id', 'year', 'annual_report']
        df_doc[doc_cols].to_sql('documents', conn, if_exists='append', index=False)
        
        # prosandcons
        pc_cols = ['company_id', 'pros', 'cons']
        df_pc[pc_cols].to_sql('prosandcons', conn, if_exists='append', index=False)
        
        # sectors
        sec_cols = ['company_id', 'broad_sector', 'sub_sector', 'index_weight_pct', 'market_cap_category']
        df_sec[sec_cols].to_sql('sectors', conn, if_exists='append', index=False)
        
        # stock_prices
        sp_cols = ['company_id', 'date', 'open_price', 'high_price', 'low_price',
                   'close_price', 'volume', 'adjusted_close']
        df_sp[sp_cols].to_sql('stock_prices', conn, if_exists='append', index=False)
        
        # market_cap
        mc_cols = ['company_id', 'year', 'market_cap_crore', 'enterprise_value_crore',
                   'pe_ratio', 'pb_ratio', 'ev_ebitda', 'dividend_yield_pct']
        df_mc[mc_cols].to_sql('market_cap', conn, if_exists='append', index=False)
        
        # peer_groups
        pg_cols = ['peer_group_name', 'company_id', 'is_benchmark']
        df_pg[pg_cols].to_sql('peer_groups', conn, if_exists='append', index=False)

    df_audit = pd.DataFrame(audit_records)
    audit_path = os.path.join(OUTPUT_DIR, 'load_audit.csv')
    df_audit.to_csv(audit_path, index=False)
    logger.info(f"ETL completed in {time.time() - start_time:.2f}s. Audit saved to {audit_path}")

if __name__ == '__main__':
    load_data()
