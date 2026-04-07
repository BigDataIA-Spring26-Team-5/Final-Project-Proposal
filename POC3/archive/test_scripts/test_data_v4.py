"""
Data Testing v4 — Debug API issues, use working endpoints
"""
import requests
import json
import time

HEADERS = {"User-Agent": "DAMG7245-BigData/1.0 - akshay.rajchevala@northeastern.edu"}

# ============================================================
# 1. Debug OFF API
# ============================================================
print("=" * 70)
print("1. OPEN FOOD FACTS — Testing different endpoints")
print("=" * 70)

# Test 1: Direct product lookup by known barcode (Cheerios = 0016000275287)
print("\n  Test 1: Direct barcode lookup (Cheerios)")
url = "https://world.openfoodfacts.org/api/v2/product/0016000275287.json"
resp = requests.get(url, timeout=15, headers=HEADERS)
print(f"  Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    print(f"  Found: {data.get('status', 'N/A')} (1=found)")
    if data.get("status") == 1:
        p = data["product"]
        print(f"  Name: {p.get('product_name', 'N/A')}")
        print(f"  Brand: {p.get('brands', 'N/A')}")
        print(f"  Categories: {str(p.get('categories', 'N/A'))[:100]}")
        print(f"  Ingredients: {str(p.get('ingredients_text', 'N/A'))[:100]}")
        print(f"  Completeness: {p.get('completeness', 'N/A')}")
        print(f"  Nutrition grade: {p.get('nutrition_grades', 'N/A')}")
else:
    print(f"  Response: {resp.text[:200]}")

time.sleep(1)

# Test 2: Different search endpoint
print("\n  Test 2: Search via cgi (cheerios)")
url = "https://world.openfoodfacts.org/cgi/search.pl?search_terms=cheerios&search_simple=1&action=process&json=1&page_size=5"
resp = requests.get(url, timeout=15, headers=HEADERS)
print(f"  Status: {resp.status_code}, Content-Type: {resp.headers.get('Content-Type', 'N/A')}")
if resp.status_code == 200:
    try:
        data = resp.json()
        products = data.get("products", [])
        print(f"  Found {len(products)} products")
        for p in products[:3]:
            print(f"    '{p.get('product_name', '')}' | brand='{p.get('brands', '')}' | code={p.get('code', '')}")
    except:
        print(f"  Response not JSON: {resp.text[:200]}")

time.sleep(1)

# Test 3: Category browse
print("\n  Test 3: Browse by category")
url = "https://world.openfoodfacts.org/api/v2/search?categories_tags=en:breakfast-cereals&page_size=10&fields=code,product_name,brands,categories,completeness,ingredients_text"
resp = requests.get(url, timeout=15, headers=HEADERS)
print(f"  Status: {resp.status_code}")
if resp.status_code == 200:
    try:
        data = resp.json()
        products = data.get("products", [])
        print(f"  Found {len(products)} products")
        for p in products[:5]:
            print(f"    name='{p.get('product_name', '')}' | brand='{p.get('brands', '')}' | completeness={p.get('completeness', '?')}")
    except:
        print(f"  Not JSON: {resp.text[:200]}")

time.sleep(1)

# ============================================================
# 2. Debug USDA API
# ============================================================
print("\n" + "=" * 70)
print("2. USDA — Testing different endpoints")
print("=" * 70)

# Test 1: Search endpoint
print("\n  Test 1: Search for 'cheerios'")
url = "https://api.nal.usda.gov/fdc/v1/foods/search?api_key=DEMO_KEY&query=cheerios&dataType=Branded&pageSize=5"
resp = requests.get(url, timeout=15)
print(f"  Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    foods = data.get("foods", [])
    print(f"  Found {len(foods)} foods, totalHits={data.get('totalHits', '?')}")
    for f in foods[:3]:
        print(f"    '{f.get('description', '')}' | brand='{f.get('brandOwner', '')}' | UPC={f.get('gtinUpc', '')}")
        print(f"      ingredients: {str(f.get('ingredients', ''))[:80]}")
        print(f"      category: {f.get('foodCategory', '')}")
elif resp.status_code == 429:
    print("  RATE LIMITED — DEMO_KEY allows 30 requests/hour")
    print(f"  Response: {resp.text[:200]}")
else:
    print(f"  Response: {resp.text[:200]}")

time.sleep(1)

# Test 2: List endpoint
print("\n  Test 2: List branded foods")
url = "https://api.nal.usda.gov/fdc/v1/foods/list?api_key=DEMO_KEY&dataType=Branded&pageSize=5"
resp = requests.get(url, timeout=15)
print(f"  Status: {resp.status_code}")
if resp.status_code == 200:
    foods = resp.json()
    print(f"  Got {len(foods)} foods")
    for f in foods[:3]:
        print(f"    '{f.get('description', '')}' | fdcId={f.get('fdcId', '')}")
else:
    print(f"  Response: {resp.text[:200]}")

# ============================================================
# 3. TARGETED CROSS-SOURCE TEST — Known barcodes
# ============================================================
print("\n" + "=" * 70)
print("3. CROSS-SOURCE MATCHING — Known products by barcode")
print("=" * 70)

# Known UPCs for common products
known_upcs = {
    "0016000275287": "Cheerios (General Mills)",
    "0044000032159": "Oreo Cookies",
    "0049000006346": "Coca-Cola Classic",
    "0028400028738": "Doritos Nacho Cheese",
    "0009800895007": "Nutella",
    "0037600109826": "Skippy Peanut Butter",
    "0013000006040": "Heinz Ketchup",
    "0818290014313": "Chobani Greek Yogurt",
    "0602652171130": "KIND Nut Bar",
    "0722252100900": "Clif Bar",
    "0038000138416": "Kellogg's Frosted Flakes",
    "0030000311707": "Quaker Oats",
    "0021130126026": "Signature Select (store brand)",
    "0041196910797": "Bowl & Basket (ShopRite)",
    "0078742370880": "Great Value (Walmart)",
}

for upc, expected_name in known_upcs.items():
    print(f"\n  --- {expected_name} (UPC: {upc}) ---")

    # Look up in OFF
    off_url = f"https://world.openfoodfacts.org/api/v2/product/{upc}.json?fields=code,product_name,brands,categories,ingredients_text,completeness,nutrition_grades,quantity"
    try:
        resp = requests.get(off_url, timeout=10, headers=HEADERS)
        data = resp.json()
        if data.get("status") == 1:
            p = data["product"]
            off_name = p.get("product_name", "")
            off_brand = p.get("brands", "")
            off_comp = p.get("completeness", "?")
            off_ing = str(p.get("ingredients_text", ""))[:60]
            off_cat = str(p.get("categories", ""))[:60]
            print(f"  OFF:  name='{off_name}' | brand='{off_brand}' | completeness={off_comp}")
            print(f"        cat='{off_cat}' | ingredients={off_ing or 'MISSING'}")
        else:
            print(f"  OFF:  NOT FOUND")
            off_name = ""
    except Exception as e:
        print(f"  OFF:  ERROR - {e}")
        off_name = ""

    # Look up in USDA
    usda_url = f"https://api.nal.usda.gov/fdc/v1/foods/search?api_key=DEMO_KEY&query={upc}&dataType=Branded&pageSize=1"
    try:
        resp = requests.get(usda_url, timeout=10)
        if resp.status_code == 200:
            foods = resp.json().get("foods", [])
            if foods:
                f = foods[0]
                usda_name = f.get("description", "")
                usda_brand = f.get("brandOwner", "")
                usda_cat = f.get("foodCategory", "")
                usda_ing = str(f.get("ingredients", ""))[:60]
                print(f"  USDA: name='{usda_name}' | brand='{usda_brand}'")
                print(f"        cat='{usda_cat}' | ingredients={usda_ing or 'MISSING'}")

                # Compare
                if off_name:
                    name_match = off_name.lower().strip() == usda_name.lower().strip()
                    print(f"  >>> Names match: {'YES' if name_match else 'NO — ENTITY RESOLUTION NEEDED'}")
            else:
                print(f"  USDA: NOT FOUND for UPC {upc}")
        elif resp.status_code == 429:
            print(f"  USDA: RATE LIMITED (DEMO_KEY: 30/hour)")
            break
        else:
            print(f"  USDA: HTTP {resp.status_code}")
    except Exception as e:
        print(f"  USDA: ERROR - {e}")

    time.sleep(2)  # Respect rate limits

print("\n" + "=" * 70)
print("DONE — Review the output above")
print("=" * 70)
