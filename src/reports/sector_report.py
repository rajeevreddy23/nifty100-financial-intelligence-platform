"""Automated Sector Reports Generator: 11 sector PDF reports using ReportLab."""
import os
import sqlite3
import datetime
import pandas as pd
import numpy as np

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
DB_PATH = os.path.join(BASE_DIR, 'data/nifty100.db')
OUTPUT_DIR = os.path.join(BASE_DIR, 'reports/sector')

def generate_sector_report(sector_name: str, conn: sqlite3.Connection):
    today_str = datetime.datetime.now().strftime("%Y%m%d")
    safe_sec = "".join([c if c.isalnum() else "_" for c in sector_name]).strip("_")
    pdf_path = os.path.join(OUTPUT_DIR, f"{safe_sec}_report_{today_str}.pdf")

    # Query sector companies and ratios
    q = f"""
    SELECT s.company_id, c.company_name, s.sub_sector, s.index_weight_pct,
           r.return_on_equity_pct, r.return_on_capital_pct, r.net_profit_margin_pct,
           r.debt_to_equity, r.free_cash_flow_cr, r.revenue_cagr_5yr, r.composite_score,
           m.pe_ratio, m.market_cap_crore
    FROM sectors s
    JOIN companies c ON s.company_id = c.id
    LEFT JOIN (
        SELECT r1.* FROM financial_ratios r1
        INNER JOIN (
            SELECT company_id, MAX(year) as max_year FROM financial_ratios WHERE net_profit_margin_pct IS NOT NULL GROUP BY company_id
        ) l ON r1.company_id = l.company_id AND r1.year = l.max_year
    ) r ON s.company_id = r.company_id
    LEFT JOIN (
        SELECT m1.* FROM market_cap m1
        INNER JOIN (
            SELECT company_id, MAX(year) as max_year FROM market_cap GROUP BY company_id
        ) l2 ON m1.company_id = l2.company_id AND m1.year = l2.max_year
    ) m ON s.company_id = m.company_id
    WHERE s.broad_sector = '{sector_name}'
    ORDER BY r.composite_score DESC
    """
    df = pd.read_sql_query(q, conn)

    doc = SimpleDocTemplate(pdf_path, pagesize=A4, leftMargin=30, rightMargin=30, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(name='T', parent=styles['Heading1'], fontSize=16, leading=18, textColor=colors.HexColor('#0F2537'))
    sub_style = ParagraphStyle(name='S', parent=styles['Normal'], fontSize=9, leading=11, textColor=colors.HexColor('#555555'))
    body_style = ParagraphStyle(name='B', parent=styles['Normal'], fontSize=8, leading=10)

    story = []
    story.append(Paragraph(f"<b>Nifty 100 Sector Intelligence: {sector_name}</b>", title_style))
    story.append(Paragraph(f"Analysis of {len(df)} Constituents | Total Index Weight: {df['index_weight_pct'].sum():.2f}% | As of {datetime.datetime.now().strftime('%d %B %Y')}", sub_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0F2537'), spaceAfter=10, spaceBefore=4))

    # Median Benchmark Tiles
    med_roe = f"{df['return_on_equity_pct'].median():.1f}%"
    med_roce = f"{df['return_on_capital_pct'].median():.1f}%"
    med_npm = f"{df['net_profit_margin_pct'].median():.1f}%"
    med_pe = f"{df['pe_ratio'].median():.1f}x"
    tot_mktcap = f"₹{df['market_cap_crore'].sum():,.0f} Cr"

    tiles = [
        ["Constituents", "Median ROE", "Median ROCE", "Median NPM", "Median P/E", "Total Market Cap"],
        [str(len(df)), med_roe, med_roce, med_npm, med_pe, tot_mktcap]
    ]
    t_box = Table(tiles, colWidths=[89, 89, 89, 89, 89, 90])
    t_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F2537')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#F1F5F9')),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_box)
    story.append(Spacer(1, 14))

    # Company Ranking Table
    story.append(Paragraph("<b>Constituent Performance & Valuation Matrix</b>", styles['Heading3']))
    story.append(Spacer(1, 4))

    tbl_data = [["Ticker", "Company Name", "ROE %", "ROCE %", "NPM %", "D/E", "P/E", "FCF (₹ Cr)", "Score"]]
    for _, r in df.iterrows():
        tbl_data.append([
            r['company_id'],
            r['company_name'][:20],
            f"{r['return_on_equity_pct']:.1f}%" if pd.notna(r['return_on_equity_pct']) else "-",
            f"{r['return_on_capital_pct']:.1f}%" if pd.notna(r['return_on_capital_pct']) else "-",
            f"{r['net_profit_margin_pct']:.1f}%" if pd.notna(r['net_profit_margin_pct']) else "-",
            f"{r['debt_to_equity']:.2f}" if pd.notna(r['debt_to_equity']) else "-",
            f"{r['pe_ratio']:.1f}" if pd.notna(r['pe_ratio']) else "-",
            f"{r['free_cash_flow_cr']:,.0f}" if pd.notna(r['free_cash_flow_cr']) else "-",
            f"{r['composite_score']:.1f}" if pd.notna(r['composite_score']) else "-"
        ])

    t_sec = Table(tbl_data, colWidths=[55, 125, 45, 45, 45, 40, 40, 90, 50])
    t_sec.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('ALIGN', (2,0), (-1,-1), 'RIGHT'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_sec)

    doc.build(story)

def run_all_sector_reports():
    logger.info("Generating 11 Sector PDF Reports...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    sectors = [s[0] for s in conn.execute("SELECT DISTINCT broad_sector FROM sectors").fetchall()]
    for s in sectors:
        generate_sector_report(s, conn)
    conn.close()
    logger.info(f"Generated {len(sectors)} sector reports in {OUTPUT_DIR}")

if __name__ == '__main__':
    run_all_sector_reports()
