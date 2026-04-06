"""
Test 2: RecipeDB + Food.com + RecipeNLG — Can recipes serve as baskets?
Ingredient lists = cross-category co-occurrence patterns
"""
import requests
import json
from collections import Counter

# ============================================================
# 1. Food.com — Test via Kaggle/HuggingFace
# ============================================================
print("=" * 70)
print("1. FOOD.COM (RECIPES + INTERACTIONS) — Testing")
print("=" * 70)

# Check HuggingFace availability
print("\n  Checking HuggingFace...")
url = "https://huggingface.co/api/datasets/Hieu-Pham/food.com-recipes-and-reviews"
try:
    resp = requests.get(url, timeout=10)
    if resp.status_code == 200:
        info = resp.json()
        print(f"  Found: {info.get('id', 'N/A')}")
        print(f"  Downloads: {info.get('downloads', 'N/A')}")
    else:
        print(f"  HTTP {resp.status_code}")
except Exception as e:
    print(f"  ERROR: {e}")

# Try to get sample rows
print("\n  Fetching sample rows...")
url = "https://datasets-server.huggingface.co/rows?dataset=Hieu-Pham/food.com-recipes-and-reviews&config=recipes&split=train&offset=0&length=20"
try:
    resp = requests.get(url, timeout=15)
    if resp.status_code == 200:
        data = resp.json()
        rows = data.get("rows", [])
        if rows:
            first = rows[0].get("row", {})
            print(f"  Columns: {list(first.keys())}")

            print(f"\n  Sample recipes (ingredient lists as baskets):")
            food_categories = {
                "dairy": ["milk", "cheese", "butter", "cream", "yogurt", "sour cream"],
                "protein": ["chicken", "beef", "pork", "fish", "egg", "turkey", "shrimp", "tofu"],
                "grain": ["flour", "bread", "rice", "pasta", "noodle", "oat", "tortilla"],
                "produce": ["onion", "garlic", "tomato", "pepper", "lettuce", "carrot", "potato", "lemon"],
                "spice": ["salt", "pepper", "cumin", "oregano", "basil", "cinnamon", "paprika"],
                "fat": ["oil", "olive oil", "vegetable oil", "coconut oil"],
                "sweetener": ["sugar", "honey", "maple syrup", "brown sugar"],
                "condiment": ["soy sauce", "vinegar", "mustard", "ketchup", "mayonnaise", "hot sauce"],
                "canned": ["broth", "stock", "canned tomato", "tomato sauce", "beans"],
                "baking": ["baking soda", "baking powder", "vanilla", "cocoa"],
            }

            cross_cat_count = 0
            all_category_pairs = Counter()

            for r in rows:
                row = r.get("row", {})
                name = row.get("Name", row.get("name", ""))
                ingredients = row.get("RecipeIngredientParts", row.get("ingredients", []))

                if isinstance(ingredients, str):
                    # Parse string list
                    ingredients = [i.strip().strip('"').strip("'") for i in ingredients.strip("[]").split(",")]

                # Categorize ingredients
                recipe_cats = set()
                for ing in ingredients:
                    ing_lower = str(ing).lower()
                    for cat, keywords in food_categories.items():
                        if any(kw in ing_lower for kw in keywords):
                            recipe_cats.add(cat)

                print(f"\n  Recipe: '{name}'")
                print(f"  Ingredients ({len(ingredients)}): {[str(i)[:30] for i in ingredients[:8]]}...")
                print(f"  Categories hit: {recipe_cats}")

                if len(recipe_cats) >= 2:
                    cross_cat_count += 1
                    print(f"  >>> CROSS-CATEGORY! <<<")

                    # Track pairs
                    cats_list = sorted(recipe_cats)
                    for i in range(len(cats_list)):
                        for j in range(i+1, len(cats_list)):
                            all_category_pairs[(cats_list[i], cats_list[j])] += 1

            print(f"\n  Cross-category recipes: {cross_cat_count}/{len(rows)} ({cross_cat_count/max(len(rows),1)*100:.0f}%)")
            if all_category_pairs:
                print(f"\n  Most common category co-occurrences:")
                for pair, count in all_category_pairs.most_common(10):
                    print(f"    {pair[0]} + {pair[1]}: {count}")
        else:
            print("  No rows returned")
    else:
        print(f"  HTTP {resp.status_code}: {resp.text[:200]}")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n")

# ============================================================
# 2. RecipeNLG — 2.2M recipes
# ============================================================
print("=" * 70)
print("2. RECIPENLG — Testing (2.2M recipes)")
print("=" * 70)

url = "https://huggingface.co/api/datasets/mbien/recipe_nlg"
try:
    resp = requests.get(url, timeout=10)
    if resp.status_code == 200:
        info = resp.json()
        print(f"  Found: {info.get('id', 'N/A')}")
        print(f"  Downloads: {info.get('downloads', 'N/A')}")
        print(f"  Tags: {info.get('tags', [])[:10]}")
    else:
        print(f"  HTTP {resp.status_code}")
except:
    pass

# Get sample
print("\n  Fetching sample rows...")
url = "https://datasets-server.huggingface.co/rows?dataset=mbien/recipe_nlg&config=default&split=train&offset=0&length=10"
try:
    resp = requests.get(url, timeout=15)
    if resp.status_code == 200:
        data = resp.json()
        rows = data.get("rows", [])
        if rows:
            first = rows[0].get("row", {})
            print(f"  Columns: {list(first.keys())}")

            for r in rows[:5]:
                row = r.get("row", {})
                title = row.get("title", "")
                ingredients = row.get("ingredients", [])
                ner = row.get("ner", [])

                if isinstance(ingredients, str):
                    try:
                        ingredients = json.loads(ingredients)
                    except:
                        ingredients = [ingredients]

                print(f"\n  Recipe: '{title}'")
                print(f"  Ingredients: {ingredients[:6]}...")
                if ner:
                    print(f"  NER entities: {ner[:6]}...")
    else:
        print(f"  HTTP {resp.status_code}: {resp.text[:200]}")
except Exception as e:
    print(f"  ERROR: {e}")

# Check total size
print("\n  Checking dataset size...")
url = "https://datasets-server.huggingface.co/info?dataset=mbien/recipe_nlg"
try:
    resp = requests.get(url, timeout=10)
    if resp.status_code == 200:
        info = resp.json()
        for config, splits in info.get("dataset_info", {}).items():
            for split_name, split_info in splits.get("splits", {}).items():
                print(f"  Split '{split_name}': {split_info.get('num_examples', '?')} recipes")
except:
    pass

print("\n")

# ============================================================
# 3. RecipeDB — USDA-integrated recipes
# ============================================================
print("=" * 70)
print("3. RECIPEDB — Testing (USDA nutrition integrated)")
print("=" * 70)

# Check if the API works
print("\n  Testing RecipeDB API...")
url = "https://cosylab.iiitd.edu.in/recipedb/api/recipe/search?query=pasta&page=1"
try:
    resp = requests.get(url, timeout=15)
    print(f"  Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        if isinstance(data, list):
            print(f"  Got {len(data)} recipes")
            for recipe in data[:3]:
                print(f"\n  Recipe: '{recipe.get('recipe_title', recipe.get('title', 'N/A'))}'")
                print(f"  Keys: {list(recipe.keys())[:15]}")
                # Check for USDA linkage
                if "ingredients" in recipe:
                    ings = recipe["ingredients"]
                    if isinstance(ings, list):
                        for ing in ings[:3]:
                            if isinstance(ing, dict):
                                print(f"    Ingredient: {ing}")
                            else:
                                print(f"    Ingredient: {ing}")
        elif isinstance(data, dict):
            print(f"  Response keys: {list(data.keys())[:10]}")
            recipes = data.get("recipes", data.get("results", data.get("data", [])))
            if recipes:
                print(f"  Got {len(recipes)} recipes")
                for recipe in recipes[:2]:
                    print(f"  Recipe: {recipe}")
            else:
                print(f"  Full response: {str(data)[:500]}")
    else:
        print(f"  Response: {resp.text[:300]}")
except Exception as e:
    print(f"  ERROR: {e}")

# Try alternative endpoints
print("\n  Trying alternative RecipeDB endpoints...")
for endpoint in [
    "https://cosylab.iiitd.edu.in/recipedb/api/recipes?page=1&limit=5",
    "https://cosylab.iiitd.edu.in/recipedb/api/v1/recipes?limit=5",
]:
    try:
        resp = requests.get(endpoint, timeout=10)
        print(f"  {endpoint}: HTTP {resp.status_code}")
        if resp.status_code == 200:
            print(f"    Response: {str(resp.json())[:200]}")
    except Exception as e:
        print(f"  {endpoint}: ERROR - {e}")

print("\n")

# ============================================================
# 4. Dunnhumby Complete Journey — Check structure
# ============================================================
print("=" * 70)
print("4. DUNNHUMBY COMPLETE JOURNEY — Structure check")
print("=" * 70)

print("""
  Available from: https://www.dunnhumby.com/source-files/
  Also on Kaggle: https://www.kaggle.com/datasets/frtgnn/dunnhumby-the-complete-journey

  8 CSV Tables:
    transaction_data.csv  — household_id, basket_id, product_id, quantity, sales_value, store_id, week_no, trans_time
    product.csv           — product_id, manufacturer, department, commodity_desc, sub_commodity_desc, curr_size_of_product, brand
    hh_demographic.csv    — household_id, age_desc, marital_status, income_desc, homeowner_desc, hh_comp_desc, household_size, kid_category
    coupon.csv            — coupon_upc, product_id, department, category
    coupon_redempt.csv    — household_id, day, coupon_upc, campaign
    campaign_desc.csv     — campaign, description, start_day, end_day
    campaign_table.csv    — household_id, campaign
    causal_data.csv       — product_id, store_id, week_no, display, mailer

  KEY FIELDS:
    - basket_id: groups products into real shopping baskets ✅
    - department: category grouping (GROCERY, DRUG GM, etc.) ✅
    - commodity_desc: subcategory (COLD CEREAL, SHREDDED CHEESE, etc.) ✅
    - product_id: internal ID (NOT UPC) ❌
    - coupon_upc: UPC for coupons only ❌

  LINKAGE TO OFF/USDA:
    - No direct barcode/UPC for products
    - But has: brand + commodity_desc + sub_commodity_desc + curr_size_of_product
    - Example: "GENERAL MILLS" + "COLD CEREAL" + "ALL FAMILY CEREAL" + "18 OZ"
    - This CAN be fuzzy matched to USDA/OFF products

  SIZE: 2,500 households, 275,000+ baskets, ~2 years
""")

# ============================================================
# FINAL COMPARISON
# ============================================================
print("=" * 70)
print("FINAL COMPARISON — UC4 DATA OPTIONS")
print("=" * 70)
print("""
  | Source              | Baskets?  | Size       | Barcodes? | Links to OFF/USDA?  | Fresh? |
  |---------------------|-----------|------------|-----------|---------------------|--------|
  | Open Prices         | Via proof | 240K prices| YES       | YES (direct)        | Daily  |
  | Instacart           | YES       | 3.4M orders| NO        | Fuzzy name match    | 2017   |
  | Dunnhumby           | YES       | 275K bask  | NO        | Brand+category match| ~2014  |
  | Food.com recipes    | Proxy     | 180K       | NO        | Ingredient match    | 2019   |
  | RecipeNLG           | Proxy     | 2.2M       | NO        | Ingredient match    | 2020   |
  | RecipeDB            | Proxy     | 118K       | NO        | USDA integrated     | 2020   |
""")
