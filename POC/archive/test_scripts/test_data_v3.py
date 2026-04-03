"""
Data Testing v3 — Direct barcode lookups + bulk data quality check
Strategy: Use USDA UPCs to look up the same products in OFF by barcode
"""
import requests
import pandas as pd
import json
import time

HEADERS = {"User-Agent": "DAMG7245-DataTest/1.0 - academic project"}

# ============================================================
# 1. Get USDA products with UPC codes
# ============================================================
print("=" * 70)
print("1. USDA — Fetching 200 branded products with UPCs")
print("=" * 70)

usda_products = []
for page in range(1, 3):
    url = f"https://api.nal.usda.gov/fdc/v1/foods/search?api_key=DEMO_KEY&dataType=Branded&pageSize=100&pageNumber={page}"
    resp = requests.get(url, timeout=30)
    foods = resp.json().get("foods", [])
    usda_products.extend(foods)
    print(f"  Page {page}: {len(foods)} products (total: {len(usda_products)})")

print(f"\n  Sample USDA products:")
for p in usda_products[:5]:
    print(f"    '{p.get('description', '')}' | brand='{p.get('brandOwner', '')}' | UPC={p.get('gtinUpc', '')}")

# ============================================================
# 2. Cross-reference: Look up USDA UPCs in Open Food Facts
# ============================================================
print("\n" + "=" * 70)
print("2. CROSS-REFERENCE — Look up USDA barcodes in Open Food Facts")
print("=" * 70)

matches = []
not_found = []
different_data = []

# Test first 50 USDA products by barcode in OFF
for i, usda_p in enumerate(usda_products[:50]):
    upc = usda_p.get("gtinUpc", "")
    if not upc:
        continue

    # OFF uses EAN-13 (13 digits), USDA uses GTIN/UPC (variable length)
    # Pad to 13 digits if shorter
    barcode = upc.zfill(13)

    off_url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json?fields=code,product_name,brands,categories,ingredients_text,quantity,completeness,nutrition_grades,image_url"
    try:
        resp = requests.get(off_url, timeout=10, headers=HEADERS)
        data = resp.json()

        if data.get("status") == 1:
            off_p = data.get("product", {})
            matches.append({
                "barcode": barcode,
                "usda_name": usda_p.get("description", ""),
                "usda_brand": usda_p.get("brandOwner", ""),
                "off_name": off_p.get("product_name", ""),
                "off_brand": off_p.get("brands", ""),
                "off_completeness": off_p.get("completeness", ""),
                "off_categories": str(off_p.get("categories", ""))[:80],
                "off_ingredients": str(off_p.get("ingredients_text", ""))[:80],
                "usda_category": usda_p.get("foodCategory", ""),
                "usda_ingredients": str(usda_p.get("ingredients", ""))[:80],
            })
        else:
            not_found.append({
                "barcode": barcode,
                "usda_name": usda_p.get("description", ""),
                "usda_brand": usda_p.get("brandOwner", ""),
            })
    except Exception as e:
        pass

    if (i + 1) % 10 == 0:
        print(f"  Checked {i+1}/50 barcodes... ({len(matches)} found in OFF)")
    time.sleep(0.5)  # Be nice to the API

print(f"\n  Results: {len(matches)} found in both / {len(not_found)} USDA-only / {50 - len(matches) - len(not_found)} errors")

if matches:
    print(f"\n  --- MATCHED PRODUCTS (same product, different data) ---")
    for m in matches[:10]:
        print(f"\n  Barcode: {m['barcode']}")
        print(f"    USDA name:  '{m['usda_name']}'")
        print(f"    OFF name:   '{m['off_name']}'")
        print(f"    USDA brand: '{m['usda_brand']}'")
        print(f"    OFF brand:  '{m['off_brand']}'")
        print(f"    USDA cat:   '{m['usda_category']}'")
        print(f"    OFF cat:    '{m['off_categories']}'")
        print(f"    OFF completeness: {m['off_completeness']}")

        # Flag differences
        diffs = []
        if m['usda_name'].lower().strip() != m['off_name'].lower().strip():
            diffs.append("NAME DIFFERS")
        if m['usda_brand'].lower().strip() != m['off_brand'].lower().strip():
            diffs.append("BRAND DIFFERS")
        if diffs:
            print(f"    >>> DIFFERENCES: {', '.join(diffs)}")
            different_data.append(m)

    print(f"\n  --- SUMMARY ---")
    print(f"  Products found in both sources: {len(matches)}/{50}")
    print(f"  Products with different names:  {len([m for m in matches if m['usda_name'].lower().strip() != m['off_name'].lower().strip()])}")
    print(f"  Products with different brands: {len([m for m in matches if m['usda_brand'].lower().strip() != m['off_brand'].lower().strip()])}")

# ============================================================
# 3. OFF Data Quality — Fetch a random batch directly
# ============================================================
print("\n" + "=" * 70)
print("3. OPEN FOOD FACTS — Data Quality on Random Products")
print("=" * 70)

# Use the facets/categories endpoint which is more reliable
off_random = []
categories = ["breakfasts", "snacks", "beverages", "dairy", "cereals"]

for cat in categories:
    url = f"https://world.openfoodfacts.org/category/{cat}/1.json"
    try:
        resp = requests.get(url, timeout=15, headers=HEADERS)
        data = resp.json()
        products = data.get("products", [])
        off_random.extend(products[:50])
        print(f"  Category '{cat}': got {len(products[:50])} products")
    except Exception as e:
        print(f"  Category '{cat}': ERROR - {e}")
    time.sleep(0.5)

if off_random:
    off_df = pd.json_normalize(off_random)
    print(f"\n  Total OFF products: {len(off_df)}")

    key_fields = [
        "product_name", "brands", "categories", "ingredients_text",
        "nutrition_grades", "image_url", "quantity", "code",
        "allergens", "labels", "stores", "completeness"
    ]

    print(f"\n  --- Field Coverage ---")
    for field in key_fields:
        if field in off_df.columns:
            non_empty = off_df[field].notna() & (off_df[field].astype(str).str.strip() != "")
            pct = non_empty.sum() / len(off_df) * 100
            print(f"  {field:25s}: {pct:5.1f}%  ({non_empty.sum()}/{len(off_df)})")
        else:
            print(f"  {field:25s}: MISSING")

    if "completeness" in off_df.columns:
        comp = off_df["completeness"].dropna().astype(float)
        print(f"\n  --- Completeness Score Distribution ---")
        print(f"  Mean:       {comp.mean():.2f}")
        print(f"  Median:     {comp.median():.2f}")
        print(f"  Below 0.3:  {(comp < 0.3).sum()}/{len(comp)} ({(comp < 0.3).sum()/len(comp)*100:.1f}%) — VERY incomplete")
        print(f"  0.3 - 0.6:  {((comp >= 0.3) & (comp < 0.6)).sum()}/{len(comp)} — partially complete")
        print(f"  0.6 - 0.8:  {((comp >= 0.6) & (comp < 0.8)).sum()}/{len(comp)} — mostly complete")
        print(f"  Above 0.8:  {(comp >= 0.8).sum()}/{len(comp)} — well documented")

    # Show messy examples
    print(f"\n  --- Messiest Products (lowest completeness) ---")
    if "completeness" in off_df.columns and "product_name" in off_df.columns:
        worst = off_df.nsmallest(10, "completeness")
        for _, row in worst.iterrows():
            print(f"  completeness={row.get('completeness', '?'):.2f} | name='{row.get('product_name', '')}' | brand='{row.get('brands', '')}' | ingredients={'YES' if pd.notna(row.get('ingredients_text')) and str(row.get('ingredients_text')).strip() else 'MISSING'}")

# ============================================================
# 4. FDA — Sample of food recalls with product details
# ============================================================
print("\n" + "=" * 70)
print("4. FDA RECALLS — Data richness check")
print("=" * 70)

fda_url = "https://api.fda.gov/food/enforcement.json?limit=20"
try:
    resp = requests.get(fda_url, timeout=15)
    recalls = resp.json().get("results", [])

    print(f"  Total recall records fetched: {len(recalls)}")
    print(f"\n  --- Field Coverage ---")
    fields = ["product_description", "reason_for_recall", "recalling_firm",
              "code_info", "classification", "distribution_pattern",
              "recall_initiation_date", "product_type", "status"]
    for field in fields:
        has = sum(1 for r in recalls if r.get(field))
        print(f"  {field:30s}: {has}/{len(recalls)} ({has/len(recalls)*100:.0f}%)")

    print(f"\n  --- Sample Recall Product Descriptions ---")
    for r in recalls[:5]:
        desc = r.get("product_description", "")[:150]
        firm = r.get("recalling_firm", "")
        reason = r.get("reason_for_recall", "")[:80]
        print(f"  Product: {desc}")
        print(f"  Firm: {firm} | Reason: {reason}")
        print()

except Exception as e:
    print(f"  ERROR: {e}")

# ============================================================
# 5. FINAL VERDICT
# ============================================================
print("=" * 70)
print("FINAL VERDICT")
print("=" * 70)
print(f"""
  CROSS-SOURCE OVERLAP:
    - {len(matches)}/50 USDA products also found in OFF by barcode
    - Overlap rate: {len(matches)/50*100:.0f}%
    - Entity resolution needed: Names and brands differ between sources

  DATA QUALITY (OFF):
    - Crowdsourced = naturally messy
    - Many products have low completeness scores
    - Missing ingredients, categories, nutrition grades are common
    - Perfect for DQ scoring (real variance between 0-100)

  FDA RECALLS:
    - Rich text descriptions but no standardized product codes
    - Entity resolution to catalog products requires NLP/fuzzy matching
    - Adds safety dimension to the platform

  OPEN PRICES (from earlier test):
    - Links to OFF via barcode
    - Adds pricing + location data
    - Crowdsourced = quality issues in prices too

  RECOMMENDATION:
    - OFF + USDA = strong core for entity resolution + DQ scoring
    - FDA = good enrichment layer (safety/compliance)
    - Open Prices = useful but smaller dataset, optional
""")
