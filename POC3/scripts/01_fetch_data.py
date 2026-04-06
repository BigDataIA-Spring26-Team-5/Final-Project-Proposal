"""
Fetch sample data from all 6 sources and save as CSVs.
Run once: python scripts/01_fetch_data.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import warnings
warnings.filterwarnings("ignore")

import requests
import pandas as pd
import time
import json
from config import (
    DATA_DIR, USDA_API_KEY, OFF_HEADERS, INSTACART_DIR,
    OFF_PRODUCT_COUNT, USDA_PRODUCT_COUNT, FDA_RECALL_COUNT,
    OPEN_PRICES_COUNT, ESCI_SAMPLE_COUNT, INSTACART_ORDER_SAMPLE,
)

# ============================================================
# SOURCE 1: Open Food Facts — 50 messy products
# Strategy: Search by known brand names to get products with
# actual names (not just "Original" or "Pumpkin spice")
# ============================================================
def fetch_off():
    print("=" * 60)
    print("Source 1: Open Food Facts — fetching ~50 US products")
    print("=" * 60)

    products = []

    # Strategy 1: Barcode lookups for known US products
    barcodes = [
        "0016000275287", "0016000487925", "0038000138416", "0030000311707",
        "0028400028738", "0044000032159", "0049000006346", "0012000001536",
        "0009800895007", "0037600109826", "0013000006040", "0021000658831",
        "0034000003204", "0040000427933", "0051000012517", "0041570054291",
        "5449000000996", "3017620422003", "8076809513753", "7622210449283",
        "5000159484695", "3175680011480", "80177173", "3228857000166",
        "8710398527943", "3033710065967", "7613034626844", "5060292302201",
    ]

    fields = "code,product_name,brands,categories,ingredients_text,quantity,nutrition_grades,nutriscore_score,nova_group,ecoscore_grade,completeness,allergens,labels,image_url,stores,countries,last_modified_t"

    print("  Phase 1: Barcode lookups...")
    for barcode in barcodes:
        if len(products) >= OFF_PRODUCT_COUNT:
            break
        url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json?fields={fields}"
        try:
            resp = requests.get(url, timeout=10, headers=OFF_HEADERS)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == 1:
                    p = data["product"]
                    name = p.get("product_name", "")
                    # Skip products with empty or very short names
                    if name and len(name) > 3:
                        products.append(_off_row(p, barcode))
        except:
            pass
        time.sleep(0.4)
    print(f"  Phase 1: {len(products)} products from barcodes")

    # Strategy 2: Search by popular US brand names
    if len(products) < OFF_PRODUCT_COUNT:
        print("  Phase 2: Searching by brand names...")
        brands_to_search = [
            "General Mills", "Kelloggs", "Quaker", "Pepsi", "Coca-Cola",
            "Kraft", "Heinz", "Campbell", "Hershey", "Mars",
            "Barilla", "Nestle", "Danone", "Ferrero", "Unilever",
            "Doritos", "Lays", "Pringles", "Oreo", "Nutella",
        ]
        for brand in brands_to_search:
            if len(products) >= OFF_PRODUCT_COUNT:
                break
            url = f"https://world.openfoodfacts.org/api/v2/search?brands_tags={brand.lower().replace(' ', '-')}&page_size=5&fields={fields}&countries_tags=en:united-states"
            try:
                resp = requests.get(url, timeout=10, headers=OFF_HEADERS)
                if resp.status_code == 200:
                    data = resp.json()
                    for p in data.get("products", []):
                        if len(products) >= OFF_PRODUCT_COUNT:
                            break
                        name = p.get("product_name", "")
                        if name and len(name) > 3:
                            # Avoid duplicates
                            existing_codes = {prod["code"] for prod in products}
                            if p.get("code", "") not in existing_codes:
                                products.append(_off_row(p, p.get("code", "")))
                    print(f"    '{brand}': found {len(data.get('products', []))} (total: {len(products)})")
                elif resp.status_code == 503:
                    print(f"    '{brand}': API 503, trying next...")
            except:
                pass
            time.sleep(0.5)

    # Strategy 3: Browse popular categories
    if len(products) < OFF_PRODUCT_COUNT:
        print("  Phase 3: Browsing categories...")
        categories = [
            "en:breakfast-cereals", "en:chips", "en:sodas", "en:chocolates",
            "en:yogurts", "en:pasta", "en:sauces", "en:biscuits",
            "en:ice-creams", "en:breads", "en:juices", "en:cheeses",
        ]
        for cat in categories:
            if len(products) >= OFF_PRODUCT_COUNT:
                break
            url = f"https://world.openfoodfacts.org/api/v2/search?categories_tags={cat}&page_size=5&fields={fields}"
            try:
                resp = requests.get(url, timeout=10, headers=OFF_HEADERS)
                if resp.status_code == 200:
                    for p in resp.json().get("products", []):
                        if len(products) >= OFF_PRODUCT_COUNT:
                            break
                        name = p.get("product_name", "")
                        if name and len(name) > 3:
                            existing_codes = {prod["code"] for prod in products}
                            if p.get("code", "") not in existing_codes:
                                products.append(_off_row(p, p.get("code", "")))
            except:
                pass
            time.sleep(0.5)

    df = pd.DataFrame(products)
    df.to_csv(DATA_DIR / "off_products.csv", index=False)
    print(f"  TOTAL: Saved {len(df)} Open Food Facts products to data/off_products.csv")
    return df


def _off_row(p, barcode):
    return {
        "code": p.get("code", barcode),
        "product_name": p.get("product_name", ""),
        "brands": p.get("brands", ""),
        "categories": p.get("categories", ""),
        "ingredients_text": p.get("ingredients_text", ""),
        "quantity": p.get("quantity", ""),
        "nutrition_grades": p.get("nutrition_grades", ""),
        "nutriscore_score": p.get("nutriscore_score", ""),
        "nova_group": p.get("nova_group", ""),
        "ecoscore_grade": p.get("ecoscore_grade", ""),
        "completeness": p.get("completeness", ""),
        "allergens": p.get("allergens", ""),
        "labels": p.get("labels", ""),
        "image_url": p.get("image_url", ""),
        "stores": p.get("stores", ""),
        "countries": p.get("countries", ""),
        "last_modified_t": p.get("last_modified_t", ""),
        "source": "off",
    }


# ============================================================
# SOURCE 2: USDA FoodData Central — 50 clean products
# Search for the SAME product types so entity resolution works
# ============================================================
def fetch_usda():
    print("\n" + "=" * 60)
    print("Source 2: USDA FoodData Central — fetching ~50 branded foods")
    print("=" * 60)

    # Search for overlapping products with OFF
    search_terms = [
        "cheerios cereal", "frosted flakes cereal", "quaker oats",
        "oreo cookies", "chips ahoy cookies",
        "coca cola soda", "pepsi cola",
        "nutella spread", "skippy peanut butter",
        "heinz ketchup", "kraft cheese",
        "hershey chocolate", "m&m candy",
        "campbell soup", "prego pasta sauce",
        "barilla pasta", "ragu sauce",
        "doritos chips", "lays potato chips", "pringles chips",
        "chobani yogurt", "dannon yogurt",
        "nature valley granola", "kind bar",
        "wonder bread",
    ]

    products = []
    for term in search_terms:
        if len(products) >= USDA_PRODUCT_COUNT:
            break
        url = f"https://api.nal.usda.gov/fdc/v1/foods/search?api_key={USDA_API_KEY}&query={term}&dataType=Branded&pageSize=3"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                foods = resp.json().get("foods", [])
                for f in foods:
                    if len(products) >= USDA_PRODUCT_COUNT:
                        break
                    # Avoid duplicates
                    existing_ids = {p["fdc_id"] for p in products}
                    if f.get("fdcId") not in existing_ids:
                        products.append({
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
                            "source": "usda",
                        })
                print(f"  '{term}': {len(foods)} results (total: {len(products)})")
            elif resp.status_code == 429:
                print(f"  Rate limited at '{term}' — waiting 60s...")
                time.sleep(60)
        except Exception as e:
            print(f"  '{term}': ERROR - {e}")
        time.sleep(1.5)

    df = pd.DataFrame(products)
    df.to_csv(DATA_DIR / "usda_products.csv", index=False)
    print(f"  TOTAL: Saved {len(df)} USDA products to data/usda_products.csv")
    return df


# ============================================================
# SOURCE 3: openFDA Food Recalls — 100 records
# ============================================================
def fetch_fda():
    print("\n" + "=" * 60)
    print("Source 3: openFDA — fetching 100 food recall records")
    print("=" * 60)

    records = []
    for skip in range(0, FDA_RECALL_COUNT, 100):
        url = f"https://api.fda.gov/food/enforcement.json?limit=100&skip={skip}"
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                for r in results:
                    records.append({
                        "recall_number": r.get("recall_number", ""),
                        "product_description": r.get("product_description", ""),
                        "reason_for_recall": r.get("reason_for_recall", ""),
                        "recalling_firm": r.get("recalling_firm", ""),
                        "classification": r.get("classification", ""),
                        "status": r.get("status", ""),
                        "voluntary_mandated": r.get("voluntary_mandated", ""),
                        "distribution_pattern": r.get("distribution_pattern", ""),
                        "code_info": r.get("code_info", ""),
                        "city": r.get("city", ""),
                        "state": r.get("state", ""),
                        "country": r.get("country", ""),
                        "recall_initiation_date": r.get("recall_initiation_date", ""),
                        "report_date": r.get("report_date", ""),
                    })
                print(f"  Batch {skip//100 + 1}: {len(results)} records (total: {len(records)})")
        except Exception as e:
            print(f"  ERROR: {e}")
        time.sleep(0.5)

    df = pd.DataFrame(records)
    df.to_csv(DATA_DIR / "fda_recalls.csv", index=False)
    print(f"  TOTAL: Saved {len(df)} FDA records to data/fda_recalls.csv")
    return df


# ============================================================
# SOURCE 4: Open Prices — 100 price entries
# ============================================================
def fetch_open_prices():
    print("\n" + "=" * 60)
    print("Source 4: Open Prices — fetching 100 price entries")
    print("=" * 60)

    records = []
    for page in range(1, (OPEN_PRICES_COUNT // 100) + 2):
        if len(records) >= OPEN_PRICES_COUNT:
            break
        url = f"https://prices.openfoodfacts.org/api/v1/prices?page={page}&size=100"
        try:
            resp = requests.get(url, timeout=15, headers=OFF_HEADERS)
            if resp.status_code == 200:
                items = resp.json().get("items", [])
                for item in items:
                    if len(records) >= OPEN_PRICES_COUNT:
                        break
                    product = item.get("product", {}) or {}
                    location = item.get("location", {}) or {}
                    records.append({
                        "price_id": item.get("id", ""),
                        "product_code": item.get("product_code", ""),
                        "price": item.get("price", ""),
                        "price_is_discounted": item.get("price_is_discounted", ""),
                        "price_without_discount": item.get("price_without_discount", ""),
                        "currency": item.get("currency", ""),
                        "date": item.get("date", ""),
                        "product_name": product.get("product_name", ""),
                        "product_brands": product.get("brands", ""),
                        "product_categories": str(product.get("categories_tags", "")),
                        "product_nutriscore": product.get("nutriscore_grade", ""),
                        "store_name": location.get("osm_name", ""),
                        "store_city": location.get("osm_address_city", ""),
                        "store_country": location.get("osm_address_country", ""),
                        "created": item.get("created", ""),
                    })
                print(f"  Page {page}: {len(items)} prices (total: {len(records)})")
        except Exception as e:
            print(f"  Page {page}: ERROR - {e}")
        time.sleep(0.5)

    df = pd.DataFrame(records)
    df.to_csv(DATA_DIR / "open_prices.csv", index=False)
    print(f"  TOTAL: Saved {len(df)} prices to data/open_prices.csv")
    return df


# ============================================================
# SOURCE 5: Amazon ESCI — 500 query-product pairs
# ============================================================
def fetch_esci():
    print("\n" + "=" * 60)
    print("Source 5: Amazon ESCI — fetching 500 query-product pairs")
    print("=" * 60)

    rows = []
    batch_size = 100
    # Sample from different parts of the dataset for diversity
    # (first 500 rows are all bathroom fans — not representative)
    offsets = [0, 5000, 15000, 50000, 100000]
    for offset in offsets:
        if len(rows) >= ESCI_SAMPLE_COUNT:
            break
        url = f"https://datasets-server.huggingface.co/rows?dataset=tasksource/esci&config=default&split=train&offset={offset}&length={batch_size}"
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                data = resp.json().get("rows", [])
                for r in data:
                    row = r.get("row", {})
                    rows.append({
                        "query": row.get("query", ""),
                        "product_id": row.get("product_id", ""),
                        "product_title": row.get("product_title", ""),
                        "product_description": str(row.get("product_description", ""))[:500],
                        "product_brand": row.get("product_brand", ""),
                        "esci_label": row.get("esci_label", ""),
                        "product_locale": row.get("product_locale", ""),
                    })
                print(f"  Offset {offset}: {len(data)} rows (total: {len(rows)})")
            else:
                print(f"  Offset {offset}: HTTP {resp.status_code}")
        except Exception as e:
            print(f"  Offset {offset}: ERROR - {e}")
        time.sleep(0.5)

    df = pd.DataFrame(rows)
    df.to_csv(DATA_DIR / "esci_sample.csv", index=False)
    print(f"  TOTAL: Saved {len(df)} ESCI pairs to data/esci_sample.csv")
    return df


# ============================================================
# SOURCE 6: Instacart — sample 10K orders
# ============================================================
def fetch_instacart():
    print("\n" + "=" * 60)
    print("Source 6: Instacart — sampling 10K orders")
    print("=" * 60)

    orders = pd.read_csv(INSTACART_DIR / "orders.csv", usecols=["order_id", "user_id", "order_dow", "order_hour_of_day"])
    products = pd.read_csv(INSTACART_DIR / "products.csv")
    departments = pd.read_csv(INSTACART_DIR / "departments.csv")
    aisles = pd.read_csv(INSTACART_DIR / "aisles.csv")

    sampled_ids = orders["order_id"].sample(n=INSTACART_ORDER_SAMPLE, random_state=42).values
    sampled_set = set(sampled_ids)
    print(f"  Sampled {len(sampled_ids)} order IDs")

    chunks = []
    for chunk in pd.read_csv(INSTACART_DIR / "order_products__prior.csv", chunksize=1_000_000):
        filtered = chunk[chunk["order_id"].isin(sampled_set)]
        if len(filtered) > 0:
            chunks.append(filtered)
        print(f"  Processing... ({sum(len(c) for c in chunks)} rows)", end="\r")

    order_products = pd.concat(chunks, ignore_index=True)
    print(f"\n  Filtered order-product pairs: {len(order_products)}")

    products_full = products.merge(aisles, on="aisle_id").merge(departments, on="department_id")
    baskets = order_products.merge(products_full[["product_id", "product_name", "aisle", "department"]], on="product_id")
    baskets = baskets.merge(orders[["order_id", "order_dow", "order_hour_of_day"]], on="order_id")

    baskets.to_csv(DATA_DIR / "instacart_baskets.csv", index=False)
    products_full.to_csv(DATA_DIR / "instacart_products.csv", index=False)
    departments.to_csv(DATA_DIR / "instacart_departments.csv", index=False)
    print(f"  TOTAL: Saved {len(baskets)} basket rows, {len(products_full)} products, {len(departments)} departments")
    return baskets


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("Fetching data from all 6 sources...\n")
    fetch_off()
    fetch_usda()
    fetch_fda()
    fetch_open_prices()
    fetch_esci()
    fetch_instacart()
    print("\n" + "=" * 60)
    print("ALL DATA FETCHED. Check data/ directory.")
    print("=" * 60)
