from __future__ import annotations

import math

import pandas as pd
from rapidfuzz import fuzz, process


def _safe_str(val) -> str:
    """Return val as a string, or '' for None/NaN."""
    if val is None:
        return ""
    if isinstance(val, float) and math.isnan(val):
        return ""
    return str(val)


def _composite_key(row: pd.Series) -> str:
    name = _safe_str(row.get("product_name")).strip().lower()
    brand = _safe_str(row.get("brands")).strip().lower()
    return f"{name}|{brand}"


def _union_find_groups(pairs: list[tuple[int, int]]) -> dict[int, int]:
    """Union-find: return mapping from node → root."""
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


def find_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Detect near-duplicate rows using rapidfuzz token_sort_ratio on composite key.

    Adds three columns to df (in-place copy):
      - duplicate_group_id: int | None
      - canonical: bool | None
      - duplicate_score: float | None

    Returns the augmented DataFrame.
    """
    result = df.copy()
    keys = result.apply(_composite_key, axis=1).tolist()
    n = len(keys)

    # Compute pairwise similarity matrix (NxN)
    matrix = process.cdist(keys, keys, scorer=fuzz.ratio)

    # Collect pairs above threshold (upper triangle only, skip self-pairs)
    pairs: list[tuple[int, int]] = []
    pair_scores: dict[tuple[int, int], float] = {}
    for i in range(n):
        for j in range(i + 1, n):
            score = float(matrix[i][j])
            if score >= 95.0:
                pairs.append((i, j))
                pair_scores[(i, j)] = score

    # Guard: require different barcode to count as semantic duplicate
    codes = result["code"].tolist() if "code" in result.columns else [None] * n
    pairs = [
        (i, j) for (i, j) in pairs
        if _safe_str(codes[i]) != _safe_str(codes[j]) or not _safe_str(codes[i])
    ]
    pair_scores = {k: v for k, v in pair_scores.items() if k in set(pairs)}

    # Build groups via union-find
    membership = _union_find_groups(pairs)

    # Assign group IDs — only nodes that appear in at least one pair
    in_pairs: set[int] = set()
    for a, b in pairs:
        in_pairs.add(a)
        in_pairs.add(b)

    # Map root → sequential group id
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

    # canonical: row with most non-null fields per group (ties → first occurrence)
    canonical_flags: list[bool | None] = [None] * n
    group_members: dict[int, list[int]] = {}
    for idx, gid in enumerate(duplicate_group_id):
        if gid is not None:
            group_members.setdefault(gid, []).append(idx)

    for gid, members in group_members.items():
        non_null_counts = [
            result.iloc[i].notna().sum() for i in members
        ]
        best = members[non_null_counts.index(max(non_null_counts))]
        for idx in members:
            canonical_flags[idx] = idx == best

    # duplicate_score: max similarity to any other member of the same group
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
