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
├── docs/
│   ├── ANALYSIS_REPORT.md      # Phase 1 — Full competition analysis
│   └── PHASE_1_SUMMARY.md      # Phase 1 — Completion summary
├── SELF_AUDIT.md                # Runtime audit trail
├── rank.py                      # (Phase 5+) Main ranking pipeline
├── features/                    # (Phase 4+) Feature extraction modules
├── scoring/                     # (Phase 5+) Scoring modules
└── tests/                       # (Phase 9+) Test suite
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
git clone <repo-url>
cd redrob-ranker

# Install dependencies
pip install -r requirements.txt

# Run the ranker (once implemented)
python rank.py --candidates ./candidates.jsonl --out ./submission.csv

# Validate the submission
python validate_submission.py submission.csv
```

## Phases

| Phase | Focus | Status |
|-------|-------|--------|
| 1 | Foundation & Analysis | ✅ Complete |
| 2 | Data Parsing & Schema Validation | ⬜ Pending |
| 3 | Feature Extraction & Engineering | ⬜ Pending |
| 4 | Scoring Strategy Design | ⬜ Pending |
| 5 | Ranker Implementation | ⬜ Pending |
| 6 | Honeypot Detection | ⬜ Pending |
| 7 | Behavioral Signal Integration | ⬜ Pending |
| 8 | Optimization & Performance Tuning | ⬜ Pending |
| 9 | Testing & Validation | ⬜ Pending |
| 10 | Final Packaging & Submission | ⬜ Pending |

---

*Built for the Redrob Intelligent Candidate Discovery & Ranking Challenge*
