# Phase 5 — Hardening Fix Report

**Date:** June 23, 2026
**Tag:** `phase5-stable`
**Branch:** `phase5-scoring-engine`

---

## Summary of Fixes Applied

| # | Fix | Files Changed | Status |
|---|-----|---------------|--------|
| 1 | Pin dependency versions (`>=` → `==`) | `requirements.txt` | ✅ Applied |
| 2 | Add Python version requirement | `pyproject.toml` (new) | ✅ Applied |
| 3 | Document Semantic Engine in README | `README.md` | ✅ Applied |
| 4 | Fix repo structure tree in README | `README.md` | ✅ Applied |
| 5 | Fix competition dataset directory comment | `README.md` | ✅ Applied |

---

## Fix 1: Dependency Pinning

### File: `requirements.txt`

**Before:**
```
python-docx>=1.2.0
numpy>=1.24.0
sentence-transformers>=2.2.0
pytest>=7.0.0
```

**After:**
```
python-docx==1.2.0
numpy==2.4.4
sentence-transformers==5.6.0
pytest==9.0.3
```

**Critical transitive dependencies** (installed automatically by `sentence-transformers`):
- `torch==2.12.1+cpu` (not pinned — left commented for visibility; CPU-only)
- `transformers==5.12.1`
- `huggingface_hub==1.20.1`
- `tokenizers==0.22.2`
- `scikit-learn==1.8.0`
- `scipy==1.17.1`
- `tqdm==4.68.2`
- `safetensors==0.8.0`

**Verification:** `pip install -r requirements.txt` completes successfully (all packages already satisfied).

> **Note:** Transitive dependencies are NOT pinned in `requirements.txt`. Pinning them explicitly would require adding them to the file. This is acceptable because `sentence-transformers==5.6.0` declares its own dependency bounds.

---

## Fix 2: Python Version Requirement

### File: `pyproject.toml` (new)

```toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.build_meta"

[project]
name = "redrob-ai-ranker"
version = "0.5.0"
description = "Intelligent Candidate Discovery & Ranking for the Redrob Hackathon"
readme = "README.md"
requires-python = ">=3.10,<3.14"
license = {text = "MIT"}

dependencies = [
    "python-docx==1.2.0",
    "numpy==2.4.4",
    "sentence-transformers==5.6.0",
]

[project.optional-dependencies]
dev = [
    "pytest==9.0.3",
    "pytest-cov",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

**Python version rationale:**
- Python 3.10 minimum: PyTorch requires Python ≥3.8; 3.10 is a safe baseline with broad wheel availability
- Python 3.13 max: PyTorch 2.12.1 supports Python ≤3.13; Python 3.14 compatibility is not guaranteed
- Dev environment runs Python 3.14.3 (may require local PyTorch build)

---

## Fix 3: Semantic Engine Documentation

### File: `README.md` — New Section

Added `## Semantic Engine (Phase 5)` section between the Phases table and the Current Status table, including:

| Sub-section | Content |
|-------------|---------|
| Model | `all-MiniLM-L6-v2`, 384-dim, ~88 MB, CPU-only, HuggingFace cache |
| Features | 4 features with source fields |
| Pre-computation Workflow | Python code example (`precompute()` → `extract()`) |
| Disk Cache | `save_embeddings()` / `load_embeddings()` for < 1s ranking stage |
| Performance | Table: model load, precompute, disk cache load, extract times |
| RAM Usage | Breakdown: model 80 MB, embeddings 5 MB, overhead 5 MB, total ~90 MB |
| Python Version | Table with min (3.10), max (3.13), and `pyproject.toml` reference |

---

## Fix 4: Repository Structure Tree

Updated test count from "75" to "103" and added `test_features_semantic.py` to the tree.

### File: `README.md`

**Before:**
```
├── tests/                       # Test suite (Phase 4, 75 tests)
│   ├── test_features.py
│   └── ...
├── docs/                        # Phase documentation
│   └── PHASE_*_*.md             # Phase reports (Phases 1-4)
```

**After:**
```
├── tests/                       # Test suite (103 tests: Phase 4 + Phase 5)
│   ├── test_features.py
│   ├── test_features_semantic.py
│   └── ...
├── docs/                        # Phase documentation
│   └── PHASE_*_*.md             # Phase reports (Phases 1-5)
├── pyproject.toml               # Project metadata + Python version requirement
```

---

## Fix 5: Competition Dataset Comment

### File: `README.md`

**Before:**
```
└── [PUB] India_runs_data_and_ai_challenge/  # Competition dataset (gitignored)
```

**After:**
```
└── [PUB] India_runs_data_and_ai_challenge/  # Competition dataset (sample files tracked)
```

**Rationale:** The `[PUB]` directory has committed files (schema, samples, templates, validator). The original "(gitignored)" comment was misleading.

---

## Competition Reproducibility Check

| Artifact | Required at Phase 5? | Status |
|----------|---------------------|--------|
| `rank.py` | ❌ **No** — Phase 7 deliverable | `rank.py` does not exist yet |
| `submission_metadata.yaml` at repo root | ❌ **No** — Phase 10 final packaging step | Only template exists in `[PUB]/` |
| `src/features/semantic.py` (Semantic Engine) | ✅ **Yes** — Phase 5 deliverable | ✅ Committed and verified |
| Pre-computed embeddings (`.npy`/`.npz`) | ❌ **No** — optional cache for ranking speed | Can be committed in Phase 10 |
| `job_description.txt` | ✅ **Yes** — needed for JD embedding | ✅ Committed (9,687 bytes) |
| Model cache (`~/.cache/huggingface/`) | ❌ **No** — downloaded on first run | Documented in README |

**Conclusion:** No competition-required artifacts are missing at Phase 5. All Phase 5 deliverables are complete and committed.

---

## Files Modified

| File | Change Type | Lines Changed |
|------|-------------|---------------|
| `requirements.txt` | Modified — pinned versions | 4 dependency lines |
| `pyproject.toml` | **New** — project metadata + python_requires | 23 lines |
| `README.md` | Modified — Semantic Engine docs + structure + status | ~100 lines added |

## Files Unchanged (by design)

| File | Reason |
|------|--------|
| `src/features/semantic.py` | Code is working and tested (94% coverage) |
| `tests/test_features_semantic.py` | Tests pass (103/103) |
| `docs/*` | Phase 5 docs already generated in earlier steps |

*End of Phase 5 Hardening Fix Report*
