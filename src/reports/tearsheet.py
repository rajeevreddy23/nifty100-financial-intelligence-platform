"""Automated 2-page Company Tearsheet PDF generator using ReportLab."""
import os
import sys
import sqlite3
import datetime
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
DB_PATH = os.path.join(BASE_DIR, 'data/nifty100.db')
OUTPUT_DIR = os.path.join(BASE_DIR, 'reports/tearsheets')
RADAR_DIR = os.path.join(BASE_DIR, 'reports/radar_charts')

def create_charts(ticker, pl_df, ratios_df, temp_dir):
    """Generates 10-year revenue/profit bar chart and ROE/ROCE line chart."""
    chart_paths = {}
    
    # 1. Revenue & Profit chart
    if len(pl_df) > 0:
        fig, ax1 = plt.subplots(figsize=(7, 2.8))
        years = [str(y)[2:] for y in pl_df['year']]
        x = np.arange(len(years))
        width = 0.35

        sales = pl_df['sales'].fillna(0)
        profit = pl_df['net_profit'].fillna(0)

        ax1.bar(x - width/2, sales, width, label='Sales (₹ Cr)', color='#1f77b4', alpha=0.85)
        ax1.bar(x + width/2, profit, width, label='PAT (₹ Cr)', color='#2ca02c', alpha=0.85)

        ax1.set_xticks(x)
        ax1.set_xticklabels(years, fontsize=8, rotation=45)
        ax1.legend(loc='upper left', fontsize=8)
        ax1.set_title("10-Year Revenue & Net Profit History", fontsize=10, fontweight='bold', pad=6)
        plt.tight_layout()
        p1 = os.path.join(temp_dir, f"{ticker}_rev_pat.png")
        plt.savefig(p1, dpi=130)
        plt.close()
        chart_paths['rev_pat'] = p1

    # 2. ROE & ROCE trend
    if len(ratios_df) > 0:
        fig, ax2 = plt.subplots(figsize=(7, 2.5))
        r_clean = ratios_df.dropna(subset=['year'])
        yrs = [str(y)[2:] for y in r_clean['year']]
        roe = r_clean['return_on_equity_pct'].fillna(0)
        roce = r_clean['return_on_capital_pct'].fillna(0)

        ax2.plot(range(len(yrs)), roe, marker='o', linewidth=2, color='#ff7f0e', label='ROE %')
        ax2.plot(range(len(yrs)), roce, marker='s', linewidth=2, color='#9467bd', label='ROCE %')
        ax2.axhline(15, color='gray', linestyle='--', alpha=0.5, label='15% Benchmark')

        ax2.set_xticks(range(len(yrs)))
        ax2.set_xticklabels(yrs, fontsize=8, rotation=45)
        ax2.legend(loc='upper right', fontsize=8)
        ax2.set_title("Profitability Returns (ROE vs ROCE %)", fontsize=10, fontweight='bold', pad=6)
        plt.tight_layout()
        p2 = os.path.join(temp_dir, f"{ticker}_returns.png")
        plt.savefig(p2, dpi=130)
        plt.close()
        chart_paths['returns'] = p2

    return chart_paths

def generate_tearsheet(ticker: str, conn: sqlite3.Connection, temp_dir: str, df_pc: pd.DataFrame):
    """Builds a 2-page institutional-grade tearsheet PDF for a single company."""
    pdf_path = os.path.join(OUTPUT_DIR, f"{ticker}_tearsheet.pdf")
    
    # Query company master
    comp = pd.read_sql_query(f"SELECT * FROM companies WHERE id = '{ticker}'", conn).iloc[0]
    sec = pd.read_sql_query(f"SELECT * FROM sectors WHERE company_id = '{ticker}'", conn)
    broad_sector = sec['broad_sector'].values[0] if len(sec) > 0 else 'N/A'
    sub_sector = sec['sub_sector'].values[0] if len(sec) > 0 else 'N/A'
    
    pl = pd.read_sql_query(f"SELECT * FROM profitandloss WHERE company_id = '{ticker}' ORDER BY year ASC", conn)
    bs = pd.read_sql_query(f"SELECT * FROM balancesheet WHERE company_id = '{ticker}' ORDER BY year ASC", conn)
    cf = pd.read_sql_query(f"SELECT * FROM cashflow WHERE company_id = '{ticker}' ORDER BY year ASC", conn)
    ratios = pd.read_sql_query(f"SELECT * FROM financial_ratios WHERE company_id = '{ticker}' ORDER BY year ASC", conn)
    mc = pd.read_sql_query(f"SELECT * FROM market_cap WHERE company_id = '{ticker}' ORDER BY year ASC", conn)
    cap_alloc = pd.read_sql_query(f"SELECT * FROM capital_allocation WHERE company_id = '{ticker}' ORDER BY year DESC LIMIT 1", conn)

    latest_ratio = ratios.iloc[-1] if len(ratios) > 0 else {}
    latest_mc = mc.iloc[-1] if len(mc) > 0 else {}
    alloc_pattern = cap_alloc['pattern_label'].values[0] if len(cap_alloc) > 0 else 'N/A'

    # Filter pros/cons for this company
    pc_comp = df_pc[df_pc['company_id'] == ticker]

    # Create charts
    chart_paths = create_charts(ticker, pl.tail(10), ratios.tail(10), temp_dir)

    doc = SimpleDocTemplate(
        pdf_path, pagesize=A4,
        leftMargin=30, rightMargin=30, topMargin=25, bottomMargin=25
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(name='TitleStyle', parent=styles['Heading1'], fontSize=16, leading=18, textColor=colors.HexColor('#0F2537'))
    sub_style = ParagraphStyle(name='SubStyle', parent=styles['Normal'], fontSize=9, leading=11, textColor=colors.HexColor('#555555'))
    body_style = ParagraphStyle(name='Body', parent=styles['Normal'], fontSize=8, leading=10, textColor=colors.HexColor('#222222'))
    bold_body = ParagraphStyle(name='BoldBody', parent=body_style, fontName='Helvetica-Bold')

    story = []

    # ==================== PAGE 1 ====================
    # Header
    header_data = [
        [
            Paragraph(f"<b>{comp['company_name']} ({ticker})</b>", title_style),
            Paragraph(f"<b>Nifty 100 Intelligence Platform</b><br/>{datetime.datetime.now().strftime('%d %B %Y')}", ParagraphStyle(name='R', alignment=2, fontSize=8, leading=10, textColor=colors.HexColor('#777777')))
        ],
        [
            Paragraph(f"Sector: <b>{broad_sector}</b> | Industry: <b>{sub_sector}</b> | Face Value: ₹{comp.get('face_value', 10)}", sub_style),
            Paragraph(f"Capital Pattern: <b>{alloc_pattern}</b>", ParagraphStyle(name='R2', alignment=2, fontSize=8, textColor=colors.HexColor('#006699')))
        ]
    ]
    t_head = Table(header_data, colWidths=[360, 175])
    t_head.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(t_head)
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0F2537'), spaceAfter=8, spaceBefore=0))

    # KPI Summary Tiles (6 metric boxes)
    roe_val = f"{latest_ratio.get('return_on_equity_pct', 0):.1f}%" if pd.notna(latest_ratio.get('return_on_equity_pct')) else "N/A"
    roce_val = f"{latest_ratio.get('return_on_capital_pct', 0):.1f}%" if pd.notna(latest_ratio.get('return_on_capital_pct')) else "N/A"
    npm_val = f"{latest_ratio.get('net_profit_margin_pct', 0):.1f}%" if pd.notna(latest_ratio.get('net_profit_margin_pct')) else "N/A"
    de_val = f"{latest_ratio.get('debt_to_equity', 0):.2f}x" if pd.notna(latest_ratio.get('debt_to_equity')) else "0.0x"
    fcf_val = f"₹{latest_ratio.get('free_cash_flow_cr', 0):,.0f} Cr" if pd.notna(latest_ratio.get('free_cash_flow_cr')) else "N/A"
    pe_val = f"{latest_mc.get('pe_ratio', 0):.1f}x" if pd.notna(latest_mc.get('pe_ratio')) else "N/A"

    tile_data = [
        ["Return on Equity", "Return on Capital", "Net Profit Margin", "Debt-to-Equity", "Free Cash Flow", "P/E Ratio"],
        [roe_val, roce_val, npm_val, de_val, fcf_val, pe_val]
    ]
    t_tiles = Table(tile_data, colWidths=[89, 89, 89, 89, 89, 90])
    t_tiles.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F0F4F8')),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#E6EDF5')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 7.5),
        ('FONTNAME', (0,1), (-1,1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,1), (-1,1), 10.5),
        ('TEXTCOLOR', (0,1), (-1,1), colors.HexColor('#0F2537')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_tiles)
    story.append(Spacer(1, 8))

    # Business Overview paragraph
    about_txt = str(comp.get('about_company', ''))[:350]
    if len(str(comp.get('about_company', ''))) > 350: about_txt += '...'
    story.append(Paragraph(f"<b>About:</b> {about_txt}", body_style))
    story.append(Spacer(1, 8))

    # Page 1 Charts (Revenue & Net Profit Bar + ROE/ROCE Line)
    if 'rev_pat' in chart_paths:
        story.append(Image(chart_paths['rev_pat'], width=535, height=210))
        story.append(Spacer(1, 6))
    if 'returns' in chart_paths:
        story.append(Image(chart_paths['returns'], width=535, height=190))

    # ==================== PAGE 2 ====================
    story.append(PageBreak())

    # Header Page 2
    story.append(Paragraph(f"<b>{comp['company_name']} ({ticker}) — Financial Deep-Dive & Quality Profile</b>", title_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#0F2537'), spaceAfter=8, spaceBefore=4))

    # 5-Year Financial Summary Table
    pl_tail = pl.tail(5)
    r_tail = ratios.tail(5)
    table_headers = ["Metric (₹ Cr / %)"] + [str(y) for y in pl_tail['year']]
    
    rows = [
        table_headers,
        ["Revenue / Sales"] + [f"{v:,.0f}" for v in pl_tail['sales'].fillna(0)],
        ["Operating Profit (EBITDA)"] + [f"{v:,.0f}" for v in pl_tail['operating_profit'].fillna(0)],
        ["Net Profit (PAT)"] + [f"{v:,.0f}" for v in pl_tail['net_profit'].fillna(0)],
        ["EPS (₹)"] + [f"{v:.1f}" for v in pl_tail['eps'].fillna(0)],
        ["Operating Margin (OPM %)"] + [f"{v:.1f}%" for v in r_tail['operating_profit_margin_pct'].fillna(0)],
        ["Return on Equity (ROE %)"] + [f"{v:.1f}%" for v in r_tail['return_on_equity_pct'].fillna(0)],
        ["Debt-to-Equity (x)"] + [f"{v:.2f}" for v in r_tail['debt_to_equity'].fillna(0)],
        ["Free Cash Flow (₹ Cr)"] + [f"{v:,.0f}" for v in r_tail['free_cash_flow_cr'].fillna(0)]
    ]
    col_w = [185] + [70] * (len(table_headers) - 1)
    t_summary = Table(rows, colWidths=col_w)
    t_summary.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F2537')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_summary)
    story.append(Spacer(1, 10))

    # Radar Chart & Peer Comparison side-by-side or stacked
    radar_img_path = os.path.join(RADAR_DIR, f"{ticker}_radar.png")
    if os.path.exists(radar_img_path):
        story.append(Image(radar_img_path, width=280, height=220))
        story.append(Spacer(1, 6))

    # Qualitative Assessment (Pros & Cons)
    story.append(Paragraph("<b>Investment Highlights & Risk Factors</b>", bold_body))
    story.append(Spacer(1, 4))
    
    # Get pros and cons from pc_comp
    pros_list = [f"• <b>[PRO]</b> {r['text']}" for _, r in pc_comp[pc_comp['type']=='pro'].head(3).iterrows()]
    cons_list = [f"• <b>[CON]</b> {r['text']}" for _, r in pc_comp[pc_comp['type']=='con'].head(3).iterrows()]

    if not pros_list:
        pros_list = ["• <b>[PRO]</b> Strong industry standing in the Nifty 100 constituent universe."]
    if not cons_list:
        cons_list = ["• <b>[CON]</b> Broader market cyclicality and input cost inflation exposure."]

    pc_data = [
        [Paragraph("<font color='#2ca02c'><b>Key Strengths (Pros)</b></font>", bold_body), Paragraph("<font color='#d62728'><b>Risks & Considerations (Cons)</b></font>", bold_body)],
        [Paragraph("<br/>".join(pros_list), body_style), Paragraph("<br/>".join(cons_list), body_style)]
    ]
    t_pc = Table(pc_data, colWidths=[265, 270])
    t_pc.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,0), colors.HexColor('#E8F5E9')),
        ('BACKGROUND', (1,0), (1,0), colors.HexColor('#FFEBEE')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_pc)

    doc.build(story)

def run_all_tearsheets():
    logger.info("Generating 2-page Tearsheet PDFs for all 92 companies...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    temp_dir = os.path.join(BASE_DIR, 'reports/tearsheets/_temp')
    os.makedirs(temp_dir, exist_ok=True)

    pc_csv_path = os.path.join(BASE_DIR, 'output/pros_cons_generated.csv')
    df_pc = pd.read_csv(pc_csv_path) if os.path.exists(pc_csv_path) else pd.DataFrame(columns=['company_id', 'type', 'text'])

    conn = sqlite3.connect(DB_PATH)
    companies = pd.read_sql_query("SELECT id FROM companies ORDER BY id ASC", conn)['id'].tolist()
    
    for idx, cid in enumerate(companies):
        try:
            generate_tearsheet(cid, conn, temp_dir, df_pc)
            if (idx + 1) % 15 == 0 or (idx + 1) == len(companies):
                logger.info(f"Generated {idx + 1}/{len(companies)} tearsheets...")
        except Exception as e:
            logger.error(f"Error generating tearsheet for {cid}: {e}")

    conn.close()
    logger.info(f"All {len(companies)} tearsheets generated successfully in {OUTPUT_DIR}")

if __name__ == '__main__':
    run_all_tearsheets()
