import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_health_200():
    res = client.get('/api/v1/health')
    assert res.status_code == 200
    assert res.json()['status'] == 'ok'
    assert 'db_row_counts' in res.json()

def test_companies_count():
    res = client.get('/api/v1/companies')
    assert res.status_code == 200
    assert len(res.json()) == 92

def test_company_tcs():
    res = client.get('/api/v1/companies/TCS')
    assert res.status_code == 200
    assert 'company' in res.json()
    assert res.json()['company']['id'] == 'TCS'

def test_invalid_ticker_404():
    res = client.get('/api/v1/companies/INVALID_TICKER_XYZ')
    assert res.status_code == 404

def test_screener_filter():
    res = client.get('/api/v1/screener?min_roe=15&max_de=1')
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 10
    for r in data:
        assert r['return_on_equity_pct'] >= 15.0

def test_sectors_count():
    res = client.get('/api/v1/sectors')
    assert res.status_code == 200
    assert len(res.json()) >= 10

def test_sector_companies():
    res = client.get('/api/v1/sectors/Information%20Technology/companies')
    assert res.status_code == 200
    assert len(res.json()) >= 4

def test_peer_group_members():
    res = client.get('/api/v1/peers/IT%20Services')
    assert res.status_code == 200
    assert len(res.json()) > 0

def test_compare_company_peers():
    res = client.get('/api/v1/companies/TCS/peers/compare')
    assert res.status_code == 200
    assert res.json()['peer_group'] == 'IT Services'

def test_market_cap_history():
    res = client.get('/api/v1/market-cap/TCS')
    assert res.status_code == 200
    assert len(res.json()) > 0

def test_portfolio_stats():
    res = client.get('/api/v1/portfolio/stats')
    assert res.status_code == 200
    assert len(res.json()) > 0

def test_tearsheet_binary():
    res = client.get('/api/v1/companies/TCS/tearsheet')
    assert res.status_code == 200
    assert res.headers['content-type'] == 'application/pdf'
    assert len(res.content) > 50000
