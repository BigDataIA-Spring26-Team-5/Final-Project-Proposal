"""Fuzzy deduplication using rapidfuzz.

Detects near-duplicate product rows based on a composite key built from
all columns in the DataFrame. Uses union-find to group duplicates and
picks a canonical row per group.
"""
from __future__ import annotations

import math

import pandas as pd
from rapidfuzz import fuzz, process

# Columns added by dedup itself — exclude from composite key
_DEDUP_OUTPUT_COLS = {"duplicate_group_id", "canonical", "duplicate_score"}


def _safe_str(val) -> str:
    if val is None:
        return ""
    if isinstance(val, float) and math.isnan(val):
        return ""
    return str(val)


def _composite_key(row: pd.Series, columns: list[str]) -> str:
    """Build a composite key from all specified columns."""
    parts = []
    for col in columns:
        val = _safe_str(row.get(col)).strip().lower()
        if val and val not in ("nan", "none"):
            parts.append(val)
    return "|".join(parts)


def _union_find_groups(pairs: list[tuple[int, int]]) -> dict[int, int]:
    parent: dict[int, int] = {}

    def find(x: int) -> int:
        while parent.get(x, x) != x:
            parent[x] = parent.get(parent.get(x, x), x)
            x = parent.get(x, x)
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for a, b in pairs:
        if a not in parent:
            parent[a] = a
        if b not in parent:
            parent[b] = b
        union(a, b)

    return {n: find(n) for n in parent}


def find_duplicates(df: pd.DataFrame, threshold: float = 90.0) -> pd.DataFrame:
    """Detect near-duplicate rows using rapidfuzz token_sort_ratio.

    Adds columns: duplicate_group_id, canonical, duplicate_score.
    Returns the augmented DataFrame.
    """
    result = df.copy()
    # Use all columns except dedup output columns as the composite key
    key_columns = [c for c in result.columns if c not in _DEDUP_OUTPUT_COLS]
    keys = result.apply(lambda row: _composite_key(row, key_columns), axis=1).tolist()
    n = len(keys)

    if n == 0:
        result["duplicate_group_id"] = []
        result["canonical"] = []
        result["duplicate_score"] = []
        return result

    matrix = process.cdist(keys, keys, scorer=fuzz.ratio)

    pairs: list[tuple[int, int]] = []
    pair_scores: dict[tuple[int, int], float] = {}
    for i in range(n):
        for j in range(i + 1, n):
            score = float(matrix[i][j])
            if score >= threshold:
                pairs.append((i, j))
                pair_scores[(i, j)] = score

    # Require different barcode/code to count as semantic duplicate
    code_col = "code" if "code" in result.columns else None
    if code_col:
        codes = result[code_col].tolist()
        pairs = [
            (i, j) for (i, j) in pairs
            if _safe_str(codes[i]) != _safe_str(codes[j]) or not _safe_str(codes[i])
        ]
        pair_scores = {k: v for k, v in pair_scores.items() if k in set(pairs)}

    membership = _union_find_groups(pairs)

    in_pairs: set[int] = set()
    for a, b in pairs:
        in_pairs.add(a)
        in_pairs.add(b)

    roots_seen: dict[int, int] = {}
    group_counter = 0
    duplicate_group_id: list[int | None] = [None] * n

    for idx in range(n):
        if idx in in_pairs:
            root = membership[idx]
            if root not in roots_seen:
                roots_seen[root] = group_counter
                group_counter += 1
            duplicate_group_id[idx] = roots_seen[root]

    # Canonical: row with most non-null fields per group
    canonical_flags: list[bool | None] = [None] * n
    group_members: dict[int, list[int]] = {}
    for idx, gid in enumerate(duplicate_group_id):
        if gid is not None:
            group_members.setdefault(gid, []).append(idx)

    for gid, members in group_members.items():
        non_null_counts = [result.iloc[i].notna().sum() for i in members]
        best = members[non_null_counts.index(max(non_null_counts))]
        for idx in members:
            canonical_flags[idx] = idx == best

    # Duplicate score: max similarity to any other member
    dup_scores: list[float | None] = [None] * n
    for (i, j), score in pair_scores.items():
        if dup_scores[i] is None or score > dup_scores[i]:
            dup_scores[i] = score
        if dup_scores[j] is None or score > dup_scores[j]:
            dup_scores[j] = score

    result["duplicate_group_id"] = duplicate_group_id
    result["canonical"] = canonical_flags
    result["duplicate_score"] = dup_scores
    return result
