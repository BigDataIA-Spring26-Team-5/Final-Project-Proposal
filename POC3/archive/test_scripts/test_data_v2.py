"""
Data Testing v2 — Fix OFF fetch + targeted overlap test
"""
import requests
import pandas as pd
import json

# ============================================================
# 1. OPEN FOOD FACTS — Fix: use the correct API endpoint
# ============================================================
print("=" * 70)
print("1. OPEN FOOD FACTS — Fetching 500 US products")
print("=" * 70)

off_products = []
for page in range(1, 26):
    url = f"https://us.openfoodfacts.org/api/v2/search?countries_tags=en:united-states&page_size=20&page={page}&fields=code,product_name,brands,categories,ingredients_text,nutrition_grades,image_url,quantity,nutriscore_score,nova_group,ecoscore_grade,allergens,labels,stores,countries,completeness"
    try:
        resp = requests.get(url, timeout=30, headers={"User-Agent": "DAMG7245-DataTest/1.0"})
        data = resp.json()
        products = data.get("products", [])
        off_products.extend(products)
        if page % 5 == 0:
            print(f"  Page {page}: total so far = {len(off_products)}")
    except Exception as e:
        print(f"  Page {page}: ERROR - {e}")
        break

if off_products:
    off_df = pd.json_normalize(off_products)

    key_fields = [
        "product_name", "brands", "categories", "ingredients_text",
        "nutrition_grades", "image_url", "quantity", "code",
        "nutriscore_score", "nova_group", "ecoscore_grade",
        "allergens", "labels", "stores", "completeness"
    ]

    print(f"\n  Total products: {len(off_df)}")

    print(f"\n  --- Field Coverage ---")
    for field in key_fields:
        if field in off_df.columns:
            non_empty = off_df[field].notna() & (off_df[field].astype(str).str.strip() != "")
            pct = non_empty.sum() / len(off_df) * 100
            print(f"  {field:25s}: {pct:5.1f}%  ({non_empty.sum()}/{len(off_df)})")
        else:
            print(f"  {field:25s}: MISSING")

    # Completeness score (OFF provides this)
    if "completeness" in off_df.columns:
        comp = off_df["completeness"].dropna().astype(float)
        print(f"\n  --- OFF Completeness Score (0-1) ---")
        print(f"  Mean:   {comp.mean():.2f}")
        print(f"  Median: {comp.median():.2f}")
        print(f"  Min:    {comp.min():.2f}")
        print(f"  Max:    {comp.max():.2f}")
        print(f"  Below 0.5: {(comp < 0.5).sum()}/{len(comp)} ({(comp < 0.5).sum()/len(comp)*100:.1f}%)")

    print(f"\n  --- Sample Product Names (showing messiness) ---")
    if "product_name" in off_df.columns:
        for i, row in off_df.head(15).iterrows():
            name = row.get("product_name", "")
            brand = row.get("brands", "")
            code = row.get("code", "")
            print(f"  [{i:2d}] name='{name}' | brand='{brand}' | barcode={code}")

print("\n")

# ============================================================
# 2. TARGETED OVERLAP TEST — Search for known brands in both sources
# ============================================================
print("=" * 70)
print("2. TARGETED OVERLAP TEST — Same product in OFF vs USDA")
print("=" * 70)

test_products = [
    "cheerios",
    "oreo",
    "coca-cola",
    "doritos",
    "nutella",
    "skippy peanut butter",
    "heinz ketchup",
    "chobani yogurt",
    "kind bar",
    "clif bar"
]

for product_query in test_products:
    print(f"\n  --- '{product_query}' ---")

    # Search OFF
    off_url = f"https://us.openfoodfacts.org/api/v2/search?search_terms={product_query}&page_size=3&fields=code,product_name,brands,categories,ingredients_text,quantity,completeness"
    try:
        resp = requests.get(off_url, timeout=15, headers={"User-Agent": "DAMG7245-DataTest/1.0"})
        off_results = resp.json().get("products", [])
    except:
        off_results = []

    # Search USDA
    usda_url = f"https://api.nal.usda.gov/fdc/v1/foods/search?api_key=DEMO_KEY&query={product_query}&dataType=Branded&pageSize=3"
    try:
        resp = requests.get(usda_url, timeout=15)
        usda_results = resp.json().get("foods", [])
    except:
        usda_results = []

    if off_results:
        p = off_results[0]
        print(f"  OFF:  name='{p.get('product_name', 'N/A')}' | brand='{p.get('brands', 'N/A')}' | barcode={p.get('code', 'N/A')}")
        print(f"        categories='{str(p.get('categories', 'N/A'))[:80]}'")
        print(f"        ingredients={str(p.get('ingredients_text', 'N/A'))[:80]}")
        print(f"        completeness={p.get('completeness', 'N/A')}")
    else:
        print(f"  OFF:  NOT FOUND")

    if usda_results:
        p = usda_results[0]
        print(f"  USDA: name='{p.get('description', 'N/A')}' | brand='{p.get('brandOwner', 'N/A')}' | UPC={p.get('gtinUpc', 'N/A')}")
        print(f"        category='{p.get('foodCategory', 'N/A')}'")
        print(f"        ingredients={str(p.get('ingredients', 'N/A'))[:80]}")
    else:
        print(f"  USDA: NOT FOUND")

    # Check if barcodes match
    if off_results and usda_results:
        off_code = str(off_results[0].get("code", ""))
        usda_upc = str(usda_results[0].get("gtinUpc", ""))
        if off_code and usda_upc and off_code == usda_upc:
            print(f"  >>> BARCODE MATCH! {off_code}")
        else:
            print(f"  >>> Different barcodes (OFF={off_code}, USDA={usda_upc}) — different variants, needs entity resolution")

print("\n")

# ============================================================
# 3. DATA QUALITY ANALYSIS — How messy is OFF really?
# ============================================================
print("=" * 70)
print("3. DATA QUALITY DEEP DIVE — How messy is Open Food Facts?")
print("=" * 70)

if off_products:
    off_df = pd.json_normalize(off_products)

    # Check for truly empty/garbage product names
    if "product_name" in off_df.columns:
        names = off_df["product_name"].astype(str)
        empty_names = (names.str.strip() == "") | (names == "nan") | names.isna()
        short_names = names.str.len() < 3
        has_weird_chars = names.str.contains(r'[^\x00-\x7F]', regex=True, na=False)

        print(f"  Product names:")
        print(f"    Empty/missing:     {empty_names.sum()}/{len(names)} ({empty_names.sum()/len(names)*100:.1f}%)")
        print(f"    Very short (<3):   {short_names.sum()}/{len(names)}")
        print(f"    Non-ASCII chars:   {has_weird_chars.sum()}/{len(names)} ({has_weird_chars.sum()/len(names)*100:.1f}%)")

    # Check categories messiness
    if "categories" in off_df.columns:
        cats = off_df["categories"].astype(str)
        empty_cats = (cats.str.strip() == "") | (cats == "nan")
        multi_lang = cats.str.contains(r'(en:|fr:|de:)', regex=True, na=False)
        print(f"\n  Categories:")
        print(f"    Empty/missing:     {empty_cats.sum()}/{len(cats)} ({empty_cats.sum()/len(cats)*100:.1f}%)")
        print(f"    Multi-language:    {multi_lang.sum()}/{len(cats)}")
        print(f"    Sample categories:")
        for cat in cats[~empty_cats].head(5):
            print(f"      '{cat[:100]}'")

    # Check ingredients messiness
    if "ingredients_text" in off_df.columns:
        ing = off_df["ingredients_text"].astype(str)
        empty_ing = (ing.str.strip() == "") | (ing == "nan")
        print(f"\n  Ingredients:")
        print(f"    Empty/missing:     {empty_ing.sum()}/{len(ing)} ({empty_ing.sum()/len(ing)*100:.1f}%)")
        print(f"    Sample messy ingredients:")
        for ingredient in ing[~empty_ing].head(3):
            print(f"      '{ingredient[:120]}'")

print("\n")

# ============================================================
# 4. FDA RECALL — Can we link recalls to OFF/USDA products?
# ============================================================
print("=" * 70)
print("4. FDA RECALL LINKAGE TEST")
print("=" * 70)

# Get some FDA recalls and see if we can find matching products
fda_url = "https://api.fda.gov/food/enforcement.json?limit=10&search=classification:\"Class+I\""
try:
    resp = requests.get(fda_url, timeout=15)
    recalls = resp.json().get("results", [])

    for i, recall in enumerate(recalls[:5]):
        product_desc = recall.get("product_description", "N/A")
        firm = recall.get("recalling_firm", "N/A")
        reason = recall.get("reason_for_recall", "N/A")

        print(f"\n  Recall [{i}]:")
        print(f"    Product: {product_desc[:120]}")
        print(f"    Firm:    {firm}")
        print(f"    Reason:  {reason[:100]}")

        # Try to find this in OFF
        search_term = firm.split()[0] if firm != "N/A" else ""
        if search_term:
            off_search = f"https://us.openfoodfacts.org/api/v2/search?search_terms={search_term}&page_size=2&fields=product_name,brands,code"
            try:
                r = requests.get(off_search, timeout=10, headers={"User-Agent": "DAMG7245-DataTest/1.0"})
                off_matches = r.json().get("products", [])
                if off_matches:
                    print(f"    OFF match: '{off_matches[0].get('product_name', '')}' by '{off_matches[0].get('brands', '')}'")
                else:
                    print(f"    OFF match: None found for '{search_term}'")
            except:
                print(f"    OFF match: Search failed")

except Exception as e:
    print(f"  ERROR: {e}")

print("\n")
print("=" * 70)
print("VERDICT")
print("=" * 70)
print("""
Review the results above and check:
1. Is OFF data messy enough? (field coverage, completeness scores)
2. Do the same products exist in both OFF and USDA? (overlap test)
3. Are the naming conventions different enough for entity resolution?
4. Can FDA recalls be linked to catalog products?
5. Does Open Prices add useful pricing data with barcodes?
""")
