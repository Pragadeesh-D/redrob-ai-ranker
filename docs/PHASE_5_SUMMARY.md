# Phase 5 Summary — Semantic Engine

**Date:** June 23, 2026
**Branch:** `phase5-scoring-engine`
**Commit:** (pending approval)

---

## What Was Built

The **Semantic Engine** — an embedding-based feature extractor that computes cosine similarity between candidate profile text fields and the target job description using `sentence-transformers/all-MiniLM-L6-v2`.

### Features Produced

| Feature | Source | Description |
|---------|--------|-------------|
| `jd_similarity_score` | Headline + Summary + Current Title | Overall profile-JD semantic similarity |
| `summary_similarity_score` | Profile Summary | Summary vs JD similarity |
| `headline_similarity_score` | Professional Headline | Headline vs JD similarity |
| `career_similarity_score` | Career History Descriptions | Career evidence vs JD similarity |

### Architecture

- Extends `BaseFeatureExtractor` (Phase 4 abstract base)
- Integrates with `FeatureRegistry` for batch dispatch
- Class-level model singleton (loaded once, shared across instances)
- Batch pre-computation for efficient per-candidate scoring
- Lazy loading: `precompute()` encodes all candidates in batch calls
- `extract()` uses cached embeddings for O(1) lookup per candidate
- Cosine similarity normalized and clamped to [0, 1]

---

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `src/features/semantic.py` | ~280 | Core Semantic Engine implementation |
| `tests/test_features_semantic.py` | ~400 | 23 tests: unit, integration, benchmarks |

## Files Modified

| File | Change |
|------|--------|
| `src/features/__init__.py` | Added `SemanticEngine` to exports |
| `requirements.txt` | Uncommented `sentence-transformers>=2.2.0` |

---

## Test Results

| Metric | Value |
|--------|-------|
| Total tests | 98 |
| Passed | 98 |
| Failed | 0 |
| Phase 4 tests preserved | 75/75 ✅ |
| New Phase 5 tests | 23/23 ✅ |
| Execution time | 31.99 s (incl. model download ~30s) |

---

## Runtime Performance

| Operation | 10 candidates | 100 candidates | 100K (projected) |
|-----------|--------------|---------------|-------------------|
| Pre-compute (4 fields) | ~1.2 s | ~1.5 s | ~10-15 min |
| Extract per candidate (cached) | ~0.02 ms | ~0.01 ms | ~0.01 ms |

**Note:** The 5-minute competition limit applies to the **entire pipeline**. If the Semantic Engine's ~10-15 min projected time exceeds this, optimization strategies include:
- Reducing to 2 fields (combined + summary) instead of 4
- Using `encode_multi_process()` for multi-core parallelism
- Pre-computing embeddings once and caching to disk

---

## RAM Usage

| Component | Size |
|-----------|------|
| Model weights (all-MiniLM-L6-v2) | ~80 MB |
| Embeddings cache (100K × 4 fields) | ~0.6 MB |
| Candidate objects (streaming) | ~3.5 KB each |
| **Total estimated peak** | **~85-90 MB** |

Well within the 2 GB target and the 16 GB competition limit.

---

## Known Limitations

| Limitation | Impact | Mitigation |
|-----------|--------|------------|
| 4-field encoding may exceed 5-min budget for 100K | High | Optimize to 2 fields or add multi-processing |
| `tracemalloc` doesn't capture PyTorch model weights | Low | Documented; actual ~80 MB model is known |
| No disk caching of embeddings | Medium | Recomputes on each run; okay for single-run pipeline |
| Single-threaded encoding | Medium | `encode_multi_process()` available for optimization |

---

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Embedding throughput bottleneck at 100K scale | Medium | Switch to 2-field encoding or multi-process |
| Model download requires network (first run) | Low | Cache model to `~/.cache/huggingface/` |
| Cosine similarity ≠ relevance | Low | Scores are normalized features, not ground truth |

---

## Next Phase Dependencies

| Phase | Depends On | Notes |
|-------|-----------|-------|
| Phase 6 (Scoring/Behavioral) | Semantic Engine features | Combines semantic + behavioral + career + honeypot |
| Phase 7 (Ranking) | All feature engines | Aggregates all features into final score |
| Phase 8 (Optimization) | Runtime benchmarks | Optimize embedding throughput if needed |

---

## Files Referenced

| File | Relationship |
|------|-------------|
| `docs/ARCHITECTURE.md` | §2.3 — Semantic Engine module definition |
| `docs/FEATURE_CATALOG.md` | §1 — Semantic Features (F1-F3) |

*End of Phase 5 Summary*
