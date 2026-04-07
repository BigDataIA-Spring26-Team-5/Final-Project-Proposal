# Marketplace Intelligence & Data Quality Observability Platform
## DAMG 7245: Big Data and Intelligent Analytics

| Resource | Link |
|---|---|
| **CodeLabs** | [View Document](https://codelabs-preview.appspot.com/?file_id=1LU7EuVDdBgW_h1k9k5esTxJd9oTW9CDTLo90mMjCWiE#0) |
| **Presentation Video** | [Watch Recording](https://northeastern-my.sharepoint.com/personal/ryan_aq_northeastern_edu/_layouts/15/stream.aspx?id=%2Fpersonal%2Fryan%5Faq%5Fnortheastern%5Fedu%2FDocuments%2FRecordings%2FCall%20with%20Bhavya%20and%201%20other%2D20260403%5F160617%2DMeeting%20Recording%2Emp4&nav=eyJyZWZlcnJhbEluZm8iOnsicmVmZXJyYWxBcHAiOiJPbmVEcml2ZUZvckJ1c2luZXNzIiwicmVmZXJyYWxBcHBQbGF0Zm9ybSI6IldlYiIsInJlZmVycmFsTW9kZSI6InZpZXciLCJyZWZlcnJhbFZpZXciOiJNeUZpbGVzTGlua0NvcHkifX0&referrer=StreamWebApp%2EWeb&referrerScenario=AddressBarCopied%2Eview%2Ea258d42b%2D22dc%2D446e%2D906f%2D28325e3f16d3&ct=1775247486820&or=Teams%2DHL&ga=1) |

> For full technical details — architecture, data sources, LLM strategy, evaluation metrics, and cost analysis — see the **[CodeLabs document](https://codelabs-preview.appspot.com/?file_id=1LU7EuVDdBgW_h1k9k5esTxJd9oTW9CDTLo90mMjCWiE#0)**.

---

### Team Members

| Name | Contribution |
|---|---|
| Bhavya Likhitha Bukka | 33.3% |
| Dwaraka Deepika Vaddadi | 33.3% |
| Aqeel Ryan | 33.3% |

**Attestation:** WE ATTEST THAT WE HAVEN'T USED ANY OTHER STUDENTS' WORK IN OUR ASSIGNMENT AND ABIDE BY THE POLICIES LISTED IN THE STUDENT HANDBOOK.

---

## Project Summary

A platform that cleans, enriches, and monitors fragmented marketplace product catalogs. Built around 4 use cases:

| Use Case | What it does |
|---|---|
| **UC1 — Catalog Enrichment** | Deduplicates products across sources, normalizes brands, extracts structured attributes via LLM |
| **UC2 — Data Quality & Observability** | Scores every product 0–100, detects anomalies, generates root-cause explanations |
| **UC3 — Hybrid Search** | BM25 + semantic search with automated relevance evaluation (LLM-as-Judge) |
| **UC4 — Recommendations** | Cross-category basket patterns from Instacart co-purchase data |

**Data:** 6 open sources — Open Food Facts (4M products), USDA FoodData (454K), openFDA Recalls (28K), Open Prices (240K), Amazon ESCI (2.68M judgments), Instacart (37.3M rows).

**Stack:** Apache Spark · Kafka · Airflow · Groq (Llama 3.3 70B) · Claude · DSPy · OpenSearch · Neo4j · Streamlit · AWS.

---

## Running the POC

The POC runs locally on a ~100-product USDA sample with no cloud dependencies.

### Setup

```bash
cd POC
poetry install        # or: pip install -r requirements.txt
```

Create a `.env` file in `POC/`:
```
GROQ_API_KEY=your_key_here
```

### Main Dashboard (4 use cases)

```bash
streamlit run app.py
```

Opens at `http://localhost:8501` with tabs for UC1–UC4. All data is pre-computed in `POC/data/` — no pipeline scripts required.

### UC1 Deduplication Walkthrough

```bash
streamlit run dedup_demo.py
```

A step-by-step interactive demo of the full product deduplication and enrichment pipeline. Each step shows **What / Why / How** and runs live on the raw CSV.

| Step | What it does |
|---|---|
| **1. Load Raw Data** | Load USDA FoodData sample; inspect schema, row counts, null rates |
| **2. Identify Duplicates** | Find exact-match groups on `description` — same product listed separately per package size |
| **3. Trim Whitespace** | Strip invisible spaces so `"Hormel Foods "` and `"Hormel Foods"` stop being different strings |
| **4. Lowercase** | Normalize case so `"GENERAL MILLS"` and `"General Mills"` become identical |
| **5. Remove Noise Words** | Two-layer detection: hardcoded legal suffixes (`inc`, `llc`, `sales`…) + data-driven frequency analysis. Also applies a **Company Aliases dictionary** mapping `"GENERAL MILLS SALES INC."` → `"General Mills"` |
| **6. Remove Punctuation** | Replace non-alphanumeric characters with spaces |
| **7. Regex — Strip Sizes** | Remove package sizes (`1.37oz`, `1.25 Liters`) from descriptions so size variants match. Saves stripped sizes to a **`sizes` column**. Adds an **`allergens` column** from FDA Big-9 keyword scan of ingredients |
| **8. Blocking & Fuzzy Matching** | Group candidates by normalized key, score pairs with `rapidfuzz` (`name×0.5 + brand×0.2 + combined×0.3`). Threshold ≥ 85 = match |
| **9. Clustering (Union-Find)** | Merge matching pairs into clusters with transitive closure |
| **10. Golden Record (DQ Score)** | Pick best row per cluster: `Completeness×0.4 + Freshness×0.35 + Ingredient Richness×0.25`. Aggregates all size variants into `sizes` / `serving_sizes` |
| **11. LLM Enrichment (Groq)** | 4-layer optimization (dedup → rules → cache → batching) minimizes LLM calls. Groq Llama 3.3 70B extracts `clean_name`, `primary_category`, `dietary_tags`, `allergens`, `is_organic` |
| **12. Final Cleaned Data** | Deduplicated, enriched dataset with `clean_description`, `canonical_brand`, `allergens`, `sizes`, `serving_sizes`. Downloadable as CSV |

### Optional: Rebuild Pipeline Data

```bash
python scripts/01_fetch_data.py
python scripts/02_enrich_products.py
python scripts/03_entity_resolution.py
python scripts/04_compute_dq_scores.py
python scripts/05_build_search_index.py
python scripts/06_prepare_instacart.py
```
