# Redrob AI Ranker — Intelligent Candidate Discovery & Ranking

**Redrob Hackathon — India Runs Data & AI Challenge**

A ranking system that identifies the best-fit candidates for a **Senior AI Engineer, Founding Team** role at **Redrob AI** from a pool of 100,000 anonymized candidate profiles.

---

## Challenge Overview

Given 100,000 candidate profiles in JSONL format, produce a ranked CSV of the **top 100** candidates best matching the provided job description. The ranking must:

- Be **CPU-only** (no GPU)
- Complete **under 5 minutes**
- Use **≤16GB RAM**
- Require **no network access** during ranking

## Repository Structure

```
├── .gitignore
├── README.md
├── requirements.txt
├── SELF_AUDIT.md                # Runtime audit trail (Phases 1-4)
├── src/                         # Core Python package
│   ├── __init__.py
│   ├── loader/                  # Streaming JSONL data loader (Phase 4)
│   ├── parser/                  # Candidate parser with schema validation (Phase 4)
│   ├── features/                # Feature extraction framework (Phase 4)
│   └── utils/                   # Utility functions (Phase 4)
├── tests/                       # Test suite (103 tests: Phase 4 + Phase 5)
│   ├── conftest.py
│   ├── test_loader.py
│   ├── test_parser.py
│   ├── test_features.py
│   └── test_features_semantic.py
├── docs/                        # Phase documentation
│   ├── ANALYSIS_REPORT.md       # Phase 1 — Full competition analysis
│   ├── FEATURE_CATALOG.md       # Phase 2 — 35-feature blueprint
│   ├── ARCHITECTURE.md          # Phase 3 — 9-module pipeline design
│   └── PHASE_*_*.md             # Phase reports (Phases 1-5)
├── pyproject.toml               # Project metadata + Python version requirement
└── [PUB] India_runs_data_and_ai_challenge/  # Competition dataset (sample files tracked)
```

## Dataset

| File | Description |
|------|-------------|
| `candidates.jsonl` | 100,000 candidate profiles (JSONL, one object per line) |
| `candidate_schema.json` | JSON Schema for candidate profiles |
| `job_description.docx` | Target job description: Senior AI Engineer, Founding Team |
| `submission_spec.docx` | Full submission specification and scoring rules |
| `redrob_signals_doc.docx` | Reference for 23 behavioral signals |
| `validate_submission.py` | Local validation script for submission CSV format |

> **Note:** Competition data files are located in `[PUB] India_runs_data_and_ai_challenge/India_runs_data_and_ai_challenge/`.

## Submission Format

```csv
candidate_id,rank,score,reasoning
CAND_0042871,1,0.987,"Senior AI Engineer with 7 years building RAG systems..."
```

- Exactly 100 rows
- Ranks 1–100 (unique)
- Scores non-increasing by rank
- Reasoning column provides explainability

## Scoring Metrics

| Metric | Weight |
|--------|--------|
| NDCG@10 | 50% |
| NDCG@50 | 30% |
| MAP | 15% |
| P@10 | 5% |

## Setup

```bash
# Clone the repository
git clone https://github.com/Pragadeesh-D/redrob-ai-ranker.git
cd redrob-ranker

# Create and activate a virtual environment (recommended)
python -m venv venv
source venv/bin/activate   # Linux/macOS
# venv\Scripts\activate    # Windows

# Install dependencies
pip install -r requirements.txt

# Run tests to verify the setup
python -m pytest tests/ -v

# Run the ranker (once fully implemented in Phase 5+)
# python rank.py --candidates "[PUB] India_runs_data_and_ai_challenge/India_runs_data_and_ai_challenge/candidates.jsonl" --out ./submission.csv

# Validate a submission CSV
# python "[PUB] India_runs_data_and_ai_challenge/India_runs_data_and_ai_challenge/validate_submission.py" submission.csv
```

## Phases

| Phase | Focus | Status |
|-------|-------|--------|
| 1 | Foundation & Analysis | ✅ Complete |
| 2 | Feature Catalog — 35 features across 9 categories | ✅ Complete |
| 3 | Architecture Design — 9-module pipeline | ✅ Complete |
| 4 | Core Engine — Data Loader, Parser, Feature Framework | ✅ Complete |
| 5 | Semantic Engine — Embedding-based JD-candidate similarity scoring | ✅ Complete |
| 6 | Honeypot Detection | ⬜ Pending |
| 7 | Ranking Pipeline & Reasoning | ⬜ Pending |
| 8 | Optimization & Performance Tuning | ⬜ Pending |
| 9 | Expanded Testing & Validation | ⬜ Pending |
| 10 | Final Packaging & Submission | ⬜ Pending |

---

## Semantic Engine (Phase 5)

The Semantic Engine computes embedding-based similarity between candidate profiles and the target job description using `sentence-transformers/all-MiniLM-L6-v2`.

### Model

| Property | Value |
|----------|-------|
| **Model** | `sentence-transformers/all-MiniLM-L6-v2` |
| **Dimensions** | 384 |
| **Size** | ~88 MB (downloaded on first use, cached locally) |
| **Execution** | CPU-only (`device="cpu"`) |
| **First-run** | Requires network to download from HuggingFace Hub |
| **Cache location** | `~/.cache/huggingface/hub/` |

### Features Produced

| Feature | Source | Description |
|---------|--------|-------------|
| `jd_similarity_score` | Headline + Summary + Current Title | Overall profile-JD semantic similarity |
| `summary_similarity_score` | Profile Summary | Summary vs JD similarity |
| `headline_similarity_score` | Professional Headline | Headline vs JD similarity |
| `career_similarity_score` | Career History Descriptions | Career evidence vs JD similarity |

### Pre-computation Workflow

```python
from src.features.semantic import SemanticEngine

# 1. Initialize (downloads model on first run, caches JD embedding)
engine = SemanticEngine()

# 2. Pre-compute embeddings for all candidates (build phase — not timed)
engine.precompute(candidates)

# 3. Extract features per candidate (O(1) lookup from cache)
features = engine.extract(candidate)
# Returns: {"jd_similarity_score": 0.85, "summary_similarity_score": 0.72, ...}
```

### Disk Cache for Ranking Phase

Pre-computed embeddings can be saved to disk and loaded in < 1 second during the timed ranking phase:

```python
# Build phase: encode all candidates and save to disk
engine.precompute(candidates)
engine.save_embeddings("./embeddings/")

# Ranking phase (timed): load cached embeddings — no model needed
from src.features.semantic import SemanticEngine
engine = SemanticEngine()
engine.load_embeddings("./embeddings/")
features = engine.extract(candidate)   # < 1 ms per candidate
```

### Performance

| Operation | 10K Candidates | 100K Candidates (Projected) |
|-----------|---------------|-----------------------------|
| Model load | ~8 s | ~8 s |
| Pre-compute (4 fields) | ~143 s | ~23.8 min (build phase) |
| Disk cache load | < 1 s | < 1 s |
| Extract (cached) | ~1 ms/candidate | ~1 ms/candidate |

### RAM Usage

| Component | Size |
|-----------|------|
| Model (all-MiniLM-L6-v2) | ~80 MB (PyTorch C++ heap) |
| Embeddings (100K × 4 fields) | ~5 MB |
| Python overhead | ~5 MB |
| **Total** | **~90 MB** |

### Python Version Requirement

| Requirement | Value |
|-------------|-------|
| **Minimum** | Python 3.10 |
| **Maximum** | Python 3.13 (PyTorch compatibility) |
| **Specified in** | `pyproject.toml` (`requires-python = "\>=3.10,\<3.14"`) |

---

## Current Status

| Metric | Value |
|--------|-------|
| **Phase completed** | Phase 5 — Semantic Engine |
| **Latest commit** | `1e13b4a` |
| **Branch** | `phase5-scoring-engine` |
| **Tags** | `phase4-stable`, `phase5-stable` |
| **Unit tests** | 103/103 passing |
| **Code coverage** | 89% overall (94% semantic.py) |
| **Data loading** | Streaming JSONL (line-by-line, no full dataset in memory) |
| **Throughput (parse)** | ~15,000+ candidates/second |
| **Peak memory (parse)** | ~3–5 MB (streaming mode) |
| **Peak memory (semantic engine)** | ~90 MB (model + embeddings) |
| **Per-candidate parse time** | ~70 µs |
| **Semantic precompute (100K)** | ~23.8 min (build phase, not timed) |
| **Semantic ranking stage** | < 1 s (with disk cache) |
| **Python version** | >=3.10, <3.14 |

---

*Built for the Redrob Intelligent Candidate Discovery & Ranking Challenge*
