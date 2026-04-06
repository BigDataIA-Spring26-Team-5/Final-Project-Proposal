from __future__ import annotations

import math
import re
import string


# Regex: optional space between number and unit, unit case-insensitive
_QTY_RE = re.compile(
    r"^(\d+(?:\.\d+)?)\s*(g|ml|l|kg|oz|fl\s*oz)$",
    re.IGNORECASE,
)


def _is_null(val) -> bool:
    """True for None, NaN floats, or empty/whitespace-only strings."""
    if val is None:
        return True
    if isinstance(val, float) and math.isnan(val):
        return True
    if isinstance(val, str) and not val.strip():
        return True
    return False


def normalize_quantity(val: str | None) -> tuple[str | None, str | None]:
    """Normalize quantity strings like '500g' → '500 g', '500 ML' → '500 ml'.

    Returns (normalized_value, label) where label is None if no change needed.
    """
    if _is_null(val):
        return None, None

    stripped = val.strip()
    m = _QTY_RE.match(stripped)
    if m is None:
        return val, None

    number = m.group(1)
    unit = m.group(2).replace(" ", "").lower()  # normalize "fl oz" spacing too
    # Rebuild with canonical spacing
    if m.group(2).lower().replace(" ", "") == "floz":
        unit = "fl oz"
    normalized = f"{number} {unit}"

    if normalized == stripped:
        return val, None
    label = f"quantity: '{stripped}' → '{normalized}'"
    return normalized, label


def normalize_brands(val: str | None) -> tuple[str | None, str | None]:
    """Strip whitespace, title-case, remove trailing punctuation.

    Returns (normalized_value, label) where label is None if no change needed.
    """
    if _is_null(val):
        return None, None

    stripped = val.strip()
    # Remove trailing punctuation
    cleaned = stripped.rstrip(string.punctuation)
    # Title-case
    titled = cleaned.title()

    if titled == val:
        return val, None
    label = f"brands: '{val}' → '{titled}'"
    return titled, label


def normalize_product_name(val: str | None) -> tuple[str | None, str | None]:
    """Title-case if fully lowercase; strip whitespace.

    Returns (normalized_value, label) where label is None if no change needed.
    """
    if _is_null(val):
        return None, None

    stripped = val.strip()
    # Apply title case only if the entire string is lowercase (no caps at all)
    if stripped == stripped.lower():
        titled = stripped.title()
        if titled != val:
            label = f"product_name: '{val}' → '{titled}'"
            return titled, label
    elif stripped != val:
        # Only whitespace changed
        label = f"product_name: stripped whitespace"
        return stripped, label

    return val, None


def flag_nulls(row: dict, fields: list[str]) -> list[str]:
    """Return list of field names that are null or empty."""
    return [f for f in fields if _is_null(row.get(f))]


def clean_row(row: dict) -> tuple[dict, list[str]]:
    """Apply all normalize_* functions to a raw row dict.

    Returns (cleaned_dict, transformations_applied).
    transformations_applied is empty list if nothing changed.
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

    return cleaned, transformations
