"""
UC3: Build search index + calibrate LLM judge against ESCI.
Run: python scripts/05_build_search_index.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from config import DATA_DIR
from utils.search import build_search_index
from utils.llm import call_llm


def build_index():
    print("=" * 60)
    print("Building hybrid search index (BM25 + embeddings)")
    print("=" * 60)
    catalog = pd.read_csv(DATA_DIR / "merged_catalog.csv")
    build_search_index(catalog, save_path=DATA_DIR / "search_index.pkl")
    print(f"  Index built for {len(catalog)} products")


def calibrate_judge():
    print("\n" + "=" * 60)
    print("Calibrating LLM-as-judge against ESCI human labels")
    print("=" * 60)

    esci = pd.read_csv(DATA_DIR / "esci_sample.csv")

    # Get diverse queries — pick 1 pair per unique query to avoid
    # testing the same bathroom fan query 30 times
    unique_queries = esci.drop_duplicates(subset=["query"])
    sample = unique_queries.sample(n=min(50, len(unique_queries)), random_state=42)
    print(f"  Testing {len(sample)} ESCI pairs...")

    results = []
    for i, (_, row) in enumerate(sample.iterrows()):
        query = str(row.get("query", ""))
        product = str(row.get("product_title", ""))
        human_label = str(row.get("esci_label", ""))

        prompt = f"""You are an e-commerce search relevance judge. Rate how relevant a product is to a search query.

Query: "{query}"
Product: "{product}"

Definitions:
- Exact: The product IS what the user is looking for. Same type, same purpose. Brand/model differences are fine — if someone searches "running shoes" and gets Nike running shoes, that's Exact.
- Substitute: The product is a reasonable alternative but not quite what was searched. Different sub-type or adjacent category.
- Complement: The product goes well WITH what was searched but is a different product entirely (e.g., phone case for a phone search).
- Irrelevant: The product has nothing to do with the query.

Important: Focus on the USER'S INTENT, not exact string matching. If the query is for a product category and the result is a specific product in that category, that's Exact.

Respond with ONLY one word: Exact, Substitute, Complement, or Irrelevant"""

        llm_label = call_llm(prompt, max_tokens=20)
        if llm_label:
            llm_label = llm_label.strip().split()[0].rstrip(".,")

        # Map ESCI labels: E=Exact, S=Substitute, C=Complement, I=Irrelevant
        label_map = {"E": "Exact", "S": "Substitute", "C": "Complement", "I": "Irrelevant"}
        human_mapped = label_map.get(human_label, human_label)

        agrees = str(llm_label).lower() == str(human_mapped).lower()
        results.append({
            "query": query,
            "product_title": product[:100],
            "human_label": human_mapped,
            "llm_label": llm_label,
            "agrees": agrees,
        })
        print(f"  [{i+1}/{len(sample)}] Human={human_mapped}, LLM={llm_label}, Agree={agrees}")

    results_df = pd.DataFrame(results)
    results_df.to_csv(DATA_DIR / "esci_calibration.csv", index=False)

    agreement = results_df["agrees"].mean() * 100
    print(f"\n  Agreement rate: {agreement:.1f}%")
    print(f"  Saved calibration results to data/esci_calibration.csv")


if __name__ == "__main__":
    build_index()
    calibrate_judge()
