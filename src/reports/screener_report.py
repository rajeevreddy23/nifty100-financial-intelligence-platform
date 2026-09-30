"""Screener PDF report generator module."""
import os
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def generate_screener_pdf(excel_path: str = "output/screener_output.xlsx", out_pdf: str = "reports/portfolio/screener_report.pdf") -> str:
    """Generate a formatted PDF summary from screener_output.xlsx."""
    os.makedirs(os.path.dirname(out_pdf), exist_ok=True)
    doc = SimpleDocTemplate(out_pdf, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    story = [Paragraph("<b>Nifty 100 Investment Screener Report</b>", styles["Title"]), Spacer(1, 12)]
    if os.path.exists(excel_path):
        df = pd.read_excel(excel_path).head(25)
        cols = list(df.columns[:8])
        table_data = [cols] + df[cols].round(2).astype(str).values.tolist()
        t = Table(table_data)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e78")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(t)
    doc.build(story)
    return out_pdf


if __name__ == "__main__":
    generate_screener_pdf()
