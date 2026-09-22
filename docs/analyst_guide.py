"""Generates 12-page comprehensive Analyst Guide PDF using ReportLab."""
import os
import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
DOCS_DIR = os.path.join(BASE_DIR, 'docs')

def generate_analyst_guide():
    os.makedirs(DOCS_DIR, exist_ok=True)
    pdf_path = os.path.join(DOCS_DIR, 'analyst_guide.pdf')

    doc = SimpleDocTemplate(pdf_path, pagesize=A4, leftMargin=35, rightMargin=35, topMargin=35, bottomMargin=35)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(name='T', parent=styles['Heading1'], fontSize=18, leading=22, textColor=colors.HexColor('#0F2537'), alignment=1)
    h2_style = ParagraphStyle(name='H2', parent=styles['Heading2'], fontSize=13, leading=16, textColor=colors.HexColor('#006699'), spaceBefore=8, spaceAfter=4)
    body_style = ParagraphStyle(name='B', parent=styles['Normal'], fontSize=9, leading=13, textColor=colors.HexColor('#2D3748'))
    bullet_style = ParagraphStyle(name='Bullet', parent=body_style, leftIndent=12)

    story = []

    # Page 1: Cover Page
    story.append(Spacer(1, 100))
    story.append(Paragraph("<b>NIFTY 100 FINANCIAL INTELLIGENCE PLATFORM</b>", title_style))
    story.append(Spacer(1, 15))
    story.append(Paragraph("<b>Comprehensive Analyst Guide & System Reference</b>", ParagraphStyle(name='Sub', alignment=1, fontSize=13, textColor=colors.HexColor('#4A5568'))))
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="60%", thickness=2, color=colors.HexColor('#006699'), spaceAfter=20, spaceBefore=10))
    story.append(Paragraph("Version 1.0 · Institutional Equity Research & Fundamental Analysis Division", ParagraphStyle(name='Meta', alignment=1, fontSize=9, textColor=colors.HexColor('#718096'))))
    story.append(Paragraph(f"Published: {datetime.datetime.now().strftime('%B %Y')}", ParagraphStyle(name='Meta2', alignment=1, fontSize=8.5, textColor=colors.HexColor('#A0AEC0'))))
    story.append(PageBreak())

    # Pages 2 to 12: Content Sections
    sections = [
        ("Section 1: Platform Overview & Architecture", [
            "The Nifty 100 Financial Intelligence Platform is a production-grade fundamental equity analytics system designed for research analysts.",
            "It transforms raw financial statements across 92 constituents of the Nifty 100 into institutional-grade KPIs, valuation screens, and interactive dashboards.",
            "Key Architectural Layers:",
            "• Layer 1 (Ingestion): Reads raw Excel files with automatic header and formatting normalization.",
            "• Layer 2 (ETL & DQ): Enforces 16 Data Quality rules preventing duplicate, invalid, or corrupted records.",
            "• Layer 3 (Storage): SQLite relational database maintaining complete foreign-key integrity.",
            "• Layer 4 (Analytics): Vectorized 50+ KPI computation engine including CAGR turnaround handling.",
            "• Layer 5 (Intelligence): Capital allocation pattern matching, KMeans clustering, and automated NLP pros/cons.",
            "• Layer 6 (Reporting): Fully automated PDF tearsheets, sector reports, and portfolio summaries.",
            "• Layer 7 (Interface): Multi-screen Streamlit application and high-performance REST API."
        ]),
        ("Section 2: Data Quality & Normalization Standard", [
            "Data fidelity is guaranteed through 16 automated Data Quality rules executed at ingest time:",
            "• DQ-01: Company Primary Key Uniqueness — Enforces unique NSE ticker identifiers.",
            "• DQ-02: Annual Time-Series Uniqueness — Enforces unique (company_id, year) composite pairs.",
            "• DQ-03: Foreign Key Integrity — Strictly rejects orphaned child records lacking master company entries.",
            "• DQ-04: Balance Sheet Equality — Flags balance sheet discrepancies exceeding 1% asset tolerance.",
            "• DQ-05: Operating Margin Validation — Cross-validates source OPM against (operating_profit / sales).",
            "• DQ-06: Revenue Plausibility — Audits zero or negative revenues for non-financial companies.",
            "• DQ-07: Year Standardisation — Coerces diverse fiscal formats (e.g. 'Mar 23', 'FY24') into 'YYYY-MM'.",
            "• DQ-08: Ticker Normalization — Enforces uppercase formatting and validates ticker character patterns."
        ]),
        ("Section 3: Financial KPI Definitions & Formulas", [
            "Comprehensive formulas utilized across the analytics layer:",
            "1. Return on Equity (ROE) = Net Profit / (Equity Capital + Reserves) × 100. Evaluates return on net assets.",
            "2. Return on Capital Employed (ROCE) = EBIT / Capital Employed × 100. Measures total capital efficiency.",
            "3. Net Profit Margin (NPM) = Net Profit / Sales × 100. Expresses final post-tax profitability.",
            "4. Debt-to-Equity (D/E) = Total Borrowings / Net Worth. Measures corporate financial leverage.",
            "5. Interest Coverage Ratio (ICR) = (Operating Profit + Other Income) / Finance Costs.",
            "6. Free Cash Flow (FCF) = Operating Cash Flow + Investing Cash Flow.",
            "7. Cash Flow Quality Ratio = Cash from Operations / Net Profit. Identifies accrual lockup when < 0.5x."
        ]),
        ("Section 4: Compound Growth (CAGR) & Turnaround Logic", [
            "Standard CAGR calculations fail when companies experience turnaround from losses or transition to losses.",
            "The Platform adopts a formal Decision Matrix:",
            "• Base > 0 and End > 0: Evaluated standard CAGR = ((End/Base)^(1/n) - 1) × 100.",
            "• Base < 0 and End > 0: Turnaround State. CAGR is mathematically undefined; tagged as 'TURNAROUND ↑'.",
            "• Base > 0 and End < 0: Deterioration to Loss. Tagged as 'DECLINE_TO_LOSS'.",
            "• Base < 0 and End < 0: Consecutive Loss-making. Tagged as 'BOTH_NEGATIVE'.",
            "• Base = 0: Zero Base denominator error. Tagged as 'ZERO_BASE'.",
            "• History < n years: Tagged as 'INSUFFICIENT'."
        ]),
        ("Section 5: Capital Allocation Pattern Matrix", [
            "Every company-year is categorized into one of 8 distinct capital allocation models based on cash flow signs:",
            "• (+, -, -): 'Reinvestor' or 'Shareholder Returns' — Cash generated from core operations is reinvested into capex while returning excess to shareholders.",
            "• (+, -, +): 'Expansion via External Capital' — Operations, debt, and equity all finance massive growth.",
            "• (+, +, -): 'Asset Divestment & Debt Repayment' — Monetizing assets to deleverage.",
            "• (-, -, +): 'High Growth / External Funding' — Early-stage capital-intensive ramp.",
            "• (-, -, -): 'Severe Cash Distress' — Burning operational cash, incurring capex, and repaying capital.",
            "• (-, +, +): 'Asset Sale to Fund Operations' — Distress signal requiring immediate analyst triage."
        ]),
        ("Section 6: Investment Screener Usage & Presets", [
            "The Screener engine allows multi-parameter filtering across 18 fundamental metrics.",
            "Six Built-in Presets:",
            "1. Quality Compounder: ROE > 15%, D/E < 1.0, FCF > 0, Revenue CAGR 5yr > 10%.",
            "2. Value Pick: P/E < 20, P/B < 3.0, D/E < 2.0, Dividend Yield > 1.0%.",
            "3. Growth Accelerator: PAT CAGR 5yr > 20%, Revenue CAGR 5yr > 15%, D/E < 2.0.",
            "4. Dividend Champion: Dividend Yield > 2.0%, Dividend Payout < 80%, FCF > 0.",
            "5. Debt-Free Blue Chip: D/E = 0.0, ROE > 12.0%, Sales > ₹5,000 Cr.",
            "6. Turnaround Watch: Revenue CAGR 3yr > 10.0%, FCF positive latest year, D/E < 2.5."
        ]),
        ("Section 7: Composite Health Scoring Model", [
            "The Composite Financial Quality Score (0–100) eliminates single-metric distortion:",
            "• Profitability (35% Weight): ROE (15%), ROCE (10%), Net Profit Margin (10%).",
            "• Cash Generation Quality (30% Weight): FCF Compounding (15%), CFO/PAT (10%), Positive FCF (5%).",
            "• Topline & Bottomline Growth (20% Weight): Revenue CAGR 5yr (10%), PAT CAGR 5yr (10%).",
            "• Balance Sheet Solvency (15% Weight): D/E Ratio (10%), Interest Coverage (5%).",
            "All underlying metrics undergo P10/P90 Winsorization to prevent extreme outliers from skewing results."
        ]),
        ("Section 8: Peer Comparison & Benchmark Engines", [
            "Covers 11 dedicated peer groups representing core sectors of the Indian economy.",
            "Within each group, companies are evaluated across 20 distinct metrics using percentile ranking (0–100%).",
            "• Best-in-Class Detection: Companies placing in the top quartile (≥ 75th percentile) on ≥ 6 of 10 primary metrics.",
            "• Watch List Detection: Companies placing in the bottom quartile (≤ 25th percentile) on ≥ 4 of 10 metrics.",
            "• Benchmark Gap Analysis: Direct metric-level spread vs group benchmark leader (e.g. TCS for IT, HDFCBANK for Private Banks)."
        ]),
        ("Section 9: Valuation & Market Multiples Analysis", [
            "Utilizes historical and current valuation multiples to uncover mispricing opportunities:",
            "• P/E vs 5-Year Historical Median: Identifies whether a company is expanding or compressing valuation.",
            "• Sector-Relative P/E: Flags 'Caution (Overvalued)' if P/E > 1.5x sector median; flags 'Discount (Undervalued)' if < 0.7x sector median.",
            "• Free Cash Flow Yield: Compares post-capex cash generation against equity market capitalization."
        ]),
        ("Section 10: Statistical Clustering & Portfolio Distribution", [
            "KMeans clustering (k=5) classifies the Nifty 100 universe into 5 behavioral archetypes:",
            "1. High-Quality Growth: Exceptional returns on equity, robust margins, and zero-to-low debt.",
            "2. Defensive Dividend: Stable cash cows with above-average dividend yield and moderate growth.",
            "3. Value Cyclicals: Capital-intensive commodity and industrial players trading at conservative multiples.",
            "4. Emerging Growth: High reinvestment rates with rapid topline scaling.",
            "5. Distressed / High Debt: Highly leveraged balance sheets or erratic operational earnings."
        ]),
        ("Section 11: Automated Reporting Layer", [
            "The platform generates complete publication-ready PDF documents:",
            "• Company Tearsheets: 2-page detailed summaries including 10-year financials, charts, and qualitative insights.",
            "• Sector Overviews: 11 sector publications summarizing constituent matrices and median benchmarks.",
            "• Master Portfolio Summary: Unified catalog of all 92 Nifty 100 companies.",
            "All reports adhere strictly to print margins, typography hierarchies, and automated vector chart embedding."
        ])
    ]

    for title, paragraphs in sections:
        story.append(Paragraph(f"<b>{title}</b>", h2_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#CBD5E1'), spaceAfter=8, spaceBefore=2))
        for p in paragraphs:
            if p.startswith("•"):
                story.append(Paragraph(p, bullet_style))
            else:
                story.append(Paragraph(p, body_style))
            story.append(Spacer(1, 3))
        story.append(PageBreak())

    doc.build(story)
    logger.info(f"Analyst guide generated at {pdf_path}")

if __name__ == '__main__':
    generate_analyst_guide()
