"""UC3: Hybrid Search + Evaluation tab."""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DATA_DIR


def render():
    st.header("UC3: Hybrid Search + Evaluation")
    st.caption("BM25 + Semantic Embeddings + RRF Fusion → LLM-as-Judge → NDCG/MRR")

    # Load search index
    index_path = DATA_DIR / "search_index.pkl"
    if not index_path.exists():
        st.error("Search index not found. Run scripts/05_build_search_index.py first.")
        return

    from utils.search import load_search_index, hybrid_search
    index = load_search_index(index_path)

    # Section 1: Search
    st.subheader("1. Hybrid Search")

    query = st.text_input("Search the enriched catalog:", placeholder="e.g., healthy breakfast cereal, organic snacks, chocolate cookies")

    if query:
        with st.spinner("Searching..."):
            results = hybrid_search(query, index, top_k=10)

        col_bm25, col_emb, col_fused = st.columns(3)

        with col_bm25:
            st.markdown("**BM25 (Keyword)**")
            for r in results["bm25"][:5]:
                st.write(f"{r['rank']}. **{r.get('name', '')[:40]}** ({r.get('brand', '')[:20]})")
                st.caption(f"Score: {r['score']:.4f} | {r.get('category', '')}")

        with col_emb:
            st.markdown("**Embedding (Semantic)**")
            for r in results["embedding"][:5]:
                st.write(f"{r['rank']}. **{r.get('name', '')[:40]}** ({r.get('brand', '')[:20]})")
                st.caption(f"Score: {r['score']:.4f} | {r.get('category', '')}")

        with col_fused:
            st.markdown("**Fused (RRF)**")
            for r in results["fused"][:5]:
                st.write(f"{r['rank']}. **{r.get('name', '')[:40]}** ({r.get('brand', '')[:20]})")
                st.caption(f"RRF Score: {r['score']:.6f} | {r.get('category', '')}")

        st.divider()

        # Section 2: AutoEval (LLM-as-Judge)
        st.subheader("2. AutoEval (LLM-as-Judge)")

        if st.button("Rate search results with LLM"):
            from utils.llm import call_llm_json

            fused_results = results["fused"][:5]
            products_text = "\n".join([f"{i+1}. {r.get('name', '')} by {r.get('brand', '')} [{r.get('category', '')}]" for i, r in enumerate(fused_results)])

            prompt = f"""You are a search relevance judge. Rate each product's relevance to the query.

Query: "{query}"

Products:
{products_text}

For each product, rate as: Exact, Substitute, Complement, or Irrelevant.
Also provide a brief reason.

Return JSON array:
[{{"product": "product name", "rating": "Exact|Substitute|Complement|Irrelevant", "reason": "brief explanation"}}]"""

            with st.spinner("LLM is judging relevance..."):
                ratings = call_llm_json(prompt)

            if ratings and isinstance(ratings, list):
                ratings_df = pd.DataFrame(ratings)
                st.dataframe(ratings_df, use_container_width=True)

                # Compute NDCG@5
                relevance_map = {"Exact": 3, "Substitute": 2, "Complement": 1, "Irrelevant": 0}
                gains = [relevance_map.get(r.get("rating", "Irrelevant"), 0) for r in ratings]

                # DCG
                dcg = sum(g / (i + 2) for i, g in enumerate(gains))  # log2(i+2)
                # Ideal DCG
                ideal = sorted(gains, reverse=True)
                idcg = sum(g / (i + 2) for i, g in enumerate(ideal))
                ndcg = dcg / idcg if idcg > 0 else 0

                # MRR
                mrr = 0
                for i, g in enumerate(gains):
                    if g >= 2:  # Exact or Substitute
                        mrr = 1.0 / (i + 1)
                        break

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("NDCG@5", f"{ndcg:.3f}")
                with col2:
                    st.metric("MRR", f"{mrr:.3f}")
            else:
                st.error("Failed to get ratings from LLM.")

    st.divider()

    # Section 3: Judge Calibration (ESCI)
    st.subheader("3. Judge Calibration (ESCI Human Labels)")

    calib_path = DATA_DIR / "esci_calibration.csv"
    if calib_path.exists():
        calib = pd.read_csv(calib_path)
        agreement = calib["agrees"].mean() * 100

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Agreement Rate", f"{agreement:.1f}%")
        with col2:
            st.metric("Pairs Tested", len(calib))
        with col3:
            st.metric("Judge Status", "Reliable" if agreement >= 70 else "Needs Tuning")

        st.dataframe(
            calib[["query", "product_title", "human_label", "llm_label", "agrees"]],
            use_container_width=True,
        )

        # Agreement breakdown
        if "human_label" in calib.columns:
            cross = pd.crosstab(calib["human_label"], calib["llm_label"], margins=True)
            st.markdown("**Confusion Matrix (Human vs LLM)**")
            st.dataframe(cross, use_container_width=True)
    else:
        st.info("Calibration data not found. Run scripts/05_build_search_index.py first.")
