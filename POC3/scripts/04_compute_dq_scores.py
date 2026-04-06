"""
UC2: Compute DQ scores + generate pipeline metrics + detect anomalies.
Run: python scripts/04_compute_dq_scores.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from config import DATA_DIR
from utils.dq_scorer import compute_dq_scores, compute_price_dq_scores
from utils.anomaly import generate_pipeline_metrics, detect_anomalies, generate_anomaly_explanations


def main():
    # DQ Scores for products
    print("=" * 60)
    print("Computing DQ scores for merged catalog")
    print("=" * 60)
    catalog = pd.read_csv(DATA_DIR / "merged_catalog.csv")
    dq = compute_dq_scores(catalog)
    dq.to_csv(DATA_DIR / "dq_scores.csv", index=False)

    off_avg = dq[dq["source"] == "off"]["dq_score"].mean()
    usda_avg = dq[dq["source"] == "usda"]["dq_score"].mean()
    print(f"  OFF avg DQ: {off_avg:.1f}")
    print(f"  USDA avg DQ: {usda_avg:.1f}")
    print(f"  Saved {len(dq)} product DQ scores")

    # DQ Scores for Open Prices
    print("\n  Computing DQ scores for Open Prices...")
    prices = pd.read_csv(DATA_DIR / "open_prices.csv")
    price_dq = compute_price_dq_scores(prices)
    price_dq.to_csv(DATA_DIR / "dq_scores_prices.csv", index=False)
    print(f"  Open Prices avg DQ: {price_dq['dq_score'].mean():.1f}")
    print(f"  Saved {len(price_dq)} price DQ scores")

    # Pipeline metrics
    print("\n" + "=" * 60)
    print("Generating pipeline metrics (30 days)")
    print("=" * 60)
    metrics = generate_pipeline_metrics(days=30)
    metrics.to_csv(DATA_DIR / "pipeline_metrics.csv", index=False)
    print(f"  Saved {len(metrics)} daily metrics")

    # Anomaly detection
    print("\n  Running Isolation Forest...")
    metrics_scored, anomalies = detect_anomalies(metrics)
    metrics_scored.to_csv(DATA_DIR / "pipeline_metrics.csv", index=False)
    print(f"  Detected {len(anomalies)} anomalies")

    # LLM explanations
    if len(anomalies) > 0:
        print("\n  Generating LLM explanations for anomalies...")
        alerts = generate_anomaly_explanations(anomalies)
        alerts.to_csv(DATA_DIR / "anomaly_alerts.csv", index=False)
        print(f"  Saved {len(alerts)} anomaly alerts with explanations")


if __name__ == "__main__":
    main()
