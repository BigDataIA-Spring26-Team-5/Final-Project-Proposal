"""
UC1: Entity resolution — match OFF products to USDA, link FDA recalls.
Run: python scripts/03_entity_resolution.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from rapidfuzz import fuzz
from config import DATA_DIR


def normalize(text):
    """Normalize text for fuzzy matching."""
    if pd.isna(text):
        return ""
    text = str(text).lower().strip()
    # Remove common noise words
    for word in ["organic", "natural", "original", "classic", "brand", "inc.", "inc", "llc", "corp", "co.", "the"]:
        text = text.replace(word, "")
    # Remove punctuation and extra spaces
    text = "".join(c if c.isalnum() or c == " " else " " for c in text)
    return " ".join(text.split())


def match_off_to_usda():
    print("=" * 60)
    print("Entity Resolution: OFF ↔ USDA matching")
    print("=" * 60)

    enriched = pd.read_csv(DATA_DIR / "enriched_products.csv")
    usda = pd.read_csv(DATA_DIR / "usda_products.csv")

    print(f"  OFF products: {len(enriched)}")
    print(f"  USDA products: {len(usda)}")

    matches = []
    for _, off_row in enriched.iterrows():
        off_name = normalize(off_row.get("clean_name", off_row.get("original_name", "")))
        off_brand = normalize(off_row.get("clean_brand", off_row.get("original_brand", "")))
        off_text = f"{off_name} {off_brand}"

        best_score = 0
        best_match = None

        for _, usda_row in usda.iterrows():
            usda_name = normalize(usda_row.get("description", ""))
            usda_brand = normalize(usda_row.get("brand_owner", ""))
            usda_text = f"{usda_name} {usda_brand}"

            # Combine name and brand similarity
            name_score = fuzz.token_sort_ratio(off_name, usda_name)
            brand_score = fuzz.token_sort_ratio(off_brand, usda_brand)
            combined_score = fuzz.token_sort_ratio(off_text, usda_text)

            # Weighted: name matters most
            score = (name_score * 0.5 + brand_score * 0.2 + combined_score * 0.3)

            if score > best_score:
                best_score = score
                best_match = usda_row

        matches.append({
            "off_code": off_row.get("code", ""),
            "off_name": off_row.get("original_name", ""),
            "off_brand": off_row.get("original_brand", ""),
            "off_clean_name": off_row.get("clean_name", ""),
            "usda_fdc_id": best_match.get("fdc_id", "") if best_match is not None else "",
            "usda_name": best_match.get("description", "") if best_match is not None else "",
            "usda_brand": best_match.get("brand_owner", "") if best_match is not None else "",
            "usda_category": best_match.get("food_category", "") if best_match is not None else "",
            "usda_ingredients": str(best_match.get("ingredients", ""))[:200] if best_match is not None else "",
            "match_score": round(best_score, 1),
            "match_quality": "high" if best_score >= 70 else "medium" if best_score >= 50 else "low",
        })
        print(f"  '{off_row.get('original_name', '')[:30]}' → '{best_match.get('description', '')[:30] if best_match is not None else 'None'}' (score: {best_score:.0f})")

    match_df = pd.DataFrame(matches)
    match_df.to_csv(DATA_DIR / "matched_products.csv", index=False)
    print(f"\n  Saved {len(match_df)} matches: {(match_df['match_quality']=='high').sum()} high, {(match_df['match_quality']=='medium').sum()} medium, {(match_df['match_quality']=='low').sum()} low")
    return match_df


def link_fda_recalls(match_df):
    print("\n" + "=" * 60)
    print("Entity Resolution: FDA recalls → catalog products")
    print("=" * 60)

    fda = pd.read_csv(DATA_DIR / "fda_recalls.csv")
    enriched = pd.read_csv(DATA_DIR / "enriched_products.csv")
    usda = pd.read_csv(DATA_DIR / "usda_products.csv")

    # Build catalog of all product names + brands
    catalog_names = []
    for _, row in enriched.iterrows():
        catalog_names.append({
            "product_code": row.get("code", ""),
            "product_name": str(row.get("clean_name", row.get("original_name", ""))),
            "brand": str(row.get("clean_brand", row.get("original_brand", ""))),
            "source": "off",
        })
    for _, row in usda.iterrows():
        catalog_names.append({
            "product_code": str(row.get("fdc_id", "")),
            "product_name": str(row.get("description", "")),
            "brand": str(row.get("brand_owner", "")),
            "source": "usda",
        })

    links = []
    for _, recall in fda.iterrows():
        recall_desc = str(recall.get("product_description", ""))
        recall_firm = str(recall.get("recalling_firm", ""))
        recall_text = normalize(f"{recall_desc} {recall_firm}")

        best_score = 0
        best_product = None

        for product in catalog_names:
            product_text = normalize(f"{product['product_name']} {product['brand']}")
            score = fuzz.token_sort_ratio(recall_text[:100], product_text)
            if score > best_score:
                best_score = score
                best_product = product

        if best_score >= 40:
            links.append({
                "recall_number": recall.get("recall_number", ""),
                "recall_description": recall_desc[:200],
                "recalling_firm": recall_firm,
                "classification": recall.get("classification", ""),
                "reason": str(recall.get("reason_for_recall", ""))[:200],
                "matched_product_code": best_product["product_code"] if best_product else "",
                "matched_product_name": best_product["product_name"] if best_product else "",
                "matched_source": best_product["source"] if best_product else "",
                "match_score": round(best_score, 1),
            })

    link_df = pd.DataFrame(links)
    link_df.to_csv(DATA_DIR / "recall_links.csv", index=False)
    print(f"  Linked {len(link_df)} recalls to catalog products")
    return link_df


def build_merged_catalog():
    print("\n" + "=" * 60)
    print("Building merged catalog")
    print("=" * 60)

    enriched = pd.read_csv(DATA_DIR / "enriched_products.csv")
    usda = pd.read_csv(DATA_DIR / "usda_products.csv")
    matches = pd.read_csv(DATA_DIR / "matched_products.csv")

    # Start with enriched OFF products
    catalog = []
    for _, row in enriched.iterrows():
        match = matches[matches["off_code"] == row.get("code")]
        usda_match = None
        if len(match) > 0 and match.iloc[0]["match_score"] >= 50:
            fdc_id = match.iloc[0]["usda_fdc_id"]
            usda_rows = usda[usda["fdc_id"] == fdc_id]
            if len(usda_rows) > 0:
                usda_match = usda_rows.iloc[0]

        catalog.append({
            "product_id": row.get("code", ""),
            "name": row.get("clean_name", row.get("original_name", "")),
            "brand": row.get("clean_brand", row.get("original_brand", "")),
            "category": row.get("primary_category", ""),
            "ingredients": row.get("original_ingredients", ""),
            "dietary_tags": row.get("dietary_tags", ""),
            "allergens": row.get("allergens_extracted", ""),
            "is_organic": row.get("is_organic", ""),
            "completeness": row.get("completeness", ""),
            "usda_category": usda_match.get("food_category", "") if usda_match is not None else "",
            "usda_ingredients": str(usda_match.get("ingredients", ""))[:300] if usda_match is not None else "",
            "match_score": match.iloc[0]["match_score"] if len(match) > 0 else 0,
            "source": "off",
            "enriched": row.get("enrichment_status", "") == "success",
        })

    # Add unmatched USDA products
    matched_fdc_ids = set(matches[matches["match_score"] >= 50]["usda_fdc_id"].values)
    for _, row in usda.iterrows():
        if row.get("fdc_id") not in matched_fdc_ids:
            catalog.append({
                "product_id": str(row.get("fdc_id", "")),
                "name": row.get("description", ""),
                "brand": row.get("brand_owner", ""),
                "category": row.get("food_category", ""),
                "ingredients": str(row.get("ingredients", ""))[:300],
                "dietary_tags": "",
                "allergens": "",
                "is_organic": "",
                "completeness": 1.0,
                "usda_category": row.get("food_category", ""),
                "usda_ingredients": str(row.get("ingredients", ""))[:300],
                "match_score": 0,
                "source": "usda",
                "enriched": False,
            })

    catalog_df = pd.DataFrame(catalog)
    catalog_df.to_csv(DATA_DIR / "merged_catalog.csv", index=False)
    print(f"  Merged catalog: {len(catalog_df)} products ({(catalog_df['source']=='off').sum()} OFF + {(catalog_df['source']=='usda').sum()} USDA)")
    return catalog_df


if __name__ == "__main__":
    match_df = match_off_to_usda()
    link_fda_recalls(match_df)
    build_merged_catalog()
