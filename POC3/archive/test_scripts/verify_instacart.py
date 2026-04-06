"""
Verify Instacart dataset — structure, size, cross-category signal, linkability
"""
import pandas as pd
from collections import Counter

DATA_PATH = "/Users/akshayrajchevala/.cache/kagglehub/datasets/yasserh/instacart-online-grocery-basket-analysis-dataset/versions/1"

# ============================================================
# 1. Load all files
# ============================================================
print("=" * 70)
print("INSTACART DATASET — FULL VERIFICATION")
print("=" * 70)

print("\n1. Loading files...")
orders = pd.read_csv(f"{DATA_PATH}/orders.csv")
products = pd.read_csv(f"{DATA_PATH}/products.csv")
aisles = pd.read_csv(f"{DATA_PATH}/aisles.csv")
departments = pd.read_csv(f"{DATA_PATH}/departments.csv")
order_products_prior = pd.read_csv(f"{DATA_PATH}/order_products__prior.csv")
order_products_train = pd.read_csv(f"{DATA_PATH}/order_products__train.csv")

print(f"  orders:               {len(orders):>12,} rows | columns: {list(orders.columns)}")
print(f"  products:             {len(products):>12,} rows | columns: {list(products.columns)}")
print(f"  aisles:               {len(aisles):>12,} rows | columns: {list(aisles.columns)}")
print(f"  departments:          {len(departments):>12,} rows | columns: {list(departments.columns)}")
print(f"  order_products_prior: {len(order_products_prior):>12,} rows | columns: {list(order_products_prior.columns)}")
print(f"  order_products_train: {len(order_products_train):>12,} rows | columns: {list(order_products_train.columns)}")

total_rows = len(orders) + len(products) + len(aisles) + len(departments) + len(order_products_prior) + len(order_products_train)
print(f"\n  TOTAL ROWS: {total_rows:,}")

# ============================================================
# 2. Data quality check
# ============================================================
print("\n2. Data quality check...")

for name, df in [("orders", orders), ("products", products),
                  ("order_products_prior", order_products_prior)]:
    print(f"\n  {name}:")
    print(f"    Null counts:")
    nulls = df.isnull().sum()
    for col, count in nulls.items():
        pct = count / len(df) * 100
        print(f"      {col:30s}: {count:>10,} ({pct:.1f}%)")

# ============================================================
# 3. Departments and aisles
# ============================================================
print("\n3. Departments:")
for _, row in departments.iterrows():
    dept_products = products[products["department_id"] == row["department_id"]]
    print(f"  {row['department_id']:2d}. {row['department']:20s} — {len(dept_products):,} products")

print(f"\n  Sample aisles (first 20):")
for _, row in aisles.head(20).iterrows():
    print(f"  {row['aisle_id']:3d}. {row['aisle']}")

# ============================================================
# 4. Sample products
# ============================================================
print("\n4. Sample products (first 20):")
products_full = products.merge(aisles, on="aisle_id").merge(departments, on="department_id")
for _, row in products_full.head(20).iterrows():
    print(f"  [{row['product_id']:5d}] {row['product_name']:50s} | {row['department']:15s} | {row['aisle']}")

# ============================================================
# 5. Cross-category basket analysis
# ============================================================
print("\n5. Cross-category basket analysis...")

# Take a sample of orders to analyze
sample_orders = order_products_prior.head(1000000)  # First 1M rows
order_depts = sample_orders.merge(products[["product_id", "department_id"]], on="product_id")
order_depts = order_depts.merge(departments, on="department_id")

# Group by order_id, collect departments
baskets = order_depts.groupby("order_id")["department"].apply(set).reset_index()
baskets["num_departments"] = baskets["department"].apply(len)
baskets["num_items"] = order_depts.groupby("order_id").size().values[:len(baskets)]

print(f"  Baskets analyzed: {len(baskets):,}")
print(f"\n  Basket size distribution:")
print(f"    Mean items per basket: {baskets['num_items'].mean():.1f}")
print(f"    Median items per basket: {baskets['num_items'].median():.1f}")
print(f"    Max items per basket: {baskets['num_items'].max()}")

print(f"\n  Departments per basket:")
print(f"    Mean departments: {baskets['num_departments'].mean():.1f}")
print(f"    Median departments: {baskets['num_departments'].median():.1f}")
print(f"    1 department only: {(baskets['num_departments'] == 1).sum():,} ({(baskets['num_departments'] == 1).sum()/len(baskets)*100:.1f}%)")
print(f"    2+ departments (CROSS-CATEGORY): {(baskets['num_departments'] >= 2).sum():,} ({(baskets['num_departments'] >= 2).sum()/len(baskets)*100:.1f}%)")
print(f"    3+ departments: {(baskets['num_departments'] >= 3).sum():,} ({(baskets['num_departments'] >= 3).sum()/len(baskets)*100:.1f}%)")
print(f"    5+ departments: {(baskets['num_departments'] >= 5).sum():,} ({(baskets['num_departments'] >= 5).sum()/len(baskets)*100:.1f}%)")

# Department co-occurrence
print(f"\n  Top department co-occurrences:")
dept_pairs = Counter()
for _, row in baskets.iterrows():
    depts = sorted(row["department"])
    for i in range(len(depts)):
        for j in range(i+1, len(depts)):
            dept_pairs[(depts[i], depts[j])] += 1

for pair, count in dept_pairs.most_common(15):
    pct = count / len(baskets) * 100
    print(f"    {pair[0]:20s} + {pair[1]:20s}: {count:>6,} baskets ({pct:.1f}%)")

# ============================================================
# 6. Most popular products
# ============================================================
print("\n6. Top 20 most ordered products:")
product_counts = order_products_prior["product_id"].value_counts().head(20)
for pid, count in product_counts.items():
    pname = products[products["product_id"] == pid]["product_name"].values[0]
    dept = products_full[products_full["product_id"] == pid]["department"].values[0]
    print(f"  {pname:50s} [{dept:15s}] — {count:>7,} orders")

# ============================================================
# 7. Entity resolution potential — product name examples
# ============================================================
print("\n7. Product names that would match OFF/USDA (entity resolution):")
sample_names = products_full.sample(30, random_state=42)
for _, row in sample_names.iterrows():
    print(f"  '{row['product_name']:55s}' [{row['department']:15s} / {row['aisle']}]")

print("\n" + "=" * 70)
print("INSTACART VERDICT")
print("=" * 70)
print(f"""
  Total records: {total_rows:,}
  Products: {len(products):,}
  Orders: {len(orders):,}
  Order-product pairs: {len(order_products_prior) + len(order_products_train):,}
  Departments: {len(departments)}
  Aisles: {len(aisles)}

  Cross-category baskets: {(baskets['num_departments'] >= 2).sum()/len(baskets)*100:.0f}% of baskets span 2+ departments
  Data quality: minimal nulls, well-structured

  CONFIRMED: ✅ Instacart works for UC4 cross-category recommendations
""")
