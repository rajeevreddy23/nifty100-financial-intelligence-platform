import pytest
import pandas as pd
from src.etl.validator import run_dq_checks

def test_dq01_company_pk():
    df_comp = pd.DataFrame({'id': ['TCS', 'TCS', 'INFY']})
    violations = run_dq_checks({'companies': df_comp})
    assert any(v['rule_id'] == 'DQ-01' for v in violations)

def test_dq02_annual_pk():
    df_pl = pd.DataFrame({
        'company_id': ['TCS', 'TCS'],
        'year': ['2023-03', '2023-03']
    })
    violations = run_dq_checks({'profitandloss': df_pl})
    assert any(v['rule_id'] == 'DQ-02' for v in violations)

def test_dq03_fk_integrity():
    df_comp = pd.DataFrame({'id': ['TCS']})
    df_pl = pd.DataFrame({'company_id': ['ORPHAN'], 'year': ['2023-03']})
    violations = run_dq_checks({'companies': df_comp, 'profitandloss': df_pl})
    assert any(v['rule_id'] == 'DQ-03' for v in violations)

def test_dq04_bs_balance():
    df_bs = pd.DataFrame({
        'company_id': ['TCS'], 'year': ['2023-03'],
        'total_assets': [1000.0], 'total_liabilities': [1020.0]
    })
    violations = run_dq_checks({'balancesheet': df_bs})
    assert any(v['rule_id'] == 'DQ-04' for v in violations)

def test_dq05_opm_cross_check():
    df_pl = pd.DataFrame({
        'company_id': ['TCS'], 'year': ['2023-03'],
        'sales': [1000.0], 'operating_profit': [250.0], 'opm_percentage': [20.0]
    })
    violations = run_dq_checks({'profitandloss': df_pl})
    assert any(v['rule_id'] == 'DQ-05' for v in violations)

def test_dq06_zero_sales():
    df_pl = pd.DataFrame({
        'company_id': ['TCS'], 'year': ['2023-03'], 'sales': [0.0]
    })
    violations = run_dq_checks({'profitandloss': df_pl})
    assert any(v['rule_id'] == 'DQ-06' for v in violations)

def test_dq07_year_format():
    df_pl = pd.DataFrame({
        'company_id': ['TCS'], 'year': ['INVALID_YEAR']
    })
    violations = run_dq_checks({'profitandloss': df_pl})
    assert any(v['rule_id'] == 'DQ-07' for v in violations)

def test_dq08_ticker_format():
    df_comp = pd.DataFrame({'id': ['TOOLONGTICKERNAME']})
    violations = run_dq_checks({'companies': df_comp})
    assert any(v['rule_id'] == 'DQ-08' for v in violations)

def test_dq09_net_cash_check():
    df_cf = pd.DataFrame({
        'company_id': ['TCS'], 'year': ['2023-03'],
        'operating_activity': [100.0], 'investing_activity': [-50.0],
        'financing_activity': [-20.0], 'net_cash_flow': [100.0]
    })
    violations = run_dq_checks({'cashflow': df_cf})
    assert any(v['rule_id'] == 'DQ-09' for v in violations)

def test_dq10_negative_fixed_assets():
    df_bs = pd.DataFrame({
        'company_id': ['TCS'], 'year': ['2023-03'], 'fixed_assets': [-100.0]
    })
    violations = run_dq_checks({'balancesheet': df_bs})
    assert any(v['rule_id'] == 'DQ-10' for v in violations)

def test_dq11_tax_rate_range():
    df_pl = pd.DataFrame({
        'company_id': ['TCS'], 'year': ['2023-03'], 'tax_percentage': [85.0]
    })
    violations = run_dq_checks({'profitandloss': df_pl})
    assert any(v['rule_id'] == 'DQ-11' for v in violations)

def test_dq12_dividend_payout_cap():
    df_pl = pd.DataFrame({
        'company_id': ['TCS'], 'year': ['2023-03'], 'dividend_payout': [250.0]
    })
    violations = run_dq_checks({'profitandloss': df_pl})
    assert any(v['rule_id'] == 'DQ-12' for v in violations)

def test_dq14_eps_sign_consistency():
    df_pl = pd.DataFrame({
        'company_id': ['TCS'], 'year': ['2023-03'], 'net_profit': [100.0], 'eps': [-5.0]
    })
    violations = run_dq_checks({'profitandloss': df_pl})
    assert any(v['rule_id'] == 'DQ-14' for v in violations)

def test_dq16_coverage_check():
    df_pl = pd.DataFrame({
        'company_id': ['NEWCO', 'NEWCO'],
        'year': ['2023-03', '2024-03']
    })
    violations = run_dq_checks({'profitandloss': df_pl})
    assert any(v['rule_id'] == 'DQ-16' for v in violations)
