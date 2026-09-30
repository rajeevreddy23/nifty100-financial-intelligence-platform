"""Unit tests for leverage and efficiency KPIs (D/E, ICR, Asset Turnover)."""
import sqlite3


def test_debt_free_companies_present():
    """Verify zero-debt companies exist in financial_ratios."""
    with sqlite3.connect("data/nifty100.db") as conn:
        cnt = conn.execute("SELECT COUNT(*) FROM financial_ratios WHERE debt_to_equity = 0").fetchone()[0]
    assert cnt > 0


def test_asset_turnover_non_negative():
    """Verify asset_turnover is non-negative where populated."""
    with sqlite3.connect("data/nifty100.db") as conn:
        neg = conn.execute("SELECT COUNT(*) FROM financial_ratios WHERE asset_turnover < 0").fetchone()[0]
    assert neg == 0
