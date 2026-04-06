"""
Data Testing Script — Marketplace Intelligence Platform
Tests all 4 data sources for quality, messiness, overlap, and fitness for the project.
"""

import requests
import pandas as pd
import json
import os

OUTPUT_DIR = "data_samples"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================
# 1. OPEN FOOD FACTS — Sample 500 products
# ============================================================
print("=" * 70)
print("1. OPEN FOOD FACTS — Fetching 500 products")
print("=" * 70)

off_products = []
# Fetch products page by page (20 per page)
for page in range(1, 26):
    url = f"https://world.openfoodfacts.org/cgi/search.pl?action=process&tagtype_0=countries&tag_contains_0=contains&tag_0=united+states&page_size=20&page={page}&json=1"
    try:
        resp = requests.get(url, timeout=30)
        data = resp.json()
        off_products.extend(data.get("products", []))
        print(f"  Page {page}: got {len(data.get('products', []))} products (total: {len(off_products)})")
    except Exception as e:
        print(f"  Page {page}: ERROR - {e}")
        break

if off_products:
    # Key fields we care about
    key_fields = [
        "product_name", "brands", "categories", "ingredients_text",
        "nutrition_grades", "image_url", "quantity", "code",
        "nutriscore_score", "nova_group", "ecoscore_grade",
        "allergens", "labels", "stores", "countries"
    ]

    off_df = pd.json_normalize(off_products)
    off_df.to_csv(f"{OUTPUT_DIR}/off_sample_raw.csv", index=False)

    print(f"\n  Total products fetched: {len(off_df)}")
    print(f"  Total columns in raw data: {len(off_df.columns)}")

    # Check field coverage
    print(f"\n  --- Field Coverage (% non-empty) ---")
    for field in key_fields:
        if field in off_df.columns:
            non_empty = off_df[field].notna() & (off_df[field].astype(str).str.strip() != "")
            pct = non_empty.sum() / len(off_df) * 100
            print(f"  {field:25s}: {pct:5.1f}% ({non_empty.sum()}/{len(off_df)})")
        else:
            print(f"  {field:25s}: MISSING COLUMN")

    # Show some messy examples
    print(f"\n  --- Sample Product Names (first 10) ---")
    if "product_name" in off_df.columns:
        for i, name in enumerate(off_df["product_name"].head(10)):
            print(f"  [{i}] {name}")

    print(f"\n  --- Sample Brands (first 10) ---")
    if "brands" in off_df.columns:
        for i, brand in enumerate(off_df["brands"].head(10)):
            print(f"  [{i}] {brand}")

    # Check for barcodes (needed for cross-source matching)
    if "code" in off_df.columns:
        has_barcode = off_df["code"].notna() & (off_df["code"].astype(str).str.strip() != "")
        print(f"\n  Barcode coverage: {has_barcode.sum()}/{len(off_df)} ({has_barcode.sum()/len(off_df)*100:.1f}%)")

print("\n")

# ============================================================
# 2. USDA FoodData Central — Sample 500 branded foods
# ============================================================
print("=" * 70)
print("2. USDA FoodData Central — Fetching 500 branded foods")
print("=" * 70)

USDA_API_KEY = "DEMO_KEY"  # Free demo key, 30 requests/hour
usda_products = []

# Fetch branded foods
for page_num in range(1, 6):
    url = f"https://api.nal.usda.gov/fdc/v1/foods/list?api_key={USDA_API_KEY}&dataType=Branded&pageSize=100&pageNumber={page_num}"
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            items = resp.json()
            usda_products.extend(items)
            print(f"  Page {page_num}: got {len(items)} items (total: {len(usda_products)})")
        else:
            print(f"  Page {page_num}: HTTP {resp.status_code}")
            break
    except Exception as e:
        print(f"  Page {page_num}: ERROR - {e}")
        break

if usda_products:
    usda_df = pd.json_normalize(usda_products)
    usda_df.to_csv(f"{OUTPUT_DIR}/usda_sample_raw.csv", index=False)

    print(f"\n  Total products fetched: {len(usda_df)}")
    print(f"  Total columns: {len(usda_df.columns)}")

    usda_key_fields = [
        "description", "brandOwner", "brandName", "gtinUpc",
        "ingredients", "foodCategory", "servingSize", "servingSizeUnit",
        "marketCountry", "dataType", "publicationDate"
    ]

    print(f"\n  --- Field Coverage (% non-empty) ---")
    for field in usda_key_fields:
        if field in usda_df.columns:
            non_empty = usda_df[field].notna() & (usda_df[field].astype(str).str.strip() != "")
            pct = non_empty.sum() / len(usda_df) * 100
            print(f"  {field:25s}: {pct:5.1f}% ({non_empty.sum()}/{len(usda_df)})")
        else:
            print(f"  {field:25s}: MISSING COLUMN")

    print(f"\n  --- Sample Descriptions (first 10) ---")
    if "description" in usda_df.columns:
        for i, desc in enumerate(usda_df["description"].head(10)):
            print(f"  [{i}] {desc}")

    print(f"\n  --- Sample Brands (first 10) ---")
    if "brandOwner" in usda_df.columns:
        for i, brand in enumerate(usda_df["brandOwner"].head(10)):
            print(f"  [{i}] {brand}")

    # Check UPC coverage
    if "gtinUpc" in usda_df.columns:
        has_upc = usda_df["gtinUpc"].notna() & (usda_df["gtinUpc"].astype(str).str.strip() != "")
        print(f"\n  UPC barcode coverage: {has_upc.sum()}/{len(usda_df)} ({has_upc.sum()/len(usda_df)*100:.1f}%)")

print("\n")

# ============================================================
# 3. openFDA Food Enforcement (Recalls)
# ============================================================
print("=" * 70)
print("3. openFDA Food Enforcement — Fetching 500 recall records")
print("=" * 70)

fda_records = []
for skip in range(0, 500, 100):
    url = f"https://api.fda.gov/food/enforcement.json?limit=100&skip={skip}"
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            fda_records.extend(results)
            print(f"  Batch {skip//100 + 1}: got {len(results)} records (total: {len(fda_records)})")
        else:
            print(f"  Batch {skip//100 + 1}: HTTP {resp.status_code}")
            break
    except Exception as e:
        print(f"  Batch {skip//100 + 1}: ERROR - {e}")
        break

if fda_records:
    fda_df = pd.json_normalize(fda_records)
    fda_df.to_csv(f"{OUTPUT_DIR}/fda_sample_raw.csv", index=False)

    print(f"\n  Total records fetched: {len(fda_df)}")
    print(f"  Total columns: {len(fda_df.columns)}")

    fda_key_fields = [
        "product_description", "reason_for_recall", "recalling_firm",
        "code_info", "status", "classification", "voluntary_mandated",
        "distribution_pattern", "state", "city", "recall_initiation_date"
    ]

    print(f"\n  --- Field Coverage (% non-empty) ---")
    for field in fda_key_fields:
        if field in fda_df.columns:
            non_empty = fda_df[field].notna() & (fda_df[field].astype(str).str.strip() != "")
            pct = non_empty.sum() / len(fda_df) * 100
            print(f"  {field:25s}: {pct:5.1f}% ({non_empty.sum()}/{len(fda_df)})")
        else:
            print(f"  {field:25s}: MISSING COLUMN")

    print(f"\n  --- Sample Product Descriptions (first 5) ---")
    if "product_description" in fda_df.columns:
        for i, desc in enumerate(fda_df["product_description"].head(5)):
            print(f"  [{i}] {str(desc)[:150]}")

    print(f"\n  --- Sample Recalling Firms (first 10) ---")
    if "recalling_firm" in fda_df.columns:
        for i, firm in enumerate(fda_df["recalling_firm"].head(10)):
            print(f"  [{i}] {firm}")

print("\n")

# ============================================================
# 4. Open Prices — Sample recent prices
# ============================================================
print("=" * 70)
print("4. Open Prices — Fetching recent price entries")
print("=" * 70)

try:
    url = "https://prices.openfoodfacts.org/api/v1/prices?page_size=100&order_by=-date"
    resp = requests.get(url, timeout=30)
    if resp.status_code == 200:
        price_data = resp.json()
        prices = price_data.get("items", price_data.get("results", []))

        if isinstance(price_data, dict) and not prices:
            # Try different response structure
            print(f"  Response keys: {list(price_data.keys())[:10]}")
            prices = price_data.get("data", price_data.get("items", []))

        if prices:
            price_df = pd.json_normalize(prices)
            price_df.to_csv(f"{OUTPUT_DIR}/open_prices_sample_raw.csv", index=False)

            print(f"  Total price entries fetched: {len(price_df)}")
            print(f"  Total columns: {len(price_df.columns)}")
            print(f"\n  --- Columns available ---")
            for col in price_df.columns:
                non_empty = price_df[col].notna() & (price_df[col].astype(str).str.strip() != "")
                pct = non_empty.sum() / len(price_df) * 100
                print(f"  {col:35s}: {pct:5.1f}%")

            print(f"\n  --- Sample entries (first 5) ---")
            for i, row in price_df.head(5).iterrows():
                print(f"  [{i}] {row.to_dict()}")
        else:
            print(f"  No price items found. Response: {str(price_data)[:300]}")
    else:
        print(f"  HTTP {resp.status_code}: {resp.text[:200]}")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n")

# ============================================================
# 5. CROSS-SOURCE OVERLAP TEST
# ============================================================
print("=" * 70)
print("5. CROSS-SOURCE OVERLAP TEST — Can we match products?")
print("=" * 70)

# Test barcode overlap between OFF and USDA
if off_products and usda_products:
    off_barcodes = set()
    for p in off_products:
        code = str(p.get("code", "")).strip()
        if code and code != "nan":
            off_barcodes.add(code)

    usda_upcs = set()
    for p in usda_products:
        upc = str(p.get("gtinUpc", "")).strip()
        if upc and upc != "nan":
            usda_upcs.add(upc)

    overlap = off_barcodes & usda_upcs

    print(f"  OFF barcodes:  {len(off_barcodes)}")
    print(f"  USDA UPCs:     {len(usda_upcs)}")
    print(f"  Direct overlap: {len(overlap)}")

    if overlap:
        print(f"\n  --- Matched Products (showing how same product looks in both sources) ---")
        for barcode in list(overlap)[:5]:
            off_match = [p for p in off_products if str(p.get("code", "")) == barcode]
            usda_match = [p for p in usda_products if str(p.get("gtinUpc", "")) == barcode]
            if off_match and usda_match:
                print(f"\n  Barcode: {barcode}")
                print(f"    OFF name:  {off_match[0].get('product_name', 'N/A')}")
                print(f"    OFF brand: {off_match[0].get('brands', 'N/A')}")
                print(f"    USDA name: {usda_match[0].get('description', 'N/A')}")
                print(f"    USDA brand: {usda_match[0].get('brandOwner', 'N/A')}")
    else:
        print("\n  No direct barcode overlap in this small sample (expected — random samples)")
        print("  This doesn't mean no overlap exists. Testing fuzzy name matching instead...")

        # Try fuzzy name matching
        print(f"\n  --- Fuzzy Name Matching Candidates ---")
        off_names = [(p.get("product_name", ""), p.get("brands", "")) for p in off_products if p.get("product_name")]
        usda_names = [(p.get("description", ""), p.get("brandOwner", "")) for p in usda_products if p.get("description")]

        # Simple word overlap check
        matches_found = 0
        for off_name, off_brand in off_names[:100]:
            off_words = set(str(off_name).lower().split() + str(off_brand).lower().split())
            for usda_name, usda_brand in usda_names[:100]:
                usda_words = set(str(usda_name).lower().split() + str(usda_brand).lower().split())
                common = off_words & usda_words - {"", "nan", "the", "and", "or", "of", "with", "in", "a"}
                if len(common) >= 2:
                    print(f"    OFF:  '{off_name}' ({off_brand})")
                    print(f"    USDA: '{usda_name}' ({usda_brand})")
                    print(f"    Common words: {common}")
                    print()
                    matches_found += 1
                    if matches_found >= 5:
                        break
            if matches_found >= 5:
                break

        if matches_found == 0:
            print("  No fuzzy matches in this small sample either. Need larger sample or targeted search.")

print("\n")
print("=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"  Samples saved to: {OUTPUT_DIR}/")
print(f"  Files: off_sample_raw.csv, usda_sample_raw.csv, fda_sample_raw.csv, open_prices_sample_raw.csv")
print("  Review the field coverage and messiness above to decide if these sources work.")
