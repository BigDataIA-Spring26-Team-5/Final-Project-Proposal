"""Association rules for cross-category recommendations (UC4)."""
import pandas as pd
import numpy as np
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder


def prepare_transactions(baskets_df, level="department"):
    """Convert basket data to transaction format at department or aisle level."""
    grouped = baskets_df.groupby("order_id")[level].apply(list).reset_index()
    # Deduplicate items within each basket
    grouped[level] = grouped[level].apply(lambda x: list(set(x)))
    return grouped[level].tolist()


def run_apriori(transactions, min_support=0.01, min_confidence=0.3, min_lift=1.0):
    """Run Apriori algorithm and return association rules."""
    te = TransactionEncoder()
    te_array = te.fit(transactions).transform(transactions)
    df = pd.DataFrame(te_array, columns=te.columns_)

    # Remove 'missing' department if present
    if "missing" in df.columns:
        df = df.drop(columns=["missing"])

    frequent = apriori(df, min_support=min_support, use_colnames=True)
    if len(frequent) == 0:
        return pd.DataFrame()

    rules = association_rules(frequent, metric="confidence", min_threshold=min_confidence)
    rules = rules[rules["lift"] >= min_lift]

    # Convert frozensets to strings for readability
    rules["antecedents_str"] = rules["antecedents"].apply(lambda x: ", ".join(sorted(x)))
    rules["consequents_str"] = rules["consequents"].apply(lambda x: ", ".join(sorted(x)))

    rules = rules.sort_values("lift", ascending=False)
    return rules


def get_category_cooccurrence(baskets_df, level="department"):
    """Compute co-occurrence matrix at department/aisle level."""
    transactions = prepare_transactions(baskets_df, level)
    all_categories = sorted(set(cat for basket in transactions for cat in basket))

    matrix = pd.DataFrame(0, index=all_categories, columns=all_categories)
    for basket in transactions:
        for i, cat1 in enumerate(basket):
            for cat2 in basket[i+1:]:
                matrix.loc[cat1, cat2] += 1
                matrix.loc[cat2, cat1] += 1

    return matrix


def get_top_recommendations(rules_df, category, top_k=5):
    """Given a category, return top recommended co-purchase categories."""
    category_lower = category.lower()
    relevant = rules_df[rules_df["antecedents_str"].str.lower().str.contains(category_lower)]
    if len(relevant) == 0:
        return []

    recs = []
    for _, row in relevant.head(top_k).iterrows():
        recs.append({
            "recommended": row["consequents_str"],
            "confidence": round(row["confidence"] * 100, 1),
            "lift": round(row["lift"], 2),
            "support": round(row["support"] * 100, 2),
        })
    return recs
