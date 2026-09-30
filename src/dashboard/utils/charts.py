"""Chart utility helpers for the Nifty 100 Streamlit dashboard."""
from typing import List
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def plot_kpi_trend(df: pd.DataFrame, x_col: str, y_col: str, title: str) -> go.Figure:
    """Create an interactive line chart for a financial KPI time-series."""
    fig = px.line(df, x=x_col, y=y_col, markers=True, title=title)
    fig.update_layout(template="plotly_white", height=360)
    return fig


def plot_sector_donut(df: pd.DataFrame, sector_col: str = "broad_sector") -> go.Figure:
    """Create a sector composition donut chart."""
    counts = df[sector_col].value_counts().reset_index()
    counts.columns = [sector_col, "count"]
    fig = px.pie(counts, names=sector_col, values="count", hole=0.45, title="Nifty 100 Sector Distribution")
    fig.update_layout(template="plotly_white", height=380)
    return fig


def plot_peer_radar(categories: List[str], company_vals: List[float], peer_vals: List[float], ticker: str) -> go.Figure:
    """Create an 8-axis polar radar chart comparing a company against its peer average."""
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=company_vals, theta=categories, fill="toself", name=ticker))
    fig.add_trace(go.Scatterpolar(r=peer_vals, theta=categories, fill="toself", name="Peer Avg"))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=True, height=420)
    return fig
