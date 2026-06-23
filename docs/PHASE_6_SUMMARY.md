# Phase 6 — Career Intelligence Engine

**Date:** June 23, 2026  
**Branch:** `phase6-career-intelligence`  
**Previous tag:** `phase5-hardened` (commit `8f4a92b`)

---

## What Was Built

The **Career Intelligence Engine** analyzes candidate career history, skills, profile fields, and career patterns to detect signals aligned with the target job description (Senior AI Engineer, Founding Team). It produces both positive signals (relevant experience detection) and penalty signals (misaligned career patterns).

Unlike the Phase 5 Semantic Engine (which uses embedding-based similarity), Phase 6 uses **keyword/pattern matching** — no new ML models, no network calls, CPU-only. Each signal is scored 0.0–1.0 and is explainable by examining which keywords matched.

### Files Created

| File | Purpose |
|------|---------|
| `src/features/career_intelligence.py` | Main module: `CareerIntelligence(BaseFeatureExtractor)` with all 20 features |
| `tests/test_features_career_intelligence.py` | Test suite: 37 tests covering detection, penalties, edge cases, integration, performance |

### Files Modified

| File | Change |
|------|--------|
| `src/features/__init__.py` | Added `CareerIntelligence` import and `__all__` entry |

---

## Features Produced (20 total)

### Career Intelligence Signals (16)

| Feature | Detection Method | Purpose |
|---------|-----------------|---------|
| `product_company_score` | Company name matching against product company list | Detects product company experience (Google, Meta, Flipkart, etc.) |
| `startup_experience_score` | Keyword matching in career text + titles | Detects startup/early-stage/founding team experience |
| `engineering_depth_score` | Title + skill keyword matching | Measures software engineering depth |
| `relevant_tech_experience_score` | Aggregate of 7 domain signals | Combined tech relevance score |
| `career_progression_score` | Tenure analysis + career stability | Rewards long tenure + multiple roles + current role |
| `skill_relevance_score` | Skill name matching against JD-relevant skills | Measures skill alignment with target role |
| `ranking_experience_score` | Keyword matching | Detects ranking/ranker experience |
| `retrieval_experience_score` | Keyword matching | Detects retrieval/IR/vector search experience |
| `recommendation_experience_score` | Keyword matching | Detects recommendation system experience |
| `search_experience_score` | Keyword matching | Detects search engine/infrastructure experience |
| `embeddings_experience_score` | Keyword matching | Detects embedding model experience |
| `vector_db_experience_score` | Tool name matching | Detects Pinecone/FAISS/Milvus/etc. experience |
| `production_ml_score` | Keyword matching | Detects production deployment/A-B testing experience |
| `evaluation_framework_score` | Metric name matching | Detects NDCG/MRR/MAP/A-B test experience |
| `python_engineering_score` | Keyword matching | Detects Python/backend/distributed systems experience |
| `nlp_ir_experience_score` | Keyword matching | Detects NLP/IR/LLM/transformer experience |

### Penalty Signals (4)

| Feature | Detection Method | Purpose |
|---------|-----------------|---------|
| `consulting_penalty` | Company name matching against consulting firm list | Penalizes consulting-only careers (TCS, Infosys, etc.) |
| `research_penalty` | Title + career text keyword matching | Penalizes pure research without production deployment |
| `keyword_stuffing_penalty` | Skill duration analysis | Penalizes expert-level skills with 0 months duration |
| `title_chasing_penalty` | Tenure + title inflation pattern matching | Penalizes frequent job switching with inflating titles |

---

## Test Results

| Metric | Value |
|--------|-------|
| **Phase 6 tests** | **37/37 passing** |
| **Full suite** | **140/140 passing** (103 Phase 4-5 + 37 Phase 6) |
| **Phase 5 regression** | ✅ **None** |

---

## Performance

| Metric | Value |
|--------|-------|
| **Extract throughput** | > 10,000 candidates/sec |
| **Additional RAM** | ~200 KB (no new ML models) |
| **CPU only** | ✅ Yes |
| **No network** | ✅ Yes |
| **No GPU** | ✅ Yes |

---

## Known Limitations

1. **Product company detection** uses a predefined company list — new/emerging product companies not on the list may not be detected. The list covers ~60 major product companies (global + Indian + AI/ML).
2. **Consulting firm detection** similarly relies on a predefined list — smaller consulting firms may be missed.
3. **Career progression scoring** uses `years_of_experience` from profile for average tenure calculation, which may not match actual career duration if the candidate has gaps.
4. **Research penalty** title matching excludes "data scientist" titles (applied ML) but may still have false positives/negatives with other ambiguous titles.

---

## Phase 7 Dependencies

Phase 7 (Ranking Pipeline) will need to:

1. Combine Phase 5 (Semantic Engine) features with Phase 6 (Career Intelligence) features
2. Normalize feature scores from both engines
3. Compute a composite ranking score
4. Sort and output top-100 candidates with reasoning

---

*Phase 6 implementation complete. All 20 features implemented, 37 tests passing, 0 Phase 5 regressions.*
