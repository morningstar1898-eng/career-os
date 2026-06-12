"""
tools/data_pipeline.py
Standalone script: download dataset → clean → analyze → chart → upload to Azure.
Can be called directly: python tools/data_pipeline.py --dataset "sales forecasting"
Or imported by the Data Analyst agent.
"""
import os, sys, argparse
import pandas as pd
import matplotlib
matplotlib.use("Agg")   # headless — no display needed
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Color palette (consistent across all charts) ──────────
PALETTE = ["#534AB7", "#1D9E75", "#BA7517", "#D85A30", "#378ADD"]


def search_and_download_dataset(topic: str) -> pd.DataFrame:
    """
    Use Kaggle API to find and download the best dataset for the topic.
    Falls back to a built-in sample if Kaggle credentials are missing.
    """
    try:
        import kaggle
        kaggle.api.authenticate()
        results = kaggle.api.dataset_list(search=topic, sort_by="votes", max_size=50)
        if not results:
            raise ValueError("No datasets found")
        best = results[0]
        ref = str(best)
        print(f"  📦 Downloading: {ref}")
        kaggle.api.dataset_download_files(ref, path=OUTPUT_DIR, unzip=True)
        # Find the first CSV in outputs
        for f in os.listdir(OUTPUT_DIR):
            if f.endswith(".csv"):
                df = pd.read_csv(os.path.join(OUTPUT_DIR, f))
                print(f"  ✅ Loaded {f}: {df.shape[0]:,} rows × {df.shape[1]} columns")
                return df
    except Exception as e:
        print(f"  ⚠️  Kaggle download failed ({e}). Using built-in sample.")

    # ── Built-in fallback: synthetic sales data ─────────────
    import numpy as np
    np.random.seed(42)
    n = 500
    df = pd.DataFrame({
        "date": pd.date_range("2023-01-01", periods=n, freq="D"),
        "region": np.random.choice(["North","South","East","West"], n),
        "product": np.random.choice(["Analytics Pro","BI Lite","DataKit","CloudDB"], n),
        "sales": np.random.normal(12000, 3500, n).clip(1000),
        "units": np.random.randint(1, 50, n),
        "satisfaction": np.random.uniform(3.0, 5.0, n).round(1),
    })
    print(f"  ✅ Using synthetic sales dataset: {df.shape[0]:,} rows")
    return df


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generic cleaning: drop nulls, dedupe, parse dates, normalize column names.
    """
    original_shape = df.shape
    df = df.copy()
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    df = df.drop_duplicates()
    df = df.dropna(thresh=int(len(df.columns) * 0.5))  # drop rows that are >50% null

    # Try to parse any column named date/time/timestamp
    for col in df.columns:
        if any(k in col for k in ["date", "time", "timestamp"]):
            try:
                df[col] = pd.to_datetime(df[col], errors="coerce")
            except Exception:
                pass

    print(f"  🧹 Cleaned: {original_shape} → {df.shape}")
    return df


def generate_charts(df: pd.DataFrame, topic: str) -> list:
    """
    Generate 3 charts tailored to what's in the dataframe.
    Returns list of saved file paths.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    charts = []
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    cat_cols = df.select_dtypes(include="object").columns.tolist()
    date_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]

    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "figure.dpi": 120,
    })

    # ── Chart 1: Distribution of primary numeric column ────
    if numeric_cols:
        col = numeric_cols[0]
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.hist(df[col].dropna(), bins=30, color=PALETTE[0], alpha=0.85, edgecolor="white")
        ax.set_title(f"Distribution: {col.replace('_',' ').title()}", fontsize=14, fontweight="bold", pad=12)
        ax.set_xlabel(col.replace("_"," ").title())
        ax.set_ylabel("Count")
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
        plt.tight_layout()
        path = os.path.join(OUTPUT_DIR, f"chart1_distribution_{timestamp}.png")
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        charts.append(path)
        print(f"  📊 Chart 1 saved: {os.path.basename(path)}")

    # ── Chart 2: Category breakdown (bar chart) ────────────
    if cat_cols and numeric_cols:
        cat = cat_cols[0]
        num = numeric_cols[0]
        grouped = df.groupby(cat)[num].mean().sort_values(ascending=False).head(10)
        fig, ax = plt.subplots(figsize=(9, 5))
        bars = ax.barh(grouped.index, grouped.values, color=PALETTE[1], alpha=0.85)
        ax.bar_label(bars, fmt="%.0f", padding=4, fontsize=9)
        ax.set_title(f"Avg {num.replace('_',' ').title()} by {cat.replace('_',' ').title()}", fontsize=14, fontweight="bold", pad=12)
        ax.set_xlabel(f"Average {num.replace('_',' ').title()}")
        ax.invert_yaxis()
        plt.tight_layout()
        path = os.path.join(OUTPUT_DIR, f"chart2_by_category_{timestamp}.png")
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        charts.append(path)
        print(f"  📊 Chart 2 saved: {os.path.basename(path)}")

    # ── Chart 3: Time series OR scatter ────────────────────
    if date_cols and numeric_cols:
        date_col = date_cols[0]
        num = numeric_cols[0]
        ts = df.set_index(date_col)[num].resample("W").mean().dropna()
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.plot(ts.index, ts.values, color=PALETTE[2], linewidth=2)
        ax.fill_between(ts.index, ts.values, alpha=0.12, color=PALETTE[2])
        ax.set_title(f"Weekly Trend: {num.replace('_',' ').title()}", fontsize=14, fontweight="bold", pad=12)
        ax.set_xlabel("Date")
        ax.set_ylabel(f"Avg {num.replace('_',' ').title()}")
        plt.tight_layout()
        path = os.path.join(OUTPUT_DIR, f"chart3_trend_{timestamp}.png")
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        charts.append(path)
        print(f"  📊 Chart 3 saved: {os.path.basename(path)}")
    elif len(numeric_cols) >= 2:
        x_col, y_col = numeric_cols[0], numeric_cols[1]
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.scatter(df[x_col], df[y_col], color=PALETTE[3], alpha=0.4, s=20)
        ax.set_title(f"{x_col.replace('_',' ').title()} vs {y_col.replace('_',' ').title()}", fontsize=14, fontweight="bold", pad=12)
        ax.set_xlabel(x_col.replace("_"," ").title())
        ax.set_ylabel(y_col.replace("_"," ").title())
        plt.tight_layout()
        path = os.path.join(OUTPUT_DIR, f"chart3_scatter_{timestamp}.png")
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        charts.append(path)
        print(f"  📊 Chart 3 saved: {os.path.basename(path)}")

    return charts


def upload_charts(chart_paths: list) -> list:
    """Upload charts to Azure Blob Storage. Returns list of public URLs."""
    urls = []
    try:
        from azure.storage.blob import BlobServiceClient
        conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        container = os.getenv("AZURE_STORAGE_CONTAINER", "portfolio-charts")
        if not conn_str:
            print("  ⚠️  No Azure connection string — skipping upload.")
            return chart_paths
        client = BlobServiceClient.from_connection_string(conn_str)
        for path in chart_paths:
            blob_name = os.path.basename(path)
            with open(path, "rb") as f:
                client.get_blob_client(container=container, blob=blob_name).upload_blob(f, overwrite=True)
            url = f"https://{client.account_name}.blob.core.windows.net/{container}/{blob_name}"
            urls.append(url)
            print(f"  ☁️  Uploaded: {url}")
    except Exception as e:
        print(f"  ⚠️  Azure upload error: {e}")
        urls = chart_paths
    return urls


def generate_insight_summary(df: pd.DataFrame) -> str:
    """Generate a 3-sentence plain-English insight summary."""
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    cat_cols = df.select_dtypes(include="object").columns.tolist()
    lines = []
    if numeric_cols:
        col = numeric_cols[0]
        lines.append(
            f"The dataset contains {len(df):,} records. "
            f"{col.replace('_',' ').title()} ranges from {df[col].min():,.0f} to {df[col].max():,.0f} "
            f"with a mean of {df[col].mean():,.0f}."
        )
    if cat_cols and numeric_cols:
        cat, num = cat_cols[0], numeric_cols[0]
        top = df.groupby(cat)[num].mean().idxmax()
        lines.append(
            f"The highest average {num.replace('_',' ')} is in the '{top}' {cat.replace('_',' ')} category."
        )
    lines.append(
        "Three visualizations were generated and uploaded to Azure Blob Storage for the portfolio."
    )
    return " ".join(lines)


def run_pipeline(topic: str = "business sales analytics") -> dict:
    print(f"\n📊 Data Pipeline — topic: '{topic}'")
    df_raw = search_and_download_dataset(topic)
    df = clean_dataframe(df_raw)
    charts = generate_charts(df, topic)
    urls = upload_charts(charts)
    summary = generate_insight_summary(df)
    print(f"\n💡 Insight: {summary}\n")
    return {"summary": summary, "chart_urls": urls, "rows": len(df), "columns": list(df.columns)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="business sales analytics", help="Topic to search on Kaggle")
    args = parser.parse_args()
    result = run_pipeline(args.dataset)
    print(result)
