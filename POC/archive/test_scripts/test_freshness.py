"""
Test data freshness — how recent are updates across all sources?
"""
import requests
import json
from datetime import datetime, timezone

HEADERS = {"User-Agent": "DAMG7245-BigData/1.0 - academic project"}

# ============================================================
# 1. Open Food Facts — Recent changes
# ============================================================
print("=" * 70)
print("1. OPEN FOOD FACTS — How recent are edits?")
print("=" * 70)

# Get recently modified products
url = "https://world.openfoodfacts.org/api/v2/search?sort_by=last_modified_t&page_size=20&fields=code,product_name,brands,last_modified_t,creator,last_editor"
try:
    resp = requests.get(url, timeout=15, headers=HEADERS)
    if resp.status_code == 200:
        products = resp.json().get("products", [])
        print(f"  Latest {len(products)} modified products:")
        for p in products[:20]:
            ts = p.get("last_modified_t", 0)
            if ts:
                dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                age = datetime.now(timezone.utc) - dt
                print(f"    {dt.strftime('%Y-%m-%d %H:%M UTC')} ({age.days}d {age.seconds//3600}h ago) | '{p.get('product_name', 'N/A')}' | editor={p.get('last_editor', '?')}")
    else:
        print(f"  HTTP {resp.status_code}")
except Exception as e:
    print(f"  ERROR: {e}")

# Check the changes/updates endpoint
print(f"\n  --- OFF Changes Stream (last 10 changes) ---")
url = "https://world.openfoodfacts.org/api/v2/search?sort_by=last_modified_t&page_size=10&fields=code,product_name,last_modified_t,last_editor"
try:
    resp = requests.get(url, timeout=15, headers=HEADERS)
    if resp.status_code == 200:
        products = resp.json().get("products", [])
        if products:
            newest = datetime.fromtimestamp(products[0].get("last_modified_t", 0), tz=timezone.utc)
            oldest = datetime.fromtimestamp(products[-1].get("last_modified_t", 0), tz=timezone.utc)
            print(f"  Most recent edit: {newest.strftime('%Y-%m-%d %H:%M UTC')}")
            print(f"  10th most recent: {oldest.strftime('%Y-%m-%d %H:%M UTC')}")
            diff = newest - oldest
            print(f"  Time span of last 10 edits: {diff.total_seconds()/60:.1f} minutes")
            print(f"  → Estimated edit rate: ~{10/(diff.total_seconds()/60):.1f} edits per minute")
    else:
        print(f"  HTTP {resp.status_code}")
except Exception as e:
    print(f"  ERROR: {e}")

# Check bulk dump freshness
print(f"\n  --- OFF Bulk Dump ---")
url = "https://static.openfoodfacts.org/data/delta/index.txt"
try:
    resp = requests.get(url, timeout=15, headers=HEADERS)
    if resp.status_code == 200:
        lines = resp.text.strip().split("\n")
        print(f"  Available delta files: {len(lines)}")
        print(f"  Latest deltas:")
        for line in lines[-5:]:
            print(f"    {line}")
    else:
        print(f"  HTTP {resp.status_code}")
except Exception as e:
    print(f"  ERROR: {e}")

print()

# ============================================================
# 2. USDA — How fresh is the data?
# ============================================================
print("=" * 70)
print("2. USDA FoodData Central — How recent?")
print("=" * 70)

USDA_KEY = "gZJUqbshltC7qfQ9lk0meZcMJjazosPLfPVnEbgF"

# Get most recently published branded foods
url = f"https://api.nal.usda.gov/fdc/v1/foods/search?api_key={USDA_KEY}&query=*&dataType=Branded&pageSize=10&sortBy=publishedDate&sortOrder=desc"
try:
    resp = requests.get(url, timeout=15)
    if resp.status_code == 200:
        data = resp.json()
        print(f"  Total branded foods in USDA: {data.get('totalHits', '?')}")
        foods = data.get("foods", [])
        print(f"\n  Most recently published:")
        for f in foods[:10]:
            print(f"    {f.get('publishedDate', '?')} | '{f.get('description', '')[:50]}' | {f.get('brandOwner', '')}")
    else:
        print(f"  HTTP {resp.status_code}: {resp.text[:200]}")
except Exception as e:
    print(f"  ERROR: {e}")

print()

# ============================================================
# 3. openFDA — How recent are recalls?
# ============================================================
print("=" * 70)
print("3. openFDA Recalls — How recent?")
print("=" * 70)

url = "https://api.fda.gov/food/enforcement.json?limit=10&sort=report_date:desc"
try:
    resp = requests.get(url, timeout=15)
    if resp.status_code == 200:
        results = resp.json().get("results", [])
        print(f"  Most recent recalls:")
        for r in results[:10]:
            report = r.get("report_date", "?")
            initiation = r.get("recall_initiation_date", "?")
            firm = r.get("recalling_firm", "")
            desc = r.get("product_description", "")[:60]
            print(f"    Report: {report} | Initiated: {initiation} | {firm} | {desc}")
    else:
        print(f"  HTTP {resp.status_code}")
except Exception as e:
    print(f"  ERROR: {e}")

print()

# ============================================================
# 4. Open Prices — How recent?
# ============================================================
print("=" * 70)
print("4. Open Prices — How recent?")
print("=" * 70)

url = "https://prices.openfoodfacts.org/api/v1/prices?order_by=-created&size=10"
try:
    resp = requests.get(url, timeout=15, headers=HEADERS)
    if resp.status_code == 200:
        data = resp.json()
        items = data.get("items", data.get("results", []))
        total = data.get("total", "?")
        print(f"  Total price entries: {total}")
        print(f"\n  Most recent price entries:")
        for item in items[:10]:
            created = item.get("created", "?")
            price = item.get("price", "?")
            currency = item.get("currency", "?")
            code = item.get("product_code", "?")
            product = item.get("product", {}) or {}
            name = product.get("product_name", "?")
            print(f"    {created} | {price} {currency} | barcode={code} | '{name}'")
    else:
        print(f"  HTTP {resp.status_code}")
except Exception as e:
    print(f"  ERROR: {e}")

print()
print("=" * 70)
print("FRESHNESS VERDICT")
print("=" * 70)
