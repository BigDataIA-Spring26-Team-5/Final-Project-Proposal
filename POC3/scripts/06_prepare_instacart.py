"""
UC4: Prepare Instacart basket data + run association rules.
Run: python scripts/06_prepare_instacart.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from config import DATA_DIR
from utils.association import prepare_transactions, run_apriori


def main():
    print("=" * 60)
    print("Preparing Instacart basket data for UC4")
    print("=" * 60)

    baskets = pd.read_csv(DATA_DIR / "instacart_baskets.csv")
    print(f"  Loaded {len(baskets)} basket rows")
    print(f"  Unique orders: {baskets['order_id'].nunique()}")
    print(f"  Unique products: {baskets['product_name'].nunique()}")
    print(f"  Departments: {baskets['department'].nunique()}")

    # Run Apriori at department level
    print("\n  Running Apriori at department level...")
    transactions = prepare_transactions(baskets, level="department")
    print(f"  Transactions: {len(transactions)}")

    rules = run_apriori(transactions, min_support=0.01, min_confidence=0.1, min_lift=1.0)
    if len(rules) > 0:
        # Save top 50 rules
        top_rules = rules.head(50)[["antecedents_str", "consequents_str", "support", "confidence", "lift"]]
        top_rules.columns = ["antecedent", "consequent", "support", "confidence", "lift"]
        top_rules["support"] = (top_rules["support"] * 100).round(2)
        top_rules["confidence"] = (top_rules["confidence"] * 100).round(1)
        top_rules["lift"] = top_rules["lift"].round(2)
        top_rules.to_csv(DATA_DIR / "association_rules.csv", index=False)
        print(f"  Saved {len(top_rules)} association rules")

        print(f"\n  Top 10 rules:")
        for _, row in top_rules.head(10).iterrows():
            print(f"    {row['antecedent']:30s} → {row['consequent']:20s} (conf={row['confidence']}%, lift={row['lift']})")
    else:
        print("  No rules found — try lower thresholds")
        pd.DataFrame(columns=["antecedent", "consequent", "support", "confidence", "lift"]).to_csv(DATA_DIR / "association_rules.csv", index=False)

    # Save basket summary stats
    summary = baskets.groupby("order_id").agg(
        num_items=("product_name", "count"),
        num_departments=("department", "nunique"),
    ).reset_index()
    print(f"\n  Basket stats:")
    print(f"    Avg items/basket: {summary['num_items'].mean():.1f}")
    print(f"    Avg departments/basket: {summary['num_departments'].mean():.1f}")
    print(f"    Cross-category (2+ depts): {(summary['num_departments'] >= 2).sum()} / {len(summary)} ({(summary['num_departments'] >= 2).mean()*100:.0f}%)")


if __name__ == "__main__":
    main()
