"""
Final verification — Can we actually download and parse all 6 data sources?
"""
import requests
import json
import gzip
import os
import time

HEADERS = {"User-Agent": "DAMG7245-BigData/1.0 - academic project"}
OUTPUT_DIR = "data_samples"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================
# 1. OPEN FOOD FACTS — Bulk dump download test
# ============================================================
print("=" * 70)
print("1. OPEN FOOD FACTS — Bulk dump verification")
print("=" * 70)

# Check what bulk files are available
print("\n  a) Checking available bulk downloads...")
urls_to_check = [
    ("Full CSV (gz)", "https://static.openfoodfacts.org/data/en.openfoodfacts.org.products.csv.gz"),
    ("Full JSONL (gz)", "https://static.openfoodfacts.org/data/openfoodfacts-products.jsonl.gz"),
    ("Delta index", "https://static.openfoodfacts.org/data/delta/index.txt"),
    ("Parquet (HuggingFace)", "https://huggingface.co/api/datasets/openfoodfacts/product-database"),
]

for name, url in urls_to_check:
    try:
        resp = requests.head(url, timeout=15, headers=HEADERS, allow_redirects=True)
        size = resp.headers.get("Content-Length", "unknown")
        content_type = resp.headers.get("Content-Type", "unknown")
        if size != "unknown":
            size_gb = int(size) / (1024**3)
            print(f"  {name:30s}: {resp.status_code} | {size_gb:.2f} GB | {content_type}")
        else:
            print(f"  {name:30s}: {resp.status_code} | size unknown | {content_type}")
    except Exception as e:
        print(f"  {name:30s}: ERROR - {e}")

# Download first 5MB of the CSV to verify it parses
print("\n  b) Downloading first 5MB of CSV dump to verify format...")
url = "https://static.openfoodfacts.org/data/en.openfoodfacts.org.products.csv.gz"
try:
    resp = requests.get(url, timeout=30, headers={**HEADERS, "Range": "bytes=0-5242880"}, stream=True)
    print(f"  Status: {resp.status_code}")

    chunk_path = f"{OUTPUT_DIR}/off_bulk_sample.csv.gz"
    with open(chunk_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    file_size = os.path.getsize(chunk_path)
    print(f"  Downloaded: {file_size/1024:.0f} KB")

    # Try to decompress and read first lines
    try:
        import gzip
        with gzip.open(chunk_path, "rt", encoding="utf-8", errors="replace") as f:
            lines = []
            for i, line in enumerate(f):
                lines.append(line)
                if i >= 20:
                    break

        if lines:
            # Parse header
            header = lines[0].strip().split("\t")
            print(f"  Format: TSV (tab-separated)")
            print(f"  Columns: {len(header)}")
            print(f"  First 20 column names: {header[:20]}")

            # Check key columns exist
            key_cols = ["code", "product_name", "brands", "categories", "ingredients_text",
                        "nutrition_grades", "completeness", "last_modified_t"]
            found = [c for c in key_cols if c in header]
            missing = [c for c in key_cols if c not in header]
            print(f"\n  Key columns found: {found}")
            if missing:
                print(f"  Key columns MISSING: {missing}")

            # Show a few data rows
            print(f"\n  Sample rows:")
            for line in lines[1:4]:
                fields = line.strip().split("\t")
                # Show code, product_name, brands
                code_idx = header.index("code") if "code" in header else 0
                name_idx = header.index("product_name") if "product_name" in header else 1
                brand_idx = header.index("brands") if "brands" in header else 2
                print(f"    code={fields[code_idx][:20]} | name={fields[name_idx][:40]} | brand={fields[brand_idx][:30]}")
        else:
            print("  Could not read lines from gzip")
    except Exception as e:
        print(f"  Parse error: {e}")
except Exception as e:
    print(f"  Download error: {e}")

# Test delta files (for Kafka streaming)
print("\n  c) Testing delta files (for continuous streaming)...")
try:
    resp = requests.get("https://static.openfoodfacts.org/data/delta/index.txt", timeout=10, headers=HEADERS)
    if resp.status_code == 200:
        delta_files = resp.text.strip().split("\n")
        print(f"  Available delta files: {len(delta_files)}")
        latest = delta_files[-1]
        print(f"  Latest delta: {latest}")

        # Download latest delta to check format
        delta_url = f"https://static.openfoodfacts.org/data/delta/{latest}"
        print(f"  Downloading latest delta...")
        resp = requests.get(delta_url, timeout=30, headers=HEADERS, stream=True)
        delta_path = f"{OUTPUT_DIR}/off_latest_delta.json.gz"
        total = 0
        with open(delta_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                total += len(chunk)
                if total > 2 * 1024 * 1024:  # Stop at 2MB
                    break

        print(f"  Downloaded: {total/1024:.0f} KB")

        # Parse delta
        try:
            with gzip.open(delta_path, "rt", encoding="utf-8") as f:
                delta_products = []
                for i, line in enumerate(f):
                    try:
                        product = json.loads(line)
                        delta_products.append(product)
                    except:
                        pass
                    if i >= 50:
                        break

            print(f"  Products in delta sample: {len(delta_products)}")
            if delta_products:
                p = delta_products[0]
                print(f"  Sample delta product keys: {list(p.keys())[:15]}")
                print(f"  Name: {p.get('product_name', 'N/A')}")
                print(f"  Brand: {p.get('brands', 'N/A')}")
                print(f"  Last modified: {p.get('last_modified_t', 'N/A')}")

                # Check how recent
                from datetime import datetime, timezone
                ts = p.get("last_modified_t", 0)
                if ts:
                    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                    age = datetime.now(timezone.utc) - dt
                    print(f"  Modified: {dt.strftime('%Y-%m-%d %H:%M UTC')} ({age.days}d ago)")
        except Exception as e:
            print(f"  Delta parse error: {e}")
except Exception as e:
    print(f"  Delta check error: {e}")

print("\n")

# ============================================================
# 2. USDA FoodData Central — Bulk download test
# ============================================================
print("=" * 70)
print("2. USDA FoodData Central — Bulk download verification")
print("=" * 70)

USDA_KEY = "gZJUqbshltC7qfQ9lk0meZcMJjazosPLfPVnEbgF"

# Check bulk download page
print("\n  a) Checking USDA bulk downloads...")
# USDA provides bulk CSV downloads
usda_bulk_urls = [
    ("Branded Foods CSV", "https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_branded_food_csv_2024-10-31.zip"),
    ("Full Download CSV", "https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_csv_2024-10-31.zip"),
]

for name, url in usda_bulk_urls:
    try:
        resp = requests.head(url, timeout=15, allow_redirects=True)
        size = resp.headers.get("Content-Length", "unknown")
        if size != "unknown":
            size_mb = int(size) / (1024**2)
            print(f"  {name:30s}: {resp.status_code} | {size_mb:.1f} MB")
        else:
            print(f"  {name:30s}: {resp.status_code} | size unknown")
    except Exception as e:
        print(f"  {name:30s}: ERROR - {e}")

# Verify API works with our key for incremental updates
print("\n  b) Verifying API for incremental updates...")
url = f"https://api.nal.usda.gov/fdc/v1/foods/search?api_key={USDA_KEY}&query=*&dataType=Branded&pageSize=5&sortBy=publishedDate&sortOrder=desc"
try:
    resp = requests.get(url, timeout=15)
    if resp.status_code == 200:
        data = resp.json()
        total = data.get("totalHits", 0)
        foods = data.get("foods", [])
        print(f"  Total branded foods: {total:,}")
        print(f"  Most recent publication dates:")
        for f in foods[:5]:
            print(f"    {f.get('publishedDate', '?')} | '{f.get('description', '')[:50]}'")
    else:
        print(f"  HTTP {resp.status_code}")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n")

# ============================================================
# 3. AMAZON ESCI — Full dataset access test
# ============================================================
print("=" * 70)
print("3. AMAZON ESCI — Full dataset verification")
print("=" * 70)

# Check HuggingFace dataset
print("\n  a) Checking HuggingFace dataset info...")
url = "https://huggingface.co/api/datasets/tasksource/esci"
try:
    resp = requests.get(url, timeout=10)
    if resp.status_code == 200:
        info = resp.json()
        print(f"  ID: {info.get('id')}")
        print(f"  License: {info.get('cardData', {}).get('license', 'N/A')}")
        print(f"  Downloads: {info.get('downloads', 'N/A')}")
except:
    pass

# Check dataset size/splits
print("\n  b) Checking dataset splits and sizes...")
url = "https://datasets-server.huggingface.co/info?dataset=tasksource/esci"
try:
    resp = requests.get(url, timeout=10)
    if resp.status_code == 200:
        info = resp.json()
        dataset_info = info.get("dataset_info", {})
        for config_name, config_data in dataset_info.items():
            splits = config_data.get("splits", {})
            print(f"  Config: {config_name}")
            for split_name, split_data in splits.items():
                num = split_data.get("num_examples", "?")
                size = split_data.get("num_bytes", 0)
                print(f"    {split_name}: {num:,} rows ({size/(1024**2):.1f} MB)" if isinstance(num, int) else f"    {split_name}: {num} rows")
    else:
        print(f"  HTTP {resp.status_code}")
except Exception as e:
    print(f"  ERROR: {e}")

# Fetch sample rows and verify structure
print("\n  c) Verifying data structure...")
url = "https://datasets-server.huggingface.co/rows?dataset=tasksource/esci&config=default&split=train&offset=0&length=5"
try:
    resp = requests.get(url, timeout=10)
    if resp.status_code == 200:
        rows = resp.json().get("rows", [])
        if rows:
            first = rows[0].get("row", {})
            print(f"  Columns: {list(first.keys())}")

            # Count label distribution in a larger sample
            url2 = "https://datasets-server.huggingface.co/rows?dataset=tasksource/esci&config=default&split=train&offset=0&length=100"
            resp2 = requests.get(url2, timeout=15)
            if resp2.status_code == 200:
                rows2 = resp2.json().get("rows", [])
                labels = Counter()
                queries = set()
                has_title = 0
                has_desc = 0
                for r in rows2:
                    row = r.get("row", {})
                    labels[row.get("esci_label", "?")] += 1
                    queries.add(row.get("query", ""))
                    if row.get("product_title"):
                        has_title += 1
                    if row.get("product_description"):
                        has_desc += 1

                print(f"\n  In 100 sample rows:")
                print(f"    Label distribution: {dict(labels)}")
                print(f"    Unique queries: {len(queries)}")
                print(f"    Has product_title: {has_title}/100")
                print(f"    Has product_description: {has_desc}/100")
except Exception as e:
    print(f"  ERROR: {e}")

# Check the original GitHub repo
print("\n  d) Checking original GitHub repo...")
url = "https://api.github.com/repos/amazon-science/esci-data"
try:
    resp = requests.get(url, timeout=10)
    if resp.status_code == 200:
        repo = resp.json()
        print(f"  Repo: {repo.get('full_name')}")
        print(f"  Stars: {repo.get('stargazers_count')}")
        print(f"  Last updated: {repo.get('updated_at')}")
        print(f"  License: {repo.get('license', {}).get('name', 'N/A')}")
except:
    pass

print("\n")

# ============================================================
# 4. INSTACART — Kaggle availability check
# ============================================================
print("=" * 70)
print("4. INSTACART MARKET BASKET — Availability verification")
print("=" * 70)

print("""
  Dataset: Instacart Market Basket Analysis
  URL: https://www.kaggle.com/c/instacart-market-basket-analysis/data
  Alt: https://www.kaggle.com/datasets/psparks/instacart-market-basket-analysis

  Download method: Kaggle CLI or manual download (requires free Kaggle account)
    $ pip install kaggle
    $ kaggle competitions download -c instacart-market-basket-analysis

  OR download from: https://www.instacart.com/datasets/grocery-shopping-2017
""")

# Check if Instacart's own site has the data
print("  Checking Instacart direct download...")
url = "https://www.instacart.com/datasets/grocery-shopping-2017"
try:
    resp = requests.head(url, timeout=10, allow_redirects=True)
    print(f"  Instacart direct: HTTP {resp.status_code} (final URL: {resp.url[:80]})")
except Exception as e:
    print(f"  Instacart direct: {e}")

# Check Kaggle dataset page
print("\n  Checking Kaggle...")
url = "https://www.kaggle.com/datasets/psparks/instacart-market-basket-analysis"
try:
    resp = requests.head(url, timeout=10, allow_redirects=True)
    print(f"  Kaggle page: HTTP {resp.status_code}")
except Exception as e:
    print(f"  Kaggle: {e}")

print("""
  FILES YOU'LL DOWNLOAD:
    orders.csv              — 3.4M rows (order_id, user_id, order_dow, order_hour, days_since_prior)
    products.csv            — 49,688 rows (product_id, product_name, aisle_id, department_id)
    aisles.csv              — 134 rows
    departments.csv         — 21 rows
    order_products__train.csv  — 1.38M rows
    order_products__prior.csv  — 32.4M rows (this is the big one)

  TOTAL SIZE: ~1.1 GB uncompressed
""")

print("\n")

# ============================================================
# 5. openFDA — Already verified (100% working)
# ============================================================
print("=" * 70)
print("5. openFDA — Quick re-verification")
print("=" * 70)

url = "https://api.fda.gov/food/enforcement.json?limit=1"
try:
    resp = requests.get(url, timeout=10)
    total = resp.json().get("meta", {}).get("results", {}).get("total", "?")
    print(f"  Status: {resp.status_code}")
    print(f"  Total recall records available: {total}")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n")

# ============================================================
# 6. OPEN PRICES — Already verified (working)
# ============================================================
print("=" * 70)
print("6. Open Prices — Quick re-verification")
print("=" * 70)

url = "https://prices.openfoodfacts.org/api/v1/prices?size=1"
try:
    resp = requests.get(url, timeout=10, headers=HEADERS)
    data = resp.json()
    total = data.get("total", "?")
    print(f"  Status: {resp.status_code}")
    print(f"  Total price entries: {total}")
except Exception as e:
    print(f"  ERROR: {e}")

# Check HuggingFace bulk
url = "https://huggingface.co/api/datasets/openfoodfacts/open-prices"
try:
    resp = requests.get(url, timeout=10)
    if resp.status_code == 200:
        print(f"  HuggingFace bulk: available (ID: {resp.json().get('id')})")
except:
    pass

print("\n")

# ============================================================
# FINAL VERIFICATION SUMMARY
# ============================================================
print("=" * 70)
print("FINAL VERIFICATION SUMMARY")
print("=" * 70)
print("""
  Source                  | Bulk Download | API Access | Parse OK | Verdict
  ------------------------|--------------|------------|----------|--------
""")
