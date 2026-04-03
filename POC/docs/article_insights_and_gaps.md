# Engineering Article Insights & Project Gap Analysis

What we learned from reading all 20 engineering blog posts listed in the project proposal, and what it means for our data and pipeline choices.

---

## Part 1: What Each Article Taught Us

### DoorDash (7 Articles)

#### 1. LLMs for Better Search Retrieval (2024)

**What they did:** Used LLMs to understand search queries by breaking them into structured components. A query like "small no-milk vanilla ice cream" gets segmented into {Quantity: small, Dietary: no-milk, Flavor: vanilla, Category: ice cream}.

**What data they used:**
- Menu items and retail product catalogs with rich metadata
- A knowledge graph with controlled vocabularies covering dietary preferences, flavors, product categories, cuisine types
- Search query logs from live user traffic

**Their pipeline:**
1. Items annotated with metadata from knowledge graph before indexing
2. LLM segments queries into structured components
3. Embeddings generated for queries and knowledge graph concepts
4. ANN retrieves top 100 taxonomy concepts per query segment
5. RAG constrains the LLM to pick from retrieved candidates only — no free generation
6. Post-processing validation catches hallucinations
7. Manual audits on every batch via statistically significant sampling

**Key metrics:** <1% hallucination rate on segmentation, ~30% increase in popular dishes carousel trigger rate, >2% whole page relevance improvement.

**Critical insight for our project:** Pure LLM generation hallucinates. The breakthrough was constraining LLM outputs through RAG to a controlled vocabulary from the knowledge graph. The knowledge graph IS the data quality layer. Without it, the LLM generates plausible but incorrect taxonomy mappings. **We need to build our food taxonomy before running DSPy extraction.**

---

#### 2. AutoEval — LLMs to Evaluate Search (2025)

**What they did:** Replaced human search evaluators with a fine-tuned GPT-4o that judges search result relevance.

**What data they used:**
- Live search traffic queries sampled across intent type, frequency, geography, and time of day
- Expert-labeled golden data where annotators provided justifications, not just labels
- External rater audit data for quality control

**Their pipeline:**
1. Sample real user queries from live traffic (stratified sampling)
2. Construct structured prompts per evaluation task type
3. Fine-tuned GPT-4o returns relevance judgments with chain-of-thought reasoning
4. Judgments rolled up into Whole-Page Relevance (WPR) scores
5. External raters audit a sample of LLM judgments
6. Flagged items investigated by internal experts
7. Findings feed back into prompt improvements and new golden data

**Key metrics:** 98% reduction in evaluation turnaround time, 9x increase in evaluation capacity.

**Critical insight for our project:** Expert annotations required justification, not just labels — the fine-tuning data taught the model both correct answers AND reasoning. The continuous HITL loop (experts create golden data → model fine-tuned → external raters audit → experts refine) is what made automation trustworthy. **We need to build our own evaluation set with justified labels, not just use ESCI as-is.**

---

#### 3. LLM-Powered Entity Profiles (2025)

**What they did:** Generated personalized consumer, merchant, and item profiles using LLMs. Used these profiles to create personalized carousels like "Late-Night Noodle Cravings" and "Cozy Italian Comfort Food."

**What data they used:**
- Consumer profiles: past orders, browsing history, cuisine patterns, time-of-day behavior
- Merchant profiles: primary offerings, cuisine type, service quality, review data
- Item profiles: ingredients, taste profiles, dietary classifications

**Their pipeline:**
1. LLM generates carousel titles per user per time period
2. Titles converted to embeddings for semantic matching against restaurants
3. Three separate LLMs independently review every title (LLMs-as-jury, single-veto system)
4. Store and item retrieval matches carousel embeddings to restaurant embeddings
5. Ranking balances semantic relevance with click/conversion likelihood

**Key design principle:** "Code for facts, LLMs for narrative." Traditional code handles factual extraction (order frequency, top-selling items). LLMs handle interpretation (summarizing taste profiles, describing ambiance from reviews).

**Critical insight for our project:** Not everything needs an LLM. Factual data extraction should use traditional code. LLMs are only for where interpretation is needed. Content moderation (3 LLMs as jury) is a first-class pipeline stage, not an afterthought. **Applies to our RAG chatbot — ground answers in facts, use LLM only for narrative.**

---

#### 4. HITL for Menu Item Tagging (2020)

**What they did:** Tagged millions of menu items with attributes (cuisine type, dietary info) using a combination of classifiers and human annotators.

**What data they used:**
- Menu item names and descriptions across the entire DoorDash catalog
- Hierarchical tag taxonomy (e.g., "Chinese" → "Shanghainese", "Sichuan")
- Seed data from high-precision classifier outputs
- Augmented data from edit-distance and embedding-cosine-similarity neighbors

**Their pipeline:**
1. Design hierarchical taxonomy that maps to binary questions
2. High-precision classifier selects seed samples for annotation
3. Amazon Mechanical Turk for simple questions, professional annotators for complex ones
4. Data augmentation via edit distance and embedding similarity neighbors
5. Active learning: embeddings identify ambiguous samples near decision boundaries
6. Model trains on accumulated labels
7. Low-confidence predictions routed back for human annotation

**Key metrics:** Nearly doubled recall while maintaining precision for the rarest tags.

**Critical insight for our project:** The cold start problem for rare tags is a data problem, not a model problem. The taxonomy design was the key innovation — structuring tags hierarchically meant annotations could be reused. Active learning (model identifies ambiguous samples → humans label them → model retrains) is what made scaling feasible. **Directly applicable to our entity resolution — route low-confidence matches to human review.**

---

#### 5. Things Not Strings — Search Intent (2020)

**What they did:** Built a knowledge graph to understand food concepts and their relationships, replacing a bag-of-words search system.

**What data they used:**
- Knowledge graph with three entity types: Stores, Store Categories, Store Tags
- Three relationship types between entities
- Search query logs
- Manually curated food concept relationships

**Their pipeline:**
1. Manually curated knowledge graph of food concept relationships
2. When query arrives, system identifies which food entity/concept the user means
3. Graph traversal derives similar and related concepts
4. Results include semantically related items, not just exact string matches
5. Ranking considers entity relationships

**Key metrics:** 76% reduction in null results, 9% CTR improvement, 10% conversion improvement.

**Critical insight for our project:** The knowledge graph had to be manually created. The quality of the graph directly determined the quality of search. "Chicken" should find Korean, Southern, and Mexican restaurants — but only if the graph captures those relationships. **This is a data curation problem, not an algorithm problem. Our Neo4j knowledge graph needs thoughtful relationship design.**

---

#### 6. Mind the Gap — Multi-Vertical Recs / H-RAG (2025)

**What they did:** Used LLMs to bridge behavioral silos between restaurant ordering and grocery shopping. Users have dense restaurant history but sparse grocery history.

**What data they used:**
- 20% sample of last 3 months of consumer data
- Restaurant orders (item names, chronologically ordered)
- Search queries
- Four-level product taxonomy: L1 (broad) → L2 (sub) → L3 (specific) → L4 (individual)
- 1,000 samples per signal type for human evaluation

**Their pipeline (H-RAG — Hierarchical RAG):**
1. Collect 3 months of consumer behavior
2. First pass: identify broad L1/L2 taxonomic affinities
3. Second pass: L1/L2 classifications constrain search space for L3/L4 retrieval
4. Confidence gating: temperature 0.1, threshold ≥ 0.80
5. LLM features concatenated with user/item engagement features
6. Multi-task ranking: shared trunk with task-specific heads for CTR, add-to-cart, purchase

**Key metrics:** AUC-ROC +4.4%, MRR +4.8% offline. +4.3% AUC-ROC online. ~80% cost reduction.

**Critical insight for our project:** L1 and L4 taxonomy levels were useless in practice — L1 too generic, L4 too sparse. Only L2 and L3 provided meaningful signals. The 80% cost saving came from deduplicating taxonomy mappings (many orders map to same tagsets). **When we build our food taxonomy, focus on L2/L3 granularity, not too broad or too specific.**

---

#### 7. Five Big Areas for GenAI (2023)

**What they did:** Strategic roadmap for GenAI at DoorDash across 5 areas: customer assistance, recommendations, content creation, data extraction, employee productivity.

**What data they used:**
- Menu images (OCR extraction)
- Receipts (OCR error detection)
- Unstructured text (nutritional info, ingredients)
- Knowledge graph relationships
- Customer order history + location + temporal context

**Critical insight for our project:** DoorDash's marketplace runs on structured data (item names, prices, ingredients) but input arrives unstructured (menu photos, receipts, merchant descriptions). GenAI's primary value is converting unstructured marketplace data into structured, queryable data at scale. **This is exactly what our UC1 does — unstructured OFF/FDA data → structured enriched catalog.**

---

### Airbnb (4 Articles)

#### 8. LAEP — Listing Attribute Extraction Pipeline (2023)

**What they did:** Extracted structured attributes from unstructured listing content (text descriptions + photos). Hosts write "ocean view from the balcony" but that doesn't map to a structured "has ocean view" field.

**What data they used:**
- Listing titles and descriptions (free-text from hosts)
- Listing photos
- Structured listing metadata (amenities checkboxes)

**Their pipeline:**
1. Pull raw listing text, photos, and existing structured fields
2. LLMs extract attributes from text, CV models extract from photos
3. Cross-reference extracted attributes against existing structured data
4. Confidence scoring on extractions
5. Output: enriched structured attribute catalog per listing

**Key metrics:** Precision and recall per attribute type, coverage percentage, human evaluation accuracy.

**Critical insight for our project:** Unstructured content contains far richer attribute information than structured forms. Extracting this programmatically requires heavy investment in precision — a false positive directly harms the user experience. **Same for our DSPy extraction: falsely tagging a product as "gluten-free" when it isn't would be harmful.**

---

#### 9. Data Quality Score (2024)

**What they did:** Created a single composite Data Quality Score (0-100) for every data asset in their warehouse.

**What data they used:**
- Metadata about internal data assets (tables, columns, pipelines)
- Operational metrics: freshness (SLA adherence), completeness (null rates), schema stability
- Usage data: query frequency, who uses it, for what
- Incident history: past DQ incidents per asset

**Their pipeline:**
1. Automated profiling of every table/column — null rates, freshness, schema changes
2. Composite score aggregating freshness, completeness, accuracy, consistency, lineage health
3. Score exposed in internal data catalog
4. Score changes trigger alerts
5. Teams accountable for maintaining scores above thresholds

**Critical insight for our project:** A single composite score makes data quality actionable. Without a number, "data quality" is abstract. The score creates a feedback loop: producers see their score drop and fix issues proactively. **This is exactly our UC2 — DQ Score 0-100 per product, exposed in dashboard and chatbot.**

---

#### 10. Midas — Data Quality (2021)

**What they did:** Created a tiered certification system for datasets. Only datasets passing all quality checks earn "Midas" certification and are recommended for use.

**What data they used:**
- All data flowing through canonical/certified datasets
- Validation rules per table/column
- Row count anomalies, null rate thresholds, distribution drift, referential integrity

**Their pipeline:**
1. Teams define certified datasets with explicit contracts (schema, freshness SLAs, DQ checks, ownership)
2. Automated checks run on every pipeline execution
3. Only passing datasets earn "Midas" certification
4. Non-certified datasets flagged in catalog
5. Continuous monitoring with alerting on failures

**Key metrics:** Check pass/fail rates, SLA adherence, null rates vs thresholds, row count anomaly detection, incident count and MTTR.

**Critical insight for our project:** The problem isn't detecting bad data — it's that nobody knows which datasets to trust. Certification creates positive incentives. **Applies to our pipeline: after enrichment, products that pass all DQ checks get "certified" status, others flagged for review.**

---

#### 11. Categories with ML + HITL (2023)

**What they did:** Classified millions of listings into categories ("Beachfront", "Treehouses", "A-frames") using ML + human reviewers for subjective/ambiguous cases.

**What data they used:**
- Listing attributes, photos, text descriptions, geospatial data
- Human labels from editorial/ops teams for training and edge cases
- Guest feedback (did listing match category expectation?)

**Their pipeline:**
1. Product team defines category taxonomy
2. LAEP extracts features from text + photos + structured data
3. ML classifies listings (multi-label)
4. Human reviewers handle ambiguous cases and correct errors
5. Guest feedback feeds back into retraining

**Critical insight for our project:** Categories that seem simple are hard at scale. "Beachfront" requires resolving: on the beach or 2 blocks away? Host claim vs reality? The HITL component was essential for defining category boundaries that pure ML couldn't learn. **Same for our food categories: "organic" means different things across sources. Human review needed for ambiguous cases.**

---

### Uber (2 Articles)

#### 12. INCA — Catalog Enrichment (2025)

**What they did:** Enriched millions of Uber Eats menu items that arrive with missing/incorrect attributes across hundreds of thousands of restaurants.

**What data they used:**
- Menu items across hundreds of thousands of restaurants
- Items with missing descriptions, photos, dietary tags, categories
- Multilingual, highly heterogeneous data

**Their pipeline:**
1. Ingest raw merchant catalog data
2. LLM extracts and normalizes missing attributes from item names/descriptions
3. Embedding-based similarity matching propagates attributes from known to unknown items
4. HITL validation for low-confidence predictions
5. Corrections re-train models

**Key metrics:** Attribute coverage rate, precision/recall of inferred attributes, human override rate, downstream click-through and conversion rate.

**Critical insight for our project:** Catalog data quality directly drives revenue — items with complete attributes get significantly more orders. The challenge isn't building one model; it's handling the long tail of edge cases across millions of items. **Validates our approach: OFF's missing attributes hurt discoverability. Enrichment makes products findable.**

---

#### 13. Data Quality at Scale (2017)

**What they did:** Built automated data quality monitoring across all Uber datasets.

**What data they used:**
- Hundreds of Hive tables with billions of rows
- Column-level null rates, value distributions, schema drift

**Their pipeline:**
1. Automated DQ checks as part of ETL pipelines
2. Statistical profiling: null rates, distributions, schema drift
3. Anomaly detection on time-series of DQ metrics
4. Alerting when quality degrades
5. Organization-wide dashboard

**Critical insight for our project:** Data quality is a time-series problem. You track metrics over time and detect anomalies, rather than applying static rules. At scale, manual inspection is impossible. **This is our UC2 observability layer — track DQ metrics over time via Kafka, detect anomalies with Isolation Forest.**

---

### Netflix (1 Article)

#### 14. RPCA + DBSCAN Anomaly Detection

**What they did:** Detected anomalies in millions of streaming performance time series using matrix decomposition.

**What data they used:**
- Millions of time series: per-title, per-device, per-region streaming metrics
- Metrics: stream starts, rebuffer rates, errors, latency
- Inherently seasonal data (viewing patterns vary by time of day, day of week)

**Their pipeline:**
1. Collect high-dimensional time-series into a matrix (rows = time, columns = metric streams)
2. RPCA decomposes matrix into low-rank (normal behavior) + sparse (anomalies)
3. DBSCAN clusters correlated anomalies into single incidents
4. Grouped anomalies presented as incidents, not thousands of individual alerts

**Key metrics:** Alert precision, alert volume reduction (orders of magnitude), detection latency, false negative rate.

**Critical insight for our project:** Individual anomaly detection per metric produces too many alerts. RPCA naturally separates systemic patterns from true anomalies. DBSCAN then groups correlated anomalies into root causes. **Validates our UC2 anomaly detection approach. Key: group related anomalies, don't just flag individual metrics.**

---

### Instacart (1 Article)

#### 15. Hybrid Retrieval (2024)

**What they did:** Combined lexical (keyword) and semantic (embedding) search for grocery products.

**What data they used:**
- Product catalog: hundreds of thousands of grocery SKUs across thousands of retailers
- Search queries: millions per day
- Click/add-to-cart/purchase signals
- Product attributes: brand, category, size, dietary info

**Their pipeline:**
1. Lexical retrieval: Elasticsearch with grocery-specific tokenization (oz vs ounce, brand abbreviations)
2. Semantic retrieval: Dense embeddings trained on query-product interaction pairs, indexed in ANN
3. Hybrid fusion: Reciprocal Rank Fusion (RRF) combines both result sets
4. Re-ranking: Cross-encoder or LTR model re-ranks using personalization and purchase history

**Key metrics:** Recall@K, NDCG, add-to-cart rate, latency P50/P99.

**Critical insight for our project:** Neither lexical nor semantic retrieval alone works for grocery. Lexical handles exact brand/product matches but fails on "healthy snack." Semantic handles intent but misses exact matches. Hybrid with RRF gave significant improvements on tail queries. **Validates our UC3 hybrid search approach (BM25 + embeddings + RRF).**

---

### Walmart (1 Article)

#### 16. Entity Resolution (2023)

**What they did:** Matched/deduplicated tens of millions of product listings from thousands of suppliers and marketplace sellers.

**What data they used:**
- Product catalog from thousands of suppliers
- Inconsistent naming, varying attribute schemas, different images
- No universal identifier across sources

**Their pipeline:**
1. Blocking/candidate generation: LSH on title TF-IDF + category constraints to reduce O(n²) space
2. Pairwise features: title similarity (Jaccard, edit distance, semantic), attribute overlap, brand normalization, price proximity
3. Gradient-boosted classifier: match/non-match/uncertain per pair
4. Transitive closure: graph-based clustering merges pairs into product clusters
5. Human review for low-confidence matches

**Key metrics:** Precision, recall, F1 on held-out labeled pairs, cluster purity. Prioritized precision — false merges are worse than missed matches.

**Critical insight for our project:** Blocking strategy is critical at scale. Too aggressive and you miss matches, too loose and computation explodes. Combining multiple blocking keys (title n-grams + brand + category) gave the best trade-off. **Directly applicable to our OFF ↔ USDA entity resolution. We need blocking before pairwise comparison.**

---

### Faire (1 Article)

#### 17. Llama3 Search Relevance (2024)

**What they did:** Fine-tuned Llama 3 8B as a relevance judge to label search query-product pairs, then used those labels to train the production ranking model.

**What data they used:**
- Product catalog (hundreds of thousands of wholesale products)
- Search query logs with click/purchase signals
- Human-annotated relevance judgments (graded scale)
- Synthetic labels from GPT-4 for scale

**Their pipeline:**
1. Fine-tune Llama 3 8B with LoRA on human relevance labels + GPT-4 synthetic labels
2. Deploy fine-tuned model as offline annotation pipeline
3. Model labels query-product pairs in bulk
4. Production ranking model (lighter, latency-sensitive) trained on these LLM-generated labels
5. A/B test: compare ranker trained on LLM labels vs baseline

**Key metrics:** Agreement with human annotators, NDCG of downstream ranker, cost per label, throughput.

**Critical insight for our project:** A fine-tuned 8B model approaches GPT-4 quality for domain-specific relevance at a fraction of cost. The key pattern: LLM as teacher (offline labeling tool), not as server (too slow for real-time). **This is our AutoEval pattern — use LLM to generate evaluation labels offline, train production model on them.**

---

### Pinterest (1 Article)

#### 18. Multi-task Learning for Ranking (2020)

**What they did:** Replaced a single engagement score with separate calibrated prediction heads per action type (click, repin, close-up, long-click, hide).

**What data they used:**
- User engagement logs: clicks, repins, close-ups, long-clicks, hides
- 80+ features per pin (user features, pin performance, position, device)
- 7 days of logs for training, next day for testing
- 400+ million monthly users

**Their pipeline:**
1. Features fed into AutoML model for representation learning
2. Shared DNN layers (hard parameter sharing across all tasks)
3. Separate output heads per engagement type
4. Calibration layer: Logistic Regression per head to produce true probabilities
5. Utility function: weighted sum of calibrated probabilities
6. Business stakeholders adjust weights without retraining

**Key metrics:** Calibration error, log loss, Brier score, AU-PRC. Video distribution +40%.

**Critical insight for our project:** Decouple prediction from ranking logic. Business weights can be adjusted in hours instead of weeks of retraining. L2/L3 taxonomy levels provide meaningful signal, L1 too generic, L4 too sparse. **Applicable to UC4: separate recommendation signals (co-purchase, category affinity, dietary match) combined via adjustable weights.**

---

### Spotify (1 Article)

#### 19. Content Annotations (2024)

**What they did:** Added semantic annotations (mood, activity, theme) to hundreds of millions of tracks and podcast episodes.

**What data they used:**
- Audio content catalog
- Track titles, artist bios, lyrics, podcast descriptions
- Audio features (tempo, energy, valence)
- User interaction data

**Their pipeline:**
1. Audio feature extraction from actual audio signals
2. LLM-based annotation from text metadata
3. Multi-modal fusion of audio + text annotations
4. Taxonomy management for consistent ontology
5. Sampling-based human review of automated annotations

**Critical insight for our project:** No single signal is sufficient — combine multiple sources. The quality challenge is consistency: the same label must mean the same thing whether applied by an LLM, a model, or a human. **Taxonomy governance is as important as model accuracy. Relevant to our knowledge graph design.**

---

### Google (1 Article)

#### 20. Data Validation for ML — TFX / TFDV (2019)

**What they did:** Built TensorFlow Data Validation (TFDV) to automatically validate ML training and serving data by detecting schema violations, distribution drift, and anomalies.

**What data they used:**
- ML training and serving datasets with billions of examples and thousands of features
- Feature statistics: mean, stddev, quantiles, top-K values, % missing
- Schema definitions: expected features, types, value ranges, domain vocabularies

**Their pipeline:**
1. Automatically infer schema from training data
2. Compute distributional statistics per feature using Apache Beam
3. Compare new data statistics against schema
4. Detect: unexpected features, missing features, type mismatches, distribution skew, feature drift
5. Schema evolution with human approval

**Critical insight for our project:** The majority of ML pipeline failures in production are data problems, not model problems. Training-serving skew detection was particularly valuable: models silently degrade without explicit validation. **Validates our Great Expectations + pipeline monitoring approach. Check data before it enters the pipeline, not after.**

---

### Amazon (1 Article)

#### 21. Data Quality Verification — Deequ (2018)

**What they did:** Built Deequ, an open-source framework that treats data quality constraints as "unit tests for data."

**What data they used:**
- Internal datasets across all Amazon business units
- Datasets ranging from millions to billions of rows in S3/data lakes

**Their pipeline:**
1. Automatically profile dataset and suggest quality constraints
2. Run constraints against data using Spark
3. Compute metrics: completeness, consistency, uniqueness, compliance rate
4. Incremental computation for append-only datasets (only process new data)
5. Track metrics over time, alert on deviations

**Critical insight for our project:** Data quality verification must be declarative and unit-testable. Constraint suggestion was key for adoption — teams with no DQ experience could start immediately. Incremental computation was essential at scale. **Validates Great Expectations choice. Also: suggest constraints automatically from data profiling, don't just manually define them.**

---

## Part 2: Patterns Across All 20 Articles

### Pattern 1: Knowledge graphs / taxonomies are the foundation (8 articles)

DoorDash (articles 1, 2, 4, 5, 6), Airbnb (11), Spotify (19), and Pinterest (18) all built taxonomies BEFORE building ML/LLM systems on top. The taxonomy constrains LLM outputs, prevents hallucination, and defines the vocabulary for search and categorization.

**DoorDash's L1-L4 taxonomy finding is critical:** L1 (broad, like "Food") is too generic. L4 (individual products) is too sparse. L2 and L3 provide the meaningful signal.

### Pattern 2: HITL is non-negotiable (10 articles)

Every system that uses LLMs for extraction or evaluation includes human oversight:
- DoorDash: expert auditing + crowdsourced annotation + structured sampling
- Airbnb: editorial teams handle ambiguous categories
- Uber INCA: human validation for low-confidence predictions
- Walmart: human review for low-confidence entity matches
- Faire: human annotators create ground truth, LLM scales it

### Pattern 3: Data quality is a time-series problem (5 articles)

Uber DQ (13), Netflix RPCA (14), Google TFDV (20), Amazon Deequ (21), and Airbnb Midas (10) all track quality metrics OVER TIME and detect anomalies, rather than applying static one-time rules.

### Pattern 4: Hybrid search beats single-method (3 articles)

Instacart (15), DoorDash (1), and Netflix (14) all found that combining methods (lexical + semantic, RPCA + DBSCAN) outperforms any single approach.

### Pattern 5: LLMs as offline tools, not real-time servers (4 articles)

DoorDash AutoEval (2), Faire (17), DoorDash Entity Profiles (3), and Uber INCA (12) all use LLMs for batch/offline processing (labeling, extraction, profile generation), not real-time serving. Production models are lighter and faster.

### Pattern 6: Composite scores drive action (2 articles)

Airbnb DQ Score (9) and Airbnb Midas (10) both found that a single number creates accountability. Teams fix issues proactively when they can see their score drop.

### Pattern 7: Schema validation prevents silent failures (3 articles)

Google TFDV (20), Amazon Deequ (21), and Uber DQ (13) all emphasize: validate data BEFORE it enters the pipeline. Most ML failures are data problems, not model problems.

---

## Part 3: Gap Analysis — What We Have vs What Articles Say We Need

| What Articles Say You Need | Do We Have It? | Status | Which Articles |
|---|---|---|---|
| Messy product catalog to enrich | **YES** | Open Food Facts (4M products, crowdsourced, messy) | DoorDash 1, 4, 7; Uber INCA |
| Clean reference catalog to enrich against | **YES** | USDA FoodData (454K, government, complete) | DoorDash 1; Uber INCA |
| Multiple sources with different schemas for entity resolution | **YES** | OFF + USDA + FDA + Instacart (4 different naming conventions) | Walmart 16 |
| Knowledge graph / taxonomy built BEFORE ML/LLM systems | **NEED TO BUILD** | Must merge USDA categories + OFF categories into unified L2/L3 taxonomy with controlled vocabularies | DoorDash 1, 5, 6; Airbnb 11; Spotify 19 |
| Controlled vocabulary to constrain LLM outputs | **NEED TO BUILD** | Define: dietary tags, cuisine types, product types, brand normalization rules, unit standardization | DoorDash 1 (<1% hallucination with this) |
| Composite DQ score (0-100) per data asset | **YES** | OFF low (40-70%) vs USDA high (95-100%) creates real variance | Airbnb DQ Score 9; Airbnb Midas 10 |
| Pipeline metrics tracked as time series | **YES** | Kafka streams metrics from all 4 live sources | Uber DQ 13; Netflix 14; Google 20; Amazon 21 |
| Schema validation / data unit tests on ingestion | **YES** | Great Expectations before data enters pipeline | Amazon Deequ 21; Google TFDV 20 |
| Anomaly detection on metric time series | **YES** | Isolation Forest on pipeline metrics | Netflix RPCA 14; Uber DQ 13 |
| Hybrid search (lexical + semantic + fusion) | **YES** | BM25 + embeddings + RRF in OpenSearch | Instacart 15; DoorDash 1 |
| Search query logs from real users | **NO — biggest gap** | ESCI has Amazon queries, not food queries on our catalog. Every search article uses their own query logs. | DoorDash 1, 2; Instacart 15; Faire 17 |
| Domain-specific search evaluation set with justified labels | **NEED TO CREATE** | Must create 300-500 food queries against our catalog, LLM-as-judge labels with justification, human validation on sample | DoorDash AutoEval 2; Faire 17 |
| ESCI for calibrating the LLM judge | **YES** | Use ESCI's human labels to measure if our LLM judge agrees with humans before trusting it on our catalog | Faire 17; DoorDash AutoEval 2 |
| HITL feedback loop for low-confidence predictions | **DESIGN NEEDED** | Entity resolution <70% confidence → human review. DSPy extraction below threshold → review. AutoEval disagreements → calibration. | DoorDash 4; Walmart 16; Uber INCA 12; Airbnb 11 |
| Blocking strategy for entity resolution at scale | **NEED TO IMPLEMENT** | Combine title n-grams + brand + category as blocking keys before pairwise comparison | Walmart 16 |
| Cross-category purchase patterns | **YES** | Instacart (3.4M orders, 91% cross-category baskets) | DoorDash H-RAG 6; Pinterest 18 |
| Multi-task ranking with adjustable business weights | **OPTIONAL** | Could apply to UC4 recs: separate heads for co-purchase, category, dietary signals | Pinterest 18; DoorDash 6 |
| LLMs used offline for extraction/labeling, not real-time serving | **PLANNED** | DSPy for batch extraction, AutoEval for offline labeling, RAG chatbot for real-time (but with cached/pre-computed data) | DoorDash 2, 3; Faire 17; Uber INCA 12 |
| Content moderation / output validation | **PLANNED** | Pydantic schema enforcement on DSPy outputs, hallucination checks, score bounds enforcement | DoorDash 3 (LLMs-as-jury); DoorDash 1 (post-processing validation) |
| Unstructured text → structured extraction | **YES** | FDA recall descriptions + OFF product descriptions → DSPy extracts structured attributes | DoorDash 7; Airbnb LAEP 8; Uber INCA 12 |

---

## Part 4: The 3 Things We Must Fix

### Fix 1: Build a Food Taxonomy Before Running DSPy

**Why (from articles):** DoorDash's #1 lesson across 3 articles (1, 5, 6): knowledge graphs with controlled vocabularies prevent hallucination and make search work. Without a taxonomy, LLM outputs are unconstrained and unreliable. Their hallucination rate dropped to <1% by constraining outputs to the taxonomy via RAG.

**What to do:**
- Extract USDA's `foodCategory` hierarchy (21 categories like "Cereal", "Snacks", "Dairy")
- Extract OFF's `categories_tags` hierarchy (thousands of nested categories like `en:breakfast-cereals`)
- Merge into unified L2/L3 taxonomy (not too broad like L1, not too sparse like L4 — per DoorDash H-RAG finding)
- Define controlled vocabularies for:
  - Dietary attributes: vegan, vegetarian, gluten-free, organic, dairy-free, nut-free, kosher, halal
  - Product types: cereal, yogurt, chips, pasta, bread, beverage, etc.
  - Brand normalization: "General Mills" = "GENERAL MILLS" = "general-mills"
  - Unit standardization: oz = ounce, g = gram, ml = milliliter, lb = pound
- Store in Neo4j as knowledge graph with relationships
- Constrain DSPy outputs to this taxonomy via RAG (DoorDash pattern)

### Fix 2: Create a Domain-Specific Search Evaluation Set

**Why (from articles):** DoorDash AutoEval (article 2) and Faire (article 17) both create their own evaluation sets from their own catalogs. ESCI is useful for calibrating the judge, but our search evaluation must test queries against OUR enriched catalog with OUR products. This is standard practice, not synthetic data generation.

**What to do:**
1. Write 300-500 diverse food search queries (e.g., "healthy breakfast cereal", "gluten-free pasta", "organic baby food", "spicy chips", "low sodium soup")
2. Run each query against our enriched OFF/USDA catalog in OpenSearch
3. Use LLM-as-judge (with chain-of-thought reasoning and justification — per DoorDash AutoEval) to label each query-product pair as Exact/Substitute/Complement/Irrelevant
4. Have team members validate a sample of LLM labels (the HITL component)
5. Measure agreement rate between LLM and human labels
6. Calibrate using ESCI: run our LLM judge on ESCI pairs (where human labels exist) to prove reliability
7. Track NDCG/MRR over time as catalog changes

### Fix 3: Design the HITL Feedback Loop

**Why (from articles):** Every single production system described in these articles includes human review for low-confidence cases. DoorDash (4 articles), Airbnb (2 articles), Uber INCA, Walmart — all route uncertain predictions to humans and feed corrections back into models.

**What to do:**
- **Entity resolution:** Pairs below 70% confidence → human review queue. Decisions feed back into classifier (active learning, per DoorDash article 4).
- **DSPy extraction:** Products where extracted attributes fail Pydantic validation or have low confidence → human review. Corrections update training examples.
- **AutoEval:** Cases where LLM judge disagrees with expected behavior → human calibration. Update golden set.
- **Anomaly alerts:** Severity "critical" requires human acknowledgment before auto-remediation (already in proposal).
- **Implementation:** Streamlit page or simple queue UI where reviewers see the uncertain case, make a decision, and that decision is logged and fed back.

---

## Part 5: What We Got Right (Validated by Articles)

These choices from our data sources are directly validated by the engineering articles:

1. **OFF as messy source + USDA as clean reference** — matches DoorDash, Uber INCA, Airbnb LAEP pattern of enriching messy catalog data against authoritative sources
2. **Entity resolution across OFF ↔ USDA ↔ FDA** — matches Walmart's entity resolution pattern exactly (multiple sources, different naming, no universal ID)
3. **DQ Score 0-100** — matches Airbnb's Data Quality Score approach (composite score per asset)
4. **Great Expectations for validation** — matches Amazon Deequ's "unit tests for data" approach
5. **Pipeline metrics via Kafka → anomaly detection** — matches Uber DQ (time-series) + Netflix RPCA (matrix decomposition on metrics)
6. **Hybrid search (BM25 + embeddings + RRF)** — matches Instacart's hybrid retrieval exactly
7. **AutoEval with LLM-as-judge** — matches DoorDash AutoEval + Faire Llama3 pattern
8. **DSPy for batch extraction** — matches the "LLMs as offline tools" pattern from DoorDash, Faire, Uber INCA
9. **Instacart basket data for cross-category recs** — validated by DoorDash H-RAG (cross-vertical patterns) + Pinterest (multi-task ranking)
10. **RAG chatbot grounded in evidence** — matches DoorDash entity profiles ("code for facts, LLMs for narrative")

---

## Part 6: Updated Data Source Roles After Article Review

| Source | Original Role | Updated Role After Reading Articles |
|---|---|---|
| **Open Food Facts** | Messy catalog for enrichment | Same + serves as the "merchant-provided data" that Uber INCA and DoorDash describe — unstructured, incomplete, needs LLM extraction |
| **USDA FoodData** | Clean reference | Same + provides the category taxonomy foundation (L2/L3 levels) that DoorDash says is essential. USDA's `foodCategory` becomes our knowledge graph backbone. |
| **openFDA Recalls** | Safety enrichment | Same + serves as "unstructured text → structured extraction" testbed (per DoorDash GenAI article). Free-text recall descriptions → entity matching to catalog. |
| **Open Prices** | Pricing + streaming | Same. Validated as real-time Kafka source. |
| **Amazon ESCI** | Search evaluation benchmark | **Refined role:** NOT our primary evaluation set. Used ONLY to calibrate our LLM-as-judge (measure agreement with human labels). Primary evaluation is our own food query set against our catalog. |
| **Instacart Baskets** | Cross-category patterns | Same. Validated by DoorDash H-RAG and Pinterest multi-task learning. 91% cross-category signal is strong. |
| **NEW: Food Taxonomy** | (did not exist) | **Must build.** Merge USDA categories + OFF tags into unified L2/L3 hierarchy with controlled vocabularies. This is the knowledge graph that constrains DSPy and powers search. |
| **NEW: Domain Evaluation Set** | (did not exist) | **Must create.** 300-500 food queries with LLM-judged + human-validated relevance labels against our enriched catalog. This is our AutoEval dataset. |
