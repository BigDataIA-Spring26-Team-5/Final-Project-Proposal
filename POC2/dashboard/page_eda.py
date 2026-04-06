from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

DATA_DIR = Path(__file__).parent.parent / "data"
CSV_PATH = DATA_DIR / "en.openfoodfacts.org.products-1k.csv"
SAMPLES_DIR = Path(__file__).parent.parent / "POC" / "archive" / "data_samples"

_OFF_SAMPLE_NAME = "open_food_facts_sample.csv"
_OFF_SAMPLE_RENAME = {
    "barcode": "code",
    "categories": "categories_en",
    "allergens": "allergens_en",
    "ingredients_text": "ingredients_text_en",
    "labels": "labels_en",
}


def _normalize_columns(df: pd.DataFrame, source_path: Path) -> pd.DataFrame:
    if source_path.name == _OFF_SAMPLE_NAME:
        return df.rename(columns=_OFF_SAMPLE_RENAME)
    return df

_KEY_FIELDS_RAW = [
    "product_name",
    "brands",
    "quantity",
    "categories_en",
    "allergens_en",
    "ingredients_text_en",
]

_KEY_FIELDS_ENRICHED = [
    "product_name",
    "brands",
    "quantity_normalized",
    "categories_clean",
    "allergens_extracted",
    "ingredients_text_en",
]

_FIELD_LABELS = [
    "product_name",
    "brands",
    "quantity",
    "categories",
    "allergens",
    "ingredients",
]


def _null_rate(df: pd.DataFrame, col: str) -> float:
    if col not in df.columns:
        return 1.0
    total = len(df)
    if total == 0:
        return 0.0
    nulls = df[col].apply(
        lambda v: v is None
        or (isinstance(v, float) and pd.isna(v))
        or (isinstance(v, str) and not v.strip())
        or (isinstance(v, list) and len(v) == 0)
    ).sum()
    return nulls / total


_ENRICHED_PATH = DATA_DIR / "products_enriched.csv"


def _load_cached() -> None:
    """Load pre-computed results from products_enriched.csv."""
    from src.dspy_pipe import get_token_log

    src = st.session_state.get("input_csv_path", CSV_PATH)
    pre_df = _normalize_columns(pd.read_csv(src, dtype=str), src)
    post_df = pd.read_csv(_ENRICHED_PATH)
    # Restore list columns serialised as strings
    for col in ("allergens_extracted", "dietary_flags", "transformations_applied"):
        if col in post_df.columns:
            import ast
            post_df[col] = post_df[col].apply(
                lambda v: ast.literal_eval(v) if isinstance(v, str) and v.startswith("[") else (v if isinstance(v, list) else [])
            )
    st.session_state["pre_df"] = pre_df
    st.session_state["post_df"] = post_df
    st.session_state["token_log"] = get_token_log()


def _run_pipeline_cached():
    """Run pipeline and cache results in session_state."""
    from src.pipeline import run_pipeline
    from src.dspy_pipe import get_token_log

    src = st.session_state.get("input_csv_path", CSV_PATH)
    df = _normalize_columns(pd.read_csv(src, dtype=str), src)
    progress_bar = st.progress(0, text="Starting pipeline…")

    def _cb(n: int, total: int) -> None:
        progress_bar.progress(n / total, text=f"Processing row {n} / {total}…")

    pre_df, post_df = run_pipeline(df, progress_callback=_cb)
    progress_bar.empty()

    st.session_state["pre_df"] = pre_df
    st.session_state["post_df"] = post_df
    st.session_state["token_log"] = get_token_log()


st.title("📊 EDA Overview")

# --- Data source selector ---
_sample_csvs = sorted(f.name for f in SAMPLES_DIR.glob("*.csv")) if SAMPLES_DIR.exists() else []
_source_options = ["Default (1k products)"] + _sample_csvs
_prev_source = st.session_state.get("_selected_source_label", _source_options[0])
_selected_label = st.selectbox(
    "Input dataset",
    _source_options,
    index=_source_options.index(_prev_source) if _prev_source in _source_options else 0,
)
if _selected_label != _prev_source:
    for key in ("pre_df", "post_df", "token_log"):
        st.session_state.pop(key, None)
    st.session_state["_selected_source_label"] = _selected_label

if _selected_label == "Default (1k products)":
    st.session_state["input_csv_path"] = CSV_PATH
else:
    st.session_state["input_csv_path"] = SAMPLES_DIR / _selected_label
    if _selected_label != _OFF_SAMPLE_NAME:
        st.info(f"**{_selected_label}** has a different schema and may not produce meaningful DQ scores. Only `{_OFF_SAMPLE_NAME}` is fully compatible with this pipeline.")

# --- Cache shortcut ---
_active_src = st.session_state.get("input_csv_path", CSV_PATH)
_cache_available = (
    _ENRICHED_PATH.exists()
    and _ENRICHED_PATH.stat().st_mtime > Path(_active_src).stat().st_mtime
)
if _cache_available and "pre_df" not in st.session_state:
    st.info("A cached result from a previous run is available.")
    if st.button("📂 Load Cached Results (skip API calls)"):
        _load_cached()
        st.rerun()

# --- Run button ---
if st.button("▶ Run Pipeline", type="primary", disabled="pre_df" in st.session_state):
    _run_pipeline_cached()
    st.rerun()

if "pre_df" not in st.session_state:
    st.info("Click **Run Pipeline** to start the data quality pipeline.")
    st.stop()

pre_df: pd.DataFrame = st.session_state["pre_df"]
post_df: pd.DataFrame = st.session_state["post_df"]

# --- Metric row ---
avg_pre = pre_df["dq_score_pre"].mean() if "dq_score_pre" in pre_df.columns else 0.0
avg_post = post_df["dq_score_post"].mean() if "dq_score_post" in post_df.columns else 0.0

llm_rows = post_df["enriched_by_llm"].sum() if "enriched_by_llm" in post_df.columns else 0
pct_llm = llm_rows / len(post_df) * 100 if len(post_df) else 0.0

dup_count = post_df["duplicate_group_id"].notna().sum() if "duplicate_group_id" in post_df.columns else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Avg DQ Score (Before)", f"{avg_pre:.1f}")
col2.metric("Avg DQ Score (After)", f"{avg_post:.1f}", delta=f"+{avg_post - avg_pre:.1f}")
col3.metric("Rows Enriched by LLM", f"{llm_rows} ({pct_llm:.1f}%)")
col4.metric("Duplicate Records", str(dup_count))

st.markdown("---")

# --- Chart 1: Null rates before vs after ---
null_before = [_null_rate(pre_df, f) * 100 for f in _KEY_FIELDS_RAW]
null_after = [_null_rate(post_df, f) * 100 for f in _KEY_FIELDS_ENRICHED]

fig1 = go.Figure(data=[
    go.Bar(name="Before", x=_FIELD_LABELS, y=null_before, marker_color="#E74C3C"),
    go.Bar(name="After", x=_FIELD_LABELS, y=null_after, marker_color="#2ECC71"),
])
fig1.update_layout(
    barmode="group",
    title="Null Rates by Field — Before vs After",
    yaxis_title="Null %",
    xaxis_title="Field",
    height=400,
)
st.plotly_chart(fig1, width="stretch")

# --- Chart 2: DQ score distribution ---
fig2 = go.Figure()
if "dq_score_pre" in pre_df.columns:
    fig2.add_trace(go.Histogram(
        x=pre_df["dq_score_pre"],
        name="Before",
        opacity=0.65,
        marker_color="#E74C3C",
        nbinsx=20,
    ))
if "dq_score_post" in post_df.columns:
    fig2.add_trace(go.Histogram(
        x=post_df["dq_score_post"],
        name="After",
        opacity=0.65,
        marker_color="#2ECC71",
        nbinsx=20,
    ))
fig2.update_layout(
    barmode="overlay",
    title="DQ Score Distribution — Before vs After",
    xaxis_title="DQ Score (0–100)",
    yaxis_title="Count",
    height=400,
)
st.plotly_chart(fig2, width="stretch")

# --- Charts 3 in two columns ---
left, right = st.columns(2)

# Chart 3: Duplicate pie
with left:
    if "duplicate_group_id" in post_df.columns:
        dup_rows = int(post_df["duplicate_group_id"].notna().sum())
        unique_rows = len(post_df) - dup_rows
        fig3 = go.Figure(data=[go.Pie(
            labels=["Unique", "Duplicate"],
            values=[unique_rows, dup_rows],
            marker_colors=["#2ECC71", "#E74C3C"],
            hole=0.35,
        )])
        fig3.update_layout(title="Duplicate vs Unique Records", height=350)
        st.plotly_chart(fig3, width="stretch")

# Chart 4: LLM vs rules-only enrichment
with right:
    if "enriched_by_llm" in post_df.columns:
        llm_enriched = int(post_df["enriched_by_llm"].sum())
        rules_only = len(post_df) - llm_enriched
        fig4 = go.Figure(data=[go.Pie(
            labels=["Rules Only", "LLM Enriched"],
            values=[rules_only, llm_enriched],
            marker_colors=["#3498DB", "#F39C12"],
            hole=0.35,
        )])
        fig4.update_layout(title="Enrichment Method", height=350)
        st.plotly_chart(fig4, width="stretch")
