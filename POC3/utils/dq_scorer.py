"""Data Quality scoring — 0-100 across 4 dimensions."""
import re

import pandas as pd
import numpy as np
from datetime import datetime


# ---------------------------------------------------------------------------
# Per-row DQ score (POC2-style) — used for pre/post enrichment comparison
# ---------------------------------------------------------------------------

_QTY_CANONICAL = re.compile(r"^\d+(\.\d+)?\s(g|ml|l|kg|oz|fl oz|gal|lb)$")
_VALID_NUTRISCORE = {"a", "b", "c", "d", "e"}

_ENRICHMENT_FIELDS = [
    ("product_name", "clean_name"),
    ("brands", "clean_brand"),
    ("quantity", "quantity"),
    ("categories", "primary_category"),
    ("allergens", "allergens_extracted"),
    ("ingredients_text", "ingredients_text"),
]


def _is_present(val) -> bool:
    if val is None:
        return False
    if isinstance(val, float) and np.isnan(val):
        return False
    if isinstance(val, list):
        return len(val) > 0
    return bool(str(val).strip()) and str(val).strip() not in ("nan", "None")


def compute_row_dq_score(row: dict) -> float:
    """Compute a per-row DQ score (0-100) for enrichment comparison.

    Completeness (60%): % of 6 key fields non-null.
    Consistency (40%): 4 binary checks worth 10 pts each.
    """
    # --- Completeness (60 pts) ---
    filled = sum(
        1 for raw_f, enr_f in _ENRICHMENT_FIELDS
        if _is_present(row.get(enr_f)) or _is_present(row.get(raw_f))
    )
    completeness = (filled / len(_ENRICHMENT_FIELDS)) * 60.0

    # --- Consistency (40 pts) ---
    consistency = 0.0

    # 1. Quantity matches canonical pattern (10 pts)
    qty = row.get("quantity", "") or ""
    if isinstance(qty, str) and _QTY_CANONICAL.match(qty.strip()):
        consistency += 10.0

    # 2. Brand not all-caps and no leading/trailing whitespace (10 pts)
    brand = row.get("brands", row.get("clean_brand"))
    if isinstance(brand, str) and brand:
        if not brand.isupper() and brand == brand.strip():
            consistency += 10.0

    # 3. Category is clean single value (no pipes or long comma chains) (10 pts)
    cat = row.get("primary_category", row.get("categories"))
    if isinstance(cat, str) and cat.strip():
        if "|" not in cat and cat.count(",") <= 1:
            consistency += 10.0

    # 4. Nutrition grade valid if present (10 pts)
    ns = row.get("nutrition_grades", row.get("nutriscore_grade"))
    if ns is None or (isinstance(ns, str) and ns.strip() in ("", "nan", "None")):
        consistency += 10.0  # absent = not penalized
    elif isinstance(ns, str) and ns.strip().lower() in _VALID_NUTRISCORE:
        consistency += 10.0

    return round(completeness + consistency, 1)


def score_completeness(row, fields):
    """Score 0-25 based on % of non-null, non-empty fields."""
    filled = 0
    for f in fields:
        val = row.get(f, "")
        if pd.notna(val) and str(val).strip() not in ("", "nan", "None"):
            filled += 1
    return round((filled / len(fields)) * 25, 1)


def score_consistency(row):
    """Score 0-25 based on format consistency checks."""
    score = 25.0
    name = str(row.get("name", row.get("product_name", "")))
    brand = str(row.get("brand", row.get("brands", "")))

    # Penalize ALL CAPS or all lowercase names
    if name == name.upper() and len(name) > 3:
        score -= 5
    if name == name.lower() and len(name) > 3:
        score -= 3

    # Penalize if brand is empty
    if not brand or brand in ("nan", "None", ""):
        score -= 8

    # Penalize if name contains weird characters
    non_ascii = sum(1 for c in name if ord(c) > 127)
    if non_ascii > 2:
        score -= 5

    # Penalize if category is empty
    cat = str(row.get("category", row.get("categories", "")))
    if not cat or cat in ("nan", "None", ""):
        score -= 7

    return max(0, round(score, 1))


def score_accuracy(row):
    """Score 0-25 based on data accuracy signals."""
    score = 25.0
    ingredients = str(row.get("ingredients", row.get("ingredients_text", "")))
    nutrition = str(row.get("nutrition_grades", ""))

    # Penalize very short ingredients (likely OCR garbage)
    if len(ingredients) < 10 or ingredients in ("nan", "None", ""):
        score -= 10
    elif len(ingredients) < 30:
        score -= 5

    # Penalize invalid nutrition grade
    if nutrition and nutrition not in ("a", "b", "c", "d", "e", "nan", "None", ""):
        score -= 5

    # Penalize if product name is too short
    name = str(row.get("name", row.get("product_name", "")))
    if len(name) < 3:
        score -= 10

    return max(0, round(score, 1))


def score_freshness(row, reference_timestamp=None):
    """Score 0-25 based on data recency."""
    if reference_timestamp is None:
        reference_timestamp = datetime.now().timestamp()

    last_modified = row.get("last_modified_t", "")
    if pd.isna(last_modified) or str(last_modified) in ("", "nan", "None"):
        return 10.0  # Unknown freshness — middle score

    try:
        ts = float(last_modified)
        days_old = (reference_timestamp - ts) / 86400
        if days_old < 30:
            return 25.0
        elif days_old < 90:
            return 20.0
        elif days_old < 365:
            return 15.0
        elif days_old < 730:
            return 10.0
        else:
            return 5.0
    except (ValueError, TypeError):
        return 10.0


def compute_dq_scores(catalog_df):
    """Compute DQ scores for the merged catalog."""
    product_fields = ["name", "brand", "category", "ingredients", "dietary_tags", "allergens"]
    scores = []

    for _, row in catalog_df.iterrows():
        comp = score_completeness(row, product_fields)
        cons = score_consistency(row)
        acc = score_accuracy(row)
        fresh = score_freshness(row)
        total = round(comp + cons + acc + fresh, 1)

        scores.append({
            "product_id": row.get("product_id", ""),
            "name": row.get("name", ""),
            "brand": row.get("brand", ""),
            "source": row.get("source", ""),
            "completeness": comp,
            "consistency": cons,
            "accuracy": acc,
            "freshness": fresh,
            "dq_score": total,
        })

    return pd.DataFrame(scores)


def compute_price_dq_scores(prices_df):
    """Compute DQ scores for Open Prices entries."""
    price_fields = ["product_name", "product_brands", "price", "currency", "store_name", "store_city"]
    scores = []

    for _, row in prices_df.iterrows():
        comp = score_completeness(row, price_fields)
        # Simplified consistency/accuracy for prices
        cons = 20.0 if row.get("currency") and str(row["currency"]) not in ("nan", "", "None") else 10.0
        acc = 20.0 if row.get("price") and float(row.get("price", 0)) > 0 else 5.0
        fresh = 25.0  # Open Prices is always fresh
        total = round(comp + cons + acc + fresh, 1)

        scores.append({
            "price_id": row.get("price_id", ""),
            "product_name": row.get("product_name", ""),
            "source": "open_prices",
            "completeness": comp,
            "consistency": cons,
            "accuracy": acc,
            "freshness": fresh,
            "dq_score": total,
        })

    return pd.DataFrame(scores)
