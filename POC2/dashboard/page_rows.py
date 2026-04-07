from __future__ import annotations

import pandas as pd
import streamlit as st


def _badge(status: str) -> str:
    """Return a colored emoji badge for a field status."""
    if status == "filled":
        return "🔴 → 🟢"
    if status == "reformatted":
        return "🟡"
    return "⚪"


def _val_str(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "_null_"
    if isinstance(v, list):
        return ", ".join(str(x) for x in v) if v else "_empty list_"
    return str(v).strip() or "_empty_"


def _field_status(raw_val, rule_val, dspy_val) -> str:
    raw_present = bool(raw_val and str(raw_val).strip())
    dspy_present = bool(dspy_val and str(dspy_val).strip())
    rule_present = bool(rule_val and str(rule_val).strip())

    if not raw_present and dspy_present:
        return "filled"
    if not raw_present and rule_present:
        return "filled"
    if raw_present and rule_val != raw_val:
        return "reformatted"
    return "unchanged"


def _render_row_expander(label: str, description: str, raw: dict, post: dict):
    with st.expander(f"**{label}** — {description}"):
        # DQ delta
        dq_pre = post.get("dq_score_pre", 0.0)
        dq_post = post.get("dq_score_post", 0.0)
        c1, c2 = st.columns(2)
        c1.metric("DQ Score (Pre)", f"{dq_pre:.1f}")
        c2.metric("DQ Score (Post)", f"{dq_post:.1f}", delta=f"+{dq_post - dq_pre:.1f}")

        # Transformations
        transforms = post.get("transformations_applied", [])
        if transforms:
            st.markdown("**Transformations Applied:**")
            for t in transforms:
                st.markdown(f"- {t}")
        else:
            st.markdown("_No transformations applied._")

        st.markdown("---")

        # Side-by-side table
        display_fields = [
            ("product_name", "product_name", "product_name"),
            ("brands", "brands", "brands"),
            ("quantity", "quantity_normalized", "quantity_normalized"),
            ("categories_en", "categories_clean", "categories_clean"),
            ("allergens_en", "allergens_extracted", "allergens_extracted"),
            ("ingredients_text_en", "ingredients_text_en", "ingredients_text_en"),
            ("nutriscore_grade", "nutriscore_grade", "nutriscore_grade"),
        ]

        table_data = []
        for raw_key, post_key, _dspy_key in display_fields:
            raw_v = raw.get(raw_key)
            post_v = post.get(post_key)
            # After-rules value: same as post if only rules changed (we don't store intermediate)
            rule_v = post_v
            dspy_enriched = post.get("enriched_by_llm", False)
            dspy_v = post_v if dspy_enriched else rule_v

            status = _field_status(raw_v, rule_v, dspy_v)
            table_data.append({
                "Field": raw_key,
                "Raw Value": _val_str(raw_v),
                "After Rules": _val_str(rule_v),
                "After DSPy": _val_str(dspy_v),
                "Status": _badge(status),
            })

        st.dataframe(pd.DataFrame(table_data), width="stretch", hide_index=True)


st.title("🔍 Transformation Explorer")

if "post_df" not in st.session_state or "pre_df" not in st.session_state:
    st.info("Run the pipeline on the **EDA Overview** page first.")
    st.stop()

post_df: pd.DataFrame = st.session_state["post_df"]
pre_df: pd.DataFrame = st.session_state["pre_df"]


def _find_row(mask: pd.Series, fallback_idx: int = 0) -> tuple[dict, dict]:
    """Find a matching row, fall back to fallback_idx if none found."""
    idxs = post_df.index[mask].tolist()
    if not idxs:
        idxs = [post_df.index[fallback_idx]]
    post_row = post_df.loc[idxs[0]].to_dict()
    # Find matching raw row by code
    code = post_row.get("code")
    raw_matches = pre_df[pre_df["code"].astype(str) == str(code)]
    raw_row = raw_matches.iloc[0].to_dict() if not raw_matches.empty else {}
    return raw_row, post_row


def _is_null(v) -> bool:
    return v is None or (isinstance(v, float) and pd.isna(v)) or (isinstance(v, str) and not v.strip())


# Row A: null product_name, enriched by LLM
mask_a = (
    pre_df["product_name"].apply(_is_null)
    & post_df.get("enriched_by_llm", pd.Series([False] * len(post_df))).astype(bool)
)
raw_a, post_a = _find_row(mask_a, 0)

# Row B: null brands + malformed quantity (no space in raw)
mask_b = (
    pre_df["brands"].apply(_is_null)
    & pre_df["quantity"].apply(
        lambda v: bool(v) and " " not in str(v).strip() if v else False
    )
)
raw_b, post_b = _find_row(mask_b, 1)

# Row C: null categories_en, filled by LLM
mask_c = (
    pre_df["categories_en"].apply(_is_null)
    & post_df["categories_clean"].apply(lambda v: not _is_null(v))
    & post_df.get("enriched_by_llm", pd.Series([False] * len(post_df))).astype(bool)
)
raw_c, post_c = _find_row(mask_c, 2)

# Row D: non-null ingredients but null allergens — best DSPy candidate
mask_d = (
    pre_df["ingredients_text_en"].apply(lambda v: not _is_null(v))
    & pre_df["allergens_en"].apply(_is_null)
    & post_df.get("enriched_by_llm", pd.Series([False] * len(post_df))).astype(bool)
)
raw_d, post_d = _find_row(mask_d, 3)

# Row E: all fields present but quantity ALL CAPS — rules-only fix, DSPy not called
mask_e = (
    pre_df["quantity"].apply(
        lambda v: bool(v) and str(v).strip().isupper() if v else False
    )
    & ~post_df.get("enriched_by_llm", pd.Series([False] * len(post_df))).astype(bool)
)
raw_e, post_e = _find_row(mask_e, 4)

st.markdown("Five representative rows showing different transformation stories.")

_render_row_expander(
    "Row A",
    "Null product_name — DSPy fills it",
    raw_a, post_a,
)
_render_row_expander(
    "Row B",
    "Null brands + malformed quantity — rules fix quantity, DSPy fills brand",
    raw_b, post_b,
)
_render_row_expander(
    "Row C",
    "Null categories_en — DSPy fills it",
    raw_c, post_c,
)
_render_row_expander(
    "Row D",
    "Non-null ingredients but null allergens — best DSPy candidate",
    raw_d, post_d,
)
_render_row_expander(
    "Row E",
    "All fields present but quantity ALL CAPS — rules-only fix, DSPy not called",
    raw_e, post_e,
)
