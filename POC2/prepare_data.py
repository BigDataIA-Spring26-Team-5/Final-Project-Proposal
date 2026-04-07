"""
Generates 1K synthetic food product rows with realistic messiness.
No external API or downloads needed.
Usage: poetry run python prepare_data.py
"""

import os
import random
import pandas as pd
import numpy as np

random.seed(42)
np.random.seed(42)
os.makedirs("data", exist_ok=True)

OUTPUT_PATH = "data/en.openfoodfacts.org.products-1k.csv"

# --- Realistic product data pools ---

PRODUCTS = [
    ("Whole Milk", "Organic Valley", "dairy", "1 gal", "milk,dairy", "gluten-free", "a"),
    ("Greek Yogurt Strawberry", "Chobani", "dairy", "5.3 oz", "milk,dairy", "gluten-free", "b"),
    ("Cheddar Cheese Slices", "Kraft", "dairy", "200 g", "milk,dairy", "gluten-free", "c"),
    ("Honey Nut Cheerios", "General Mills", "cereals", "10.8 oz", "gluten,wheat", "vegetarian", "b"),
    ("Multigrain Cheerios", "General Mills", "cereals", "9.8 oz", "gluten,wheat", "vegetarian", "b"),
    ("Classic Peanut Butter", "Skippy", "spreads", "500 g", "peanuts", "vegan", "c"),
    ("Natural Almond Butter", "Justin's", "spreads", "180 g", "tree nuts", "vegan,gluten-free", "a"),
    ("Sourdough Bread", "Pepperidge Farm", "bread", "680 g", "gluten,wheat", "vegetarian", "b"),
    ("Whole Wheat Bread", "Nature's Own", "bread", "570 g", "gluten,wheat", "vegetarian", "b"),
    ("Orange Juice", "Tropicana", "beverages", "1.75 l", "", "vegan,gluten-free", "b"),
    ("Apple Juice", "Mott's", "beverages", "64 fl oz", "", "vegan,gluten-free", "b"),
    ("Sparkling Water Lemon", "LaCroix", "beverages", "12 x 355 ml", "", "vegan,gluten-free", "a"),
    ("Tomato Pasta Sauce", "Rao's", "sauces", "240 g", "", "vegan,gluten-free", "a"),
    ("Marinara Sauce", "Prego", "sauces", "680 g", "", "vegan,gluten-free", "c"),
    ("Chicken Noodle Soup", "Campbell's", "soups", "305 g", "gluten,wheat", "contains meat", "c"),
    ("Tomato Soup", "Campbell's", "soups", "305 g", "", "vegan,gluten-free", "c"),
    ("Lays Classic Chips", "Lay's", "snacks", "184 g", "", "vegan,gluten-free", "d"),
    ("Oreo Cookies", "Nabisco", "snacks", "14.3 oz", "gluten,wheat,soy", "vegetarian", "e"),
    ("Dark Chocolate Bar", "Lindt", "confectionery", "100 g", "milk,soy", "vegetarian", "b"),
    ("Granola Bar Honey Oat", "Nature Valley", "snacks", "6 x 42 g", "gluten,wheat,oats", "vegetarian", "c"),
    ("Baby Spinach", "Earthbound Farm", "vegetables", "5 oz", "", "vegan,gluten-free,organic", "a"),
    ("Cherry Tomatoes", "Sunset", "vegetables", "1 pint", "", "vegan,gluten-free", "a"),
    ("Basmati Rice", "Royal", "grains", "2 lb", "", "vegan,gluten-free", "b"),
    ("Spaghetti Pasta", "Barilla", "pasta", "500 g", "gluten,wheat", "vegan", "b"),
    ("Penne Rigate", "De Cecco", "pasta", "500 g", "gluten,wheat", "vegan", "b"),
    ("Salted Butter", "Land O Lakes", "dairy", "1 lb", "milk,dairy", "gluten-free", "c"),
    ("Free Range Eggs", "Vital Farms", "eggs", "12 count", "eggs", "gluten-free,vegetarian", "a"),
    ("Sliced Turkey Breast", "Boar's Head", "deli", "8 oz", "", "gluten-free", "b"),
    ("Frozen Broccoli", "Birds Eye", "frozen", "12 oz", "", "vegan,gluten-free", "a"),
    ("Vanilla Ice Cream", "Häagen-Dazs", "frozen", "14 fl oz", "milk,eggs", "gluten-free,vegetarian", "e"),
]

QUANTITY_VARIANTS = {
    "1 gal": ["1gal", "1 GAL", "1Gal", "1 gal"],
    "5.3 oz": ["5.3oz", "5.3 OZ", "5.3oz", "5.3 oz"],
    "200 g": ["200g", "200G", "200 G", "200 g"],
    "10.8 oz": ["10.8oz", "10.8 OZ", "10.8oz", "10.8 oz"],
    "500 g": ["500g", "500G", "500 G", "500 g"],
    "680 g": ["680g", "680G", "680 g", "680 g"],
    "1.75 l": ["1.75l", "1.75L", "1.75 L", "1.75 l"],
    "500 g": ["500g", "500G", "500 G", "500 g"],
}

BRAND_VARIANTS = {
    "General Mills": ["GENERAL MILLS", "General Mills,", "General Mills Inc", "general mills"],
    "Chobani": ["CHOBANI", "Chobani LLC", "chobani", "Chobani,"],
    "Kraft": ["KRAFT", "Kraft Foods", "kraft", "Kraft,"],
    "Campbell's": ["CAMPBELLS", "Campbell Soup", "campbells", "Campbell's,"],
    "Lay's": ["LAYS", "Lay's", "lays", "Frito-Lay"],
}

INGREDIENT_TEXTS = {
    "dairy": "Milk, Cream, Vitamin D3",
    "cereals": "Whole Grain Oats, Sugar, Oat Bran, Modified Corn Starch, Salt, Calcium Carbonate, Niacinamide",
    "spreads": "Roasted Peanuts, Sugar, Contains 2% or less of: Molasses, Fully Hydrogenated Vegetable Oils, Mono and Diglycerides, Salt",
    "bread": "Enriched Flour, Water, High Fructose Corn Syrup, Yeast, Soybean Oil, Salt, Wheat Gluten",
    "beverages": "Filtered Carbonated Water, Natural Flavors",
    "sauces": "Tomatoes, Olive Oil, Onions, Garlic, Salt, Basil, Black Pepper",
    "soups": "Chicken Stock, Cooked Enriched Egg Noodles, Cooked Chicken Meat, Salt, Starch",
    "snacks": "Potatoes, Vegetable Oil, Salt",
    "confectionery": "Sugar, Cocoa Butter, Chocolate, Skim Milk, Cocoa Mass, Lactose, Soy Lecithin, Vanilla",
    "vegetables": "Organic Baby Spinach",
    "grains": "Long Grain White Basmati Rice",
    "pasta": "Durum Wheat Semolina",
    "eggs": "Grade A Eggs",
    "deli": "Turkey Breast, Water, Sea Salt, Carrageenan",
    "frozen": "Broccoli Florets",
}


def generate_rows(n=1000):
    rows = []
    for i in range(n):
        base = random.choice(PRODUCTS)
        name, brand, category, quantity, allergens, labels, nutriscore = base
        ingredients = INGREDIENT_TEXTS.get(category, "")

        # --- Inject specific bad data types ---

        # ~20% null product_name
        if random.random() < 0.20:
            name = None

        # ~30% brand messiness or null
        r = random.random()
        if r < 0.10:
            brand = None
        elif r < 0.25 and brand in BRAND_VARIANTS:
            brand = random.choice(BRAND_VARIANTS[brand])
        elif r < 0.30:
            brand = "  " + brand + "  "   # whitespace padding

        # ~40% quantity messiness or null
        r = random.random()
        if r < 0.15:
            quantity = None
        elif r < 0.40:
            variants = QUANTITY_VARIANTS.get(quantity, [quantity])
            quantity = random.choice(variants)

        # ~50% null allergens
        if random.random() < 0.50:
            allergens = None

        # ~45% null categories
        if random.random() < 0.45:
            category = None

        # ~40% null labels
        if random.random() < 0.40:
            labels = None

        # ~35% null ingredients
        if random.random() < 0.35:
            ingredients = None

        # ~5% null nutriscore
        if random.random() < 0.05:
            nutriscore = None

        # Duplicate codes — ~5% share a barcode with a previous product
        if i > 10 and random.random() < 0.05:
            code = rows[random.randint(0, i - 1)]["code"]
        else:
            code = str(random.randint(1000000000000, 9999999999999))

        rows.append({
            "code": code,
            "product_name": name,
            "brands": brand,
            "quantity": quantity,
            "categories_en": category,
            "allergens_en": allergens,
            "labels_en": labels,
            "ingredients_text_en": ingredients,
            "nutriscore_grade": nutriscore,
        })

    return rows


def main():
    print("Generating 1K synthetic food product rows...")
    rows = generate_rows(1000)
    df = pd.DataFrame(rows).reset_index(drop=True)
    df.to_csv(OUTPUT_PATH, index=False)

    print(f"\n✅ Saved {len(df)} rows to {OUTPUT_PATH}")
    print(f"\nNull rates:")
    for col in df.columns:
        null_pct = df[col].isna().mean() * 100
        print(f"  {col:30s} {null_pct:.1f}% null")
    print(f"\nSample:")
    print(df[["product_name", "brands", "quantity"]].head(10).to_string())


if __name__ == "__main__":
    main()