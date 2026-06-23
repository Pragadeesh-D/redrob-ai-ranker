# Phase 6 — Career Intelligence Engine: Pre-Implementation Audit

**Audit date:** June 23, 2026  
**Branch:** `phase6-career-intelligence`  
**Based on:** `phase5-hardened` (commit `8f4a92b`)  
**Documents inspected:**
- `submission_spec.docx` (Sections 3, 7, 10.3)
- `README.docx` (Participant bundle)
- `job_description.docx` (Senior AI Engineer, Founding Team)
- `redrob_signals_doc.docx` (23 behavioral signals)
- `candidate_schema.json` (Data schema)
- `sample_candidates.json` (50 sample profiles)
- `sample_submission.csv` (Format reference)

---

## 1. Evidence Table — JD Requirements vs. Planned Features

### JD Requirements (from `job_description.docx`)

| JD Requirement | Quote | Source |
|----------------|-------|--------|
| Ranking systems | *"Own the search, retrieval, and ranking systems"* | [P0 onwards] |
| Retrieval systems | *"Transition from current BM25/rule-based system to a v2 architecture involving embeddings, hybrid retrieval"* | [P0 onwards] |
| Embeddings | *"Production experience with systems like sentence-transformers, OpenAI embeddings, BGE, or E5"* | [P0 onwards] |
| Vector databases | *"Operational experience with tools like Pinecone, Weaviate, Qdrant, Milvus, OpenSearch, Elasticsearch, or FAISS"* | [P0 onwards] |
| Production ML | *"Must have shipped at least one end-to-end ranking, search, or recommendation system to real users"* | [P0 onwards] |
| Evaluation | *"Hands-on experience with metrics like NDCG, MRR, MAP, and A/B test interpretation"* | [P0 onwards] |
| Product company experience | *"6–8 years of experience, with 4–5 years in applied ML/AI roles specifically at product companies"* | [P0 onwards] |
| Startup/Founding team | Role title is *"Senior AI Engineer — Founding Team"* | [P0] |
| Consulting penalty | *"Exclusively working at service-based firms (e.g., TCS, Infosys, Accenture) without prior product-company experience is a negative signal"* | [P0 onwards] |
| Research penalty | *"Candidates with only pure research/academic backgrounds and no production deployment experience are disqualified"* | [P0 onwards] |
| Framework-only penalty | *"Experience purely with LLM wrappers ... without significant pre-LLM production ML experience"* | [P0 onwards] |

---

## 2. Feature Decision Matrix

### Career Intelligence Features

| Feature | Purpose | Evidence from JD | Ranking Impact | FP Risk | FN Risk | Runtime | RAM | Decision |
|---------|---------|------------------|----------------|---------|---------|---------|-----|----------|
| **Ranking systems detection** | Detect candidates who mention ranking/reranking/search in career descriptions | *"Own the search, retrieval, and ranking systems"* | High — core JD signal | Low — keywords are domain-specific (NDCG, ranking, reranking) | Low — semantic matching catches paraphrases | Minimal (~0.1 ms per candidate via keyword + embedding) | ~1 KB | **✅ KEEP** |
| **Retrieval systems detection** | Detect retrieval, information retrieval, hybrid retrieval experience | *"Transition from current BM25/rule-based system to a v2 architecture involving embeddings, hybrid retrieval"* | High — core JD signal | Low | Low | Minimal | ~1 KB | **✅ KEEP** |
| **Recommendation systems detection** | Detect recommendation engine, collaborative filtering experience | *"One end-to-end ranking, search, or recommendation system"* | Medium — related signal | Medium — some non-ML roles have "recommendation" | Low | Minimal | ~1 KB | **✅ KEEP** |
| **Search systems detection** | Detect search engine, Elasticsearch, search infrastructure | *"Own the search, retrieval, and ranking systems"* | High — core JD signal | Low | Low | Minimal | ~1 KB | **✅ KEEP** |
| **Embeddings detection** | Detect embedding-based retrieval, sentence-transformers | *"Production experience with systems like sentence-transformers, OpenAI embeddings, BGE, or E5"* | High — explicit JD requirement | Low | Medium — candidate may know embeddings but not list them | Minimal | ~1 KB | **✅ KEEP** |
| **Vector database detection** | Detect Pinecone, Milvus, FAISS, Weaviate, Qdrant | *"Operational experience with tools like Pinecone, Weaviate, Qdrant, Milvus, OpenSearch, Elasticsearch, or FAISS"* | High — explicit JD requirement | Low — specific tool names | Low — tool names are concrete | Minimal | ~1 KB | **✅ KEEP** |
| **Production ML detection** | Detect production deployment, shipped, A/B testing, evaluation | *"Must have shipped at least one end-to-end ranking, search, or recommendation system to real users"* | High — gates all other signals | Medium — some candidates write "production" loosely | Medium — candidate may have shipped without documenting it | Minimal | ~1 KB | **✅ KEEP** |
| **Product company experience** | Detect product-focused companies vs service/consulting | *"4–5 years in applied ML/AI roles specifically at product companies"* | High — JD requirement | Medium — company classification is fuzzy | Medium — skill matters regardless of company type | Minimal | ~1 KB | **✅ KEEP** |
| **Startup experience** | Detect startup, founding team, early-stage roles | Role title: *"Senior AI Engineer — Founding Team"* | Medium — matching role context | Medium — many candidates claim "startup" loosely | Low | Minimal | ~1 KB | **✅ KEEP** |

### Penalty Features

| Feature | Purpose | Evidence from JD | Ranking Impact | FP Risk | FN Risk | Runtime | RAM | Decision |
|---------|---------|------------------|----------------|---------|---------|---------|-----|----------|
| **Consulting-only career penalty** | Penalize candidates who have only worked at TCS, Infosys, Accenture, etc. | *"Exclusively working at service-based firms ... without prior product-company experience is a negative signal"* | Medium — disqualifier | Low — company names are enumerable | Medium — some product work at service firms | Minimal | ~1 KB | **✅ KEEP** |
| **Pure research career penalty** | Penalize candidates with research-only roles, no production deployment | *"Candidates with only pure research/academic backgrounds and no production deployment experience are disqualified"* | Medium — disqualifier | Medium — some research roles include deployment | Medium — researcher may have production skills not listed | Minimal | ~1 KB | **✅ KEEP** |
| **Keyword stuffing penalty** | Penalize candidates with many keyword skills but 0 duration_months | *Spec does not name this explicitly but §7 (Honeypot warning) mentions: *\"expert proficiency in 10 skills with 0 years used\"* | Low — prevent false positives | Low — 0-duration skills are a honeypot signal | Low | Minimal | ~1 KB | **✅ KEEP** (aligns with Phase 8 honeypot) |

---

## 3. Risk Analysis

### False Positive Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Product company classification** | Medium | Use a curated list of known product companies + industry classification + company size heuristic. Accept fuzzy matching in Phase 6; refine in Phase 8. |
| **Keyword stuffing detection** | Low | Only penalize when skill has `duration_months == 0` AND proficiency is "expert" or "advanced" — the exact pattern the spec describes as honeypot-like |
| **Startup detection** | Medium | Use company size (< 200 employees) + company_age (founded < 10 years ago) + title-based heuristics ("founding", "early") |

### False Negative Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Undocumented production experience** | Medium | Use semantic matching on career descriptions — candidates who deployed production systems often describe it even without using the word "production" |
| **Missing embedding experience** | Medium | Embedding detection via keyword matching on tool names (sentence-transformers, BGE, E5, OpenAI embeddings) — these are concrete enough to match directly |
| **Career descriptions too brief** | Low | Some candidates have minimal descriptions. Fall back to skill-based features |

### Competition Constraint Risks

| Risk | Severity | Assessment |
|------|----------|------------|
| **Runtime exceeds 5 min limit** | ✅ **Low** | All Career Intelligence features are text-processing only (keyword matching + minimal semantic). Estimated total: ~15-30 seconds for 100K candidates. |
| **RAM exceeds 16 GB** | ✅ **Low** | No new ML model needed. Just lookup tables (company lists, keyword lists). Estimated: ~1-5 MB. |
| **GPU dependency** | ✅ **None** | All features use CPU-only text processing |
| **Network dependency** | ✅ **None** | No API calls required |

---

## 4. Missing Career Intelligence Features

The following features are not in the current planned scope but are supported by competition evidence:

| Missing Feature | Evidence | Priority | Recommended Action |
|----------------|----------|----------|-------------------|
| **Evaluation framework experience** (NDCG, MRR, MAP) | JD: *"Hands-on experience with metrics like NDCG, MRR, MAP, and A/B test interpretation"* | **High** — explicit JD requirement | Add to Phase 6 scope |
| **Production Python / engineering** | JD: *"Strong Python skills are mandatory"* and *"Senior engineers who haven't written production code in the last 18 months"* | **High** — explicit JD signal | Add Python detection to Phase 6 |
| **NLP/IR experience** | JD: *"Primary expertise in Computer Vision, Speech, or Robotics without significant NLP/IR experience is not preferred"* | **Medium** — discriminator | Add NLP/IR detection |
| **Open-source contributions** | JD: *"Candidates with 5+ years solely in closed-source proprietary systems without public validation (papers/talks/open-source) are discouraged"* | **Medium** — discriminator | Add open-source detection via career descriptions |
| **Title-chaser detection** (frequent job switches) | JD: *"Candidates frequently switching companies (every ~1.5 years) are not a fit"* | **Medium** — penalty feature | Add tenure calculation per role |

---

## 5. Features Likely to Improve Leaderboard Performance

| Feature | Expected Impact | Why |
|---------|----------------|-----|
| **Ranking + Retrieval detection** | High | These match the JD's core requirement — candidates with this background will rank higher |
| **Vector database detection** | High | Concrete, verifiable skill that directly matches JD |
| **Product company experience** | High | JD explicitly weights this — product-company candidates are preferred |
| **Evaluation framework detection** | High | JD explicitly requires NDCG/MRR/MAP experience |

## 6. Features Likely to Create Overfitting Risk

| Feature | Risk Level | Why |
|---------|------------|-----|
| **Keyword stuffing penalty** | Medium | Only 80 honeypots in 100K — tuning this too aggressively could penalize real candidates with broad skills |
| **Consulting-only penalty** | Medium | Some service firms do product work internally. Over-penalizing could miss good candidates. |
| **Startup experience** | Low | Safer signal — startups are explicitly mentioned in the JD |

## 7. Features Likely to Violate Competition Constraints

**None identified.** All features use CPU-only text processing with negligible runtime and RAM impact.

## 8. Features That Should Be Postponed

| Feature | Postpone to | Reason |
|---------|-------------|--------|
| **Honeypot detection** | Phase 8 | Different class of problem (impossible profile detection). Phase 6 should focus on career intelligence |
| **Behavioral signal integration** | Phase 7 | Belongs in the ranking pipeline, not the feature extraction engine |
| **Reasoning generation** | Phase 7 | Requires ranker output, not feature extraction |
| **Dockerfile + metadata** | Phase 10 | Final packaging |

---

## 9. Recommended Phase 6 Scope

### Keep in Scope (12 features)

**Career Intelligence Features (9):**
1. Ranking systems detection
2. Retrieval systems detection
3. Recommendation systems detection
4. Search systems detection
5. Embeddings detection
6. Vector database detection
7. Production ML detection
8. Product company experience
9. Startup experience

**Penalty Features (3):**
10. Consulting-only career penalty
11. Pure research career penalty
12. Keyword stuffing penalty

**Newly Identified (to add):**
13. Evaluation framework detection (NDCG, MRR, MAP) — **ADD**
14. Python/engineering experience detection — **ADD**
15. NLP/IR experience detection — **ADD**
16. Tenure / title-changer detection — **ADD**

### Out of Scope for Phase 6

| Excluded | Reason | Target Phase |
|----------|--------|-------------|
| Honeypot detection | Different detection paradigm | Phase 8 |
| Behavioral signal scoring | Ranking-phase integration | Phase 7 |
| Open-source contribution detection | Low priority discriminator | Phase 8+ |
| Reasoning generation | Requires ranked output | Phase 7 |

---

## 10. Recommended Files to Create

| File | Purpose |
|------|---------|
| `src/features/career_intelligence.py` | Main module: `CareerIntelligence` class extending `BaseFeatureExtractor` |
| `src/features/data/company_classifier.py` | Product vs service company classification logic + curated lists |
| `src/features/data/keyword_registry.py` | Keyword mappings for ranking, retrieval, embeddings, vector DB, evaluation terms |
| `src/features/data/consulting_firms.txt` | Known consulting/service firm names for penalty detection |
| `tests/test_features_career_intelligence.py` | Test suite for all Career Intelligence features |

---

## 11. Recommended Tests to Write

| Test Category | Test Cases | Priority |
|---------------|------------|----------|
| **Ranking detection** | Candidate with "ranking" in career → high score. Candidate without → low score | Critical |
| **Retrieval detection** | Candidate with "vector search" → detected. Candidate with "data entry" → not detected | Critical |
| **Embeddings detection** | Candidate with "sentence-transformers" → detected | Critical |
| **Vector DB detection** | Candidate with "Pinecone", "FAISS" → detected | Critical |
| **Production ML** | Candidate with "shipped", "A/B testing", "production deployment" → detected | Critical |
| **Product company** | Candidate at Google → product. Candidate at TCS → service | High |
| **Consulting penalty** | Candidate with only TCS/Infosys → penalty applied | High |
| **Keyword stuffing** | Candidate with 10 "expert" skills at 0 months → penalty | High |
| **Empty/missing data** | Candidate with no career history → graceful fallback | High |
| **Edge cases** | Non-technical candidates → low scores across all features | Medium |
| **Runtime** | 100K candidates processed in < 30 seconds | High |

---

## 12. Runtime Estimate

| Feature | Runtime per 1K Candidates | Runtime for 100K Candidates |
|---------|---------------------------|----------------------------|
| Keyword-based features (detection + penalties) | ~30 ms | ~3 seconds |
| Product company classification | ~20 ms | ~2 seconds |
| Tenure calculation | ~15 ms | ~1.5 seconds |
| Total (16 features, no new model) | ~65 ms | **~6.5 seconds** |

**Note:** No new embedding model needed. Uses existing Phase 5 semantic engine or simple keyword matching. Runtime well under 5-minute limit.

---

## 13. RAM Estimate

| Component | Size |
|-----------|------|
| Keyword registries (16 feature categories) | ~100 KB |
| Product company lookup table | ~50 KB |
| Consulting firm list | ~5 KB |
| Scoring weights/config | ~10 KB |
| **Total incremental RAM** | **~200 KB** |

**Note:** Negligible compared to Phase 5's ~90 MB. No new models required.

---

## 14. Success Criteria for Completing Phase 6

| Criterion | Target | Verification |
|-----------|--------|-------------|
| 16 Career Intelligence features implemented | All pass tests | `pytest tests/test_features_career_intelligence.py` |
| Test coverage > 90% for new module | Coverage report | `pytest --cov=src/features/career_intelligence` |
| No regression in Phase 4-5 tests | 103/103 still pass | `pytest tests/ -v` |
| Runtime < 30 seconds for 100K | Benchmark | `python -m cProfile` on 100K candidates |
| RAM < 200 MB total | Memory profile | `tracemalloc` snapshot |
| No GPU or network dependencies | Code review | Verify no GPU/network imports |
| Phase boundary maintained | No Phase 7/8 logic | Code review |
| README updated | Phase 6 section added | README inspection |

---

## 15. Phase 6 Implementation Readiness

## ✅ **READY TO IMPLEMENT**

**Rationale:**
1. All 12 originally planned features are validated against competition document evidence
2. 4 additional features identified (Evaluation frameworks, Python/engineering, NLP/IR, Tenure) — add to scope
3. Zero competition constraint violations (CPU-only, minimal RAM, no network)
4. Negligible runtime impact (~6.5 seconds for 100K candidates)
5. Clear file structure and test plan established
6. Phase boundary clear — no overlap with Phase 7 (Ranking) or Phase 8 (Honeypot)

### Recommended Starting Point

```python
# File: src/features/career_intelligence.py
# Class: CareerIntelligence(BaseFeatureExtractor)
# Features: 16 total (12 detection + 4 penalty)
#
# Pattern: each feature is a method that scores a candidate field
#          (career description, headline, summary, skills)
#          against keyword-based or pattern-based signals
#
# No new ML models. No network calls. CPU-only text processing.
```

**Phase 6 Career Intelligence Engine can proceed immediately as scoped.**

---

*Pre-implementation audit complete. No code created. No tests created. No source files modified. No commits made.*
