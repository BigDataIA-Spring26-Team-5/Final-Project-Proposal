"""
Fetch sample data from all 4 sources and save as CSVs
"""
import requests
import pandas as pd
import json
import time
import os

OUTPUT_DIR = "data_samples"
os.makedirs(OUTPUT_DIR, exist_ok=True)

HEADERS = {"User-Agent": "DAMG7245-BigData/1.0 - academic project"}

# ============================================================
# 1. OPEN FOOD FACTS — Barcode lookups for known US products
# ============================================================
print("=" * 70)
print("1. OPEN FOOD FACTS — Fetching products by barcode")
print("=" * 70)

# Known US product barcodes
barcodes = [
    "0016000275287", "0016000487925", "0016000124325",  # General Mills: Cheerios, Lucky Charms, Cinnamon Toast
    "0044000032159", "0044000000745", "0044000031022",  # Mondelez: Oreo, Ritz, Chips Ahoy
    "0049000006346", "0049000042566", "0049000028911",  # Coca-Cola variants
    "0028400028738", "0028400064057", "0028400090988",  # Frito-Lay: Doritos, Lays, Tostitos
    "0009800895007", "0009800800124",                    # Nutella
    "0037600109826", "0037600107792",                    # Skippy
    "0013000006040", "0013000001243",                    # Heinz
    "0818290014313", "0818290014214",                    # Chobani
    "0722252100900", "0722252101204",                    # Clif Bar
    "0038000138416", "0038000199578",                    # Kellogg's
    "0030000311707", "0030000560310",                    # Quaker
    "0041196910797",                                      # Store brand
    "0078742370880", "0078742011523",                    # Great Value (Walmart)
    "0011110038364", "0011110901378",                    # Kroger
    "0021130126026",                                      # Signature Select
    "0041318020571", "0041318020717",                    # Barilla
    "0051000012517", "0051000237828",                    # Campbell's
    "0041331092470", "0041331021579",                    # Nature's Own
    "0012000001536", "0012000204029",                    # Pepsi
    "0040000427933", "0040000495451",                    # M&M's / Mars
    "0034000003204", "0034000140244",                    # Hershey's
    "0036800109667", "0036800454538",                    # Goya
    "0888109010003", "0888109010010",                    # Banza pasta
    "0052200004173", "0052200070840",                    # Green Giant
    "0027400002076", "0027400004759",                    # Frito-Lay
    "0041498169503", "0041498112653",                    # Annie's
    "0016000153899", "0016000439887",                    # Betty Crocker
    "0076183003626", "0076183644101",                    # Justin's
    "0021000658831", "0021000015078",                    # Kraft
    "0017000335452", "0017000335025",                    # Smucker's
    "0014100096832", "0014100044437",                    # Pepperidge Farm
    "0041570054291", "0041570052747",                    # Prego
    "0070662007099", "0070662006795",                    # Deep Indian Kitchen
    "0085239017180",                                      # RXBAR
    "0853152100315",                                      # HIPPEAS
    "0829696000626",                                      # Siete Foods
]

off_products = []
for i, barcode in enumerate(barcodes):
    url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
    try:
        resp = requests.get(url, timeout=10, headers=HEADERS)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == 1:
                p = data["product"]
                off_products.append({
                    "barcode": p.get("code", barcode),
                    "product_name": p.get("product_name", ""),
                    "brands": p.get("brands", ""),
                    "categories": p.get("categories", ""),
                    "ingredients_text": p.get("ingredients_text", ""),
                    "quantity": p.get("quantity", ""),
                    "nutrition_grades": p.get("nutrition_grades", ""),
                    "nutriscore_score": p.get("nutriscore_score", ""),
                    "nova_group": p.get("nova_group", ""),
                    "ecoscore_grade": p.get("ecoscore_grade", ""),
                    "image_url": p.get("image_url", ""),
                    "allergens": p.get("allergens", ""),
                    "labels": p.get("labels", ""),
                    "stores": p.get("stores", ""),
                    "countries": p.get("countries", ""),
                    "completeness": p.get("completeness", ""),
                    "last_modified_t": p.get("last_modified_t", ""),
                })
    except:
        pass

    if (i + 1) % 20 == 0:
        print(f"  Fetched {i+1}/{len(barcodes)} barcodes... ({len(off_products)} found)")
    time.sleep(0.3)

print(f"\n  Total OFF products: {len(off_products)}")
if off_products:
    off_df = pd.DataFrame(off_products)
    off_df.to_csv(f"{OUTPUT_DIR}/open_food_facts_sample.csv", index=False)
    print(f"  Saved: {OUTPUT_DIR}/open_food_facts_sample.csv")

    # Quick stats
    print(f"\n  --- Field Coverage ---")
    for col in off_df.columns:
        non_empty = off_df[col].notna() & (off_df[col].astype(str).str.strip() != "")
        pct = non_empty.sum() / len(off_df) * 100
        print(f"  {col:25s}: {pct:5.1f}%")

print("\n")

# ============================================================
# 2. USDA FoodData Central — Using search for same products
# ============================================================
print("=" * 70)
print("2. USDA — Fetching branded foods (using DEMO_KEY, may be rate limited)")
print("=" * 70)

usda_products = []
search_terms = [
    "cheerios", "oreo", "coca cola", "doritos", "nutella",
    "skippy", "heinz ketchup", "chobani", "clif bar", "frosted flakes",
    "quaker oats", "barilla pasta", "campbell soup", "pepsi",
    "m&m", "hershey", "goya beans", "green giant", "kraft cheese",
    "smucker", "pepperidge farm", "prego sauce", "rxbar", "kind bar",
    "annie organic", "betty crocker", "great value cereal", "kroger",
    "nature own bread", "justin peanut", "ritz crackers", "chips ahoy",
    "tostitos", "lays chips", "lucky charms"
]

for term in search_terms:
    url = f"https://api.nal.usda.gov/fdc/v1/foods/search?api_key=gZJUqbshltC7qfQ9lk0meZcMJjazosPLfPVnEbgF&query={term}&dataType=Branded&pageSize=5"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            foods = resp.json().get("foods", [])
            for f in foods:
                usda_products.append({
                    "fdc_id": f.get("fdcId", ""),
                    "description": f.get("description", ""),
                    "brand_owner": f.get("brandOwner", ""),
                    "brand_name": f.get("brandName", ""),
                    "gtin_upc": f.get("gtinUpc", ""),
                    "ingredients": f.get("ingredients", ""),
                    "food_category": f.get("foodCategory", ""),
                    "serving_size": f.get("servingSize", ""),
                    "serving_size_unit": f.get("servingSizeUnit", ""),
                    "published_date": f.get("publishedDate", ""),
                    "market_country": f.get("marketCountry", ""),
                    "data_source": f.get("dataSource", ""),
                    "search_term": term,
                })
            print(f"  '{term}': {len(foods)} results")
        elif resp.status_code == 429:
            print(f"  '{term}': RATE LIMITED — stopping USDA fetch")
            print(f"  Register for free API key at: https://fdc.nal.usda.gov/api-key-signup")
            break
        else:
            print(f"  '{term}': HTTP {resp.status_code}")
    except Exception as e:
        print(f"  '{term}': ERROR - {e}")
    time.sleep(1)

print(f"\n  Total USDA products: {len(usda_products)}")
if usda_products:
    usda_df = pd.DataFrame(usda_products)
    usda_df.to_csv(f"{OUTPUT_DIR}/usda_fooddata_sample.csv", index=False)
    print(f"  Saved: {OUTPUT_DIR}/usda_fooddata_sample.csv")

    print(f"\n  --- Field Coverage ---")
    for col in usda_df.columns:
        non_empty = usda_df[col].notna() & (usda_df[col].astype(str).str.strip() != "")
        pct = non_empty.sum() / len(usda_df) * 100
        print(f"  {col:25s}: {pct:5.1f}%")

print("\n")

# ============================================================
# 3. openFDA Food Recalls
# ============================================================
print("=" * 70)
print("3. openFDA — Fetching 500 food recall records")
print("=" * 70)

fda_records = []
for skip in range(0, 500, 100):
    url = f"https://api.fda.gov/food/enforcement.json?limit=100&skip={skip}"
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            for r in results:
                fda_records.append({
                    "recall_number": r.get("recall_number", ""),
                    "product_description": r.get("product_description", ""),
                    "reason_for_recall": r.get("reason_for_recall", ""),
                    "recalling_firm": r.get("recalling_firm", ""),
                    "classification": r.get("classification", ""),
                    "status": r.get("status", ""),
                    "voluntary_mandated": r.get("voluntary_mandated", ""),
                    "distribution_pattern": r.get("distribution_pattern", ""),
                    "code_info": r.get("code_info", ""),
                    "product_type": r.get("product_type", ""),
                    "city": r.get("city", ""),
                    "state": r.get("state", ""),
                    "country": r.get("country", ""),
                    "recall_initiation_date": r.get("recall_initiation_date", ""),
                    "center_classification_date": r.get("center_classification_date", ""),
                    "report_date": r.get("report_date", ""),
                    "event_id": r.get("event_id", ""),
                })
            print(f"  Batch {skip//100 + 1}: {len(results)} records (total: {len(fda_records)})")
        else:
            print(f"  Batch {skip//100 + 1}: HTTP {resp.status_code}")
    except Exception as e:
        print(f"  Batch {skip//100 + 1}: ERROR - {e}")
    time.sleep(0.5)

print(f"\n  Total FDA records: {len(fda_records)}")
if fda_records:
    fda_df = pd.DataFrame(fda_records)
    fda_df.to_csv(f"{OUTPUT_DIR}/fda_recalls_sample.csv", index=False)
    print(f"  Saved: {OUTPUT_DIR}/fda_recalls_sample.csv")

    print(f"\n  --- Field Coverage ---")
    for col in fda_df.columns:
        non_empty = fda_df[col].notna() & (fda_df[col].astype(str).str.strip() != "")
        pct = non_empty.sum() / len(fda_df) * 100
        print(f"  {col:25s}: {pct:5.1f}%")

print("\n")

# ============================================================
# 4. Open Prices
# ============================================================
print("=" * 70)
print("4. Open Prices — Fetching recent prices")
print("=" * 70)

price_records = []
for page in range(1, 6):
    url = f"https://prices.openfoodfacts.org/api/v1/prices?page={page}&size=100"
    try:
        resp = requests.get(url, timeout=15, headers=HEADERS)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("items", data.get("results", []))
            for item in items:
                product = item.get("product", {}) or {}
                location = item.get("location", {}) or {}
                price_records.append({
                    "price_id": item.get("id", ""),
                    "product_code": item.get("product_code", ""),
                    "price": item.get("price", ""),
                    "price_is_discounted": item.get("price_is_discounted", ""),
                    "price_without_discount": item.get("price_without_discount", ""),
                    "currency": item.get("currency", ""),
                    "date": item.get("date", ""),
                    "receipt_quantity": item.get("receipt_quantity", ""),
                    "product_name": product.get("product_name", ""),
                    "product_brands": product.get("brands", ""),
                    "product_categories": str(product.get("categories_tags", "")),
                    "product_nutriscore": product.get("nutriscore_grade", ""),
                    "product_image_url": product.get("image_url", ""),
                    "store_name": location.get("osm_name", ""),
                    "store_city": location.get("osm_address_city", ""),
                    "store_country": location.get("osm_address_country", ""),
                    "store_lat": location.get("osm_lat", ""),
                    "store_lon": location.get("osm_lon", ""),
                    "created": item.get("created", ""),
                })
            print(f"  Page {page}: {len(items)} prices (total: {len(price_records)})")
        else:
            print(f"  Page {page}: HTTP {resp.status_code}")
    except Exception as e:
        print(f"  Page {page}: ERROR - {e}")
    time.sleep(0.5)

print(f"\n  Total price records: {len(price_records)}")
if price_records:
    price_df = pd.DataFrame(price_records)
    price_df.to_csv(f"{OUTPUT_DIR}/open_prices_sample.csv", index=False)
    print(f"  Saved: {OUTPUT_DIR}/open_prices_sample.csv")

    print(f"\n  --- Field Coverage ---")
    for col in price_df.columns:
        non_empty = price_df[col].notna() & (price_df[col].astype(str).str.strip() != "") & (price_df[col].astype(str) != "nan")
        pct = non_empty.sum() / len(price_df) * 100
        print(f"  {col:25s}: {pct:5.1f}%")

print("\n")

# ============================================================
# SUMMARY
# ============================================================
print("=" * 70)
print("ALL CSVs SAVED")
print("=" * 70)
print(f"  1. {OUTPUT_DIR}/open_food_facts_sample.csv")
print(f"  2. {OUTPUT_DIR}/usda_fooddata_sample.csv")
print(f"  3. {OUTPUT_DIR}/fda_recalls_sample.csv")
print(f"  4. {OUTPUT_DIR}/open_prices_sample.csv")
print()
print("  USDA API key registration: https://fdc.nal.usda.gov/api-key-signup")
