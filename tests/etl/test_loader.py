"""Unit tests for ETL database loader and table integrity."""
import sqlite3


def test_companies_count():
    """Verify 92 companies exist in nifty100.db."""
    with sqlite3.connect("data/nifty100.db") as conn:
        cnt = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
    assert cnt == 92


def test_financial_ratios_completeness():
    """Verify financial_ratios has >= 1,184 rows."""
    with sqlite3.connect("data/nifty100.db") as conn:
        cnt = conn.execute("SELECT COUNT(*) FROM financial_ratios").fetchone()[0]
    assert cnt >= 1184
