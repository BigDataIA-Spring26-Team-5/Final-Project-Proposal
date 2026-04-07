"""
Balanced EDA script — works on raw AND enriched data.
Usage:
  poetry run python eda.py                                  # raw data
  poetry run python eda.py data/products_enriched.csv      # enriched data
"""

import sys
import pandas as pd
import re

path = sys.argv[1] if len(sys.argv) > 1 else "data/en.openfoodfacts.org.products-1k.csv"
df = pd.read_csv(path)

print("=" * 60)
print(f"FILE : {path}")
print(f"SHAPE: {df.shape[0]} rows x {df.shape[1]} cols")

# --- 1. Null rates (both null and filled) ---
print("\n--- FIELD FILL RATES ---")
print(f"  {'Column':30s} {'Filled':>8} {'Null':>8} {'Fill %':>8}")
print(f"  {'-'*30} {'-'*8} {'-'*8} {'-'*8}")
for col in df.columns:
    filled = df[col].notna().sum()
    null   = df[col].isna().sum()
    pct    = filled / len(df) * 100
    print(f"  {col:30s} {filled:8d} {null:8d} {pct:7.1f}%")

# --- 2. Sample values — both valid and problematic ---
print("\n--- SAMPLE VALUES PER COLUMN (3 valid, 3 null context) ---")
for col in df.columns:
    valid   = df[col].dropna().head(3).tolist()
    null_ct = df[col].isna().sum()
    print(f"  {col:30s} valid={valid}  nulls={null_ct}")

# --- 3. Brand quality —- good and bad ---
print("\n--- BRAND QUALITY ---")
brands = df["brands"]
total = len(brands)
non_null = brands.notna().sum()
null = brands.isna().sum()
padded    = brands.dropna().loc[brands.dropna().str.strip().ne(brands.dropna())].count()
all_caps  = brands.dropna().str.isupper().sum()
clean     = brands.dropna().loc[
    ~brands.dropna().str.isupper() &
    brands.dropna().str.strip().eq(brands.dropna())
].count()

print(f"  Total rows              : {total}")
print(f"  Non-null (filled)       : {non_null} ({non_null/total*100:.1f}%)")
print(f"  Null                    : {null} ({null/total*100:.1f}%)")
print(f"  Clean (no issues found) : {clean} ({clean/total*100:.1f}%)")
print(f"  Whitespace padding      : {padded}")
print(f"  ALL CAPS                : {all_caps}")
print(f"  Unique brand values     : {brands.dropna().nunique()}")
print(f"  Top 5 brands:")
for brand, count in brands.dropna().str.strip().value_counts().head(5).items():
    print(f"    {brand:30s} {count}")

# --- 4. Quantity quality --- good and bad ---
print("\n--- QUANTITY QUALITY ---")
qty_col = "quantity" if "quantity" in df.columns else "quantity_normalized"
qty = df[qty_col]
non_null_qty = qty.dropna()
normalized = non_null_qty[non_null_qty.str.match(r"^\d+(\.\d+)?\s[a-zA-Z ]+$", na=False)]
no_space   = non_null_qty[non_null_qty.str.match(r"^\d+(\.\d+)?[a-zA-Z]+$", na=False)]
all_caps_q = non_null_qty[non_null_qty.str.isupper() & non_null_qty.str.contains(r"[A-Z]{2,}", na=False)]

print(f"  Total rows              : {len(qty)}")
print(f"  Non-null                : {len(non_null_qty)} ({len(non_null_qty)/len(qty)*100:.1f}%)")
print(f"  Null                    : {qty.isna().sum()} ({qty.isna().sum()/len(qty)*100:.1f}%)")
print(f"  Clean normalized        : {len(normalized)} ({len(normalized)/len(qty)*100:.1f}%)")
print(f"  No space (e.g. '500g')  : {len(no_space)}")
print(f"  ALL CAPS (e.g. '500ML') : {len(all_caps_q)}")
print(f"  Sample clean values     : {normalized.head(3).tolist()}")
print(f"  Sample problematic      : {(no_space.tolist() + all_caps_q.tolist())[:3]}")

# --- 5. Product name quality ---
print("\n--- PRODUCT NAME QUALITY ---")
names = df["product_name"]
non_null_n = names.dropna()
lowercase  = non_null_n[non_null_n.str.islower()]
all_caps_n = non_null_n[non_null_n.str.isupper()]
clean_n    = non_null_n[~non_null_n.str.islower() & ~non_null_n.str.isupper()]

print(f"  Total rows              : {len(names)}")
print(f"  Non-null                : {len(non_null_n)} ({len(non_null_n)/len(names)*100:.1f}%)")
print(f"  Null                    : {names.isna().sum()} ({names.isna().sum()/len(names)*100:.1f}%)")
print(f"  Clean (mixed case)      : {len(clean_n)} ({len(clean_n)/len(names)*100:.1f}%)")
print(f"  Forced lowercase        : {len(lowercase)}")
print(f"  ALL CAPS                : {len(all_caps_n)}")
print(f"  Sample clean names      : {clean_n.head(3).tolist()}")
print(f"  Sample lowercase names  : {lowercase.head(3).tolist()}")

# --- 6. Duplicate barcodes ---
print("\n--- DUPLICATE BARCODES ---")
total_codes  = df["code"].notna().sum()
unique_codes = df["code"].nunique()
dup_rows     = df[df.duplicated("code", keep=False)]
print(f"  Total barcodes          : {total_codes}")
print(f"  Unique barcodes         : {unique_codes}")
print(f"  Duplicate rows          : {len(dup_rows)} ({len(dup_rows)/len(df)*100:.1f}%)")
if len(dup_rows) > 0:
    print(f"  Sample duplicate groups:")
    for code, grp in list(dup_rows.groupby("code"))[:2]:
        print(f"    code={code} → {grp['product_name'].tolist()}")

# --- 7. Sparse fields summary ---
print("\n--- SPARSE FIELDS SUMMARY ---")
sparse_cols = ["categories_en", "allergens_en", "labels_en", "ingredients_text_en"]
for col in sparse_cols:
    if col not in df.columns:
        print(f"  {col:30s} (column not present)")
        continue
    filled = df[col].notna().sum()
    null   = df[col].isna().sum()
    print(f"  {col:30s} {filled:4d} filled / {null:4d} null ({filled/len(df)*100:.1f}% coverage)")

# --- 8. DQ completeness score distribution ---
print("\n--- DQ COMPLETENESS SCORE DISTRIBUTION ---")
key_fields = [f for f in
    ["product_name", "brands", "quantity", "quantity_normalized",
     "categories_en", "allergens_en", "ingredients_text_en"]
    if f in df.columns]

df["_completeness"] = df[key_fields].notna().mean(axis=1) * 100
mean_score = df["_completeness"].mean()
median_score = df["_completeness"].median()

print(f"  Fields scored           : {key_fields}")
print(f"  Mean completeness       : {mean_score:.1f} / 100")
print(f"  Median completeness     : {median_score:.1f} / 100")
print(f"  Rows >= 80 (good)       : {(df['_completeness'] >= 80).sum()}")
print(f"  Rows 50–79 (partial)    : {((df['_completeness'] >= 50) & (df['_completeness'] < 80)).sum()}")
print(f"  Rows < 50  (poor)       : {(df['_completeness'] < 50).sum()}")
print(f"\n  Score distribution:")
buckets = pd.cut(df["_completeness"], bins=[0,25,50,75,100],
                 labels=["0-25 (poor)","26-50 (partial)","51-75 (fair)","76-100 (good)"],
                 include_lowest=True)
for bucket, count in buckets.value_counts().sort_index().items():
    bar = "█" * (count // 10)
    print(f"    {str(bucket):20s} {count:4d}  {bar}")