"""Pipeline observability — synthetic metrics + Isolation Forest anomaly detection."""
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from datetime import datetime, timedelta


def generate_pipeline_metrics(days=30, seed=42):
    """Generate realistic pipeline metrics with injected anomalies."""
    rng = np.random.RandomState(seed)
    base_date = datetime(2026, 3, 1)
    dates = [base_date + timedelta(days=i) for i in range(days)]

    # Normal patterns
    null_rate = rng.normal(0.05, 0.01, days).clip(0.01, 0.15)
    row_count = rng.normal(4500, 200, days).clip(3000, 6000).astype(int)
    avg_completeness = rng.normal(0.65, 0.03, days).clip(0.4, 0.9)
    schema_fields = np.full(days, 210)

    # Inject anomalies
    # Day 12: null rate spike (OFF schema change)
    null_rate[11] = 0.42
    null_rate[12] = 0.38
    # Day 18: row count drop (USDA API outage)
    row_count[17] = 1200
    row_count[18] = 800
    # Day 23: schema field count change (OFF added columns)
    schema_fields[22:] = 215
    # Day 25: completeness drop
    avg_completeness[24] = 0.35
    avg_completeness[25] = 0.40

    metrics = pd.DataFrame({
        "date": dates,
        "null_rate": null_rate.round(4),
        "row_count": row_count,
        "avg_completeness": avg_completeness.round(4),
        "schema_fields": schema_fields,
        "source": ["pipeline"] * days,
    })
    return metrics


def detect_anomalies(metrics_df):
    """Run Isolation Forest on pipeline metrics."""
    feature_cols = ["null_rate", "row_count", "avg_completeness", "schema_fields"]
    X = metrics_df[feature_cols].values

    model = IsolationForest(contamination=0.15, random_state=42, n_estimators=100)
    predictions = model.fit_predict(X)
    scores = model.decision_function(X)

    metrics_df = metrics_df.copy()
    metrics_df["is_anomaly"] = predictions == -1
    metrics_df["anomaly_score"] = (-scores).round(4)  # Higher = more anomalous

    anomalies = metrics_df[metrics_df["is_anomaly"]].copy()

    # Determine which metric is most anomalous for each point
    for idx in anomalies.index:
        row = metrics_df.loc[idx]
        deviations = {}
        for col in feature_cols:
            mean = metrics_df[col].mean()
            std = metrics_df[col].std()
            if std > 0:
                deviations[col] = abs(row[col] - mean) / std
            else:
                deviations[col] = 0
        anomalies.loc[idx, "primary_metric"] = max(deviations, key=deviations.get)
        anomalies.loc[idx, "severity"] = "critical" if max(deviations.values()) > 3 else "warning"

    return metrics_df, anomalies


def generate_anomaly_explanations(anomalies_df):
    """Generate plain-English explanations for anomalies using LLM."""
    from utils.llm import call_llm

    explanations = []
    for _, row in anomalies_df.iterrows():
        date = row.get("date", "unknown")
        metric = row.get("primary_metric", "unknown")
        severity = row.get("severity", "warning")
        null_rate = row.get("null_rate", 0)
        row_count = row.get("row_count", 0)
        completeness = row.get("avg_completeness", 0)
        schema = row.get("schema_fields", 0)

        prompt = f"""You are a data pipeline observability expert. Explain this anomaly in 2-3 sentences.

Date: {date}
Primary anomalous metric: {metric}
Severity: {severity}
Current values: null_rate={null_rate}, row_count={row_count}, avg_completeness={completeness}, schema_fields={schema}
Normal ranges: null_rate=0.04-0.07, row_count=4000-5000, avg_completeness=0.60-0.70, schema_fields=210

What likely happened and what should the team investigate?"""

        explanation = call_llm(prompt, max_tokens=200)
        explanations.append({
            "date": str(date),
            "primary_metric": metric,
            "severity": severity,
            "null_rate": null_rate,
            "row_count": int(row_count),
            "avg_completeness": completeness,
            "schema_fields": int(schema),
            "explanation": explanation or f"Anomaly detected in {metric} on {date}. Value deviates significantly from normal range.",
        })

    return pd.DataFrame(explanations)
