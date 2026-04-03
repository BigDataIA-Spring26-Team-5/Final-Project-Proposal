# Final Project Proposal
## DAMG 7245: Big Data and Intelligent Analytics
### Team Members

- Bhavya Likhitha Bukka
- Deepika Vaddadi
- Aqeel Ryan

### Attestation (Required)

WE ATTEST THAT WE HAVEN'T USED ANY OTHER STUDENTS' WORK IN OUR ASSIGNMENT AND ABIDE BY THE POLICIES LISTED IN THE STUDENT HANDBOOK.

Bhavya Likhitha Bukka: 33.3%
Deepika Vaddadi: 33.3%
Aqeel Ryan: 33.3%


## 1. Title : **Marketplace Intelligence & Data Quality Observability Platform**
## 2. Introduction
### 2.1 Background

Marketplace product catalogs are fragmented, inconsistent, and difficult to trust. Every marketplace company (DoorDash, Instacart, Airbnb, Shopify, Walmart, Amazon) ingests product data from thousands of sellers and sources, and none of it is standardized. The same product appears with different names, different attributes, and different levels of completeness depending on who entered it and where.

For example, the same cereal appears across sources as:

| Source | How it appears |
|---|---|
| Open Food Facts | `Cheerios` by `Cheerios` |
| USDA FoodData | `Cheerios Cereal` by `General Mills` |
| FDA Recalls | `General Mills CHEERIOS Honey Nut 10.8oz` |
| Instacart | `Cheerios` in breakfast department |

Four naming conventions, no universal product ID. When a customer searches "gluten-free breakfast cereal," nothing useful comes up because the catalog is messy: missing attributes, inconsistent brands, no structured dietary tags. This costs marketplace companies millions in failed searches and missed conversions.

The deeper problem is trust over time: even if you clean the catalog today, data sources change formats overnight, null rates silently spike, and search quality degrades after a catalog refresh with nobody noticing for days.

This project was inspired by studying **20 engineering blog posts** from companies that solve these exact problems in production. We combined ideas from DoorDash (knowledge graphs, AutoEval, cross-vertical recommendations), Airbnb (Data Quality Score, LAEP attribute extraction), Uber (INCA catalog enrichment, statistical DQ monitoring), Netflix (RPCA anomaly detection), Walmart (entity resolution), Instacart (hybrid retrieval), Faire (LLM-as-Judge for search), Pinterest (multi-task ranking), Spotify (taxonomy governance), Google (data validation for ML), and Amazon (automated DQ verification) into a unified multi-use-case platform where each layer feeds the others.

We chose grocery and food products as the demonstration domain because this category has the richest open datasets available: 4M+ products across government and crowdsourced databases, with real continuous updates. However, every technique we build (entity resolution, data quality scoring, hybrid search, pipeline observability) applies to any product catalog at any marketplace. The domain is grocery products, but the engineering is universal.

### 2.2 Objective

This project delivers:

**Big data engineering component:** Apache Spark processes 4M+ products. Apache Kafka streams data from 4 continuous sources (Open Food Facts daily, Open Prices every few minutes, FDA recalls weekly, pipeline events). Apache Airflow orchestrates the full pipeline. Pathway streams pipeline telemetry for near-real-time anomaly detection. 44M+ total records across 6 sources.

**Significant LLM use:** 5 distinct LLM applications. (1) DSPy attribute extraction from messy product descriptions (Groq/Llama 3.3 70B), DSPy root-cause diagnosis for detected anomalies (Groq), LLM-as-Judge for search relevance evaluation (Claude), RAG chatbot with MCP tool calling for data quality engineers (Claude), and LLM-generated user affinity profiles for cross-category recommendations (Groq). All outputs validated with Pydantic schemas, hallucination checks, and taxonomy constraints.

**Cloud-native architecture:** AWS: S3 (data lake), EC2 (compute), Snowflake (analytical warehouse), PostgreSQL (operational database), OpenSearch (hybrid search), Neo4j (knowledge graph), ChromaDB (RAG vector store), Kafka (streaming), Airflow (orchestration), MLflow (experiment tracking). GitHub Actions for CI/CD. Docker + ECR for containers.

**User-facing application:** Streamlit dashboard with data quality score overview, anomaly alerts ranked by severity, search quality trends measured by NDCG (Normalized Discounted Cumulative Gain, which measures how good the ranking order is) and MRR (Mean Reciprocal Rank, which measures how quickly the first relevant result appears), pipeline health monitor, LLM cost tracker, and a RAG chatbot that answers natural-language questions about catalog quality by calling MCP tools and citing evidence.

---

## 3. Project Overview

### 3.1 Scope

**In-scope:**

- **Data sources:** 6 verified sources (Open Food Facts 4M products, USDA FoodData 454K products, openFDA Recalls 28K records, Open Prices 240K entries, Amazon ESCI 2.68M judgments, Instacart 37.3M rows) + 2 assets we build (product taxonomy, domain search evaluation set). Total: 44M+ records, ~10.5 GB.
- **ETL pipelines:** Spark batch ingestion orchestrated by Airflow. Kafka streaming for continuous sources. Great Expectations validation on ingestion. data quality scoring pipeline.
- **LLM components:** DSPy extraction (Groq), DSPy root-cause diagnosis (Groq), LLM-as-Judge AutoEval (Claude), RAG chatbot with MCP tools (Claude), affinity profile generation (Groq).
- **Cloud infrastructure:** AWS (S3, EC2, Snowflake, PostgreSQL, OpenSearch, Kafka, Neo4j, ChromaDB, MLflow). Docker deployment.
- **Guardrails & human-in-the-loop:** Pydantic schema enforcement on all DSPy outputs constrained to taxonomy. Hallucination checks on root-cause diagnoses. Entity resolution pairs below 70% confidence routed to human review. Critical anomaly alerts require human acknowledgment. Search eval disagreements flagged for calibration.
- **Evaluation strategy:** AutoEval with LLM-as-Judge calibrated on Amazon ESCI (>80% agreement target). Domain evaluation set of 300-500 domain-specific product queries with human-in-the-loop validation. NDCG/MRR tracked in MLflow. Isolation Forest precision/recall on synthetic anomalies. Entity resolution F1 tracked in MLflow.

### 3.2 Stakeholders / End Users

| Stakeholder | How they use the platform |
|---|---|
| **Data Quality Engineer** | Views data quality scores per product, investigates anomaly alerts, uses chatbot to ask "why did organic product scores drop?" |
| **Search / Relevance Engineer** | Monitors NDCG/MRR trends, reviews AutoEval results, tunes ranking parameters |
| **Data Platform Engineer** | Monitors pipeline health, investigates schema drifts, reviews root-cause diagnoses |
| **Product Data Analyst** | Explores knowledge graph relationships, reviews entity resolution decisions, checks cross-category patterns |

---

## 4. Problem Statement

### 4.1 Current Challenges

**Data fragmentation:** Product data spread across 4+ sources with zero standardization. Same product has different names, brands, categories, and attribute completeness in each source. No universal product ID connects them.

**Manual workflows:** Entity resolution (matching "Cheerios" across sources) done manually or not at all. Data quality assessed by ad-hoc spot checks. Search quality evaluated by expensive human annotators.

**Lack of intelligent automation:** When a data source changes schema overnight or null rates spike, nobody knows until a downstream report breaks. Root-cause analysis is manual debugging that takes hours.

**Big-data bottleneck:** 4M+ product records can't be processed with pandas. LLM extraction on millions of products requires batching, cost optimization, and smart subsetting. Search over large catalogs needs proper indexing infrastructure.

**LLM-related challenges:** Without taxonomy constraints, LLM extraction hallucinates product categories. Without calibration, LLM-as-Judge produces unreliable relevance labels. Without caching and batching, LLM API costs spiral.

### 4.2 Opportunities

**Scalable pipelines:** Spark + Airflow + Kafka handle ingestion at scale. Designed for 4M+ products with demonstrated subset for LLM extraction (50K-100K). Scale by increasing Groq tier.

**LLM-assisted analysis:** DSPy extracts structured attributes from unstructured descriptions (DoorDash, Airbnb, Uber pattern). LLM-as-Judge replaces manual search evaluation (DoorDash AutoEval: 98% reduction in human eval turnaround). LLM generates root-cause explanations (DoorDash pattern: "code for facts, LLMs for narrative").

**Automated decision-making:** Anomaly detection (Isolation Forest) + severity ranking + auto-remediation for non-critical issues. Entity resolution ML classifier automates matching with human review only for uncertain cases.

**Real-time / near-real-time insights:** Kafka streams continuous data from 4 sources. Pathway streams pipeline telemetry for near-real-time anomaly detection. Alerts delivered within minutes of issue, not on next daily batch.

---

## 5. Methodology

### 5.1 Data Sources

| # | Source | Records | Size | Freshness | Use Cases | License |
|---|---|---|---|---|---|---|
| 1 | Open Food Facts | ~4M products | 1.16 GB | Daily (continuous) | Enrichment, Quality, Streaming | ODbL v1.0 |
| 2 | USDA FoodData Central | 454,678 | 420 MB | Monthly (March 2026) | Enrichment, Quality | Public domain |
| 3 | openFDA Food Recalls | 28,679 | ~50 MB | Weekly | Enrichment, Quality, Streaming | Public domain |
| 4 | Open Prices | 240,718 | ~100 MB | Real-time (every few min) | Quality, Streaming | ODbL |
| 5 | Amazon ESCI | 2.68M judgments | ~8 GB | Static (correct for benchmark) | Search calibration | Apache 2.0 |
| 6 | Instacart Market Basket | 37.3M rows | 713 MB | Static (correct for patterns) | Recommendations (stretch) | Non-commercial |

**Total: 44M+ records, ~10.5 GB. All free. All verified April 2, 2026.**

**Assets we build:**
- **Product Taxonomy / Knowledge Graph**: Merged from USDA `foodCategory` (21 categories, L2) + Open Food Facts `categories_tags` (nested tags, L3). Controlled vocabularies for dietary, product types, brands, units. Constrains DSPy outputs to <1% hallucination (DoorDash pattern). Stored in Neo4j.
- **Domain Search Evaluation Set**: 300-500 domain-specific product queries evaluated against our enriched catalog. LLM-as-Judge labels with chain-of-thought justification. Team validates 50-100 pairs (human-in-the-loop). ESCI calibrates the judge first. This is the primary search quality measurement.

**Why static benchmarks are correct:** Search evaluation benchmarks must be static to measure improvement over time. NDCG/MRR require stable labels. DoorDash AutoEval, Faire, and Instacart all use versioned evaluation snapshots. Instacart's co-purchase patterns (cereal→milk, pasta→sauce) are among the most stable consumer behaviors: 91% cross-category signal verified in data.

**Why Kafka is justified:** Four genuinely continuous data sources. Open Prices (every few minutes), OFF delta files (daily community edits), FDA recalls (weekly), pipeline events (data quality scores, anomaly alerts). Kafka decouples producers from consumers and handles multiple data frequencies.

**Data source URLs:**
- Open Food Facts: https://world.openfoodfacts.org/data
- USDA FoodData: https://fdc.nal.usda.gov/download-datasets/
- openFDA: https://open.fda.gov/apis/food/enforcement/
- Open Prices: https://prices.openfoodfacts.org/
- Amazon ESCI: https://huggingface.co/datasets/tasksource/esci
- Instacart: https://www.kaggle.com/datasets/yasserh/instacart-online-grocery-basket-analysis-dataset

### 5.2 Tools & Technologies at a Glance

#### Big Data & Processing

| Tool | What it does (plain English) |
|---|---|
| **Apache Spark** | Processes 4M+ products in parallel. Pandas can't handle this scale |
| **Apache Kafka** | Catches new data as it arrives (every few minutes from Open Prices, daily from Open Food Facts, weekly from FDA) |
| **Pathway** | Streams pipeline health metrics in real-time so anomalies are caught in minutes, not next morning |

#### Orchestration

| Tool | What it does (plain English) |
|---|---|
| **Apache Airflow** | The backbone. Schedules and runs the entire pipeline automatically: "run Open Food Facts ingestion daily → trigger data quality scoring → refresh search index → run anomaly detection." Every step depends on the previous one. If ingestion fails, nothing downstream runs. |

#### LLM & AI

| Tool | What it does (plain English) |
|---|---|
| **DSPy** | Programs LLMs to extract structured attributes. Not prompt engineering, but actual code with optimizers |
| **Groq (Llama 3.3 70B)** | Free, fast LLM for bulk tasks. Extracts attributes from thousands of products |
| **Claude (Anthropic)** | Smart LLM for reasoning tasks. Judges search relevance and powers the chatbot |
| **MCP Server** | Wraps pipeline capabilities as tools. Any LLM (Claude Desktop, chatbot) can call "score this product" or "check pipeline health" |

#### Search & Knowledge

| Tool | What it does (plain English) |
|---|---|
| **Neo4j** | Graph database. Stores how products, categories, brands, and attributes connect to each other |
| **OpenSearch** | Search engine. Handles both keyword search ("cheerios") and meaning search ("healthy breakfast") in one place |
| **ChromaDB** | Vector database for the chatbot. Stores anomaly logs and DQ reports so the chatbot can find relevant context |

#### Data Quality & Observability

| Tool | What it does (plain English) |
|---|---|
| **Great Expectations** | Data quality checks as code: "this column should never have more than 5% nulls." Halts pipeline if violated |
| **Isolation Forest** | Anomaly detection ML model. Spots unusual values in pipeline metrics (sudden null spikes, row count drops) |

#### ML & Experiment Tracking

| Tool | What it does (plain English) |
|---|---|
| **MLflow** | Tracks every ML experiment. Tracks model versions, accuracy, and cost. Manages staging → production |
| **rapidfuzz** | Fuzzy string matching. Figures out that "Cheerios" and "Cheerios Cereal" are the same product |
| **mlxtend** | Association rule mining. Finds patterns like "people who buy cereal also buy milk" from Instacart data |

#### Evaluation & Testing

| Tool | What it does (plain English) |
|---|---|
| **DeepEval** | LLM evaluation framework. Measures if search results are actually good using 14+ metrics |
| **ArkSim** | Stress-tests the search system and chatbot by simulating realistic multi-turn user conversations at scale |

#### Novel Libraries (new tools not used in any previous project)

| Library | What it brings to this project | License |
|---|---|---|
| **DSPy** | Programmatic LLM pipelines with automatic prompt optimization | MIT |
| **Great Expectations** | Declarative data quality validation rules as code | Apache 2.0 |
| **Neo4j** | Graph database for product-category-brand relationships | GPLv3 community |
| **DeepEval** | LLM output evaluation with 14+ built-in metrics | Apache 2.0 |
| **ArkSim** | Synthetic user simulation for stress-testing search and chatbot | Apache 2.0 |
| **MLflow** | ML experiment tracking with model registry and cost logging | Apache 2.0 |
| **ChromaDB** | Lightweight vector database for RAG chatbot retrieval | Apache 2.0 |
| **rapidfuzz** | High-performance fuzzy string matching for entity resolution | MIT |
| **mlxtend** | Association rule mining (Apriori algorithm) for basket analysis | BSD-3 |
| **Pathway** | Real-time streaming framework for pipeline telemetry | BSL 1.1 (free) |

#### API & Frontend

| Tool | What it does (plain English) |
|---|---|
| **FastAPI** | Backend API. Serves all data to the dashboard, chatbot, and MCP tools |
| **Streamlit** | Frontend dashboard + RAG chatbot interface. What the data quality engineer actually sees and uses |

#### Cloud & Storage (AWS)

| Tool | What it does (plain English) |
|---|---|
| **S3** | Data lake. Stores all raw data, processed files, and model artifacts |
| **EC2** | Compute. Runs Spark, Kafka, Neo4j, and application services |
| **Snowflake** | Cloud data warehouse. Analytical queries on data quality scores, anomaly trends, search eval aggregations across millions of products |
| **PostgreSQL** | Operational database. MLflow metadata, chatbot session state, real-time alert logs (sub-second response) |
| **AWS Secrets Manager** | Keeps API keys and passwords safe: never in code |

#### CI/CD & Deployment

| Tool | What it does (plain English) |
|---|---|
| **Docker** | Packages everything into containers so it runs the same everywhere |
| **Amazon ECR** | Stores Docker images in the cloud |
| **GitHub Actions** | Automates testing and deployment. Every code push triggers lint → test → build → deploy |

### 5.3 Architecture

#### System Architecture Description

The platform has 4 layers:

**Layer 1: Data Ingestion:** 6 data sources feed into the platform through two paths. Batch sources (USDA monthly, OFF full dump daily) are scheduled via Airflow DAGs, processed by Spark, and land in S3 (raw) → PostgreSQL (structured). Continuous sources (OFF delta files, Open Prices, FDA recalls, pipeline events) flow through Kafka topics, consumed by processing workers.

**Layer 2: Intelligence Pipeline:** DSPy (Groq) extracts structured attributes from messy product descriptions, constrained to the product taxonomy via RAG. Entity resolution (rapidfuzz + ML classifier) matches products across 4 sources. Knowledge graph (Neo4j) stores product → category → brand → attribute → recall relationships. Great Expectations validates every data load. Data Quality Score (0-100) computed per product.

**Layer 3: Observability Layer:** Wraps around the entire pipeline. Monitors every stage: ingestion health (schema drift, volume, freshness), content quality (data quality scores), search quality (NDCG/MRR). Isolation Forest detects anomalies on pipeline metric time series. DSPy generates root-cause diagnoses. Alerts ranked by severity. Pathway streams telemetry continuously. Kafka carries continuous data events.

**Layer 4: User-Facing Intelligence:** FastAPI REST endpoints. MCP Server wraps 7 tools callable by any LLM client. RAG Chatbot (Streamlit + ChromaDB + Claude) answers data quality engineer questions with cited evidence via MCP tool calls. Dashboard shows data quality scores, anomaly alerts, search quality, pipeline health, cost tracking.

**System Architecture Diagram:** *(to be created as Mermaid diagram: see Appendix)*

**Data Flow Diagram:**

```
Sources → Kafka/Airflow → Spark → S3/PostgreSQL → DSPy Enrichment → Neo4j (KG)
                                                         ↓
                                               Great Expectations (DQ validation)
                                                         ↓
                                               Data Quality Scoring (0-100 per product)
                                                         ↓
                                               OpenSearch (BM25 + vector index)
                                                         ↓
                                               AutoEval (Claude LLM-as-Judge)
                                                         ↓
                                               NDCG/MRR → MLflow

Observability (runs in parallel):
All stages → Kafka pipeline events → Pathway telemetry → Isolation Forest
                                                              ↓
                                                    DSPy root-cause (Groq)
                                                              ↓
                                                    Severity-ranked alerts
                                                              ↓
                                                    Dashboard + Chatbot
```

### 5.4 Data Processing & Transformation

**Batch processing:** Spark on EC2 processes the full 4M+ OFF product dump (daily), USDA branded foods (monthly refresh), FDA recalls (weekly pull). Airflow DAGs define dependencies: ingest → validate → enrich → score → index.

**Stream processing:** Kafka ingests continuous events from OFF delta files, Open Prices API, FDA weekly recalls, and pipeline events (data quality scores, anomaly alerts). Pathway consumes pipeline telemetry stream for near-real-time anomaly detection.

**Data formats:** Raw data lands in S3 as CSV/JSON/Parquet depending on source. Processed data stored as Parquet in S3 (columnar, compressed). Analytical data in Snowflake (data quality score aggregations, anomaly trends, enriched catalog analytics). Operational data in PostgreSQL (MLflow metadata, chatbot state, real-time alert logs). Vectors in OpenSearch (BM25 text + vector embeddings). Graph in Neo4j (product relationships).

**Storage schemas:** PostgreSQL tables for: products (enriched), dq_scores (per product per dimension), anomaly_alerts (timestamped with severity), search_eval_results (query, NDCG, MRR), llm_cost_log (per call). S3 partitioned by source/date for raw data.

**Parallel processing:** Spark handles data-parallel transformation across 4M+ products. Kafka enables parallel consumption of multiple topics. Embedding generation batched (10-20 products per call for DSPy, single-product for embedding model).

**Embedding generation:** Product text → all-MiniLM-L6-v2 (or best model from MLflow comparison of BGE-small, E5-base). Embeddings stored in OpenSearch for vector search. Computed once, cached in S3 + OpenSearch. Only re-embed changed products (saves ~80% cost).

### 5.5 LLM Integration Strategy

**5 distinct LLM applications:**

**1. DSPy Attribute Extraction (UC1: Groq/Llama 3.3 70B):**
Extracts structured attributes (dietary, brand, category, size, ingredients) from messy Open Food Facts product descriptions. DSPy modules define input/output schemas. Taxonomy provided via RAG context: the LLM can only output categories that exist in the taxonomy, achieving <1% hallucination (DoorDash's pattern). BootstrapFewShot/MIPRO optimize prompts automatically. Runs on ~50K-100K product subset (pipeline designed for full 4M, subset due to API throughput).

**2. DSPy Root-Cause Diagnosis (UC2: Groq/Llama 3.3 70B):**
When Isolation Forest detects an anomaly, DSPy generates a plain-English explanation. Input: anomaly details (metric name, value, expected range, timestamp) + schema diff logs + recent pipeline run history. Output: structured diagnosis with cause, affected scope, and suggested action. Cross-checked against actual logs to catch hallucination.

**3. LLM-as-Judge AutoEval (UC3: Claude):**
Evaluates search relevance at scale. For each query-result pair, Claude provides a 4-level grade (Exact/Substitute/Complement/Irrelevant) with chain-of-thought justification. Calibrated on ESCI first (>80% agreement with human labels). Then applied to domain evaluation set. This is the DoorDash AutoEval + Faire Llama3 pattern.

**4. RAG Chatbot with MCP Tools (All use cases, Claude):**
Data quality engineer asks natural-language questions. Chatbot retrieves context from ChromaDB (anomaly logs, DQ reports, enriched catalog) and calls MCP tools for live data. Answers with cited evidence. Pattern: "code for facts, LLMs for narrative" (DoorDash).

**5. Affinity Profile Generation (UC4 stretch, Groq/Llama 3.3 70B):**
Given Instacart co-purchase patterns (Apriori rules), LLM generates human-readable user affinity profiles bridging categories: "Healthy breakfast shoppers buy: organic milk, granola, blueberries across dairy/breakfast/produce."

**API usage pattern:** Groq for bulk tasks (free tier ~30 req/min, batch 10-20 products per call). Claude for reasoning tasks (direct Anthropic API). DSPy framework handles retries, structured parsing, and model swapping.

### 5.6 Guardrails & Human-in-the-Loop (human-in-the-loop)

**Input moderation:**
- Pydantic schema enforcement on all DSPy outputs: extracted attributes must conform to strict types, enums from taxonomy, value ranges. Invalid output rejected and retried automatically.
- Input sanitization for search queries and chatbot: strip injection attempts, normalize unicode, limit length.
- Great Expectations validation on every data ingestion: failed schema checks halt Airflow DAG and alert.

**Output validation:**
- Hallucination checks on root-cause diagnoses. DSPy explanation cross-checked against actual schema diff logs and pipeline run history. Reference to non-existent column or table flagged.
- Taxonomy constraint on extraction. DSPy outputs must map to existing taxonomy entries. Unknown categories queued for human review, not auto-accepted.
- Score bounds enforcement: data quality scores 0-100, anomaly severity 0-1, NDCG 0-1. Out-of-range values clamped and logged.
- RAG chatbot grounding: answers must cite specific evidence from retrieved documents. Claims without citations flagged with low confidence warning.
- LLM-as-Judge confidence thresholds. AutoEval results below 0.6 confidence routed to manual review.

**Schema enforcement:** All API inputs/outputs validated with Pydantic models. FastAPI auto-generates OpenAPI docs from schemas. MCP tool inputs validated before execution.

**Safety layers:** Taxonomy constraint prevents category hallucination. Root-cause cross-check prevents fabricated explanations. Confidence thresholds prevent low-quality evaluations from entering metrics.

**When/where human approval is required:**
- Entity resolution pairs below 70% confidence → human review queue. Decisions feed back into ML classifier (active learning).
- Critical anomaly alerts (>20% data loss, primary source schema change) → require human acknowledgment before auto-remediation.
- Search eval disagreements (LLM-judge vs NDCG metric significantly disagree) → flagged for human calibration.
- Taxonomy additions (DSPy extracts category not in taxonomy) → queued for human review, not auto-added.

### 5.7 Evaluations & Testing

**LLM eval framework:**
- AutoEval (UC3): LLM-as-Judge calibrated on ESCI (target >80% agreement with human labels). Cohen's Kappa measured. Domain evaluation set of 300-500 queries with human-in-the-loop validation of 50-100 pairs.
- DSPy extraction (UC1): Precision/recall on extracted attributes measured against manually verified sample of 200 products.
- Root-cause diagnosis (UC2): Accuracy measured against known synthetic anomalies with ground truth causes.
- ArkSim stress testing: Simulate realistic multi-turn user conversations with the search system and RAG chatbot. ArkSim generates synthetic users who query the catalog, ask follow-up questions, and test edge cases at scale: instead of manually typing 50 test queries. Measures: response quality, tool calling accuracy, latency under load, failure modes.

**Unit tests:**
- ETL: Spark transformation correctness, schema validation, null handling
- APIs. FastAPI endpoint response codes, Pydantic validation, MCP tool outputs
- LLM wrappers. DSPy module input/output contracts, retry logic, error handling
- Pipeline logic: data quality scoring formula correctness, anomaly threshold behavior, RRF fusion math

**Integration tests:**
- End-to-end: ingest raw OFF product → enrich → score DQ → index in OpenSearch → search → evaluate
- Kafka: produce event → consume → process → store
- MCP: chatbot question → tool call → data retrieval → grounded answer

**CI pipeline:** GitHub Actions: lint (ruff) → unit tests (pytest) → integration tests → build Docker → deploy to ECR → deploy to EC2.

**Metrics we track:**

| Category | What we measure | Target |
|---|---|---|
| Search quality | NDCG@10 (how good is the ranking order of results) | > 0.60 on our evaluation set |
| Search quality | MRR (how quickly the first relevant result appears) | > 0.70 |
| Entity resolution | F1 score (balance of precision and recall in product matching) | > 0.85 |
| LLM reliability | Agreement rate between LLM judge and human labels | > 80% |
| Anomaly detection | Precision (when we flag an anomaly, is it real) | > 0.80 |
| Pipeline speed | Products processed per hour via Spark | > 100K/hour |
| Pipeline speed | Events consumed per minute via Kafka | > 500/min |
| Alert speed | Time from anomaly detected to alert delivered | < 5 minutes |
| LLM cost | Daily spend on Groq + Claude API calls | < $11/day dev, < $5 steady |
| Extraction quality | Accuracy of DSPy-extracted attributes vs manual review | > 90% on 200-product sample |

### 5.8 Proof of Concept (POC)

We have a working demo running locally on ~100 products:

**Preliminary EDA:**
- Open Food Facts: 210 columns parsed, completeness ranges 36-75% across key fields (brands, allergens, quantity), data quality scores range 40-70
- USDA: 100% field coverage on 6 tested fields, data quality scores 95-100
- Entity resolution: 20/20 test product names matched across USDA ↔ Instacart
- Instacart: 91% of baskets span 2+ departments, avg 10.1 items across 4.7 departments

**Example transformations:**
- DSPy extraction on 100 OFF products → structured attributes (dietary, brand, category) via Groq
- data quality scoring on Open Food Facts vs USDA products → visible contrast (40-70% vs 95-100%)
- Fuzzy matching via rapidfuzz: "Cheerios" ↔ "Cheerios Cereal" → 89% match score

**First LLM experiments:**
- DSPy + Groq extracting attributes from messy OFF descriptions: working with retry logic
- RRF fusion combining BM25 (rank-bm25) + embedding (sentence-transformers) results: working

**Small architecture demo:**
- 4-tab Streamlit app: data quality scores radar chart, entity resolution pairs, search results, association rules
- Plotly charts: histograms, time series, network graphs
- Running on Python 3.12 with Pandas (scales to Spark for production)

POC code saved in GitHub repository.

---

## 6. Project Plan & Timeline

### 6.1 Milestones

| Phase | Milestone | Description |
|---|---|---|
| M1 | Data ingestion | All 6 sources downloaded to S3. Kafka producers for 4 continuous sources. |
| M2 | Big data pipeline | Spark processing 4M+ OFF products. Airflow DAGs for all sources. Great Expectations validation. |
| M3 | LLM integration + guardrails | DSPy extraction on 50K-100K products (Groq). Taxonomy built. Pydantic validation. Hallucination checks. |
| M4 | Entity resolution + KG | rapidfuzz + ML classifier. Neo4j knowledge graph populated. MLflow tracking. |
| M5 | Search + evaluation | OpenSearch (BM25 + vector). Domain eval set built. AutoEval (Claude). NDCG/MRR baseline. |
| M6 | Observability | Isolation Forest on pipeline metrics. Pathway streaming telemetry. DSPy root-cause. Alert severity ranking. |
| M7 | MCP + Chatbot + Dashboard | 7 MCP tools. RAG chatbot (ChromaDB + Claude). Streamlit dashboard with all metrics. |
| M8 | CI/CD + Polish | GitHub Actions pipeline. Docker deployment to EC2. README. Architecture diagram. Demo video. |
| Stretch | Cross-category recs | UC4: Instacart basket mining + LLM affinity profiles. Only if M1-M8 complete. |

### 6.2 Timeline

**3-week build: April 1 – April 21, 2026**

| Week | Dates | Milestones | Key Deliverables |
|---|---|---|---|
| **Week 1** | Apr 1–7 | M1, M2, M3 (partial) | AWS setup. Data in S3 + PostgreSQL. Spark ingestion running. Kafka streaming. Airflow DAGs. Great Expectations validation. data quality scores computed. DSPy extraction on first 5K products. Taxonomy built. Neo4j initial load. |
| **Week 2** | Apr 8–14 | M3, M4, M5, M6 | DSPy scaled to 50K-100K. Entity resolution trained (MLflow). OpenSearch setup. Domain eval set built. AutoEval scoring. NDCG/MRR baseline. Isolation Forest running. Pathway streaming. Root-cause diagnosis. |
| **Week 3** | Apr 15–21 | M7, M8, Stretch | MCP server (7 tools). RAG chatbot. Dashboard. CI/CD. Docker deployment. Documentation. Demo video. Stretch goal: UC4 if time. |

---

## 7. Team Roles & Responsibilities

| Member | Role | Core Responsibilities | Shared Responsibilities |
|---|---|---|---|
| **Bhavya Likhitha Bukka** | **Project Lead, Data Pipeline + Enrichment** | Spark ingestion pipeline, Airflow DAG design, Kafka producer setup, DSPy extraction pipeline, entity resolution (rapidfuzz + ML classifier), Neo4j knowledge graph, product taxonomy construction, overall architecture decisions | Documentation, testing, code review, demo preparation |
| **Deepika Vaddadi** | **Data Quality + Observability + Cloud** | AWS infrastructure setup (S3, Snowflake, OpenSearch), Great Expectations validation rules, data quality scoring engine, Isolation Forest anomaly detection, Pathway streaming telemetry, DSPy root-cause diagnosis, alert severity ranking, MLflow experiment tracking setup | Documentation, testing, code review, demo preparation |
| **Aqeel Ryan** | **Search + LLM Applications + Frontend** | OpenSearch hybrid search (BM25 + vector + RRF), AutoEval with Claude as LLM judge, domain evaluation set creation, MCP server (7 tools), RAG chatbot (ChromaDB + Claude), Streamlit dashboard, GitHub Actions CI/CD, Docker deployment | Documentation, testing, code review, demo preparation |

**Workload distribution:** Each member owns one major vertical of the platform (pipeline + enrichment, quality + observability, search + application). All verticals are roughly equal in complexity and effort. Bhavya serves as overall project lead for architecture decisions and cross-team coordination.

---

## 8. Risks & Mitigation

### 8.1 Potential Risks

| Risk | Likelihood | Impact | Category |
|---|---|---|---|
| Groq free tier rate limits throttle DSPy extraction | High | Medium | API cost/scaling |
| OFF data messier than expected (>50% unparseable) | Medium | High | Data quality |
| OpenSearch BM25 + vector setup takes longer than expected | Medium | Medium | Infrastructure |
| LLM-as-Judge agreement with humans below 80% on ESCI | Medium | High | LLM reliability |
| Kafka + Airflow + Pathway conflicts on EC2 memory | Medium | Medium | Infrastructure |
| Entity resolution false positive rate too high | Low | High | ML accuracy |
| DSPy hallucination despite taxonomy constraint | Low | Medium | LLM reliability |

### 8.2 Mitigation Strategies

| Risk | Mitigation |
|---|---|
| Groq rate limits | Batch 10-20 products per call. Cache results with 24hr TTL. Fall back to Groq paid tier ($0.59/M tokens) if free tier insufficient. Design pipeline for subset (50K-100K) from start. |
| OFF data too messy | Great Expectations catches bad data at ingestion. data quality scoring handles variance gracefully (low score ≠ rejected: it's the input to the quality system). Skip products below minimum parseable threshold. |
| OpenSearch setup time | Budget 2-3 days. Fall back to rank-bm25 + sentence-transformers (demo stack) if OpenSearch not ready by Week 2. |
| LLM-judge below 80% | Iterate on Claude prompts. Add few-shot examples from ESCI. Narrow to product-category ESCI subset. If still below 70%, use human labels only (50-100) and report as limitation. |
| EC2 memory conflicts | Use t3.xlarge (16 GB). Run Kafka and Neo4j as Docker containers with memory limits. Pathway is lightweight (~200 MB). |
| Entity resolution false positives | Tune confidence threshold (start at 70%, adjust based on precision/recall in MLflow). Route uncertain pairs to human review. |
| DSPy hallucination | Taxonomy constraint via RAG reduces to <1% (DoorDash pattern). Pydantic validation catches invalid categories. Log and flag any output not in taxonomy. |

---

## 9. Expected Outcomes & Metrics

### 9.1 KPIs

| Category | Metric | Target | How We Measure It |
|---|---|---|---|
| **Accuracy** | Entity resolution F1 score | > 0.85 | Precision and recall tracked per confidence threshold in MLflow |
| **Accuracy** | DSPy attribute extraction correctness | > 90% | Manual review of 200 extracted products against actual attributes |
| **Accuracy** | LLM judge agreement with human labels | > 80% | Cohen's Kappa between Claude judgments and team-validated labels on ESCI |
| **Search quality** | NDCG@10 (ranking quality) | > 0.60 | Computed against our domain evaluation set, tracked in MLflow |
| **Anomaly detection** | Precision (flagged anomalies are real) | > 0.80 | Measured against synthetic injected anomalies with known ground truth |
| **Runtime** | Anomaly detection to alert delivery | < 5 min | Pathway timestamp compared to alert delivery timestamp |
| **Runtime** | Spark processing throughput | > 100K products/hour | Airflow task duration logs |
| **Throughput** | Kafka event consumption rate | > 500 events/min | Kafka consumer lag monitoring |
| **Throughput** | Products enriched via DSPy | 50K-100K (pipeline designed for 4M+) | Count of products with enrichment status complete in Snowflake |
| **Coverage** | Data quality score coverage | 100% of products scored 0-100 | Count of scored products in Snowflake |
| **Cost** | Daily LLM API spend | < $11/day dev, < $5 steady state | Per-component token and cost logs aggregated daily |
| **Cost** | Monthly AWS infrastructure | < $125/month | AWS billing dashboard |
| **Reliability** | Airflow pipeline success rate | > 95% of DAG runs succeed | Airflow task success rate metric |
| **Token efficiency** | Tokens per product enriched | Decrease 20% via DSPy optimization | MLflow: compare token counts before and after BootstrapFewShot/MIPRO |

### 9.2 Expected Benefits

**Technical value:**
- Unified product catalog from 4 fragmented sources with entity resolution across naming conventions
- Data quality quantified (0-100) and monitored continuously: not guessed at by spot checks
- Search quality measured automatically via AutoEval: not by expensive manual evaluation
- Pipeline health monitored in near-real-time with root-cause diagnosis: not discovered when reports break

**Business value:**
- Data quality engineer can identify and fix the worst quality products in minutes, not days
- Search team can catch ranking regressions before they reach customers
- Data platform team spends hours on root cause instead of days: LLM explains the "why"
- Cross-category recommendations unlock revenue from existing catalog data

**Portfolio value:**
- Fills 12+ skill gaps not covered by any existing project (knowledge graphs, entity resolution, data quality scoring, pipeline observability, Kafka, Spark, DSPy, hybrid search, LLM evaluation, MCP in new domain)
- Directly maps to roles at DoorDash, Airbnb, Instacart, Uber, Netflix, Walmart, Shopify, Databricks, Snowflake, Monte Carlo, and more

---

## 10. Token & Cost Report (Required)

### Token consumption by component

| Component | Provider | Est. Calls/Day | Est. Tokens/Day | Est. Cost/Day |
|---|---|---|---|---|
| UC1: DSPy extraction | Groq (free) | ~5,000 | ~2.5M input + 500K output | $0 (free tier) |
| UC2: Anomaly explanations | Groq (free) | ~50-100 | ~50K input + 25K output | $0 |
| UC3: AutoEval judging | Claude | ~2,000-5,000 | ~3M input + 1M output | ~$3-8 |
| UC4: Affinity profiles | Groq (free) | ~100-500 | ~200K input + 100K output | $0 |
| RAG Chatbot | Claude | ~100-500 | ~500K input + 200K output | ~$1-3 |

**Estimated total: $4-11/day during development, ~$2-5/day steady state.**

### Cost drivers

- AutoEval (UC3) is the largest cost: Claude reasoning over thousands of query-result pairs
- RAG Chatbot is second: conversational use with retrieval context
- All Groq tasks are free during development (free tier: ~30 req/min)

### Prompt optimization strategy

- **DSPy BootstrapFewShot/MIPRO**: automatically find shorter effective prompts. Fewer tokens per call = lower cost.
- **Batch calls**: 10-20 products per DSPy extraction call with structured JSON output. Reduces per-call overhead.
- **Model tiering**: Groq (free, fast) for routine bulk tasks. Claude only for tasks requiring reasoning depth.

### Caching / batching techniques

- **Embedding caching**: compute once, store in S3 + OpenSearch. Only re-embed changed products. Saves ~80% of embedding cost after initial load.
- **Result caching (Redis or in-memory)**: 24hr TTL on DSPy extraction results. Pipeline retries use cache instead of re-calling API.
- **Daily budget caps**: per-component spending limits. Auto-pause + alert when threshold reached.

### Tracking and reporting

- Every LLM call logged to PostgreSQL: component, model, input tokens, output tokens, latency, cost
- MLflow logs API cost as a metric per experiment run: compare cost across model versions
- Streamlit dashboard page: tokens by component, cost trend over time, cost per product enriched, most expensive prompts

### AWS infrastructure cost

| Service | Est. Monthly |
|---|---|
| EC2 (t3.large or t3.xlarge) | ~$60-120 |
| S3 (10 GB) | ~$0.25 |
| Data transfer | ~$5 |
| **Total AWS** | **~$65-125/month** |

---

## 11. Conclusion

This project builds a complete marketplace product intelligence and data quality observability platform: from messy multi-source catalog data to enriched knowledge graph, quality-scored products, hybrid search with automated evaluation, and real-time pipeline monitoring with LLM-powered root-cause diagnosis.

The platform is inspired by and modeled after production systems at DoorDash, Airbnb, Uber, Netflix, Walmart, Instacart, Faire, Pinterest, Spotify, Google, and Amazon. No single company builds all of this: we combined catalog intelligence, data quality observability, and search evaluation into one connected system where each layer feeds the others.

Every technique we build (entity resolution, data quality scoring, hybrid search, pipeline observability, LLM-based extraction, automated evaluation) applies to any product catalog at any marketplace. We chose grocery products as the domain because of data availability; the engineering is universal.

The platform fills 12+ skill gaps not covered by any existing team member project, directly maps to roles at the companies we're targeting, and demonstrates production-grade engineering patterns at meaningful scale.

---

## 12. References

### Engineering Blog Posts (Inspiration)

1. DoorDash: [How DoorDash Leverages LLMs for Better Search Retrieval (2024)](https://doordash.engineering/2024/02/27/how-doordash-leverages-llms-for-better-search-retrieval/)
2. DoorDash: [AutoEval: LLMs to Evaluate Search Result Pages (2025)](https://doordash.engineering/2025/01/21/autoeval-using-llms-to-evaluate-search-result-pages/)
3. DoorDash: [Things Not Strings: Understanding Search Intent (2020)](https://doordash.engineering/2020/12/15/things-not-strings-understanding-search-intent/)
4. DoorDash: [LLM-Powered Entity Profiles (2025)](https://doordash.engineering/2025/02/11/llm-entity-profiles/)
5. DoorDash: [Mind the Gap: LLMs for Multi-Vertical Recommendations (2025)](https://doordash.engineering/2025/03/04/mind-the-gap-llms-multi-vertical-recommendations/)
6. DoorDash: [Human-in-the-Loop for Menu Item Tagging (2020)](https://doordash.engineering/2020/08/28/overcome-the-cold-start-problem-in-menu-item-tagging/)
7. DoorDash: [Five Big Areas for Using Generative AI (2023)](https://doordash.engineering/2023/04/26/doordash-identifies-five-big-areas-for-using-generative-ai/)
8. Airbnb: [Wisdom of Unstructured Data: LAEP Attribute Extraction (2023)](https://medium.com/airbnb-engineering/wisdom-of-unstructured-data-building-airbnbs-listing-knowledge-from-big-text-data-7c533466a63c)
9. Airbnb: [Data Quality Score: The Next Chapter (2024)](https://medium.com/airbnb-engineering/data-quality-score-the-next-chapter-of-data-quality-at-airbnb-851dccda19c3)
10. Airbnb: [Data Quality at Airbnb: Midas Certification (2021)](https://medium.com/airbnb-engineering/data-quality-at-airbnb-870d03080469)
11. Airbnb: [Building Airbnb Categories with ML + human-in-the-loop (2023)](https://medium.com/airbnb-engineering/building-airbnb-categories-with-ml-human-in-the-loop-35b78a837725)
12. Uber: [INCA: From Restaurants to Retail (2025)](https://www.uber.com/blog/outrider-from-restaurants-to-retail/)
13. Uber: [Monitoring Data Quality at Scale (2017)](https://eng.uber.com/monitoring-data-quality-at-scale/)
14. Netflix: [Anomaly Detection for Global Scale (RPCA + DBSCAN)](https://www.slideshare.net/slideshow/anomaly-detection-for-global-scale-at-netflix/54798799)
15. Instacart: [Optimizing Search Relevance Using Hybrid Retrieval (2024)](https://tech.instacart.com/optimizing-search-relevance-at-instacart-using-hybrid-retrieval/)
16. Walmart: [Exploring an Entity Resolution Framework (2023)](https://medium.com/walmartglobaltech/exploring-an-entity-resolution-framework-across-various-use-cases-cb172632e4ae)
17. Faire: [Fine-tuning Llama3 to Measure Semantic Relevance in Search (2024)](https://craft.faire.com/fine-tuning-llama3-to-measure-semantic-relevance-in-search/)
18. Pinterest: [Multi-task Learning for Utility-based Ranking (2020)](https://medium.com/pinterest-engineering/multi-task-learning-and-calibration-for-utility-based-home-feed-ranking-64087a7bcbad)
19. Spotify: [How We Generated Millions of Content Annotations (2024)](https://engineering.atspotify.com/2024/10/how-we-generated-millions-of-content-annotations)
20. Google: [Data Validation for Machine Learning (2019)](https://research.google/pubs/pub47967/)
21. Amazon: [Automating Large-Scale Data Quality Verification (2018)](https://www.amazon.science/publications/automating-large-scale-data-quality-verification)

### Datasets

- Open Food Facts: https://world.openfoodfacts.org/data (ODbL v1.0)
- USDA FoodData Central: https://fdc.nal.usda.gov/download-datasets/ (Public domain)
- openFDA Food Enforcement: https://open.fda.gov/apis/food/enforcement/ (Public domain)
- Open Prices: https://prices.openfoodfacts.org/ (ODbL)
- Amazon ESCI: https://huggingface.co/datasets/tasksource/esci (Apache 2.0)
- Instacart Market Basket: https://www.kaggle.com/datasets/yasserh/instacart-online-grocery-basket-analysis-dataset (Non-commercial)

### Libraries & Tools

- DSPy: https://github.com/stanfordnlp/dspy (MIT)
- Great Expectations: https://github.com/great-expectations/great_expectations (Apache 2.0)
- Neo4j: https://neo4j.com/product/community/ (GPLv3)
- DeepEval: https://github.com/confident-ai/deepeval (Apache 2.0)
- MLflow: https://mlflow.org/ (Apache 2.0)
- ChromaDB: https://github.com/chroma-core/chroma (Apache 2.0)
- rapidfuzz: https://github.com/rapidfuzz/RapidFuzz (MIT)
- mlxtend: https://github.com/rasbt/mlxtend (BSD-3)
- ArkSim: https://github.com/arksim-ai/arksim (Apache 2.0)
- Pathway: https://pathway.com/ (BSL 1.1)
- Apache Kafka: https://kafka.apache.org/ (Apache 2.0)
- Apache Spark: https://spark.apache.org/ (Apache 2.0)
- Apache Airflow: https://airflow.apache.org/ (Apache 2.0)
- FastAPI: https://fastapi.tiangolo.com/ (MIT)
- Streamlit: https://streamlit.io/ (Apache 2.0)

---

## Appendix

### A. System Architecture Diagram (Mermaid)

```mermaid
graph TB
    subgraph Sources["Data Sources"]
        Open Food Facts[Open Food Facts<br/>4M products, daily]
        USDA[USDA FoodData<br/>454K, monthly]
        FDA[openFDA Recalls<br/>28K, weekly]
        OP[Open Prices<br/>240K, real-time]
        ESCI[Amazon ESCI<br/>2.68M, static]
        IC[Instacart<br/>37.3M rows, static]
    end

    subgraph Ingestion["Ingestion Layer"]
        Kafka[Apache Kafka<br/>4 topics]
        Airflow[Apache Airflow<br/>Scheduled DAGs]
        Spark[Apache Spark<br/>Batch processing]
    end

    subgraph Intelligence["Intelligence Pipeline"]
        DSPy[DSPy + Groq<br/>Attribute extraction]
        ER[Entity Resolution<br/>rapidfuzz + ML]
        KG[Neo4j<br/>Knowledge Graph]
        Tax[Product Taxonomy<br/>USDA L2 + Open Food Facts L3]
        GE[Great Expectations<br/>Validation]
        DQ[Data Quality Scoring<br/>0-100 per product]
    end

    subgraph Observability["Observability Layer"]
        PW[Pathway<br/>Streaming telemetry]
        IF[Isolation Forest<br/>Anomaly detection]
        RC[DSPy + Groq<br/>Root-cause diagnosis]
        AL[Alert Engine<br/>Severity ranking]
    end

    subgraph Search["Search + Evaluation"]
        OS[OpenSearch<br/>BM25 + vector]
        AE[AutoEval<br/>Claude LLM-as-Judge]
        ML[MLflow<br/>NDCG/MRR tracking]
    end

    subgraph UserFacing["User-Facing Layer"]
        API[FastAPI<br/>REST endpoints]
        MCP[MCP Server<br/>7 tools]
        Chat[RAG Chatbot<br/>Claude + ChromaDB]
        Dash[Streamlit<br/>Dashboard]
    end

    subgraph Storage["Storage"]
        S3[Amazon S3<br/>Data lake]
        SF[Snowflake<br/>Analytical warehouse]
        PG[PostgreSQL<br/>Operational DB]
        Chroma[ChromaDB<br/>RAG vectors]
    end

    Open Food Facts --> Kafka
    OP --> Kafka
    FDA --> Kafka
    Open Food Facts --> Airflow
    USDA --> Airflow
    FDA --> Airflow
    Kafka --> Spark
    Airflow --> Spark
    Spark --> S3
    Spark --> SF
    S3 --> DSPy
    Tax --> DSPy
    DSPy --> ER
    ER --> KG
    GE --> DQ
    Spark --> GE
    DQ --> SF
    KG --> OS
    ESCI --> AE
    OS --> AE
    AE --> ML
    SF --> PW
    PW --> IF
    IF --> RC
    RC --> AL
    AL --> PG
    API --> MCP
    MCP --> Chat
    Chat --> Chroma
    Chat --> Dash
    SF --> Dash
    PG --> Dash
    ML --> Dash
    IC --> |UC4 Stretch| PG
```

### B. MCP Tool Definitions

```json
{
  "tools": [
    {
      "name": "score_product_quality",
      "description": "Returns 0-100 data quality score with dimension breakdown",
      "inputSchema": {
        "type": "object",
        "properties": {
          "product_id": {"type": "string"}
        },
        "required": ["product_id"]
      }
    },
    {
      "name": "get_anomaly_alerts",
      "description": "Returns active anomaly alerts filtered by severity",
      "inputSchema": {
        "type": "object",
        "properties": {
          "severity": {"type": "string", "enum": ["critical", "high", "medium", "low", "all"]}
        },
        "required": ["severity"]
      }
    },
    {
      "name": "search_catalog",
      "description": "Hybrid search (BM25 + embeddings + RRF) over enriched catalog",
      "inputSchema": {
        "type": "object",
        "properties": {
          "query": {"type": "string"},
          "top_k": {"type": "integer", "default": 10}
        },
        "required": ["query"]
      }
    },
    {
      "name": "get_entity_graph",
      "description": "Returns Neo4j subgraph for a product",
      "inputSchema": {
        "type": "object",
        "properties": {
          "product_id": {"type": "string"}
        },
        "required": ["product_id"]
      }
    },
    {
      "name": "get_pipeline_health",
      "description": "Returns pipeline status, freshness, active drifts, NDCG trend",
      "inputSchema": {
        "type": "object",
        "properties": {}
      }
    },
    {
      "name": "run_dq_check",
      "description": "Triggers Great Expectations validation on a data source",
      "inputSchema": {
        "type": "object",
        "properties": {
          "source_name": {"type": "string", "enum": ["off", "usda", "fda", "open_prices"]}
        },
        "required": ["source_name"]
      }
    },
    {
      "name": "get_search_eval_report",
      "description": "Returns AutoEval results with 7-day comparison",
      "inputSchema": {
        "type": "object",
        "properties": {
          "date": {"type": "string", "format": "date"}
        },
        "required": ["date"]
      }
    }
  ]
}
```

### C. Sample DSPy Extraction Prompt

```python
import dspy

class ProductEnricher(dspy.Signature):
    """Extract structured attributes from a messy product description.
    Only use categories from the provided taxonomy. If unsure, output 'unknown'."""

    product_name: str = dspy.InputField(desc="Raw product name from Open Food Facts")
    description: str = dspy.InputField(desc="Raw product description/ingredients")
    taxonomy: str = dspy.InputField(desc="Allowed categories from product taxonomy")

    brand: str = dspy.OutputField(desc="Normalized brand name")
    category_l2: str = dspy.OutputField(desc="L2 category from taxonomy")
    category_l3: str = dspy.OutputField(desc="L3 category from taxonomy")
    dietary: list[str] = dspy.OutputField(desc="Dietary tags: vegan, gluten-free, organic, etc.")
    size: str = dspy.OutputField(desc="Normalized size with unit: '5.3 oz', '500 ml'")
    confidence: float = dspy.OutputField(desc="Extraction confidence 0-1")

enricher = dspy.ChainOfThought(ProductEnricher)
```

### D. Data Quality Scoring Formula

```python
def compute_dq_score(product: dict) -> float:
    """Compute 0-100 data quality score across 4 dimensions."""

    # Completeness: % of key fields that are non-null
    key_fields = ['product_name', 'brands', 'categories', 'ingredients_text',
                  'quantity', 'allergens', 'nutrition_grade']
    filled = sum(1 for f in key_fields if product.get(f))
    completeness = (filled / len(key_fields)) * 100

    # Consistency: do related fields agree?
    consistency_checks = [
        brand_matches_name(product),       # brand in product_name?
        category_matches_ingredients(product),  # category plausible given ingredients?
        size_format_valid(product),         # size in standard format?
    ]
    consistency = (sum(consistency_checks) / len(consistency_checks)) * 100

    # Accuracy: are values plausible?
    accuracy_checks = [
        price_in_range(product),            # price reasonable for category?
        nutrition_values_valid(product),     # no negative calories?
        barcode_format_valid(product),       # valid EAN/UPC?
    ]
    accuracy = (sum(accuracy_checks) / len(accuracy_checks)) * 100

    # Freshness: how recently updated?
    days_since_update = (now() - product['last_modified']).days
    freshness = max(0, 100 - days_since_update)  # lose 1 point per day

    # Weighted composite
    score = (0.35 * completeness +
             0.25 * consistency +
             0.25 * accuracy +
             0.15 * freshness)

    return round(score, 1)
```