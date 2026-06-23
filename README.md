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
├── tests/                       # Test suite (Phase 4, 75 tests)
│   ├── conftest.py
│   ├── test_loader.py
│   ├── test_parser.py
│   └── test_features.py
├── docs/                        # Phase documentation
│   ├── ANALYSIS_REPORT.md       # Phase 1 — Full competition analysis
│   ├── FEATURE_CATALOG.md       # Phase 2 — 35-feature blueprint
│   ├── ARCHITECTURE.md          # Phase 3 — 9-module pipeline design
│   └── PHASE_*_*.md             # Phase reports (Phases 1-4)
└── [PUB] India_runs_data_and_ai_challenge/  # Competition dataset (gitignored)
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
| 5 | Scoring Engine Implementation | ⬜ Pending |
| 6 | Honeypot Detection | ⬜ Pending |
| 7 | Ranking Pipeline & Reasoning | ⬜ Pending |
| 8 | Optimization & Performance Tuning | ⬜ Pending |
| 9 | Expanded Testing & Validation | ⬜ Pending |
| 10 | Final Packaging & Submission | ⬜ Pending |

---

## Current Status

| Metric | Value |
|--------|-------|
| **Phase completed** | Phase 4 — Core Engine |
| **Latest commit** | `0c12969` |
| **Unit tests** | 75/75 passing |
| **Code coverage** | 87% overall (96% target modules) |
| **Data loading** | Streaming JSONL (line-by-line, no full dataset in memory) |
| **Throughput** | ~15,000+ candidates/second |
| **Peak memory** | ~3–5 MB (streaming mode) |
| **Per-candidate parse time** | ~70 µs |
| **100K candidate projection** | ~7 seconds |
| **5-minute budget margin** | ~80%+ |

---

*Built for the Redrob Intelligent Candidate Discovery & Ranking Challenge*
