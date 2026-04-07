import sys
from pathlib import Path

# Ensure project root is on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rules import (
    clean_row,
    flag_nulls,
    normalize_brands,
    normalize_product_name,
    normalize_quantity,
)


def test_normalize_quantity_no_space():
    val, label = normalize_quantity("500g")
    assert val == "500 g"
    assert label is not None


def test_normalize_quantity_caps():
    val, label = normalize_quantity("500 ML")
    assert val == "500 ml"
    assert label is not None


def test_normalize_quantity_none():
    val, label = normalize_quantity(None)
    assert val is None
    assert label is None


def test_normalize_brands_whitespace():
    val, label = normalize_brands("  General Mills  ")
    assert val == "General Mills"
    assert label is not None


def test_normalize_brands_caps():
    val, label = normalize_brands("GENERAL MILLS")
    assert val == "General Mills"
    assert label is not None


def test_normalize_product_name_lower():
    val, label = normalize_product_name("honey nut cheerios")
    assert val == "Honey Nut Cheerios"
    assert label is not None


def test_flag_nulls_counts():
    row = {"a": None, "b": "", "c": "value", "d": None}
    result = flag_nulls(row, ["a", "b", "c", "d"])
    assert len(result) == 3
    assert "a" in result
    assert "b" in result
    assert "d" in result


def test_clean_row_returns_tuple():
    row = {"product_name": "test", "brands": "acme", "quantity": "100g"}
    result = clean_row(row)
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert isinstance(result[0], dict)
    assert isinstance(result[1], list)


def test_clean_row_no_change():
    row = {
        "product_name": "Honey Nut Cheerios",
        "brands": "General Mills",
        "quantity": "100 g",
    }
    _, transforms = clean_row(row)
    assert transforms == []
