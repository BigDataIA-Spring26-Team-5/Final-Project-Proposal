from __future__ import annotations

import math
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Optional

import pandas as pd
import structlog

from src.rules import clean_row
from src.dspy_pipe import enrich_row, reset_token_log, get_token_log, save_token_log
from src.dedup import find_duplicates
from src.dq_score import compute_dq_score

log = structlog.get_logger(__name__)

_DATA_DIR = Path(__file__).parent.parent / "data"
_MAX_WORKERS = min(16, (os.cpu_count() or 4) * 2)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _str_safe(val) -> str:
    """Return str(val), or '' for None/NaN."""
    if val is None:
        return ""
    if isinstance(val, float) and math.isnan(val):
        return ""
    return str(val)


def _raw_row_to_score_dict(row: dict) -> dict:
    """Map raw column names to the field names expected by compute_dq_score."""
    return {
        "product_name": row.get("product_name"),
        "brands": row.get("brands"),
        "quantity_normalized": row.get("quantity"),   # raw field name
        "categories_clean": row.get("categories_en"),
        "allergens_extracted": row.get("allergens_en"),
        "ingredients_text_en": row.get("ingredients_text_en"),
        "nutriscore_grade": row.get("nutriscore_grade"),
    }


def _make_rule_only_enriched(cleaned: dict) -> dict:
    """Apply field-mapping defaults without calling the LLM."""
    enriched = dict(cleaned)
    enriched.setdefault("quantity_normalized", enriched.pop("quantity", None))
    enriched.setdefault("categories_clean", enriched.get("categories_en"))
    allergens_raw = _str_safe(enriched.get("allergens_en"))
    enriched.setdefault(
        "allergens_extracted",
        [a.strip() for a in allergens_raw.split(",") if a.strip()],
    )
    labels_raw = _str_safe(enriched.get("labels_en"))
    enriched.setdefault(
        "dietary_flags",
        [f.strip() for f in labels_raw.split(",") if f.strip()],
    )
    return enriched


def _process_one(args: tuple) -> dict:
    """Worker: clean + enrich one row. Returns enriched dict."""
    i, raw, dq_pre = args
    worker_log = structlog.get_logger(__name__)

    cleaned, rule_transforms = clean_row(raw)

    try:
        enriched, llm_transforms, llm_called = enrich_row(cleaned)
    except RuntimeError as e:
        if "Cost cap" in str(e):
            worker_log.warning("cost_cap_hit", row_index=i)
            enriched = _make_rule_only_enriched(cleaned)
            llm_transforms, llm_called = [], False
        else:
            raise

    all_transforms = rule_transforms + llm_transforms
    enriched["dq_score_pre"] = dq_pre
    enriched["transformations_applied"] = all_transforms
    enriched["enriched_by_llm"] = llm_called
    if not enriched.get("code"):
        enriched["code"] = raw.get("code", "")

    worker_log.debug(
        "row_processed",
        row_index=i,
        llm_called=llm_called,
        transforms_count=len(all_transforms),
    )
    return enriched


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_pipeline(
    df: pd.DataFrame,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run the full DQ pipeline.

    Steps:
      1. compute_dq_score on raw rows → dq_score_pre
      2. clean_row + enrich_row per row (parallel via ThreadPoolExecutor)
      3. find_duplicates on enriched df
      4. compute_dq_score on enriched rows → dq_score_post
      5. Save to data/products_enriched.csv

    Returns (pre_df, post_df).
    """
    reset_token_log()
    t0 = time.perf_counter()
    total = len(df)
    log.info("pipeline_start", total_rows=total, workers=_MAX_WORKERS)

    # --- Pre-pipeline scoring ---
    pre_df = df.copy()
    pre_scores = [
        compute_dq_score(_raw_row_to_score_dict(row.to_dict()))
        for _, row in pre_df.iterrows()
    ]
    pre_df["dq_score_pre"] = pre_scores

    # --- Parallel per-row enrichment ---
    jobs = [(i, df.iloc[i].to_dict(), pre_scores[i]) for i in range(total)]
    enriched_rows: list[dict] = []

    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
        for n, result in enumerate(pool.map(_process_one, jobs), start=1):
            enriched_rows.append(result)
            if progress_callback:
                progress_callback(n, total)

    # --- Build post_df ---
    post_df = pd.DataFrame(enriched_rows)

    # --- Deduplication ---
    log.info("dedup_start", rows=len(post_df))
    post_df = find_duplicates(post_df)
    dup_groups = int(post_df["duplicate_group_id"].notna().nunique())
    log.info("dedup_done", duplicate_groups=dup_groups)

    # --- Post-pipeline scoring ---
    post_scores = [
        compute_dq_score(row.to_dict())
        for _, row in post_df.iterrows()
    ]
    post_df["dq_score_post"] = post_scores

    # --- Save ---
    out_path = _DATA_DIR / "products_enriched.csv"
    post_df.to_csv(out_path, index=False)

    elapsed = time.perf_counter() - t0
    llm_rows = int(post_df["enriched_by_llm"].sum()) if "enriched_by_llm" in post_df.columns else 0
    tl = get_token_log()
    log.info(
        "pipeline_done",
        elapsed_s=round(elapsed, 1),
        llm_rows=llm_rows,
        dup_groups=dup_groups,
        token_calls=tl["calls"],
        input_tokens=tl["input_tokens"],
        cache_tokens=tl["cache_tokens"],
        output_tokens=tl["output_tokens"],
        total_cost_usd=tl["total_cost_usd"],
        output=str(out_path),
    )
    save_token_log()

    return pre_df, post_df
