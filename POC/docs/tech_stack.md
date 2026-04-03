# Final Tech Stack — Marketplace Intelligence & Data Observability Platform

---

## LLM Strategy: Groq + Claude (No Bedrock)

| Task | Model | Provider | Why |
|---|---|---|---|
| DSPy extraction (UC1) | Llama 3.3 70B | Groq (free tier) | Free, fast inference, good at structured extraction from messy product data |
| Anomaly explanations (UC2) | Llama 3.3 70B | Groq (free tier) | Simple prompts, fast response, bulk explanations |
| AutoEval / LLM-as-Judge (UC3) | Claude | Anthropic API | Better reasoning for nuanced relevance judgments, provides justification |
| RAG Chatbot (MCP) | Claude | Anthropic API | Best for conversational, evidence-grounded answers with citations |
| Affinity profiles (UC4) | Llama 3.3 70B | Groq (free tier) | Simple generation task, free tier sufficient |

**Why two providers:**
- **Groq** handles bulk/batch tasks — 50+ product enrichments, anomaly explanations, affinity profiles. Free tier (~30 requests/minute). Fast.
- **Claude** handles tasks requiring reasoning depth — search relevance judging needs nuance (is this product an "Exact" match or a "Substitute"?), chatbot needs grounded conversation with evidence.
- **No Bedrock.** Direct API calls to Groq and Anthropic. Simpler, cheaper, no AWS overhead.

---

## Demo Tech Stack (Current POC)

What we built and are running now on ~100 products locally.

| Layer | Technology | Purpose |
|---|---|---|
| **LLM - Bulk** | Groq (Llama 3.3 70B) | DSPy extraction, anomaly explanations, affinity profiles |
| **LLM - Reasoning** | Claude (Anthropic API) | Search evaluation (AutoEval), RAG chatbot |
| **LLM Framework** | DSPy | Structured extraction with retry logic, swappable models |
| **Search - Keyword** | rank-bm25 | BM25 keyword matching, lightweight, no server needed |
| **Search - Semantic** | sentence-transformers (all-MiniLM-L6-v2) | Free local embedding model, 80MB, fast |
| **Search - Fusion** | Reciprocal Rank Fusion (custom) | Combines BM25 + embedding ranked lists |
| **Entity Resolution** | rapidfuzz | Fuzzy name matching (token_sort_ratio) across sources |
| **Anomaly Detection** | scikit-learn (Isolation Forest) | Point anomaly detection on pipeline metric time series |
| **Association Rules** | mlxtend (Apriori) | Cross-category basket pattern mining |
| **DQ Scoring** | Custom Python (4 dimensions) | Completeness, consistency, accuracy, freshness → 0-100 score |
| **Frontend** | Streamlit | 4-tab interactive demo app |
| **Charts** | Plotly | Radar charts, histograms, time series, network graphs |
| **Data Processing** | Pandas | Sufficient for 100-product demo |
| **Language** | Python 3.12 | Everything runs on it |

---

## Production Tech Stack (Full Implementation)

What the project scales to for the final deliverable.

### Compute + Processing

| Component | Technology | Purpose | Why This Choice |
|---|---|---|---|
| Cloud | AWS (S3 + EC2) | Hosting and storage | Simple, cost-effective for student project |
| Batch Processing | Apache Spark on EC2 | Process 4M+ Open Food Facts products | Pandas can't handle 4M rows. Spark distributes the work. |
| Orchestration | Apache Airflow | Schedule pipelines: OFF daily, USDA monthly, FDA weekly, DQ scoring after ingestion | Dependency-aware DAGs, native S3/EC2 integration |
| Streaming | Apache Kafka | Real-time ingestion: OFF delta files, Open Prices (every few minutes), FDA weekly, pipeline events (DQ scores, anomaly alerts) | Decouples producers from consumers, handles multiple data frequencies |

### LLM + ML

| Component | Technology | Purpose | Why This Choice |
|---|---|---|---|
| LLM - Bulk Tasks | Groq (Llama 3.3 70B) | DSPy extraction (50K-100K products), anomaly explanations, affinity profiles | Free tier for development. Fast inference. Switch to paid tier for full scale. |
| LLM - Reasoning | Claude (Anthropic API) | AutoEval search judging, RAG chatbot, complex analysis | Best reasoning quality for nuanced judgments. Conversational grounding. |
| LLM Framework | DSPy | Structured extraction constrained to taxonomy via RAG | Prompt optimization (BootstrapFewShot/MIPRO), structured output parsing, model-swappable |
| Anomaly Detection | Isolation Forest (scikit-learn) | Detect point anomalies on pipeline metrics (null rate spikes, row count drops) | Simple, effective, fast. sklearn implementation. |
| Entity Resolution | rapidfuzz + ML classifier | Fuzzy name matching for blocking, trained classifier for pairwise match/non-match | rapidfuzz for speed, ML classifier (tracked in MLflow) for accuracy |
| Experiment Tracking | MLflow | Track: entity resolution precision/recall, embedding model comparisons, LLM cost per call, Isolation Forest thresholds | Model registry manages staging → production. Artifacts stored in S3. |

### Search + Knowledge

| Component | Technology | Purpose | Why This Choice |
|---|---|---|---|
| Search Engine | OpenSearch | Hybrid search: BM25 keyword + kNN vector in one service | Native BM25 + vector support. Replaces rank-bm25 + sentence-transformers in production. |
| Knowledge Graph | Neo4j (Community Edition) | Store product → category → brand → attribute → recall relationships. Power graph traversal queries. | DoorDash's #1 lesson: knowledge graphs constrain LLM outputs and power search. |
| Vector Store | ChromaDB | RAG chatbot indexes anomaly logs, DQ reports, pipeline history | Python-native. Perfect for RAG retrieval. Lightweight. |
| Embeddings | all-MiniLM-L6-v2 (or compare BGE-small, E5-base via MLflow) | Convert product text to vectors for semantic search | Free, local, fast. Compare models via MLflow and promote best to production. |

### Data Quality + Validation

| Component | Technology | Purpose | Why This Choice |
|---|---|---|---|
| DQ Validation | Great Expectations | Declarative data quality rules as code. Validate on ingestion. Failed checks halt Airflow DAG. | Amazon Deequ / Google TFDV pattern: "unit tests for data." |
| DQ Scoring | Custom (4 dimensions) | Score every product 0-100: completeness, consistency, accuracy, freshness | Airbnb DQ Score pattern: single composite number drives accountability. |
| Pipeline Observability | Kafka + Isolation Forest | Stream pipeline metrics → detect anomalies → LLM explains root cause → alerts ranked by severity | Uber DQ + Netflix RPCA pattern: data quality as a time-series problem. |

### API + Frontend

| Component | Technology | Purpose | Why This Choice |
|---|---|---|---|
| API | FastAPI | REST endpoints for all pipeline capabilities. Backend for MCP server and chatbot. | Async, fast, auto-docs, Pydantic validation. |
| MCP Server | Custom (wraps 7 tools) | Any LLM client (Claude Desktop, chatbot) can call: score_product_quality, get_anomaly_alerts, search_catalog, get_entity_graph, get_pipeline_health, run_dq_check, get_search_eval_report | Proves MCP pattern transfers to a different domain than PE Org-AI-R. |
| Frontend | Streamlit | Dashboard: DQ scores overview, anomaly alerts, search quality trends, pipeline health, cost tracking. RAG chatbot interface. | Fast prototyping. Scalability through Streamlit Cloud or ECS. |
| RAG Chatbot | Streamlit + ChromaDB + Claude + MCP | Catalog manager asks questions, chatbot uses RAG over anomaly logs + DQ reports, calls MCP tools for live data, answers with cited evidence | DoorDash entity profiles pattern: "code for facts, LLMs for narrative." |

### CI/CD + Deployment

| Component | Technology | Purpose | Why This Choice |
|---|---|---|---|
| CI/CD | GitHub Actions | Lint → test → build Docker → deploy to EC2 | Standard, free for public repos. |
| Containers | Docker + Amazon ECR | Package: FastAPI + MCP + Streamlit + Neo4j + Kafka + MLflow | Reproducible deployments. |
| Secrets | AWS Secrets Manager or .env | API keys (Groq, Anthropic), DB credentials | Never in code or commits. |
| Deployment | AWS CLI scripts | Manual for MVP. Deploy Docker containers to EC2. | Simple for student project. Auto-scaling is a future enhancement. |

### Storage

| Component | Technology | Purpose | Why This Choice |
|---|---|---|---|
| Data Lake | Amazon S3 | Raw data (OFF dump, USDA CSV, FDA JSON), processed Parquet, model artifacts, DQ reports, MLflow artifacts | Central storage. Versioned. Cheap. |
| Relational DB | PostgreSQL (on EC2 or RDS) | Enriched catalog, DQ scores, anomaly logs, eval results, alert history, MLflow metadata | Structured queries. Joins. ACID transactions. |
| Search Index | OpenSearch | BM25 + kNN vectors for product search | Combined keyword + vector in one service. |
| Graph DB | Neo4j (on EC2) | Knowledge graph: products, categories, attributes, relationships | Community edition. Graph traversal for entity relationships. |
| Vector Store | ChromaDB (on EC2) | RAG chatbot retrieval index over anomaly logs and DQ reports | Python-native. Lightweight. |

---

## Demo → Production: What Changes

| Component | Demo (now) | Production | Why It Changes |
|---|---|---|---|
| Data processing | Pandas (100 products) | Spark on EC2 (4M+ products) | Pandas crashes at 4M rows |
| Search | rank-bm25 + sentence-transformers | OpenSearch | Need a real search server for production queries |
| Orchestration | Run scripts manually in order | Airflow DAGs with dependencies | Need scheduled, automated, dependency-aware pipelines |
| Streaming | None (batch only) | Kafka | Need real-time ingestion of OFF deltas + Open Prices |
| Storage | CSV files in data/ folder | S3 + PostgreSQL | Need persistent, versioned, queryable storage |
| DQ validation | Custom Python scoring functions | Great Expectations | Need declarative rules as code, not hardcoded checks |
| Knowledge graph | Taxonomy in code variables | Neo4j | Need traversable graph for search + chatbot queries |
| API | Streamlit only | FastAPI + MCP server | Need programmatic access for chatbot + external LLM tools |
| Experiment tracking | None | MLflow | Need to compare models, track costs, manage model versions |
| Chatbot | None in demo | Streamlit + ChromaDB + Claude + MCP | Full RAG chatbot with evidence-grounded answers |
| Deployment | Local laptop | Docker on EC2 | Need it running 24/7 |

## What Stays the Same (Demo = Production)

These components don't change — the demo proves the logic, production scales the infrastructure:

| Component | Same in Both |
|---|---|
| Groq (Llama 3.3 70B) | Bulk LLM tasks: extraction, explanations, profiles |
| Claude (Anthropic API) | Reasoning tasks: AutoEval, chatbot |
| DSPy | Structured extraction framework |
| Isolation Forest | Anomaly detection algorithm |
| Apriori (mlxtend) | Association rule mining |
| rapidfuzz | Entity resolution fuzzy matching |
| RRF fusion | Search result combination logic |
| DQ scoring dimensions | Completeness, consistency, accuracy, freshness → 0-100 |
| Streamlit | Frontend/dashboard |

---

## Cost Estimate

### LLM Costs

| Component | Provider | Est. Calls/Day | Est. Cost/Day |
|---|---|---|---|
| UC1: DSPy extraction | Groq (free tier) | ~5,000 (batch) | $0 (free tier) to ~$3 (paid) |
| UC2: Anomaly explanations | Groq (free tier) | ~50-100 | $0 |
| UC3: AutoEval judging | Claude (Anthropic) | ~2,000-5,000 | ~$3-8 |
| UC4: Affinity profiles | Groq (free tier) | ~100-500 | $0 |
| RAG Chatbot | Claude (Anthropic) | ~100-500 | ~$1-3 |

**Estimated total: $4-11/day during development, ~$2-5/day steady state.**

### Cost Optimization (from DoorDash articles)
- **Embedding caching** — compute once, store in S3 + OpenSearch. Re-embed only changed products. Saves ~80%.
- **DSPy prompt optimization** — BootstrapFewShot/MIPRO find shorter effective prompts.
- **Batch LLM calls** — 10-20 products per call with structured JSON output.
- **Model tiering** — Groq (free) for routine extraction. Claude only for AutoEval and complex reasoning.
- **Result caching** — 24hr TTL. Pipeline retries use cache.
- **Daily budget caps** — per-component limits. Auto-pause + alert.

### AWS Costs (Production)

| Service | Est. Monthly |
|---|---|
| EC2 (t3.large for app + services) | ~$60 |
| S3 (10 GB data lake) | ~$0.25 |
| Data transfer | ~$5 |
| **Total AWS** | **~$65/month** |

---

## Novel Libraries (from proposal)

| Library | Purpose | Used In | License |
|---|---|---|---|
| DSPy | Program LLM pipelines with structured I/O | UC1 extraction, UC2 diagnosis | MIT |
| Great Expectations | DQ validation rules as code | UC2 (production) | Apache 2.0 |
| Neo4j | Knowledge graph for entity relationships | UC1 (production) | GPLv3 community |
| DeepEval | LLM evaluation with 14+ metrics | UC3 AutoEval (production) | Apache 2.0 |
| MLflow | Experiment tracking + model registry | All UCs (production) | Apache 2.0 |
| ChromaDB | Vector store for RAG chatbot | Chatbot (production) | Apache 2.0 |
| rapidfuzz | Fast fuzzy string matching | UC1 entity resolution | MIT |
| mlxtend | Association rules (Apriori/FP-Growth) | UC4 recommendations | BSD-3 |

---

## Architecture Summary

```
Data Sources (6)                    Processing                         Output
─────────────────                   ──────────                         ──────
Open Food Facts ──┐                                                    
(daily, messy)    │   Kafka    ┌─→ Spark ──→ DSPy+Groq ──→ Neo4j     ┌─→ Streamlit Dashboard
                  ├──→ ──────→│                            (KG)       │   (DQ scores, anomalies,
USDA FoodData ────┤   topics  ├─→ Great Expectations                  │    search quality, recs)
(monthly, clean)  │           │   (validation)                        │
                  │           ├─→ Isolation Forest                    ├─→ RAG Chatbot
openFDA Recalls ──┤           │   (anomaly detection)                 │   (Claude + ChromaDB + MCP)
(weekly)          │           ├─→ OpenSearch                          │
                  │           │   (BM25 + vectors)                    ├─→ FastAPI + MCP Server
Open Prices ──────┘           └─→ Apriori                             │   (7 tools for any LLM client)
(real-time)                       (basket rules)                      │
                                                                      └─→ MLflow
Amazon ESCI ────────────→ AutoEval calibration (Claude)                   (experiments, model registry)
(static benchmark)                                                    
                                                                      
Instacart Baskets ──────→ Association rules + LLM profiles            
(static patterns)                                                     
                                                                      
                  Airflow orchestrates everything                      
                  GitHub Actions for CI/CD                             
```
