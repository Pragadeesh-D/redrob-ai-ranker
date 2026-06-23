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
├── rank.py                        # CLI entry point — reproducible ranking pipeline
├── app.py                         # Streamlit demo app
├── submission.csv                 # Generated submission (top 100 ranked candidates)
├── submission_metadata.yaml       # Competition metadata
├── .gitignore
├── README.md
├── requirements.txt
├── src/                           # Core Python package
│   ├── __init__.py
│   ├── loader/                    # Streaming JSONL data loader (Phase 4)
│   ├── parser/                    # Candidate parser with schema validation (Phase 4)
│   ├── features/                  # Feature extraction framework + 5 engines
│   │   ├── base.py
│   │   ├── framework.py
│   │   ├── semantic.py            # Phase 5 — Semantic Engine
│   │   ├── career_intelligence.py # Phase 6 — Career Intelligence
│   │   ├── behavioral_intelligence.py # Phase 7 — Behavioral Intelligence
│   │   └── honeypot_detection.py  # Phase 8 — Honeypot Detection
│   └── ranker/                    # Final ranking pipeline (Phase 9)
│       └── ranker.py
├── tests/                         # Test suite (276 tests)
│   ├── conftest.py
│   ├── test_loader.py
│   ├── test_parser.py
│   ├── test_features.py
│   ├── test_features_semantic.py
│   ├── test_features_career_intelligence.py
│   ├── test_features_behavioral_intelligence.py
│   ├── test_features_honeypot_detection.py
│   └── test_ranker.py
├── docs/                          # Phase documentation
│   ├── ARCHITECTURE.md
│   ├── FEATURE_CATALOG.md
│   ├── PHASE_*.md
│   └── ...
└── [PUB] India_runs_data_and_ai_challenge/  # Competition dataset
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

# Run the ranking pipeline
python rank.py --candidates "[PUB] India_runs_data_and_ai_challenge/India_runs_data_and_ai_challenge/candidates.jsonl" --out ./submission.csv

# Validate a submission CSV
python "[PUB] India_runs_data_and_ai_challenge/India_runs_data_and_ai_challenge/validate_submission.py" submission.csv

# Launch the Streamlit demo
streamlit run app.py
```

## Ranking Pipeline

The ranking pipeline (`rank.py`) runs 5 feature engines:

| Phase | Engine | Features | Network? |
|-------|--------|----------|----------|
| 5 | Semantic Engine | 4 (JD similarity scores) | Yes (first run to download model) |
| 6 | Career Intelligence | 20 (product, startup, ML, retrieval exp.) | No |
| 7 | Behavioral Intelligence | 11 (availability, trust, demand, engagement) | No |
| 8 | Honeypot Detection | 10 (timeline, skill, progression checks) | No |
| 9 | Score Fusion + Ranking | Composite score + reasoning | No |

### Pipeline Flow

```
candidates.jsonl → DataLoader → CandidateParser
                                    ↓
                           FeatureRegistry
                        ┌───────┼───────┬───────┐
                        ↓       ↓       ↓       ↓
                   Career   Behav.  Honeypot  Semantic
                   Intel.   Intel.  Detect.  Engine
                        └───────┼───────┴───────┘
                                ↓
                          ScoreFusion
                                ↓
                      FinalRanker → submission.csv
```

### Embedding Cache

The Semantic Engine downloads `all-MiniLM-L6-v2` on first run (~88 MB). Pre-computed embeddings can be cached to disk for subsequent runs without network:

```python
# Build phase (network required)
engine.precompute(candidates)
engine.save_embeddings("./embeddings/")

# Ranking phase (no network)
engine.load_embeddings("./embeddings/")
features = engine.extract(candidate)   # < 1 ms per candidate
```

## Phases

| Phase | Focus | Status |
|-------|-------|--------|
| 1 | Foundation & Analysis | ✅ Complete |
| 2 | Feature Catalog — 35 features across 9 categories | ✅ Complete |
| 3 | Architecture Design — 9-module pipeline | ✅ Complete |
| 4 | Core Engine — Data Loader, Parser, Feature Framework | ✅ Complete |
| 5 | Semantic Engine — Embedding-based JD-candidate similarity scoring | ✅ Complete |
| 6 | Career Intelligence — Product/ML/Startup/Ranking experience signals | ✅ Complete |
| 7 | Behavioral Intelligence — Availability, Trust, Demand, Engagement | ✅ Complete |
| 8 | Honeypot Detection — Timeline/skill/seniority consistency checks | ✅ Complete |
| 9 | Final Ranker — Weighted score fusion, reasoning, submission generation | ✅ Complete |
| 10 | Submission Package — CLI, Streamlit demo, validation, packaging | ✅ Complete |

## Performance

| Metric | Value |
|--------|-------|
| **Total tests** | 276/276 passing |
| **Phase 5-9 regression** | Zero — all previous phases unchanged |
| **Ranking throughput** | > 500 candidates/sec (3 engines, no semantic) |
| **Peak RAM (no semantic)** | < 5 MB |
| **Peak RAM (with semantic)** | ~90 MB (model + embeddings) |
| **Python version** | >=3.10, <3.14 |
| **CPU-only** | ✅ No GPU dependency |
| **Deterministic** | ✅ Same input → same output |

## Streamlit Demo

A visual demo is available at `app.py` showing:

- Candidate ranking table with scores
- Per-candidate radar chart (6 dimensions)
- Cross-candidate comparison bar chart
- Component score heatmap
- Downloadable submission.csv

```bash
streamlit run app.py
```

---

*Built for the Redrob Intelligent Candidate Discovery & Ranking Challenge*
*10-phase architecture, CPU-only, fully reproducible*
