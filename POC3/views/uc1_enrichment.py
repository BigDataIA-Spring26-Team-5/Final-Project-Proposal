"""UC1: Catalog Enrichment + Entity Resolution tab."""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DATA_DIR


def render():
    st.header("UC1: Catalog Enrichment + Entity Resolution")
    st.caption("Rule Cleaning -> DQ Pre-Score -> Fuzzy Dedup -> LLM Enrichment (canonical only) -> DQ Post-Score -> Entity Resolution")
    st.info("**Pipeline**: Raw OFF Data -> Rule-based Cleaning -> DQ Pre -> Dedup (all columns) -> Groq LLM (canonical rows only) -> DQ Post -> Entity Resolution -> Merged Catalog")

    # Load data
    try:
        off = pd.read_csv(DATA_DIR / "off_products.csv")
        usda = pd.read_csv(DATA_DIR / "usda_products.csv")
        enriched = pd.read_csv(DATA_DIR / "enriched_products.csv")
        matched = pd.read_csv(DATA_DIR / "matched_products.csv")
        recalls = pd.read_csv(DATA_DIR / "recall_links.csv") if (DATA_DIR / "recall_links.csv").exists() else pd.DataFrame()
        catalog = pd.read_csv(DATA_DIR / "merged_catalog.csv")
    except FileNotFoundError as e:
        st.error(f"Data not found: {e}. Run the data prep scripts first.")
        return

    # ================================================================
    # Section 1: Raw Data Comparison
    # ================================================================
    st.subheader("1. Raw Data: The Mess vs The Clean")

    col1, col2, col3 = st.columns(3)
    with col1:
        off_comp = off["completeness"].astype(float).mean() if "completeness" in off.columns else 0
        st.metric("Open Food Facts Avg Completeness", f"{off_comp:.0%}")
    with col2:
        st.metric("USDA FoodData Field Coverage", "97-100%")
    with col3:
        st.metric("Total Data Sources", "6 datasets")

    tab_off, tab_usda = st.tabs(["Open Food Facts -- Crowdsourced (Messy)", "USDA FoodData Central -- Government (Clean)"])
    with tab_off:
        st.dataframe(
            off[["product_name", "brands", "categories", "completeness", "ingredients_text"]].head(20),
            use_container_width=True,
        )
    with tab_usda:
        st.dataframe(
            usda[["description", "brand_owner", "food_category", "ingredients"]].head(20),
            use_container_width=True,
        )

    st.divider()

    # ================================================================
    # Section 2: Rule-Based Cleaning
    # ================================================================
    st.subheader("2. Rule-Based Cleaning")
    st.caption("Normalize product names, brands, quantities, and categories using regex and string operations")

    if "rule_transforms" in enriched.columns:
        rules_applied = enriched[enriched["rule_transforms"].fillna("").str.len() > 0]
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Products with Rule Transforms", len(rules_applied))
        with col2:
            st.metric("Products Unchanged", len(enriched) - len(rules_applied))
        with col3:
            pct = len(rules_applied) / len(enriched) * 100 if len(enriched) > 0 else 0
            st.metric("Transform Rate", f"{pct:.0f}%")

        if len(rules_applied) > 0:
            with st.expander("View Rule Transforms Applied", expanded=False):
                display = rules_applied[["original_name", "clean_name", "original_brand", "clean_brand", "rule_transforms"]].head(20)
                st.dataframe(display, use_container_width=True)
    else:
        st.info("No rule transform data available. Re-run scripts/02_enrich_products.py.")

    st.divider()

    # ================================================================
    # Section 3: DQ Score Pre-Enrichment
    # ================================================================
    st.subheader("3. Data Quality: Pre-Enrichment Baseline")
    st.caption("Per-row DQ score (0-100) after rule cleaning, before LLM enrichment. Completeness (60%) + Consistency (40%)")

    has_dq_pre = "dq_score_pre" in enriched.columns
    if has_dq_pre:
        avg_pre = enriched["dq_score_pre"].mean()
        min_pre = enriched["dq_score_pre"].min()
        max_pre = enriched["dq_score_pre"].max()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Avg DQ (Pre)", f"{avg_pre:.1f}/100")
        with col2:
            st.metric("Min DQ (Pre)", f"{min_pre:.1f}")
        with col3:
            st.metric("Max DQ (Pre)", f"{max_pre:.1f}")

        fig = px.histogram(enriched, x="dq_score_pre", nbins=20,
                           title="DQ Score Distribution (Pre-Enrichment)",
                           color_discrete_sequence=["salmon"])
        fig.update_layout(xaxis_title="DQ Score", yaxis_title="Count")
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ================================================================
    # Section 4: Fuzzy Deduplication
    # ================================================================
    st.subheader("4. Fuzzy Deduplication (Before LLM)")
    st.caption("Near-duplicate detection on rule-cleaned data using rapidfuzz on all columns. Duplicates are skipped during LLM enrichment to save cost.")

    has_dedup = "duplicate_group_id" in enriched.columns
    if has_dedup:
        dup_df = enriched[enriched["duplicate_group_id"].notna()].copy()
        dup_groups = int(dup_df["duplicate_group_id"].nunique()) if len(dup_df) > 0 else 0
        canonical_count = int(dup_df["canonical"].sum()) if "canonical" in dup_df.columns and len(dup_df) > 0 else 0
        non_canonical = len(dup_df) - canonical_count
        unique_rows = enriched["duplicate_group_id"].isna().sum() + canonical_count

        # How many LLM calls were saved
        skipped_dup = (enriched["enrichment_status"] == "skipped_dup").sum() if "enrichment_status" in enriched.columns else non_canonical

        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Total Rows (Before)", len(enriched))
        with col2:
            st.metric("Unique Rows (After)", int(unique_rows))
        with col3:
            st.metric("Rows Deduplicated", int(non_canonical))
        with col4:
            st.metric("Duplicate Groups", dup_groups)
        with col5:
            st.metric("LLM Calls Saved", int(skipped_dup))

        # --- Before Dedup Table ---
        st.markdown("#### Before Dedup (All Rows)")
        before_cols = ["original_name", "original_brand", "categories", "quantity", "ingredients_text"]
        available_before = [c for c in before_cols if c in enriched.columns]
        st.dataframe(enriched[available_before], use_container_width=True)

        # --- After Dedup Table ---
        st.markdown("#### After Dedup (Canonical / Unique Rows Only)")
        is_canonical_or_unique = (
            enriched["duplicate_group_id"].isna() |
            (enriched["canonical"] == True)
        )
        after_dedup = enriched[is_canonical_or_unique]
        st.dataframe(after_dedup[available_before], use_container_width=True)

        # --- Removed Duplicates (Outliers) ---
        is_non_canonical_dup = (
            enriched["duplicate_group_id"].notna() &
            (enriched["canonical"] == False)
        )
        removed_dups = enriched[is_non_canonical_dup]
        if len(removed_dups) > 0:
            st.markdown(f"#### Deduplicated Rows Removed ({len(removed_dups)} rows)")
            st.caption("These non-canonical duplicate rows were removed. Each is shown alongside the canonical row it matched against.")
            removed_cols = ["original_name", "original_brand", "categories", "quantity", "duplicate_group_id", "duplicate_score"]
            available_removed = [c for c in removed_cols if c in removed_dups.columns]
            # For each removed row, show it alongside its canonical match
            display_rows = []
            for _, rem_row in removed_dups.iterrows():
                gid = rem_row["duplicate_group_id"]
                # Find the canonical row for this group
                canonical_match = enriched[
                    (enriched["duplicate_group_id"] == gid) &
                    (enriched["canonical"] == True)
                ]
                canonical_name = canonical_match.iloc[0]["original_name"] if len(canonical_match) > 0 else ""
                canonical_brand = canonical_match.iloc[0]["original_brand"] if len(canonical_match) > 0 else ""
                display_rows.append({
                    "removed_name": rem_row.get("original_name", ""),
                    "removed_brand": rem_row.get("original_brand", ""),
                    "removed_categories": rem_row.get("categories", ""),
                    "removed_quantity": rem_row.get("quantity", ""),
                    "matched_canonical_name": canonical_name,
                    "matched_canonical_brand": canonical_brand,
                    "duplicate_group_id": int(gid),
                    "similarity_score": rem_row.get("duplicate_score", ""),
                })
            st.dataframe(pd.DataFrame(display_rows), use_container_width=True)
        else:
            st.success("No rows were removed by deduplication.")

        # --- Duplicate Groups Detail ---
        if len(dup_df) > 0:
            st.markdown("#### Duplicate Groups Detail")
            st.caption("All rows flagged as near-duplicates. Canonical = True means this row is kept; False = removed.")
            dup_display_cols = ["original_name", "original_brand", "categories", "quantity", "duplicate_group_id", "canonical", "duplicate_score"]
            available_dup = [c for c in dup_display_cols if c in dup_df.columns]
            dup_display = dup_df[available_dup].sort_values("duplicate_group_id")
            st.dataframe(dup_display, use_container_width=True)

            if "duplicate_score" in dup_df.columns:
                fig = px.histogram(dup_df, x="duplicate_score", nbins=15,
                                   title="Duplicate Similarity Score Distribution",
                                   color_discrete_sequence=["coral"])
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.success("No duplicates detected in the rule-cleaned dataset.")
    else:
        st.info("Dedup data not available. Re-run scripts/02_enrich_products.py.")

    st.divider()

    # ================================================================
    # Section 5: LLM Enrichment (Canonical Rows Only)
    # ================================================================
    st.subheader("5. LLM Enrichment (Groq Llama 3 70B)")
    st.caption("Only canonical/unique rows are sent to the LLM. Non-canonical duplicates are skipped.")

    if "enrichment_status" in enriched.columns:
        success_count = (enriched["enrichment_status"] == "success").sum()
        skipped_dup_count = (enriched["enrichment_status"] == "skipped_dup").sum()
        skipped_complete_count = (enriched["enrichment_status"] == "skipped_complete").sum()
        failed_count = (enriched["enrichment_status"] == "failed").sum()

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("LLM Enriched", int(success_count))
        with col2:
            st.metric("Skipped (Duplicate)", int(skipped_dup_count))
        with col3:
            st.metric("Skipped (Complete)", int(skipped_complete_count))
        with col4:
            st.metric("Failed", int(failed_count))

    product_options = enriched["original_name"].dropna().tolist()
    if product_options:
        selected = st.selectbox("Pick a product to see before/after:", product_options)
        row = enriched[enriched["original_name"] == selected].iloc[0]

        col_before, col_after = st.columns(2)
        with col_before:
            st.markdown("**BEFORE (Raw OFF Data)**")
            st.json({
                "name": row.get("original_name", ""),
                "brand": row.get("original_brand", ""),
                "categories": row.get("original_categories", ""),
                "ingredients": str(row.get("original_ingredients", ""))[:200],
            })
        with col_after:
            st.markdown("**AFTER (Rules + LLM Enriched)**")
            after_data = {
                "clean_name": row.get("clean_name", ""),
                "clean_brand": row.get("clean_brand", ""),
                "primary_category": row.get("primary_category", ""),
                "dietary_tags": row.get("dietary_tags", ""),
                "allergens": row.get("allergens_extracted", ""),
                "is_organic": row.get("is_organic", ""),
                "enrichment_status": row.get("enrichment_status", ""),
            }
            st.json(after_data)

        # Show transforms for selected product
        transforms = row.get("all_transforms", "")
        if transforms and str(transforms).strip() and str(transforms) != "nan":
            st.markdown("**Transforms Applied:**")
            for t in str(transforms).split("; "):
                if t.strip():
                    st.markdown(f"- `{t.strip()}`")

    # Live enrichment button
    with st.expander("Try Live Enrichment (calls Groq API)"):
        live_name = st.text_input("Product name:", "Cheerios Honey Nut")
        live_brand = st.text_input("Brand:", "General Mills")
        if st.button("Enrich with LLM"):
            from utils.llm import call_llm_json
            prompt = f"""Extract structured attributes from this product:
Name: {live_name}, Brand: {live_brand}
Return JSON: {{"clean_name": "", "clean_brand": "", "primary_category": "", "dietary_tags": "", "allergens": "", "is_organic": ""}}"""
            with st.spinner("Calling Groq..."):
                result = call_llm_json(prompt)
            if result:
                st.json(result)
            else:
                st.error("LLM call failed. Check API key.")

    st.divider()

    # ================================================================
    # Section 6: DQ Score Post-Enrichment + Comparison
    # ================================================================
    st.subheader("6. Data Quality: Post-Enrichment + Comparison")
    st.caption("DQ score after LLM enrichment compared to pre-enrichment baseline")

    has_dq = "dq_score_pre" in enriched.columns and "dq_score_post" in enriched.columns
    if has_dq:
        avg_pre = enriched["dq_score_pre"].mean()
        avg_post = enriched["dq_score_post"].mean()
        improvement = avg_post - avg_pre

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Avg DQ (Pre)", f"{avg_pre:.1f}/100")
        with col2:
            st.metric("Avg DQ (Post)", f"{avg_post:.1f}/100")
        with col3:
            st.metric("Improvement", f"+{improvement:.1f} pts", delta=f"+{improvement:.1f}")

        # Histogram overlay
        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=enriched["dq_score_pre"], name="Pre-Enrichment",
            marker_color="salmon", opacity=0.7, nbinsx=20,
        ))
        fig.add_trace(go.Histogram(
            x=enriched["dq_score_post"], name="Post-Enrichment",
            marker_color="mediumseagreen", opacity=0.7, nbinsx=20,
        ))
        fig.update_layout(
            title="DQ Score Distribution: Pre vs Post Enrichment",
            xaxis_title="DQ Score", yaxis_title="Count",
            barmode="overlay",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Scatter: pre vs post per product
        fig2 = px.scatter(
            enriched, x="dq_score_pre", y="dq_score_post",
            hover_data=["clean_name", "clean_brand", "enrichment_status"],
            title="Per-Product DQ Score: Pre vs Post",
            labels={"dq_score_pre": "DQ Pre", "dq_score_post": "DQ Post"},
            color="enrichment_status",
            color_discrete_map={
                "success": "mediumseagreen",
                "skipped_dup": "gray",
                "skipped_complete": "steelblue",
                "failed": "salmon",
            },
        )
        fig2.add_shape(type="line", x0=0, y0=0, x1=100, y1=100,
                       line=dict(dash="dash", color="gray"))
        fig2.update_layout(xaxis=dict(range=[0, 105]), yaxis=dict(range=[0, 105]))
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("DQ pre/post scores not available. Re-run scripts/02_enrich_products.py.")

    st.divider()

    # ================================================================
    # Section 7: Entity Resolution
    # ================================================================
    st.subheader("7. Entity Resolution (Open Food Facts <-> USDA FoodData)")

    col1, col2, col3 = st.columns(3)
    high = (matched["match_quality"] == "high").sum() if "match_quality" in matched.columns else 0
    med = (matched["match_quality"] == "medium").sum() if "match_quality" in matched.columns else 0
    low = (matched["match_quality"] == "low").sum() if "match_quality" in matched.columns else 0
    with col1:
        st.metric("High Confidence (>70)", high)
    with col2:
        st.metric("Medium (50-70)", med)
    with col3:
        st.metric("Low (<50)", low)

    st.dataframe(
        matched[["off_name", "usda_name", "off_brand", "usda_brand", "match_score", "match_quality"]].sort_values("match_score", ascending=False),
        use_container_width=True,
    )

    if "match_score" in matched.columns:
        fig = px.histogram(matched, x="match_score", nbins=20, title="Match Score Distribution",
                           color="match_quality", color_discrete_map={"high": "green", "medium": "orange", "low": "red"})
        st.plotly_chart(fig, use_container_width=True)

    # FDA Recall links
    if len(recalls) > 0:
        st.subheader("FDA Recalls Linked to Catalog")
        st.dataframe(
            recalls[["recall_description", "recalling_firm", "matched_product_name", "match_score", "classification"]].head(20),
            use_container_width=True,
        )

    st.divider()

    # ================================================================
    # Section 8: Merged Catalog
    # ================================================================
    st.subheader("8. Merged Catalog")
    st.metric("Total Products", len(catalog))

    source_labels = {"off": "Open Food Facts", "usda": "USDA FoodData"}
    source_filter = st.multiselect("Filter by source:", ["off", "usda"], default=["off", "usda"], format_func=lambda x: source_labels.get(x, x))
    filtered = catalog[catalog["source"].isin(source_filter)]
    st.dataframe(
        filtered[["product_id", "name", "brand", "category", "source", "enriched", "match_score"]].head(30),
        use_container_width=True,
    )
