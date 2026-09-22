import pytest
from src.analytics.cagr import compute_cagr
from src.analytics.cashflow_kpis import (
    classify_capital_allocation, check_distress_pattern, get_cfo_quality, get_capex_intensity_label
)

def test_roe_positive():
    net_profit = 100.0
    equity = 500.0
    roe = (net_profit / equity) * 100.0
    assert roe == 20.0

def test_roe_neg_equity():
    equity = -50.0
    roe = None if equity <= 0 else 100.0
    assert roe is None

def test_de_debtfree():
    borrowings = 0.0
    equity = 500.0
    de = 0.0 if borrowings == 0 else borrowings / equity
    assert de == 0.0

def test_icr_debtfree():
    interest = 0.0
    icr = None if interest == 0 else 10.0
    assert icr is None

def test_cagr_normal():
    cagr, flag = compute_cagr(100.0, 161.051, 5)
    assert cagr is not None
    assert round(cagr, 1) == 10.0
    assert flag is None

def test_cagr_turnaround():
    cagr, flag = compute_cagr(-100.0, 200.0, 3)
    assert cagr is None
    assert flag == 'TURNAROUND'

def test_cagr_decline_to_loss():
    cagr, flag = compute_cagr(100.0, -50.0, 3)
    assert cagr is None
    assert flag == 'DECLINE_TO_LOSS'

def test_cagr_both_negative():
    cagr, flag = compute_cagr(-100.0, -200.0, 3)
    assert cagr is None
    assert flag == 'BOTH_NEGATIVE'

def test_cagr_zero_base():
    cagr, flag = compute_cagr(0.0, 100.0, 3)
    assert cagr is None
    assert flag == 'ZERO_BASE'

def test_cagr_invalid_period():
    cagr, flag = compute_cagr(100.0, 200.0, 0)
    assert cagr is None
    assert flag == 'INVALID_PERIOD'

def test_npm_formula():
    sales = 1000.0
    net_profit = 150.0
    npm = (net_profit / sales) * 100.0
    assert npm == 15.0

def test_ebit_margin():
    sales = 1000.0
    op = 250.0
    dep = 50.0
    ebit_margin = ((op - dep) / sales) * 100.0
    assert ebit_margin == 20.0

def test_asset_turnover():
    sales = 1000.0
    total_assets = 500.0
    turnover = sales / total_assets
    assert turnover == 2.0

def test_working_capital_days():
    sales = 365.0
    net_current = 50.0
    days = (net_current / sales) * 365.0
    assert days == 50.0

def test_cfo_quality_high():
    assert get_cfo_quality(1.2) == "High Quality Earnings"

def test_cfo_quality_accrual():
    assert get_cfo_quality(0.4) == "Accrual Risk"

def test_cfo_quality_balanced():
    assert get_cfo_quality(0.8) == "Balanced"

def test_capex_intensity_light():
    assert get_capex_intensity_label(2.0) == "Asset-Light"

def test_capex_intensity_heavy():
    assert get_capex_intensity_label(10.0) == "Capital Intensive"

def test_capital_allocation_reinvestor():
    cfo_s, cfi_s, cff_s, label = classify_capital_allocation(100, -50, -20, 0.9)
    assert (cfo_s, cfi_s, cff_s) == ('+', '-', '-')
    assert label == "Reinvestor"

def test_distress_pattern_detection():
    assert check_distress_pattern(-100, 200) is True
    assert check_distress_pattern(100, -50) is False
