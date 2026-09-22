# Nifty 100 Financial Intelligence Platform

> **Student Name:** Rajeev Reddy | **Group Code:** 62FMBF  
> **GitHub Repository:** [https://github.com/rajeevreddy23/nifty100-financial-intelligence-platform](https://github.com/rajeevreddy23/nifty100-financial-intelligence-platform)  
> **Documentation:** [Acceptance Checklist & Quality Sign-Off](docs/acceptance_checklist.pdf)  

An enterprise-grade, reproducible financial intelligence platform covering 92 constituents of the Nifty 100 index across 10–14 years of financial history (~11,000+ fundamental data points).

---

## 🏛️ System Architecture

The platform is structured into 7 distinct layers with 12 analytical modules:

- **Layer 1: Raw Ingestion**: Handles 7 core files (header=1) and 5 supplementary datasets.
- **Layer 2: ETL & Normalisation**: Enforces 16 Data Quality (DQ) validation rules with ticker & year normalization.
- **Layer 3: Relational Database**: SQLite database (data/nifty100.db) with 10 tables and foreign-key integrity.
- **Layer 4: Analytics Engine**: 50+ financial KPIs, multi-year CAGR with turnaround detection, and 8 capital allocation classes.
- **Layer 5: Intelligence Layer**: Screener ranking engine, 11 peer group benchmark engines, KMeans clustering (k=5), and NLP pros/cons generation.
- **Layer 6: Reporting Layer**: Automated ReportLab PDF engines generating 92 tearsheets, 10 sector reports, and 1 portfolio summary.
- **Layer 7: Interface Layer**: 8-screen interactive Streamlit dashboard and 16-endpoint FastAPI REST server.

---

## 🚀 Quick Start Guide (< 5 Minutes)

### 1. Requirements & Installation
```bash
pip install -r requirements.txt
```

### 2. Run ETL Data Pipeline
```bash
python src/etl/loader.py
# (or make load)
```
Populates data/nifty100.db and generates output/load_audit.csv and output/validation_failures.csv.

### 3. Compute 50+ Financial Ratios
```bash
python src/analytics/ratios.py
# (or make ratios)
```
Populates financial_ratios table and writes output/capital_allocation.csv and output/ratio_edge_cases.log.

### 4. Run Screeners & Peer Benchmarking
```bash
python src/analytics/screener/engine.py
python src/analytics/peer.py
```
Exports output/screener_output.xlsx, output/peer_comparison.xlsx, and 92 radar chart PNGs in 
reports/radar_charts/.

### 5. Run Valuation, Cash Flow, Clustering & NLP
```bash
python src/analytics/valuation.py
python src/analytics/cashflow_analytics.py
python src/analytics/clustering.py
python src/nlp/parser.py
python src/nlp/pros_cons_generator.py
```
Outputs valuation_summary.xlsx, cashflow_intelligence.xlsx, cluster_labels.csv, portfolio_stats.csv, outlier_report.csv, and pros_cons_generated.csv.

### 6. Run Automated PDF Reports
```bash
python src/reports/tearsheet.py
python src/reports/sector_report.py
python src/reports/portfolio_report.py
```
Generates 92 company tearsheet PDFs, 10 sector reports, and 1 master portfolio summary.

### 7. Run Test Suite (69 Tests)
```bash
python -m pytest tests/ -v --html=reports/pytest_report.html --self-contained-html
# (or make test)
```

### 8. Launch Streamlit Web Dashboard
```bash
streamlit run src/dashboard/app.py
# (or make dashboard)
```
Opens the 8-screen web application at http://localhost:8501.

### 9. Launch FastAPI Server
```bash
uvicorn src.api.main:app --port 8000 --reload
# (or make api)
```
Interactive OpenAPI Swagger docs available at http://localhost:8000/docs.

---

## 📋 Acceptance Criteria Verification (20/20 Gates Passed)

| Gate | Area | Criterion | Result | Status |
|:---|:---|:---|:---|:---:|
| **AC-01** | Data Coverage | 92 companies in companies table | 92 companies | **PASSED** |
| **AC-02** | Time Coverage | >= 90% have >= 10yr statements | 95.7% (PL), 95.6% (BS), 93.4% (CF) | **PASSED** |
| **AC-03** | Schema Integrity | Zero foreign key errors | PRAGMA foreign_key_check = 0 | **PASSED** |
| **AC-04** | KPI Completeness | financial_ratios >= 1,100 rows | 1,155 rows populated | **PASSED** |
| **AC-05** | CAGR Accuracy | Matches manual Excel +-0.1% | TCS 10.46%, INFY 13.20% (exact) | **PASSED** |
| **AC-06** | ROE Accuracy | Matches master ROE +-5% | ABB 32.5% vs 34.9% | **PASSED** |
| **AC-07** | Screener Accuracy | Quality compounder 10-50 cos | 22 qualified companies | **PASSED** |
| **AC-08** | Dashboard Load | Loads in < 3 seconds | 12.8ms average load time | **PASSED** |
| **AC-09** | Dashboard Export | CSV download functional | Export verified | **PASSED** |
| **AC-10** | PDF Quality | No overflow / overlapping | 2-page flowables verified | **PASSED** |
| **AC-11** | API Health | /health returns 200 with counts | 200 OK | **PASSED** |
| **AC-12** | API Accuracy | /companies/TCS/ratios >= 10yr | 13 years returned | **PASSED** |
| **AC-13** | API Screener | Matches Module 3 results | Verified consistent | **PASSED** |
| **AC-14** | Peer Coverage | All 11 peer groups populated | 11 peer groups present | **PASSED** |
| **AC-15** | Cluster Coverage | 92 companies assigned cluster | 92 clustered (0-4), 0 nulls | **PASSED** |
| **AC-16** | NLP Coverage | >=1 pro and >=1 con for all 92 | 473 total, 0 missing | **PASSED** |
| **AC-17** | Report Coverage | 92 tearsheets, each >= 50KB | 92 PDFs (avg 184 KB) | **PASSED** |
| **AC-18** | Test Coverage | >= 60 tests, 0 failures | 69 passed in 1.79s | **PASSED** |
| **AC-19** | DQ Documentation | validation_failures.csv exists | 317 audited entries | **PASSED** |
| **AC-20** | Documentation | analyst_guide.pdf >= 10 pages | 12 pages verified | **PASSED** |

---

## 📁 Repository Structure

```
nifty100/
├── config/
│   ├── screener_config.yaml
│   ├── logging_config.yaml
│   └── .env.template
├── data/
│   ├── raw/                 # 7 core Excel files
│   ├── supporting/          # 5 supplementary Excel files
│   └── nifty100.db          # SQLite 10-table relational database
├── docs/
│   ├── Nifty100_Project_Document_FINAL.pdf
│   ├── analyst_guide.pdf    # 12-page analyst documentation
│   ├── acceptance_checklist.pdf
│   └── openapi.json         # Exported OpenAPI 3.0 specification
├── output/
│   ├── screener_output.xlsx
│   ├── peer_comparison.xlsx
│   ├── valuation_summary.xlsx
│   ├── cashflow_intelligence.xlsx
│   ├── cluster_labels.csv
│   ├── portfolio_stats.csv
│   ├── outlier_report.csv
│   ├── correlation_heatmap.png
│   ├── pros_cons_generated.csv
│   ├── analysis_parsed.csv
│   ├── capital_allocation.csv
│   ├── load_audit.csv
│   └── validation_failures.csv
├── reports/
│   ├── tearsheets/          # 92 2-page company tearsheet PDFs
│   ├── sector/              # 10 broad sector PDF reports
│   ├── portfolio/           # Master portfolio summary PDF
│   ├── radar_charts/        # 92 8-axis polar radar chart PNGs
│   └── pytest_report.html   # HTML test results
├── src/
│   ├── etl/                 # loader.py, normaliser.py, validator.py, schema.sql
│   ├── analytics/           # ratios.py, cagr.py, cashflow_kpis.py, peer.py, clustering.py
│   ├── nlp/                 # parser.py, pros_cons_generator.py
│   ├── reports/             # tearsheet.py, sector_report.py, portfolio_report.py
│   ├── api/                 # main.py (16 endpoints)
│   └── dashboard/           # app.py, pages/ (01-08), utils/
├── tests/
│   ├── etl/                 # 22 tests
│   ├── kpi/                 # 21 tests
│   ├── dq/                  # 14 tests
│   ├── api/                 # 12 tests
│   └── conftest.py
├── .env
├── Makefile
├── requirements.txt
└── README.md
```
