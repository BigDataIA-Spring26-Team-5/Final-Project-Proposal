"""Rule-based cleaning functions for food product data.

Each normalizer returns (cleaned_value, transform_label).
transform_label is None if no change was made.
"""
from __future__ import annotations

import math
import re
import string


_QTY_RE = re.compile(
    r"^(\d+(?:\.\d+)?)\s*(g|ml|l|kg|oz|fl\s*oz|gal|lb|count|pint)$",
    re.IGNORECASE,
)


def _is_null(val) -> bool:
    if val is None:
        return True
    if isinstance(val, float) and math.isnan(val):
        return True
    if isinstance(val, str) and not val.strip():
        return True
    return False


def normalize_quantity(val: str | None) -> tuple[str | None, str | None]:
    """Normalize quantity: '500g' -> '500 g', '500 ML' -> '500 ml'."""
    if _is_null(val):
        return None, None
    stripped = val.strip()
    m = _QTY_RE.match(stripped)
    if m is None:
        return val, None
    number = m.group(1)
    unit = m.group(2).replace(" ", "").lower()
    if unit == "floz":
        unit = "fl oz"
    normalized = f"{number} {unit}"
    if normalized == stripped:
        return val, None
    return normalized, f"quantity: '{stripped}' -> '{normalized}'"


def normalize_brands(val: str | None) -> tuple[str | None, str | None]:
    """Strip whitespace, title-case, remove trailing punctuation."""
    if _is_null(val):
        return None, None
    stripped = val.strip()
    cleaned = stripped.rstrip(string.punctuation)
    titled = cleaned.title()
    if titled == val:
        return val, None
    return titled, f"brands: '{val}' -> '{titled}'"


def normalize_product_name(val: str | None) -> tuple[str | None, str | None]:
    """Title-case if fully lowercase; strip whitespace."""
    if _is_null(val):
        return None, None
    stripped = val.strip()
    if stripped == stripped.lower():
        titled = stripped.title()
        if titled != val:
            return titled, f"product_name: '{val}' -> '{titled}'"
    elif stripped != val:
        return stripped, "product_name: stripped whitespace"
    return val, None


def normalize_categories(val: str | None) -> tuple[str | None, str | None]:
    """Clean category strings: strip, take first if comma-separated, title-case."""
    if _is_null(val):
        return None, None
    stripped = val.strip()
    # Take the most specific category (last in comma-separated list)
    if "," in stripped:
        parts = [p.strip() for p in stripped.split(",") if p.strip()]
        if parts:
            primary = parts[-1].strip()
            titled = primary.title()
            return titled, f"categories: extracted primary '{titled}' from '{stripped[:60]}'"
    titled = stripped.title()
    if titled != val:
        return titled, f"categories: '{val}' -> '{titled}'"
    return val, None


def flag_nulls(row: dict, fields: list[str]) -> list[str]:
    """Return list of field names that are null or empty."""
    return [f for f in fields if _is_null(row.get(f))]


def clean_row(row: dict) -> tuple[dict, list[str]]:
    """Apply all normalize_* functions to a raw row dict.

    Returns (cleaned_dict, transformations_applied).
    """
    cleaned = dict(row)
    transformations: list[str] = []

    name_val, name_label = normalize_product_name(cleaned.get("product_name"))
    if name_label:
        cleaned["product_name"] = name_val
        transformations.append(name_label)

    brand_val, brand_label = normalize_brands(cleaned.get("brands"))
    if brand_label:
        cleaned["brands"] = brand_val
        transformations.append(brand_label)

    qty_val, qty_label = normalize_quantity(cleaned.get("quantity"))
    if qty_label:
        cleaned["quantity"] = qty_val
        transformations.append(qty_label)

    cat_val, cat_label = normalize_categories(cleaned.get("categories"))
    if cat_label:
        cleaned["categories"] = cat_val
        transformations.append(cat_label)

    return cleaned, transformations
