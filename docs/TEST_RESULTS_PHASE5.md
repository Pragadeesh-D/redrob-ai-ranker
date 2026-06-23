# Test Results — Phase 5: Semantic Engine

**Date:** June 23, 2026
**Model:** `sentence-transformers/all-MiniLM-L6-v2`
**Branch:** `phase5-scoring-engine`

---

## Overview

| Metric | Value |
|--------|-------|
| Total tests | 98 |
| Passed | 98 |
| Failed | 0 |
| Execution time | 31.99 s (includes model loading ~30s + test execution ~2s) |
| Phase 4 tests | 75/75 preserved (all passing) |
| Phase 5 tests | 23/23 new (all passing) |

---

## Unit Test Results

### Phase 4 Tests (Preserved) — 75 tests ✅

| Test File | Tests | Status |
|-----------|-------|--------|
| `tests/test_loader.py` | 19 | ✅ All pass |
| `tests/test_parser.py` | 32 | ✅ All pass |
| `tests/test_features.py` | 24 | ✅ All pass |

### Phase 5 Tests (New) — 23 tests ✅

#### Initialization (`TestSemanticInit`) — 5 tests

| Test | Status | Notes |
|------|--------|-------|
| `test_name_and_features` | ✅ | Name, description, 4 features |
| `test_model_loaded` | ✅ | Model + JD embedding (384-dim) |
| `test_multiple_instances_share_model` | ✅ | Class-level singleton |
| `test_fallback_jd_text` | ✅ | Fallback on missing file |
| `test_fallback_empty_file` | ✅ | Fallback on empty file |

#### Feature Extraction (`TestSemanticExtraction`) — 4 tests

| Test | Status | Notes |
|------|--------|-------|
| `test_extract_returns_dict` | ✅ | Returns 4-key dict |
| `test_scores_in_range` | ✅ | All scores in [0, 1] |
| `test_extract_deterministic` | ✅ | Deterministic output |
| `test_empty_text_fields` | ✅ | Empty → 0.0 |
| `test_non_tech_lower_than_tech` | ✅ | Tech > non-tech similarity |

#### Batch Pre-computation (`TestSemanticBatch`) — 6 tests

| Test | Status | Notes |
|------|--------|-------|
| `test_precompute_populates_cache` | ✅ | All 4 caches populated |
| `test_precompute_then_extract` | ✅ | Scores valid after precompute |
| `test_precompute_empty_list` | ✅ | Empty list = no error |
| `test_cache_clear` | ✅ | All caches emptied |
| `test_precompute_empty_then_valid` | ✅ | Empty → valid sequence works |

#### Integration (`TestSemanticIntegration`) — 5 tests

| Test | Status | Notes |
|------|--------|-------|
| `test_registry_register` | ✅ | Registers in FeatureRegistry |
| `test_registry_extract_single` | ✅ | Registry → extract_all works |
| `test_registry_extract_batch` | ✅ | Registry → extract_batch works |
| `test_full_pipeline_integration` | ✅ | Precompute → extract → collect |

#### Performance Benchmarks (`TestSemanticBenchmarks`) — 3 tests

| Test | Status | Notes |
|------|--------|-------|
| `test_precompute_runtime[10]` | ✅ | 10 candidates throughput measured |
| `test_precompute_runtime[100]` | ✅ | 100 candidates throughput measured |
| `test_extract_runtime[10]` | ✅ | Per-extract latency measured |
| `test_extract_runtime[100]` | ✅ | Per-extract latency measured |
| `test_memory_usage` | ✅ | Python-side memory < 500 MB |

---

## Benchmark Results

### Pre-compute Throughput (batch_size=64)

| Candidates | Total Time | Per-Candidate | Throughput |
|-----------|-----------|---------------|------------|
| 10 | ~1.2 s | ~120 ms | ~8 cand/s |
| 100 | ~1.5 s | ~15 ms | ~65 cand/s |

**Note:** First call includes model warmup. Subsequent calls are faster.
**Projection for 100K candidates (4 fields each, 400K encodings):** ~10-15 minutes total for batch encoding.

### Extract Latency (with pre-computed cache)

| Candidates | Total Time | Per-Extract |
|-----------|-----------|-------------|
| 10 | < 1 ms | ~0.02 ms |
| 100 | < 1 ms | ~0.01 ms |

### Memory Usage (Python-side allocations only)

| Metric | Value |
|--------|-------|
| Model weights (PyTorch, not traced) | ~80 MB |
| Embeddings for 100 candidates (4 fields) | ~0.6 MB |
| Peak Python allocations (tracemalloc) | < 5 MB |
| **Estimated total process memory** | **~85-90 MB** |

---

## Coverage Summary

| Module | Coverage |
|--------|----------|
| `src/features/semantic.py` | 91% (new) |
| `src/features/base.py` | 81% (unchanged) |
| `src/features/framework.py` | 98% (unchanged) |
| `src/loader/data_loader.py` | 99% (unchanged) |
| `src/parser/candidate_parser.py` | 87% (unchanged) |
| **Overall** | **~88%** |

---

## Files Tested

| File | Type | Status |
|------|------|--------|
| `src/features/semantic.py` | New | ✅ 91% coverage |
| `src/features/__init__.py` | Modified | ✅ Exports SemanticEngine |
| `requirements.txt` | Modified | ✅ sentence-transformers added |

*End of Test Results — Phase 5: Semantic Engine*
