"""
UC1: Full enrichment pipeline for OFF products.

Steps:
  1. Load raw OFF products
  2. Rule-based cleaning (normalize names, brands, quantity, categories)
  3. Compute DQ score PRE-enrichment
  4. Fuzzy deduplication on rule-cleaned data (all columns)
  5. LLM enrichment via Groq Llama 3 70B (only canonical/unique rows)
  6. Compute DQ score POST-enrichment
  7. Save enriched_products.csv with all metadata

Run: python scripts/02_enrich_products.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from config import DATA_DIR
from utils.llm import call_llm_json
from utils.rules import clean_row, flag_nulls
from utils.dq_scorer import compute_row_dq_score
from utils.dedup import find_duplicates


EXTRACTION_PROMPT = """You are a food product data analyst. Given messy product data, extract clean structured attributes.

Product data:
- Name: {name}
- Brand: {brand}
- Categories: {categories}
- Ingredients: {ingredients}

Extract and return ONLY valid JSON with these fields:
{{
  "clean_name": "standardized product name",
  "clean_brand": "normalized brand name (e.g., General Mills, not GENERAL MILLS INC.)",
  "primary_category": "single best category (e.g., Breakfast Cereal, Snack, Beverage, Dairy, Condiment, Pasta, Bread, Candy, Frozen)",
  "dietary_tags": "comma-separated tags: gluten-free, vegan, vegetarian, organic, dairy-free, nut-free, kosher, halal, sugar-free, low-sodium (only if applicable, empty string if none)",
  "allergens": "comma-separated: milk, eggs, wheat, soy, peanuts, tree nuts, fish, shellfish (only if found in ingredients, empty string if none)",
  "is_organic": "true or false"
}}"""


def enrich_products():
    print("=" * 60)
    print("UC1: Full Enrichment Pipeline")
    print("  Rules -> DQ Pre -> Dedup -> LLM Enrich -> DQ Post")
    print("=" * 60)

    off = pd.read_csv(DATA_DIR / "off_products.csv")
    print(f"  Loaded {len(off)} OFF products\n")

    # ------------------------------------------------------------------
    # Step 1: Rule-based cleaning
    # ------------------------------------------------------------------
    print("--- Step 1: Rule-based cleaning ---")
    cleaned_rows = []
    all_rule_transforms = []
    for i, row in off.iterrows():
        raw = row.to_dict()
        cleaned, transforms = clean_row(raw)
        cleaned_rows.append(cleaned)
        all_rule_transforms.append(transforms)
        if transforms:
            print(f"  [{i+1}] {len(transforms)} rule transforms applied")

    rows_with_transforms = sum(1 for t in all_rule_transforms if t)
    print(f"  Rule cleaning done: {rows_with_transforms}/{len(off)} rows had transforms\n")

    # ------------------------------------------------------------------
    # Step 2: Compute DQ score PRE-enrichment
    # ------------------------------------------------------------------
    print("--- Step 2: Computing DQ scores (pre-enrichment) ---")
    pre_scores = []
    for cleaned in cleaned_rows:
        score = compute_row_dq_score(cleaned)
        pre_scores.append(score)
    avg_pre = sum(pre_scores) / len(pre_scores) if pre_scores else 0
    print(f"  Average DQ score (pre): {avg_pre:.1f}/100\n")

    # ------------------------------------------------------------------
    # Step 3: Fuzzy deduplication on rule-cleaned data
    # ------------------------------------------------------------------
    print("--- Step 3: Fuzzy deduplication (on rule-cleaned data) ---")

    # Build a DataFrame from cleaned rows for dedup
    cleaned_df = pd.DataFrame(cleaned_rows)
    cleaned_df["dq_score_pre"] = pre_scores
    cleaned_df["rule_transforms"] = [
        "; ".join(t) if t else "" for t in all_rule_transforms
    ]

    cleaned_df = find_duplicates(cleaned_df, threshold=90.0)

    dup_groups = cleaned_df["duplicate_group_id"].dropna().nunique()
    dup_rows = cleaned_df["duplicate_group_id"].notna().sum()
    total_rows = len(cleaned_df)

    # Identify canonical rows and duplicate (non-canonical) rows
    is_dup_non_canonical = (
        cleaned_df["duplicate_group_id"].notna() &
        (cleaned_df["canonical"] == False)
    )
    canonical_or_unique = ~is_dup_non_canonical
    rows_to_enrich = canonical_or_unique.sum()

    print(f"  Found {dup_groups} duplicate groups ({dup_rows} rows involved)")
    print(f"  Will LLM-enrich {rows_to_enrich}/{total_rows} rows (skipping {total_rows - rows_to_enrich} non-canonical duplicates)\n")

    # ------------------------------------------------------------------
    # Step 4: LLM enrichment via Groq (only canonical/unique rows)
    # ------------------------------------------------------------------
    print("--- Step 4: LLM enrichment (Groq Llama 3 70B) ---")
    print(f"  Enriching {rows_to_enrich} canonical/unique rows only\n")

    enriched_rows = []
    enrich_counter = 0

    for i, (_, row) in enumerate(cleaned_df.iterrows()):
        cleaned = row.to_dict()
        name = str(cleaned.get("product_name", ""))
        brand = str(cleaned.get("brands", ""))
        categories = str(cleaned.get("categories", ""))
        ingredients = str(cleaned.get("ingredients_text", ""))
        rule_transforms_str = cleaned.get("rule_transforms", "")

        # Skip LLM for non-canonical duplicates
        skip_as_dup = bool(is_dup_non_canonical.iloc[i])

        llm_result = None
        llm_status = "skipped_dup" if skip_as_dup else "skipped"
        llm_transforms = []

        if not skip_as_dup:
            # Check if LLM call is needed (at least 1 key field missing)
            null_fields = flag_nulls(cleaned, ["categories", "allergens", "ingredients_text", "labels"])
            should_call_llm = len(null_fields) >= 1

            if should_call_llm:
                prompt = EXTRACTION_PROMPT.format(
                    name=name[:200], brand=brand[:100],
                    categories=categories[:200], ingredients=ingredients[:300],
                )
                enrich_counter += 1
                print(f"  [{enrich_counter}/{rows_to_enrich}] Enriching: '{name[:40]}' ...", end=" ")
                llm_result = call_llm_json(prompt)

                if llm_result:
                    llm_status = "success"
                    if llm_result.get("primary_category") and not categories.strip():
                        llm_transforms.append(f"categories: filled by LLM -> '{llm_result['primary_category']}'")
                    if llm_result.get("allergens") and not str(cleaned.get("allergens", "")).strip():
                        llm_transforms.append(f"allergens: filled by LLM -> '{llm_result['allergens']}'")
                    if llm_result.get("dietary_tags") and not str(cleaned.get("labels", "")).strip():
                        llm_transforms.append(f"dietary_tags: filled by LLM -> '{llm_result['dietary_tags']}'")
                    print("OK")
                else:
                    llm_status = "failed"
                    print("FAILED")
            else:
                llm_status = "skipped_complete"
                print(f"  [{i+1}/{total_rows}] '{name[:40]}' -- LLM skipped (data complete)")
        else:
            print(f"  [{i+1}/{total_rows}] '{name[:40]}' -- LLM skipped (non-canonical duplicate)")

        # Build the enriched row
        llm_transforms_str = "; ".join(llm_transforms) if llm_transforms else ""
        all_transforms_str = "; ".join(
            [t for t in [rule_transforms_str, llm_transforms_str] if t]
        )

        enriched = {
            "code": cleaned.get("code", ""),
            "original_name": name,
            "original_brand": brand,
            "original_categories": categories,
            "original_ingredients": str(cleaned.get("ingredients_text", ""))[:300],
            "completeness": cleaned.get("completeness", ""),
            "product_name": name,
            "brands": brand,
            "quantity": str(cleaned.get("quantity", "")),
            "categories": categories,
            "allergens": str(cleaned.get("allergens", "")),
            "ingredients_text": str(cleaned.get("ingredients_text", "")),
            "nutrition_grades": str(cleaned.get("nutrition_grades", "")),
            "labels": str(cleaned.get("labels", "")),
            # LLM-enriched fields
            "clean_name": llm_result.get("clean_name", name) if llm_result else name,
            "clean_brand": llm_result.get("clean_brand", brand) if llm_result else brand,
            "primary_category": llm_result.get("primary_category", "") if llm_result else categories,
            "dietary_tags": llm_result.get("dietary_tags", "") if llm_result else "",
            "allergens_extracted": llm_result.get("allergens", "") if llm_result else str(cleaned.get("allergens", "")),
            "is_organic": llm_result.get("is_organic", "false") if llm_result else "false",
            # Pipeline metadata
            "enrichment_status": llm_status,
            "enriched_by_llm": llm_status == "success",
            "dq_score_pre": cleaned.get("dq_score_pre", pre_scores[i] if i < len(pre_scores) else 0),
            "rule_transforms": rule_transforms_str,
            "llm_transforms": llm_transforms_str,
            "all_transforms": all_transforms_str,
            # Dedup metadata (carry forward from step 3)
            "duplicate_group_id": cleaned.get("duplicate_group_id"),
            "canonical": cleaned.get("canonical"),
            "duplicate_score": cleaned.get("duplicate_score"),
        }
        enriched_rows.append(enriched)

    df = pd.DataFrame(enriched_rows)

    success_count = (df["enrichment_status"] == "success").sum()
    skipped_dup_count = (df["enrichment_status"] == "skipped_dup").sum()
    skipped_complete_count = (df["enrichment_status"] == "skipped_complete").sum()
    failed_count = (df["enrichment_status"] == "failed").sum()
    print(f"\n  LLM results: {success_count} success, {skipped_dup_count} skipped (dup), "
          f"{skipped_complete_count} skipped (complete), {failed_count} failed\n")

    # ------------------------------------------------------------------
    # Step 5: Compute DQ score POST-enrichment
    # ------------------------------------------------------------------
    print("--- Step 5: Computing DQ scores (post-enrichment) ---")
    post_scores = []
    for _, row in df.iterrows():
        score = compute_row_dq_score(row.to_dict())
        post_scores.append(score)
    df["dq_score_post"] = post_scores
    avg_post = sum(post_scores) / len(post_scores) if post_scores else 0
    improvement = avg_post - avg_pre
    print(f"  Average DQ score (post): {avg_post:.1f}/100")
    print(f"  Improvement: +{improvement:.1f} points\n")

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------
    df.to_csv(DATA_DIR / "enriched_products.csv", index=False)
    print("=" * 60)
    print(f"  Saved {len(df)} enriched products to data/enriched_products.csv")
    print(f"  Pipeline: Rules -> DQ Pre -> Dedup -> LLM -> DQ Post")
    print(f"  DQ Score: {avg_pre:.1f} (pre) -> {avg_post:.1f} (post) [+{improvement:.1f}]")
    print(f"  Duplicate groups: {dup_groups} ({dup_rows} rows)")
    print(f"  LLM calls saved by dedup: {skipped_dup_count}")
    print(f"  LLM success: {success_count}/{rows_to_enrich} canonical rows")
    print("=" * 60)


if __name__ == "__main__":
    enrich_products()
