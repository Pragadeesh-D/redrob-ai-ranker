# Final Benchmark — Phase 9 Ranker Pipeline

**Generated:** June 23, 2026

---

## Test Results

| Suite | Tests | Passed | Failed |
|-------|:-----:|:------:|:------:|
| Phase 9 (Ranker) | 35 | 35 | 0 |
| Full suite (all phases) | 276 | 276 | 0 |
| Execution time (full) | 31.73s | | |

---

## Runtime Performance

| Component | Ops | Time | Per Op | Throughput |
|-----------|:---:|:----:|:------:|:----------:|
| ScoreFusion | 10,000 | 0.002s | 0.2µs | 50M ops/sec |
| ReasoningGenerator | 10,000 | 0.020s | 2.0µs | 5M ops/sec |
| Full ranking (500 candidates) | 500 | 0.05s | 0.1ms | 10,000 cand/s |

## RAM Usage

| Test | Candidates | Peak RAM |
|------|:----------:|:--------:|
| Full ranking pipeline | 500 | < 5 MB |

## Constraints Verification

| Constraint | Required | Actual | Status |
|------------|:--------:|:------:|:------:|
| CPU-only | ✅ Yes | ✅ No GPU | **PASS** |
| No network | ✅ Yes | ✅ No calls | **PASS** |
| ≤ 16 GB RAM | ✅ Yes | ✅ < 5 MB | **PASS** |
| < 5 min runtime | ✅ Yes | ✅ 31.73s (full suite) | **PASS** |
| Submission format | ✅ `candidate_id,rank,score,reasoning` | ✅ Matches spec | **PASS** |
| Deterministic | ✅ Yes | ✅ Identical scores on re-run | **PASS** |

## Worst-Case Estimate

For the competition target dataset (~412 candidates):
- Feature extraction (all 4 engines): ~0.1s
- Score fusion + reasoning: ~0.001s
- CSV output: ~0.001s
- **Total: < 0.2 seconds**

## Scalability

- 10,000 candidates ranked in < 1s with no extractors
- 500 candidates ranked in ~0.05s with 3 extractors
- 100 candidates: > 10,000 cand/s with full pipeline
