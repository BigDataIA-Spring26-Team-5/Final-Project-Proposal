"""
UC1: Enrich OFF products using Groq Llama 3 70B.
Extracts structured attributes from messy product descriptions.
Run: python scripts/02_enrich_products.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import json
from config import DATA_DIR
from utils.llm import call_llm_json

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
    print("UC1: Enriching OFF products with Groq Llama 3 70B")
    print("=" * 60)

    off = pd.read_csv(DATA_DIR / "off_products.csv")
    print(f"  Loaded {len(off)} OFF products")

    enriched_rows = []
    for i, row in off.iterrows():
        name = str(row.get("product_name", ""))
        brand = str(row.get("brands", ""))
        categories = str(row.get("categories", ""))
        ingredients = str(row.get("ingredients_text", ""))

        prompt = EXTRACTION_PROMPT.format(
            name=name[:200], brand=brand[:100],
            categories=categories[:200], ingredients=ingredients[:300],
        )

        print(f"  [{i+1}/{len(off)}] Enriching: '{name[:40]}' ...", end=" ")
        result = call_llm_json(prompt)

        if result:
            enriched_rows.append({
                "code": row.get("code", ""),
                "original_name": name,
                "original_brand": brand,
                "original_categories": categories,
                "original_ingredients": ingredients[:300],
                "completeness": row.get("completeness", ""),
                "clean_name": result.get("clean_name", name),
                "clean_brand": result.get("clean_brand", brand),
                "primary_category": result.get("primary_category", ""),
                "dietary_tags": result.get("dietary_tags", ""),
                "allergens_extracted": result.get("allergens", ""),
                "is_organic": result.get("is_organic", "false"),
                "enrichment_status": "success",
            })
            print("OK")
        else:
            enriched_rows.append({
                "code": row.get("code", ""),
                "original_name": name,
                "original_brand": brand,
                "original_categories": categories,
                "original_ingredients": ingredients[:300],
                "completeness": row.get("completeness", ""),
                "clean_name": name,
                "clean_brand": brand,
                "primary_category": "",
                "dietary_tags": "",
                "allergens_extracted": "",
                "is_organic": "",
                "enrichment_status": "failed",
            })
            print("FAILED")

    df = pd.DataFrame(enriched_rows)
    df.to_csv(DATA_DIR / "enriched_products.csv", index=False)
    print(f"\n  Saved {len(df)} enriched products ({(df['enrichment_status']=='success').sum()} successful)")


if __name__ == "__main__":
    enrich_products()
