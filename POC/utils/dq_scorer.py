"""Data Quality scoring — 0-100 across 4 dimensions."""
import pandas as pd
import numpy as np
from datetime import datetime


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
