"""Hybrid search: BM25 + sentence embeddings + RRF fusion."""
import pandas as pd
import numpy as np
import pickle
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

_model = None


def get_embedding_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def build_search_corpus(catalog_df):
    """Build text corpus from merged catalog for indexing."""
    docs = []
    for _, row in catalog_df.iterrows():
        text = f"{row.get('name', '')} {row.get('brand', '')} {row.get('category', '')} {row.get('ingredients', '')}"
        docs.append(text.lower().strip())
    return docs


def build_bm25_index(docs):
    """Build BM25 index from tokenized documents."""
    tokenized = [doc.split() for doc in docs]
    return BM25Okapi(tokenized)


def build_embedding_index(docs):
    """Compute embeddings for all documents."""
    model = get_embedding_model()
    embeddings = model.encode(docs, show_progress_bar=True, batch_size=32)
    return embeddings


def build_search_index(catalog_df, save_path=None):
    """Build full search index (BM25 + embeddings) and optionally save."""
    docs = build_search_corpus(catalog_df)
    print(f"  Building BM25 index for {len(docs)} documents...")
    bm25 = build_bm25_index(docs)
    print(f"  Computing embeddings...")
    embeddings = build_embedding_index(docs)

    index = {
        "docs": docs,
        "bm25": bm25,
        "embeddings": embeddings,
        "catalog": catalog_df.to_dict("records"),
    }

    if save_path:
        with open(save_path, "wb") as f:
            pickle.dump(index, f)
        print(f"  Saved search index to {save_path}")

    return index


def load_search_index(path):
    """Load pre-built search index."""
    with open(path, "rb") as f:
        return pickle.load(f)


def bm25_search(query, index, top_k=10):
    """BM25 keyword search. Returns list of (idx, score)."""
    tokenized_query = query.lower().split()
    scores = index["bm25"].get_scores(tokenized_query)
    top_indices = np.argsort(scores)[::-1][:top_k]
    return [(int(i), float(scores[i])) for i in top_indices if scores[i] > 0]


def embedding_search(query, index, top_k=10):
    """Semantic embedding search. Returns list of (idx, score)."""
    model = get_embedding_model()
    query_emb = model.encode([query.lower()])
    # Cosine similarity
    similarities = np.dot(index["embeddings"], query_emb.T).flatten()
    top_indices = np.argsort(similarities)[::-1][:top_k]
    return [(int(i), float(similarities[i])) for i in top_indices]


def rrf_fusion(bm25_results, embedding_results, k=60):
    """Reciprocal Rank Fusion to combine two ranked lists."""
    scores = {}
    for rank, (idx, _) in enumerate(bm25_results):
        scores[idx] = scores.get(idx, 0) + 1.0 / (k + rank + 1)
    for rank, (idx, _) in enumerate(embedding_results):
        scores[idx] = scores.get(idx, 0) + 1.0 / (k + rank + 1)
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return ranked


def hybrid_search(query, index, top_k=10):
    """Full hybrid search: BM25 + embedding + RRF. Returns ranked results with metadata."""
    bm25_results = bm25_search(query, index, top_k=20)
    emb_results = embedding_search(query, index, top_k=20)
    fused = rrf_fusion(bm25_results, emb_results)[:top_k]

    catalog = index["catalog"]
    results = {
        "bm25": [{"rank": i+1, "score": round(s, 4), **catalog[idx]} for i, (idx, s) in enumerate(bm25_results[:top_k])],
        "embedding": [{"rank": i+1, "score": round(s, 4), **catalog[idx]} for i, (idx, s) in enumerate(emb_results[:top_k])],
        "fused": [{"rank": i+1, "score": round(s, 6), **catalog[idx]} for i, (idx, s) in enumerate(fused)],
    }
    return results
