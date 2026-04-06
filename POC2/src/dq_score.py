from __future__ import annotations

import re

_QTY_CANONICAL = re.compile(r"^\d+(\.\d+)?\s(g|ml|l|kg|oz|fl oz)$")
_VALID_NUTRISCORE = {"a", "b", "c", "d", "e"}

_FIELD_PAIRS = [
    ("product_name",        "product_name"),
    ("brands",              "brands"),
    ("quantity",            "quantity_normalized"),
    ("categories_en",       "categories_clean"),
    ("allergens_en",        "allergens_extracted"),
    ("ingredients_text_en", "ingredients_text_en"),
]


def _is_present(val) -> bool:
    """True if value is non-null and non-empty."""
    if val is None:
        return False
    if isinstance(val, list):
        return len(val) > 0
    return bool(str(val).strip())


def compute_dq_score(row: dict) -> float:
    """Compute a data quality score (0–100) for an enriched row.

    Completeness (60%): % of 6 key fields non-null and non-empty.
    Consistency (40%): 4 binary checks worth 10 pts each.
    """
    # --- Completeness ---
    filled = sum(
        1 for raw_f, enr_f in _FIELD_PAIRS
        if _is_present(row.get(enr_f)) or _is_present(row.get(raw_f))
    )
    completeness = (filled / len(_FIELD_PAIRS)) * 60.0

    # --- Consistency ---
    consistency = 0.0

    # 1. quantity_normalized matches canonical pattern
    qty = row.get("quantity_normalized") or ""
    if isinstance(qty, str) and _QTY_CANONICAL.match(qty.strip()):
        consistency += 10.0

    # 2. brands not all-caps and no leading/trailing whitespace
    brands = row.get("brands")
    if isinstance(brands, str) and brands:
        if not brands.isupper() and brands == brands.strip():
            consistency += 10.0
    elif brands is None:
        # Field absent — skip penalty (completeness already handles it)
        pass

    # 3. categories_clean has no pipe or comma (single value)
    cats = row.get("categories_clean")
    if isinstance(cats, str) and cats.strip():
        if "|" not in cats and "," not in cats:
            consistency += 10.0
    elif cats is None:
        pass

    # 4. nutriscore_grade (if present) is one of a, b, c, d, e
    ns = row.get("nutriscore_grade")
    if ns is None:
        consistency += 10.0  # not present, not penalized
    elif isinstance(ns, str) and ns.strip().lower() in _VALID_NUTRISCORE:
        consistency += 10.0

    score = completeness + consistency
    return round(score, 1)
