"""UC1: Catalog Enrichment + Entity Resolution tab."""
import streamlit as st
import pandas as pd
import plotly.express as px
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DATA_DIR


def render():
    st.header("UC1: Catalog Enrichment + Entity Resolution")
    st.caption("Ingest messy data from multiple sources → LLM enrichment → fuzzy matching → unified catalog")
    st.info("**Open Food Facts (OFF)** = crowdsourced food database (messy) | **USDA FoodData Central** = US government food database (clean) | **openFDA** = FDA food recall database")

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

    # Section 1: Raw Data Comparison
    st.subheader("1. Raw Data: The Mess vs The Clean")

    col1, col2, col3 = st.columns(3)
    with col1:
        off_comp = off["completeness"].astype(float).mean() if "completeness" in off.columns else 0
        st.metric("Open Food Facts Avg Completeness", f"{off_comp:.0%}")
    with col2:
        st.metric("USDA FoodData Field Coverage", "97-100%")
    with col3:
        st.metric("Total Data Sources", "6 datasets")

    tab_off, tab_usda = st.tabs(["Open Food Facts — Crowdsourced (Messy)", "USDA FoodData Central — Government (Clean)"])
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

    # Section 2: LLM Enrichment
    st.subheader("2. LLM Enrichment (DSPy + Groq Llama 3 70B)")

    success_count = (enriched["enrichment_status"] == "success").sum() if "enrichment_status" in enriched.columns else 0
    st.metric("Successfully Enriched", f"{success_count} / {len(enriched)} products")

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
            st.markdown("**AFTER (LLM Enriched)**")
            st.json({
                "clean_name": row.get("clean_name", ""),
                "clean_brand": row.get("clean_brand", ""),
                "primary_category": row.get("primary_category", ""),
                "dietary_tags": row.get("dietary_tags", ""),
                "allergens": row.get("allergens_extracted", ""),
                "is_organic": row.get("is_organic", ""),
            })

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

    # Section 3: Entity Resolution
    st.subheader("3. Entity Resolution (Open Food Facts ↔ USDA FoodData)")

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

    # Section 4: Merged Catalog
    st.subheader("4. Merged Catalog")
    st.metric("Total Products", len(catalog))

    source_labels = {"off": "Open Food Facts", "usda": "USDA FoodData"}
    source_filter = st.multiselect("Filter by source:", ["off", "usda"], default=["off", "usda"], format_func=lambda x: source_labels.get(x, x))
    filtered = catalog[catalog["source"].isin(source_filter)]
    st.dataframe(
        filtered[["product_id", "name", "brand", "category", "source", "enriched", "match_score"]].head(30),
        use_container_width=True,
    )
