"""UC2: Quality Scoring + Pipeline Observability tab."""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DATA_DIR


def render():
    st.header("UC2: Quality Scoring + Pipeline Observability")
    st.caption("Score every product 0-100 → monitor pipeline metrics → detect anomalies → LLM explains root cause")

    try:
        dq = pd.read_csv(DATA_DIR / "dq_scores.csv")
        price_dq = pd.read_csv(DATA_DIR / "dq_scores_prices.csv") if (DATA_DIR / "dq_scores_prices.csv").exists() else pd.DataFrame()
        metrics = pd.read_csv(DATA_DIR / "pipeline_metrics.csv")
        alerts = pd.read_csv(DATA_DIR / "anomaly_alerts.csv") if (DATA_DIR / "anomaly_alerts.csv").exists() else pd.DataFrame()
    except FileNotFoundError as e:
        st.error(f"Data not found: {e}. Run scripts/04_compute_dq_scores.py first.")
        return

    # Section 1: DQ Scoreboard
    st.subheader("1. DQ Scoreboard")

    col1, col2, col3 = st.columns(3)
    off_avg = dq[dq["source"] == "off"]["dq_score"].mean()
    usda_avg = dq[dq["source"] == "usda"]["dq_score"].mean()
    price_avg = price_dq["dq_score"].mean() if len(price_dq) > 0 else 0
    with col1:
        st.metric("Open Food Facts", f"{off_avg:.0f}/100", delta=f"{off_avg - 75:.0f} vs target")
    with col2:
        st.metric("USDA FoodData", f"{usda_avg:.0f}/100", delta=f"{usda_avg - 75:.0f} vs target")
    with col3:
        st.metric("Open Prices", f"{price_avg:.0f}/100", delta=f"{price_avg - 75:.0f} vs target")

    source_labels = {"off": "Open Food Facts", "usda": "USDA FoodData"}
    source_filter = st.multiselect("Filter by source:", ["off", "usda"], default=["off", "usda"], key="dq_filter", format_func=lambda x: source_labels.get(x, x))
    filtered_dq = dq[dq["source"].isin(source_filter)]

    def color_score(val):
        if val >= 75:
            return "background-color: #90EE90"
        elif val >= 50:
            return "background-color: #FFD700"
        else:
            return "background-color: #FF6B6B"

    display_cols = ["name", "brand", "source", "completeness", "consistency", "accuracy", "freshness", "dq_score"]
    available_cols = [c for c in display_cols if c in filtered_dq.columns]
    styled = filtered_dq[available_cols].sort_values("dq_score").style.map(color_score, subset=["dq_score"])
    st.dataframe(styled, use_container_width=True)

    # DQ Score distribution
    dq_display = dq.copy()
    dq_display["source_label"] = dq_display["source"].map({"off": "Open Food Facts", "usda": "USDA FoodData"})
    fig = px.histogram(dq_display, x="dq_score", color="source_label", nbins=20, title="DQ Score Distribution by Source",
                       color_discrete_map={"Open Food Facts": "#FF6B6B", "USDA FoodData": "#90EE90"})
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Section 2: Score Breakdown
    st.subheader("2. Score Breakdown (Radar Chart)")

    product_options = dq["name"].dropna().tolist()
    if product_options:
        selected = st.selectbox("Select product:", product_options, key="radar_product")
        row = dq[dq["name"] == selected].iloc[0]

        categories = ["Completeness", "Consistency", "Accuracy", "Freshness"]
        values = [row["completeness"], row["consistency"], row["accuracy"], row["freshness"]]

        fig = go.Figure(data=go.Scatterpolar(
            r=values + [values[0]],
            theta=categories + [categories[0]],
            fill="toself",
            name=selected,
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 25])),
            title=f"DQ Breakdown: {selected[:40]} (Total: {row['dq_score']})",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Section 3: Pipeline Observability
    st.subheader("3. Pipeline Observability (30 Days)")

    if "date" in metrics.columns:
        metrics["date"] = pd.to_datetime(metrics["date"])
        is_anomaly = metrics.get("is_anomaly", pd.Series([False] * len(metrics)))

        for metric_name in ["null_rate", "row_count", "avg_completeness", "schema_fields"]:
            if metric_name in metrics.columns:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=metrics["date"], y=metrics[metric_name],
                    mode="lines+markers", name=metric_name,
                    line=dict(color="steelblue"),
                ))
                # Highlight anomalies
                anomaly_mask = is_anomaly.astype(bool) if is_anomaly.dtype != bool else is_anomaly
                if anomaly_mask.any():
                    anomaly_points = metrics[anomaly_mask]
                    fig.add_trace(go.Scatter(
                        x=anomaly_points["date"], y=anomaly_points[metric_name],
                        mode="markers", name="Anomaly",
                        marker=dict(color="red", size=12, symbol="x"),
                    ))
                fig.update_layout(title=f"Pipeline Metric: {metric_name}", height=300)
                st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Section 4: Anomaly Alerts
    st.subheader("4. Anomaly Alerts")

    if len(alerts) > 0:
        col1, col2 = st.columns(2)
        critical = (alerts["severity"] == "critical").sum() if "severity" in alerts.columns else 0
        warning = (alerts["severity"] == "warning").sum() if "severity" in alerts.columns else 0
        with col1:
            st.metric("Critical Alerts", critical)
        with col2:
            st.metric("Warning Alerts", warning)

        for _, alert in alerts.iterrows():
            severity = alert.get("severity", "warning")
            icon = "🔴" if severity == "critical" else "🟡"
            with st.expander(f"{icon} {alert.get('date', 'Unknown')} — {alert.get('primary_metric', 'Unknown')} ({severity})"):
                st.write(f"**Metric:** {alert.get('primary_metric', '')}")
                st.write(f"**Values:** null_rate={alert.get('null_rate', '')}, row_count={alert.get('row_count', '')}, completeness={alert.get('avg_completeness', '')}, schema={alert.get('schema_fields', '')}")
                st.write(f"**Explanation:** {alert.get('explanation', 'No explanation available.')}")
    else:
        st.info("No anomaly alerts. Run scripts/04_compute_dq_scores.py to generate.")
