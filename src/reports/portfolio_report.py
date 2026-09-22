"""Master Portfolio Summary Report: All 92 Nifty 100 constituents in a unified PDF."""
import os
import sqlite3
import datetime
import pandas as pd

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
OUTPUT_DIR = os.path.join(BASE_DIR, 'reports/portfolio')

def generate_portfolio_summary():
    today_str = datetime.datetime.now().strftime("%Y%m%d")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    pdf_path = os.path.join(OUTPUT_DIR, f"portfolio_summary_{today_str}.pdf")

    conn = sqlite3.connect(DB_PATH)
    q = """
    SELECT c.id as ticker, c.company_name, s.broad_sector,
           r.return_on_equity_pct, r.return_on_capital_pct, r.net_profit_margin_pct,
           r.debt_to_equity, r.free_cash_flow_cr, r.revenue_cagr_5yr, r.composite_score,
           m.pe_ratio, m.market_cap_crore
    FROM companies c
    JOIN sectors s ON c.id = s.company_id
    LEFT JOIN (
        SELECT r1.* FROM financial_ratios r1
        INNER JOIN (
            SELECT company_id, MAX(year) as max_year FROM financial_ratios WHERE net_profit_margin_pct IS NOT NULL GROUP BY company_id
        ) l ON r1.company_id = l.company_id AND r1.year = l.max_year
    ) r ON c.id = r.company_id
    LEFT JOIN (
        SELECT m1.* FROM market_cap m1
        INNER JOIN (
            SELECT company_id, MAX(year) as max_year FROM market_cap GROUP BY company_id
        ) l2 ON m1.company_id = l2.company_id AND m1.year = l2.max_year
    ) m ON c.id = m.company_id
    ORDER BY r.composite_score DESC
    """
    df = pd.read_sql_query(q, conn)
    conn.close()

    doc = SimpleDocTemplate(pdf_path, pagesize=A4, leftMargin=25, rightMargin=25, topMargin=25, bottomMargin=25)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(name='T', parent=styles['Heading1'], fontSize=16, leading=18, textColor=colors.HexColor('#0F2537'))
    sub_style = ParagraphStyle(name='S', parent=styles['Normal'], fontSize=8.5, leading=10, textColor=colors.HexColor('#555555'))

    story = []
    story.append(Paragraph("<b>Nifty 100 Master Portfolio Intelligence Summary</b>", title_style))
    story.append(Paragraph(f"Consolidated fundamental overview of all {len(df)} companies | Date: {datetime.datetime.now().strftime('%d %B %Y')}", sub_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0F2537'), spaceAfter=8, spaceBefore=4))

    # Chunk into pages of ~25 companies each
    chunk_size = 28
    for start in range(0, len(df), chunk_size):
        chunk = df.iloc[start:start+chunk_size]
        tbl_data = [["#", "Ticker", "Company Name", "Sector", "ROE %", "ROCE %", "NPM %", "D/E", "P/E", "FCF (₹ Cr)", "Score"]]
        
        for idx, (_, r) in enumerate(chunk.iterrows()):
            tbl_data.append([
                str(start + idx + 1),
                r['ticker'],
                r['company_name'][:20],
                r['broad_sector'][:14],
                f"{r['return_on_equity_pct']:.1f}%" if pd.notna(r['return_on_equity_pct']) else "-",
                f"{r['return_on_capital_pct']:.1f}%" if pd.notna(r['return_on_capital_pct']) else "-",
                f"{r['net_profit_margin_pct']:.1f}%" if pd.notna(r['net_profit_margin_pct']) else "-",
                f"{r['debt_to_equity']:.2f}" if pd.notna(r['debt_to_equity']) else "-",
                f"{r['pe_ratio']:.1f}" if pd.notna(r['pe_ratio']) else "-",
                f"{r['free_cash_flow_cr']:,.0f}" if pd.notna(r['free_cash_flow_cr']) else "-",
                f"{r['composite_score']:.1f}" if pd.notna(r['composite_score']) else "-"
            ])

        t_port = Table(tbl_data, colWidths=[20, 50, 115, 80, 42, 42, 42, 38, 38, 50, 28])
        t_port.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F2537')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 7.5),
            ('ALIGN', (4,0), (-1,-1), 'RIGHT'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
            ('TOPPADDING', (0,0), (-1,-1), 2.5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ]))
        story.append(t_port)
        if start + chunk_size < len(df):
            story.append(PageBreak())

    doc.build(story)
    logger.info(f"Master portfolio summary generated at {pdf_path}")

if __name__ == '__main__':
    generate_portfolio_summary()
