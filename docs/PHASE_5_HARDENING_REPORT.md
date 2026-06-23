# Phase 5 — Hardening Audit Report

**Date:** June 23, 2026
**Tag:** `phase5-stable` (commit `1e13b4a`)
**Branch:** `phase5-scoring-engine`

---

## Audit Criteria

| # | Criterion | Verdict |
|---|-----------|---------|
| 1 | `requirements.txt` uses pinned versions | ❌ **FAIL** |
| 2 | Python version requirements documented | ❌ **FAIL** |
| 3 | Semantic engine reproducible on clean machine | ⚠️ **PASS with notes** |
| 4 | Embedding generation workflow documented | ❌ **FAIL** |
| 5 | Competition submission reproducible by judges | ❌ **FAIL** |
| | **Overall** | **❌ FAIL — 4 of 5 criteria not met** |

---

## 1. requirements.txt: Pinned Versions ❌ FAIL

### Current State

| Package | Current Spec | Actual (env) | Issue |
|---------|-------------|--------------|-------|
| `python-docx` | `>=1.2.0` | (not installed) | Unpinned — could pull 2.x with breaking changes |
| `numpy` | `>=1.24.0` | 2.4.4 | Unpinned — major version 2.x may differ from 1.x |
| `sentence-transformers` | `>=2.2.0` | 5.6.0 | **Critical** — 2.2.0 → 5.6.0 is 3 major versions newer; API breaking changes possible |
| `pytest` | `>=7.0.0` | (version TBD) | Low risk (testing only) |

**Missing dependencies:** PyTorch, transformers, huggingface_hub, tokenizers, scikit-learn, scipy, tqdm, safetensors are all **transitive** — not listed in `requirements.txt`. A `pip install -r requirements.txt` will pull them automatically via `sentence-transformers`'s own dependencies, but versions are completely unpinned.

### Recommendation

```diff
- python-docx>=1.2.0
- numpy>=1.24.0
- sentence-transformers>=2.2.0
- pytest>=7.0.0
+ python-docx==1.2.0
+ numpy==1.24.0
+ sentence-transformers==2.2.0
+ pytest==7.0.0
```

Or use a `pip freeze > requirements-lock.txt` approach with `pip install -r requirements-lock.txt` for exact reproducibility.

---

## 2. Python Version Requirements: Not Documented ❌ FAIL

### Current State

| Where | What it says |
|-------|-------------|
| `README.md` | No Python version mentioned |
| `requirements.txt` | No Python version constraint |
| `submission_metadata_template.yaml` | `python_version: "3.11.4"` (placeholder, not a constraint) |
| Actual env | Python **3.14.3** |

**Issues:**
- No `python_requires` in any config file (`setup.py`, `pyproject.toml`, or `requirements.txt`)
- Python 3.14 is bleeding-edge (released Feb 2026). PyTorch CPU wheels may not be available for Python 3.12+ depending on the version
- A judge running Python 3.9 or 3.10 might get `No matching distribution found` for PyTorch

### Recommendation

Add a `pyproject.toml` or note in `README.md`:

```toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "redrob-ai-ranker"
version = "0.1.0"
requires-python = ">=3.10,<3.13"
dependencies = [
    "python-docx>=1.2.0",
    "numpy>=1.24.0",
    "sentence-transformers>=2.2.0",
]
```

Also update README with:
```
Python 3.10–3.12 required (PyTorch compatibility).
```

---

## 3. Semantic Engine: Clean Machine Reproduction ⚠️ PASS with Notes

### What Works

| Step | Status | Notes |
|------|--------|-------|
| `git clone` | ✅ | Public repo |
| `pip install -r requirements.txt` | ✅ | Pulls all deps (but unpinned — see #1) |
| `python -m pytest tests/ -v` | ✅ | 103/103 pass |
| `from src.features.semantic import SemanticEngine` | ✅ | Pure Python import |
| `SemanticEngine()` | ✅ | Loads model from HuggingFace cache or downloads |
| `engine.precompute(candidates)` | ✅ | Batch encodes 4 fields |
| `engine.extract(candidate)` | ✅ | Returns 4 similarity scores |
| `engine.save_embeddings(dir)` / `engine.load_embeddings(dir)` | ✅ | Disk cache round-trip |

### What Requires Network

| Resource | Size | When Needed |
|----------|------|-------------|
| `sentence-transformers/all-MiniLM-L6-v2` | **88 MB** | First `SemanticEngine()` instantiation |
| PyTorch CPU wheel | ~800 MB (pip) | First `pip install` |
| transformers, huggingface_hub | ~55 MB | First `pip install` |

**Mitigation for offline judges:** The model cache can be pre-seeded in the Docker container (competition spec allows pre-computed artifacts in the repo).

### Risk Assessment

| Risk | Impact | Likelihood |
|------|--------|------------|
| Different dependency versions produce different embeddings | High (semantic scores change) | Medium (with `>=` specs) |
| PyTorch not available for host Python version | Critical (engine won't load) | Low (judges use Docker with known Python) |
| Model download fails in offline container | Critical (no embeddings) | Low (model is cached in Docker image) |

---

## 4. Embedding Generation Workflow: Not Documented ❌ FAIL

### Current State

| Documentation | Mentions Pre-computation? | Mentions Disk Cache? |
|---------------|--------------------------|---------------------|
| `README.md` | ❌ No | ❌ No |
| `src/features/semantic.py` docstrings | ✅ Yes (in code) | ✅ Yes (in code) |
| `docs/PHASE_5_SUMMARY.md` | ⚠️ Briefly | ⚠️ Briefly |
| `docs/PHASE_5_COMPETITION_COMPLIANCE.md` | ✅ Yes | ✅ Yes |

**Gap:** A judge who reads only the `README.md` would have no idea that:
1. The Semantic Engine needs model download + pre-computation
2. `save_embeddings()` / `load_embeddings()` exist for disk caching
3. Pre-computation is expected to take ~23.8 minutes (but ranking is sub-second)

### Recommendation

Add to `README.md`:

```markdown
## Pre-computation Workflow

The Semantic Engine uses sentence-transformers/all-MiniLM-L6-v2 for
embedding-based similarity. This requires a one-time pre-computation step:

1. First run downloads the model (~88 MB, cached locally)
2. Run `precompute(candidates)` to encode all 4 text fields
3. (Optional) Run `save_embeddings("./embeddings/")` to persist to disk
4. On subsequent runs, `load_embeddings("./embeddings/")` loads in < 1 second

Pre-computation is part of the BUILD phase (not timed). The ranking step
(load + extract) completes in under 5 minutes with cached embeddings.

Pre-computed embedding files (`.npz`, `.npy`) are tracked in Git and
included in the reproduction Docker container.
```

---

## 5. Competition Submission: Judge Reproducibility ❌ FAIL

### Current State vs. Competition Requirements

| Competition Requirement | Status | Gap |
|-------------------------|--------|-----|
| `rank.py` exists with single reproduce command | ❌ **Missing** | `rank.py` does not exist yet (Phase 7) |
| `submission_metadata.yaml` at repo root | ❌ **Missing** | Only template exists in `[PUB]/` |
| Pre-computation declared in metadata | ⚠️ **Template only** | Template updated but actual metadata not created |
| Pre-computed artifacts committed to repo | ❌ **No `.npy`/`.npz` files** | `save_embeddings()` never called |
| README documents reproduction steps | ❌ **Outdated** | README shows Phase 4 status, Phase 5 not mentioned |
| Model cached in repo or documented | ❌ **Not documented** | 88 MB model download not mentioned |
| `reproduce_command` is functional | ❌ **Placeholder** | `python rank.py --candidates ...` — rank.py doesn't exist |

### What a Judge Would Experience

1. `git clone` → ✅ Gets all source code
2. `pip install -r requirements.txt` → ✅ Installs (unpinned) deps
3. `python rank.py --candidates ... --out ...` → ❌ **Command not found**
4. Reads README → ❌ **No mention of how to run Phase 5**
5. Discovers `src/features/semantic.py` → ✅ Code exists
6. Tries `python -m pytest tests/ -v` → ✅ Tests pass
7. Writes ad-hoc script to reproduce → ⚠️ Possible but not documented

### Recommendation (for Phase 10 — Final Packaging)

1. **Create `rank.py`** in Phase 7 with the reproduce command
2. **Create `submission_metadata.yaml`** at repo root (copy from template, fill in values)
3. **Commit pre-computed embeddings** (`.npy`/`.npz` files in `embeddings/` directory)
4. **Update README** with:
   - Reproduction command
   - Pre-computation workflow
   - Model caching instructions
   - Phase 5 status
5. **Add `embeddings/` to `.gitignore` exceptions** (so `.npy`/`.npz` files are tracked)

---

## Summary of Required Fixes

| # | Fix | Priority | Phase |
|---|-----|----------|-------|
| 1 | Pin dependency versions in `requirements.txt` | High | Now |
| 2 | Document Python version requirement in README | High | Now |
| 3 | Document embedding generation workflow in README | Medium | Now |
| 4 | Create `rank.py` with reproduce command | High | Phase 7 |
| 5 | Create `submission_metadata.yaml` at repo root | High | Phase 10 |
| 6 | Commit pre-computed `.npy`/`.npz` embedding cache | Medium | Phase 10 |
| 7 | Add `pyproject.toml` with `requires-python` | Medium | Now |

**Items marked "Now" can be done in the current phase without affecting scope.**

---

## Verdict

| Criterion | Status |
|-----------|--------|
| 1. Pinned requirements.txt | ❌ **FAIL** — All packages use `>=` |
| 2. Python version documented | ❌ **FAIL** — Not mentioned anywhere |
| 3. Clean machine reproduction | ⚠️ **PASS with notes** — Works but unpinned deps add risk |
| 4. Embedding workflow documented | ❌ **FAIL** — Not mentioned in README |
| 5. Judge reproducibility | ❌ **FAIL** — No `rank.py`, no metadata, no cache files |
| **Overall** | **❌ FAIL — Needs corrections before Phase 6** |

**Bottom line:** The code works and tests pass, but the repository is not hardened for judge reproduction. The 3 "Now" fixes should be applied before moving to Phase 6.

*End of Phase 5 Hardening Report*
