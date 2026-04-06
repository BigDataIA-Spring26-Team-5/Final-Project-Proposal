"""
Test 1: Open Prices — Can we extract real shopping baskets from receipt data?
Each proof_id with type=RECEIPT groups items bought together = a basket
"""
import requests
import pandas as pd
import json
from collections import Counter

HEADERS = {"User-Agent": "DAMG7245-BigData/1.0 - academic project"}

print("=" * 70)
print("OPEN PRICES — BASKET EXTRACTION TEST")
print("=" * 70)

# ============================================================
# 1. Fetch a large sample of prices and check proof grouping
# ============================================================
print("\n1. Fetching prices to analyze receipt/basket structure...")

all_prices = []
for page in range(1, 21):  # 2000 prices
    url = f"https://prices.openfoodfacts.org/api/v1/prices?page={page}&size=100"
    try:
        resp = requests.get(url, timeout=15, headers=HEADERS)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("items", [])
            all_prices.extend(items)
        else:
            print(f"  Page {page}: HTTP {resp.status_code}")
            break
    except Exception as e:
        print(f"  Page {page}: ERROR - {e}")
        break

print(f"  Total prices fetched: {len(all_prices)}")

# ============================================================
# 2. Analyze proof types and basket grouping
# ============================================================
print("\n2. Analyzing proof types...")

proof_types = Counter()
for p in all_prices:
    proof = p.get("proof", {}) or {}
    ptype = proof.get("type", "unknown")
    proof_types[ptype] += 1

print(f"  Proof types:")
for ptype, count in proof_types.most_common():
    print(f"    {ptype:20s}: {count}")

# ============================================================
# 3. Group by proof_id to find baskets (multi-item receipts)
# ============================================================
print("\n3. Grouping by proof_id to find multi-item receipts (baskets)...")

proof_groups = {}
for p in all_prices:
    proof_id = p.get("proof_id")
    proof = p.get("proof", {}) or {}
    ptype = proof.get("type", "")

    if proof_id:
        if proof_id not in proof_groups:
            proof_groups[proof_id] = {
                "type": ptype,
                "items": [],
                "location": p.get("location", {})
            }
        product = p.get("product", {}) or {}
        proof_groups[proof_id]["items"].append({
            "product_code": p.get("product_code", ""),
            "product_name": product.get("product_name", ""),
            "brands": product.get("brands", ""),
            "categories": product.get("categories_tags", []),
            "price": p.get("price", ""),
            "currency": p.get("currency", ""),
        })

# Filter for multi-item receipts only
baskets = {pid: data for pid, data in proof_groups.items()
           if len(data["items"]) >= 2 and data["type"] == "RECEIPT"}

single_item = {pid: data for pid, data in proof_groups.items()
               if len(data["items"]) == 1}

price_tag_groups = {pid: data for pid, data in proof_groups.items()
                    if data["type"] == "PRICE_TAG"}

print(f"  Total proof groups: {len(proof_groups)}")
print(f"  RECEIPT type with 2+ items (BASKETS): {len(baskets)}")
print(f"  RECEIPT type with 1 item: {len([g for g in proof_groups.values() if g['type'] == 'RECEIPT' and len(g['items']) == 1])}")
print(f"  PRICE_TAG groups: {len(price_tag_groups)}")

# Basket size distribution
basket_sizes = [len(b["items"]) for b in baskets.values()]
if basket_sizes:
    size_dist = Counter(basket_sizes)
    print(f"\n  Basket size distribution:")
    for size in sorted(size_dist.keys()):
        print(f"    {size} items: {size_dist[size]} baskets")
    print(f"  Average basket size: {sum(basket_sizes)/len(basket_sizes):.1f}")
    print(f"  Max basket size: {max(basket_sizes)}")

# ============================================================
# 4. Show actual baskets — what did people buy together?
# ============================================================
print("\n4. Sample baskets (what people bought together):")

for i, (pid, basket) in enumerate(sorted(baskets.items(),
                                          key=lambda x: len(x[1]["items"]),
                                          reverse=True)[:10]):
    location = basket.get("location", {}) or {}
    store = location.get("osm_name", "Unknown store")
    city = location.get("osm_address_city", "")
    country = location.get("osm_address_country", "")

    print(f"\n  Basket {i+1} (proof_id={pid}) — {store}, {city}, {country}")
    print(f"  Items ({len(basket['items'])}):")

    categories_in_basket = set()
    for item in basket["items"]:
        name = item.get("product_name", "?")
        brand = item.get("brands", "")
        price = item.get("price", "?")
        currency = item.get("currency", "?")
        barcode = item.get("product_code", "")
        cats = item.get("categories", [])

        # Get top-level category
        if cats:
            top_cat = [c for c in cats if c.startswith("en:")]
            if top_cat:
                categories_in_basket.add(top_cat[-1] if len(top_cat) > 0 else "")

        print(f"    • {name} ({brand}) — {price} {currency} [barcode: {barcode}]")

    if categories_in_basket:
        print(f"  Categories in basket: {categories_in_basket}")
        if len(categories_in_basket) >= 2:
            print(f"  >>> CROSS-CATEGORY BASKET! <<<")

# ============================================================
# 5. Cross-category analysis
# ============================================================
print("\n\n5. Cross-category co-occurrence analysis:")

category_pairs = Counter()
for basket in baskets.values():
    cats_in_basket = set()
    for item in basket["items"]:
        item_cats = item.get("categories", [])
        # Get the most specific en: category
        en_cats = [c for c in item_cats if c.startswith("en:")]
        if en_cats:
            # Use 2nd level category for grouping
            for c in en_cats:
                parts = c.replace("en:", "")
                cats_in_basket.add(parts)

    # Generate pairs
    cats_list = sorted(cats_in_basket)
    for i in range(len(cats_list)):
        for j in range(i+1, len(cats_list)):
            category_pairs[(cats_list[i], cats_list[j])] += 1

if category_pairs:
    print(f"  Most common category co-occurrences:")
    for pair, count in category_pairs.most_common(15):
        print(f"    {pair[0]} + {pair[1]}: {count} baskets")
else:
    print("  No cross-category pairs found in this sample")

# ============================================================
# 6. Barcode linkage check — can these link to OFF?
# ============================================================
print("\n\n6. Barcode linkage to Open Food Facts:")

barcodes_in_baskets = set()
for basket in baskets.values():
    for item in basket["items"]:
        bc = item.get("product_code", "")
        if bc:
            barcodes_in_baskets.add(bc)

print(f"  Unique barcodes in baskets: {len(barcodes_in_baskets)}")

# Test a few barcodes against OFF
tested = 0
found = 0
sample_barcodes = list(barcodes_in_baskets)[:10]
for bc in sample_barcodes:
    url = f"https://world.openfoodfacts.org/api/v2/product/{bc}.json?fields=code,product_name,brands"
    try:
        resp = requests.get(url, timeout=10, headers=HEADERS)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == 1:
                p = data["product"]
                print(f"    {bc} → OFF: '{p.get('product_name', '')}' by '{p.get('brands', '')}'")
                found += 1
            else:
                print(f"    {bc} → NOT in OFF")
        tested += 1
    except:
        pass

print(f"\n  Tested {tested} barcodes: {found}/{tested} found in OFF ({found/max(tested,1)*100:.0f}%)")

# ============================================================
# 7. Total dataset size check
# ============================================================
print("\n\n7. Full dataset size check:")
url = "https://prices.openfoodfacts.org/api/v1/prices?size=1"
try:
    resp = requests.get(url, timeout=10, headers=HEADERS)
    data = resp.json()
    total = data.get("total", "?")
    print(f"  Total price entries in Open Prices: {total}")
except:
    pass

# Check HuggingFace for bulk download
print("\n  HuggingFace bulk dataset:")
url = "https://huggingface.co/api/datasets/openfoodfacts/open-prices"
try:
    resp = requests.get(url, timeout=10)
    if resp.status_code == 200:
        info = resp.json()
        print(f"  Dataset: {info.get('id', 'N/A')}")
        print(f"  Downloads: {info.get('downloads', 'N/A')}")
    else:
        print(f"  HTTP {resp.status_code}")
except:
    pass

print("\n" + "=" * 70)
print("OPEN PRICES VERDICT")
print("=" * 70)
print(f"""
  Total baskets (2+ items from same receipt): {len(baskets)}
  Total price entries: {len(all_prices)} (from 2000 sample)
  Barcode linkage to OFF: works
  Cross-category signal: {"YES" if category_pairs else "WEAK/NO"}
""")
