"""Statistical Analysis & Clustering Module: KMeans clustering, correlation heatmap, portfolio stats, outliers."""
import os
import sqlite3
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
DB_PATH = os.path.join(BASE_DIR, 'data/nifty100.db')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')

CLUSTER_NAMES = {
    0: "High-Quality Growth",
    1: "Defensive Dividend",
    2: "Value Cyclicals",
    3: "Distressed / High Debt",
    4: "Emerging Growth"
}

def run_clustering_and_stats():
    logger.info("Running Statistical Clustering and Portfolio Stats Module...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)

    # Latest full annual ratios per company
    q = """
    SELECT r.*, c.company_name, s.broad_sector
    FROM financial_ratios r
    JOIN companies c ON r.company_id = c.id
    JOIN sectors s ON r.company_id = s.company_id
    INNER JOIN (
        SELECT company_id, MAX(year) as max_year
        FROM financial_ratios
        WHERE net_profit_margin_pct IS NOT NULL
        GROUP BY company_id
    ) latest ON r.company_id = latest.company_id AND r.year = latest.max_year
    """
    df = pd.read_sql_query(q, conn)
    conn.close()

    # 1. Portfolio Statistics across all 92 companies
    kpi_list = [
        'return_on_equity_pct', 'return_on_capital_pct', 'net_profit_margin_pct',
        'operating_profit_margin_pct', 'debt_to_equity', 'interest_coverage',
        'asset_turnover', 'revenue_cagr_5yr', 'pat_cagr_5yr', 'composite_score'
    ]
    stat_rows = []
    for k in kpi_list:
        s = df[k].dropna()
        if len(s) > 0:
            stat_rows.append({
                'metric': k,
                'p10': round(float(s.quantile(0.10)), 2),
                'p25': round(float(s.quantile(0.25)), 2),
                'p50': round(float(s.median()), 2),
                'p75': round(float(s.quantile(0.75)), 2),
                'p90': round(float(s.quantile(0.90)), 2),
                'mean': round(float(s.mean()), 2),
                'std': round(float(s.std()), 2)
            })
    df_stats = pd.DataFrame(stat_rows)
    stats_path = os.path.join(OUTPUT_DIR, 'portfolio_stats.csv')
    df_stats.to_csv(stats_path, index=False)
    logger.info(f"Portfolio stats saved to {stats_path}")

    # 2. Correlation Matrix Heatmap
    corr_df = df[kpi_list].corr()
    plt.figure(figsize=(10, 8))
    sns.heatmap(corr_df, annot=True, cmap='coolwarm', fmt=".2f", linewidths=0.5)
    plt.title("Nifty 100 KPI Correlation Matrix", fontsize=14, fontweight='bold', pad=12)
    plt.tight_layout()
    heatmap_path = os.path.join(OUTPUT_DIR, 'correlation_heatmap.png')
    plt.savefig(heatmap_path, dpi=150)
    plt.close()
    logger.info(f"Correlation heatmap saved to {heatmap_path}")

    # 3. Outlier Detection per Sector (|Z| > 3)
    outlier_records = []
    for sector, grp in df.groupby('broad_sector'):
        if len(grp) >= 3:
            for k in ['return_on_equity_pct', 'operating_profit_margin_pct', 'debt_to_equity']:
                s = grp[k].dropna()
                mean = s.mean()
                std = s.std()
                if std > 0:
                    for _, r in grp.iterrows():
                        val = r[k]
                        if pd.notna(val):
                            z = (val - mean) / std
                            if abs(z) >= 2.5: # Outlier threshold
                                outlier_records.append({
                                    'company_id': r['company_id'],
                                    'metric': k,
                                    'value': round(float(val), 2),
                                    'z_score': round(float(z), 2),
                                    'sector': sector,
                                    'sector_mean': round(float(mean), 2),
                                    'sector_std': round(float(std), 2)
                                })
    df_outliers = pd.DataFrame(outlier_records)
    outlier_path = os.path.join(OUTPUT_DIR, 'outlier_report.csv')
    df_outliers.to_csv(outlier_path, index=False)
    logger.info(f"Outlier report ({len(df_outliers)} items) saved to {outlier_path}")

    # 4. KMeans Clustering (5 clusters)
    features = ['return_on_equity_pct', 'debt_to_equity', 'revenue_cagr_5yr', 'operating_profit_margin_pct', 'composite_score']
    X = df[features].copy()
    for col in features:
        X[col] = X[col].fillna(X[col].median())

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(X_scaled)
    df['cluster_id'] = clusters

    # Map cluster ids to names based on centroid profile
    centroids = pd.DataFrame(scaler.inverse_transform(kmeans.cluster_centers_), columns=features)
    # Order clusters by composite_score desc
    sorted_cluster_order = centroids['composite_score'].sort_values(ascending=False).index.tolist()
    name_map = {}
    label_order = ["High-Quality Growth", "Emerging Growth", "Defensive Dividend", "Value Cyclicals", "Distressed / High Debt"]
    for idx, c_orig in enumerate(sorted_cluster_order):
        name_map[c_orig] = label_order[idx]

    df['cluster_name'] = df['cluster_id'].map(name_map)
    df['distance_from_centroid'] = np.linalg.norm(X_scaled - kmeans.cluster_centers_[clusters], axis=1).round(3)

    cluster_out = df[['company_id', 'company_name', 'broad_sector', 'cluster_id', 'cluster_name', 'distance_from_centroid'] + features]
    cluster_path = os.path.join(OUTPUT_DIR, 'cluster_labels.csv')
    cluster_out.to_csv(cluster_path, index=False)
    logger.info(f"Cluster labels for all {len(cluster_out)} companies saved to {cluster_path}")

if __name__ == '__main__':
    run_clustering_and_stats()
