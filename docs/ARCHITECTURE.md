# Architecture Design — Phase 3

> **Date:** June 19, 2026
> **Prerequisites:** `docs/ANALYSIS_REPORT.md` (Phase 1), `docs/FEATURE_CATALOG.md` (Phase 2)
> **Status:** ✅ Design complete — no implementation code generated
> **Target:** Hybrid Feature-Based Ranker with 9 modules

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Module Definitions](#2-module-definitions)
3. [Folder Structure](#3-folder-structure)
4. [Data Flow](#4-data-flow)
5. [Runtime Estimate](#5-runtime-estimate)
6. [RAM Estimate](#6-ram-estimate)
7. [Competition Constraints](#7-competition-constraints)
8. [Error Handling Strategy](#8-error-handling-strategy)
9. [Design Decisions](#9-design-decisions)

---

## 1. System Overview

The ranking system is a **hybrid feature-based pipeline** that processes 100,000 candidate profiles through 9 sequential modules. Each module has a single responsibility, well-defined interfaces, and minimal cross-module coupling.

### Architectural Principles

| Principle | Rationale |
|-----------|-----------|
| **Streaming-first** | Process one candidate at a time — never load the full dataset into memory |
| **Sequential pipeline** | Each module consumes and produces structured dicts; no shared state |
| **CPU-only design** | No GPU dependencies; all operations are pure Python + numpy |
| **No network access** | All databases (company lists, skill taxonomies) are local static files |
| **Fail-fast validation** | Schema errors are caught early; malformed data is logged, not fatal |
| **Deterministic output** | Same input always produces same output (no randomness) |

### High-Level Pipeline

```
┌──────────┐    ┌──────────┐    ┌──────────────────┐    ┌──────────────┐
│  Data    │───→│ Candidate│───→│ Feature          │───→│  Scoring     │
│  Loader  │    │  Parser  │    │ Extraction (9×)  │    │  Components  │
└──────────┘    └──────────┘    └──────────────────┘    └──────┬───────┘
                                                               │
                                                               ▼
┌──────────┐    ┌──────────┐    ┌──────────────────┐    ┌──────────────┐
│Submission│←───│ Reasoning│←───│ Final            │←───│  Score       │
│  Output  │    │ Generator│    │ Ranker           │    │  Aggregation │
└──────────┘    └──────────┘    └──────────────────┘    └──────────────┘
```

---

## 2. Module Definitions

### 2.1 Data Loader

| Field | Value |
|-------|-------|
| **Purpose** | Stream 100,000 candidate records from `candidates.jsonl` line-by-line without loading the full file into memory |
| **Inputs** | File path to `candidates.jsonl` (JSONL format, UTF-8 encoded) |
| **Outputs** | Generator yielding individual JSON objects (one per candidate) |
| **Dependencies** | Python `json` standard library |
| **Processing responsibility** | <ul><li>Open file handle with buffered I/O</li><li>Iterate lines, parse each as JSON</li><li>Yield parsed dict for downstream processing</li><li>Track line count for progress monitoring</li><li>Handle malformed JSON lines (log warning, skip, continue)</li></ul> |
| **Failure modes** | <ul><li>File not found → fatal error</li><li>Malformed JSON on line → log + skip line (count as parse error)</li><li>Encoding issues → retry with `errors='replace'`, log warning</li></ul> |
| **Runtime impact** | **~2-5 seconds** for 100K lines. I/O bound. Buffered reading is fast. |
| **Memory impact** | **~1 MB** — holds one line at a time (~2-8 KB per candidate). No accumulation. |

### 2.2 Candidate Parser

| Field | Value |
|-------|-------|
| **Purpose** | Parse a raw JSON candidate object into a validated, typed structure with accessor methods for all sub-fields |
| **Inputs** | Parsed JSON dict from Data Loader |
| **Outputs** | Structured `Candidate` object (dataclass/Pydantic-like) with validated sub-objects: `profile`, `career_history[]`, `education[]`, `skills[]`, `redrob_signals` |
| **Dependencies** | Data Loader (upstream), Python `dataclasses` module, schema definition |
| **Processing responsibility** | <ul><li>Validate top-level required fields: `candidate_id`, `profile`, `career_history`, `education`, `skills`, `redrob_signals`</li><li>Validate `candidate_id` format: `CAND_XXXXXXX`</li><li>Parse nested objects with field-level type coercion</li><li>Normalize dates to ISO format</li><li>Compute derived fields: `total_career_months`, `current_role_index`, `career_gap_months`</li><li>Handle missing optional fields (`certifications`, `languages`) gracefully</li></ul> |
| **Failure modes** | <ul><li>Missing required fields → log error, yield None (candidate skipped)</li><li>Invalid `candidate_id` format → log warning, still process (use as-is)</li><li>Type mismatch (string instead of number) → attempt coercion, log warning</li><li>Null `end_date` on current role → leave as None (expected)</li></ul> |
| **Runtime impact** | **~3-8 seconds** for 100K. Lightweight parsing + validation per record. |
| **Memory impact** | **~5-10 MB** — processes one candidate at a time. Temporary object per candidate is garbage-collected after downstream consumption. |

### 2.3 Semantic Engine

| Field | Value |
|-------|-------|
| **Purpose** | Compute text-based relevance scores by matching candidate profile text (title, headline, summary) against the JD's target role profile |
| **Inputs** | Structured `Candidate` object from Parser; `title_taxonomy.json` (title → score mapping), `skill_taxonomy.json` (skill → domain mapping) |
| **Outputs** | Feature dict: `{title_semantic_score, headline_relevance_score, summary_relevance_score, title_skill_consistency_score}` |
| **Dependencies** | Candidate Parser (upstream), `data/title_taxonomy.json`, `data/skill_taxonomy.json` |
| **Processing responsibility** | <ul><li>**Title score:** Classify `profile.current_title` against a title taxonomy. AI/ML titles → high (0.8-1.0), tech titles → medium (0.4-0.7), non-tech titles → low (0.0-0.3). Also score past career titles (weighted by recency).</li><li>**Headline score:** Tokenize `profile.headline`, match against JD keyword set with TF-style weighting (rarer keywords weigh more).</li><li>**Summary score:** Scan `profile.summary` for production ML indicators (keywords, context patterns). Penalize generic templates.</li><li>**Title-skill consistency:** If non-tech title + 3+ advanced/expert AI/ML skills → score penalty. Cross-reference career descriptions — if they support AI/ML experience, reduce penalty. (F24, 3% of BASE_MATCH_SCORE)</li></ul> |
| **Failure modes** | <ul><li>Empty headline/summary → default to 0.0 score (no penalty beyond missing signal)</li><li>Unknown title not in taxonomy → classify via substring matching, default to tech (0.4)</li><li>Title taxonomy file missing → fatal error (design-time data)</li></ul> |
| **Runtime impact** | **~5-10 seconds** for 100K. Keyword matching is O(n × keywords) per candidate. Pre-compiled regex patterns minimize overhead. |
| **Memory impact** | **~50 MB** — title taxonomy (~5 MB), skill taxonomy (~5 MB), pre-compiled regex patterns (~1 MB). Candidate data is processed and released. |

### 2.4 Career Intelligence Engine

| Field | Value |
|-------|-------|
| **Purpose** | Analyze career history to detect shipped ML systems, product company experience, AI/ML role duration, and consulting-only patterns — **the most important signal group per the JD** |
| **Inputs** | Structured `Candidate` object from Parser; `data/company_db.json` (product companies, consulting firms) |
| **Outputs** | Feature dict: `{shipped_systems_score, product_company_score, ai_ml_duration_score, role_progression_score, consulting_only_penalty, eval_experience_score}` |
| **Dependencies** | Candidate Parser (upstream), `data/company_db.json` |
| **Processing responsibility** | <ul><li>**Shipped systems:** Scan all `career_history[].description` for production ML keywords with context scoring. Weighted by role duration.</li><li>**Product company:** Cross-reference each `career_history[].company` against product/consulting databases. Score per role, normalize.</li><li>**AI/ML duration:** Classify each role as AI/ML or not based on title + description. Sum months in AI/ML roles, compute ratio.</li><li>**Role progression:** Detect junior→senior transitions, title inflation (<18 month hops), specialization trends.</li><li>**Consulting penalty:** Flag if ALL roles are at consulting firms → ×0.3 penalty. Mixed career → ×0.8.</li><li>**Evaluation experience:** Scan for NDCG/MRR/MAP/A-B test/bibliographic keywords.</li></ul> |
| **Failure modes** | <ul><li>Empty career history → all scores default to 0.0 (rare — schema requires minItems: 1)</li><li>Company not in database → classify as "unknown" → 0.0 product score (no bonus, no penalty)</li><li>Negative durations → clamp to 0, log warning (data anomaly)</li></ul> |
| **Runtime impact** | **~15-25 seconds** for 100K. Most expensive module due to career description text scanning. Each career entry's description (~50-200 words) is analyzed. |
| **Memory impact** | **~20 MB** — company database (~3 MB), pre-compiled keyword patterns (~1 MB). Career entries processed one candidate at a time. |

### 2.5 Behavioral Engine

| Field | Value |
|-------|-------|
| **Purpose** | Compute availability and engagement scores from the 23 Redrob behavioral signals — used as a multiplicative modifier on the base match score |
| **Inputs** | Structured `Candidate` object from Parser (specifically `redrob_signals` sub-object) |
| **Outputs** | Feature dict: `{recruiter_response_rate_score, profile_recency_score, open_to_work_score, platform_engagement_score, skill_assessment_score}` + computed `behavioral_modifier` (0.4–1.2) |
| **Dependencies** | Candidate Parser (upstream) |
| **Processing responsibility** | <ul><li>**Response rate:** Normalize `recruiter_response_rate` (0.0-1.0) with baseline at 0.5</li><li>**Profile recency:** Compare `last_active_date` to reference date, score by recency tier</li><li>**Open to work:** Map boolean to score (true=1.0, false=0.6)</li><li>**Engagement:** Combine `search_appearance_30d` + `saved_by_recruiters_30d` with linear normalization</li><li>**Skill assessment:** Average available assessment scores from `skill_assessment_scores` dict; treat empty dict as 0 (no bonus, no penalty)</li><li>**Compute modifier:** Weighted sum of 5 component scores → clamp to [0.4, 1.2]</li></ul> |
| **Failure modes** | <ul><li>Missing signal fields → default to baseline (0.5), log warning</li><li>`last_active_date` in future (data error) → assume very recent (score = 1.0)</li><li>Empty `skill_assessment_scores` → score = 0.0 (neutral — no bonus, no penalty)</li><li>`recruiter_response_rate` > 1.0 (data error) → clamp to 1.0</li></ul> |
| **Runtime impact** | **~2-5 seconds** for 100K. Pure numeric computation. No text analysis. |
| **Memory impact** | **~5 MB** — signal data per candidate streamed through. No large structures. |

### 2.6 Availability Engine

| Field | Value |
|-------|-------|
| **Purpose** | Compute availability-related scores: notice period, relocation willingness, salary fit, and work mode preference |
| **Inputs** | Structured `Candidate` object from Parser (profile + redrob_signals) |
| **Outputs** | Feature dict: `{notice_period_score, relocation_score, salary_fit_score}` |
| **Dependencies** | Candidate Parser (upstream) |
| **Processing responsibility** | <ul><li>**Notice period:** Tier score by `notice_period_days` (0-30=1.0, 31-60=0.8, 61-90=0.6, 90+=0.4)</li><li>**Relocation:** Boolean `willing_to_relocate` combined with location. International + not willing → strong penalty (0.3). India + not willing → mild penalty (0.7).</li><li>**Salary fit:** Compute midpoint of `expected_salary_range_inr_lpa`. Score by proximity to 20-40 LPA range. Flag inverted salaries (min>max) as data anomalies.</li></ul> |
| **Failure modes** | <ul><li>Missing `notice_period_days` → default to 90 (conservative estimate)</li><li>Inverted salary (min>max) → use max as single value, apply data anomaly flag</li><li>Missing `preferred_work_mode` → default to "hybrid" (no penalty)</li></ul> |
| **Runtime impact** | **~2-5 seconds** for 100K. Pure numeric. Negligible overhead. |
| **Memory impact** | **~2 MB** — field access + arithmetic only. |

### 2.7 Honeypot Detector

| Field | Value |
|-------|-------|
| **Purpose** | Detect spec-defined impossible profiles and other suspicious patterns. Apply additive penalties to naturally demote honeypots below rank 100 without special-casing (per spec requirement) |
| **Inputs** | Structured `Candidate` object from Parser (skills + redrob_signals) |
| **Outputs** | Penalty dict: `{expert_zero_duration_flag, excessive_expert_skills_flag, salary_inconsistency_flag, skill_diversity_penalty}` |
| **Dependencies** | Candidate Parser (upstream), `data/skill_taxonomy.json` |
| **Processing responsibility** | <ul><li>**Expert+zero duration:** Scan `skills[]` for entries where `proficiency == 'expert'` AND `duration_months == 0`. Penalty: -0.5 per instance, cumulative capped at -1.0.</li><li>**Excessive expert skills:** Count expert-level skills. 5-7 → -0.3. 8+ → -0.5.</li><li>**Salary inconsistency:** If `expected_salary_range_inr_lpa.min > max` → -0.1 (data anomaly, not honeypot).</li><li>**Skill diversity:** Categorize all skills into domains. Skills spanning 3+ unrelated domains → -0.2.</li></ul> |
| **Failure modes** | <ul><li>Empty skills array → all honeypot flags default to 0 (no penalty)</li><li>Missing proficiency field → treat as "beginner" (conservative, no false positive)</li><li>Skill not in taxonomy → classify as "unknown" (count toward diversity but not specifically penalized)</li></ul> |
| **Runtime impact** | **~3-8 seconds** for 100K. Scanning skills array and cross-referencing titles. |
| **Memory impact** | **~2 MB** — skill taxonomy for domain classification (~1 MB), plus temporary per-candidate skill analysis. |

### 2.8 Final Ranker

| Field | Value |
|-------|-------|
| **Purpose** | Aggregate all feature scores and penalties into a final score, sort 100,000 candidates, select top 100, and produce deterministic ranking with non-increasing scores |
| **Inputs** | Dict of all 35 feature scores, penalties, and modifiers from upstream engines |
| **Outputs** | Ranked list of 100 `(candidate_id, rank, score)` tuples |
| **Dependencies** | All 6 feature engines (Semantic, Career Intelligence, Behavioral, Availability, Honeypot, Location, Experience, Education, Trust) + Scoring Components |
| **Processing responsibility** | <ul><li>**Score assembly:** Collect pre-computed score components from `scoring/` package: BASE_MATCH_SCORE from `base_score.py`, behavioral modifier from `modifiers.py`, consulting penalty from `modifiers.py`, honeypot penalty from `penalties.py`</li><li>**Apply modifiers:** FINAL = BASE_MATCH × BEHAVIORAL × CONSULTING − HONEYPOT</li><li>**Normalize:** Clamp final score to [0.0, 1.0]</li><li>**Sort:** Descending by FINAL_SCORE</li><li>**Top 100 selection:** Take first 100 entries</li><li>**Tie-breaking:** Apply 4-level cascade: shipped_systems > response_rate > notice_period > candidate_id ascending</li><li>**Ensure monotonicity:** Verify score[i] >= score[i+1]; adjust if floating-point edge case</li></ul> |
| **Failure modes** | <ul><li>Feature values out of range → clamp to [0.0, 1.0] before aggregation</li><li>NaN feature value → default to 0.0 (fail-safe — should not occur with well-defined extractors)</li><li>All candidates have identical scores → rely on candidate_id ascending (final tie-breaker)</li><li>Fewer than 100 candidates total → rank whatever we have (edge case — dataset has 100K)</li></ul> |
| **Runtime impact** | **~1-2 seconds** for 100K. Pure numpy-accelerated array operations. Sorting 100K floats is O(n log n) ≈ 1.7M comparisons. |
| **Memory impact** | **~5 MB** — score arrays: float64 × 100K = 0.8 MB, plus candidate_id mappings (~2 MB). Top-100 storage is negligible. |

### 2.9 Reasoning Generator

| Field | Value |
|-------|-------|
| **Purpose** | Generate a concise, specific, unique reasoning string for each of the top 100 candidates. Used in Stage 4 manual review (10 random rows checked). Must avoid templates, hallucination, and identical strings. |
| **Inputs** | Top-100 ranked candidates with their full feature dicts; `profile` data for each |
| **Outputs** | List of 100 `(candidate_id, reasoning)` pairs |
| **Dependencies** | Final Ranker (upstream) — for ranked order + feature data |
| **Processing responsibility** | <ul><li>For each top-100 candidate, construct a 3-part reasoning string: `[Role summary] + [Key qualification stat] + [Notable signal/flag]`</li><li>**Part 1 (Role):** Current title + total years of experience</li><li>**Part 2 (Qualification):** Most relevant signal (shipped systems score, AI/ML duration, skill count) — pick the strongest</li><li>**Part 3 (Notable):** Behavioral or availability signal (response rate, notice period, location preference)</li><li>Ensure each string is unique by including at least one specific numeric value per candidate</li><li>No template text, no candidate name, no hallucinated skills</li></ul> |
| **Failure modes** | <ul><li>Duplicate reasoning strings for different candidates → append candidate-specific tie-breaker from profile</li><li>Missing profile data → use what's available, skip missing fields</li><li>Reasoning string exceeds 200 chars → truncate at last complete word within limit</li></ul> |
| **Runtime impact** | **~5-10 seconds** for top 100. String formatting only. Minimal overhead. |
| **Memory impact** | **~1 MB** — 100 reasoning strings at ~150 chars each = ~15 KB. Negligible. |

---

## 3. Folder Structure

### Proposed Repository Layout

```
redrob-ranker/
│
├── ranker/                          # Main Python package
│   ├── __init__.py                  # Package init, version
│   ├── __main__.py                  # Entry point: `python -m ranker`
│   ├── pipeline.py                  # Pipeline orchestrator
│   ├── config.py                    # Configuration (weights, paths, thresholds)
│   │
│   ├── models/                      # Data models / schemas
│   │   ├── __init__.py
│   │   ├── candidate.py             # Candidate dataclass (all sub-fields)
│   │   └── submission.py            # Submission record model
│   │
│   ├── loader/                      # Data Loading Module
│   │   ├── __init__.py
│   │   ├── data_loader.py           # Streaming JSONL reader
│   │   └── schema_validator.py      # JSON Schema validation
│   │
│   ├── parser/                      # Candidate Parser Module
│   │   ├── __init__.py
│   │   ├── profile_parser.py        # Profile/skills/education extraction
│   │   ├── career_parser.py         # Career history parsing + derived fields
│   │   └── signals_parser.py        # Behavioral signals parsing
│   │
│   ├── features/                    # Feature Extraction Modules
│   │   ├── __init__.py              # Feature registry / dispatcher
│   │   ├── semantic.py              # F1-F3: Title, headline, summary scores
│   │   ├── career_intelligence.py   # F4-F9: Shipped systems, product company, etc.
│   │   ├── behavioral.py            # F10-F14: Response rate, recency, engagement
│   │   ├── availability.py          # F15-F17: Notice period, relocation, salary
│   │   ├── honeypot.py              # F21-F23, F35: Honeypot detectors + penalties
│   │   ├── location.py              # F25-F27: India, city, work mode scores
│   │   ├── experience.py            # F28-F30, F34: Total exp, stability, industry
│   │   ├── education.py             # F31-F33: Degree, institution, level scores
│   │   └── trust.py                 # F18-F20: Completeness, verification, GitHub
│   │
│   ├── scoring/                     # Scoring Components Module
│   │   ├── __init__.py
│   │   ├── base_score.py            # Weighted sum of base features
│   │   ├── modifiers.py             # Behavioral modifier + consulting penalty
│   │   ├── penalties.py             # Honeypot penalty aggregation
│   │   └── normalizer.py            # Score clamping and monotonicity check
│   │
│   ├── ranking/                     # Final Ranker Module
│   │   ├── __init__.py
│   │   ├── ranker.py                # Sort, select top 100, rank assignment
│   │   └── tie_breaker.py           # 4-level cascade tie-breaking
│   │
│   ├── reasoning/                   # Reasoning Generator Module
│   │   ├── __init__.py
│   │   └── generator.py             # Top-100 reasoning string generation
│   │
│   └── output/                      # Output Module
│       ├── __init__.py
│       ├── submission_writer.py     # Write submission.csv
│       └── submission_validator.py  # Validate output format pre-write
│
├── data/                            # Static reference data (loaded at startup)
│   ├── company_db.json              # Product + consulting firm classification
│   ├── title_taxonomy.json          # Title → category → score mapping
│   ├── skill_taxonomy.json          # Skill → domain classification
│   ├── industry_mapping.json        # Industry → relevance score mapping
│   └── jd_keywords.json             # JD keyword set with weights
│
├── tests/                           # Test suite (Phase 9)
│   ├── __init__.py
│   ├── test_loader.py               # Data loader tests (edge cases, errors)
│   ├── test_parser.py               # Candidate parser tests
│   ├── test_features_semantic.py    # Semantic engine tests
│   ├── test_features_career.py      # Career intelligence tests
│   ├── test_features_behavioral.py  # Behavioral engine tests
│   ├── test_features_availability.py
│   ├── test_features_honeypot.py
│   ├── test_features_location.py
│   ├── test_features_experience.py
│   ├── test_features_education.py
│   ├── test_features_trust.py
│   ├── test_scoring.py              # Score aggregation tests
│   ├── test_ranking.py              # Ranking + tie-break tests
│   ├── test_reasoning.py            # Reasoning generation tests
│   ├── test_pipeline.py             # End-to-end pipeline tests
│   └── test_submission.py           # Output format tests
│
├── scripts/                         # Utility scripts
│   ├── analyze_dataset.py           # Dataset statistics (Phase 1)
│   └── validate_submission.py       # Competition-provided submission validator
│
├── docs/                            # Phase documentation
│   ├── ANALYSIS_REPORT.md           # Phase 1 — Analysis
│   ├── FEATURE_CATALOG.md           # Phase 2 — Feature blueprint
│   ├── ARCHITECTURE.md              # Phase 3 — Architecture (this file)
│   ├── PHASE_1_SUMMARY.md
│   ├── PHASE_2_SUMMARY.md
│   ├── PHASE_3_SUMMARY.md
│   └── PHASE_*.md                   # Future phases
│
├── [PUB] India_runs_data_and_ai_challenge/  # Competition data (gitignored)
│
├── requirements.txt                 # Python dependencies
├── README.md                        # Project documentation
├── SELF_AUDIT.md                    # Runtime audit trail
├── .gitignore                       # Git exclusion rules
└── submission_metadata.yaml         # Competition metadata file
```

### Key Structural Decisions

| Decision | Rationale |
|----------|-----------|
| **Single package `ranker/`** | Simple namespace; avoids deep nesting. All internal imports are relative. |
| **Separate `features/` package** | Each feature group has its own file. Makes it easy to add/remove/modify features independently. Feature registry (`__init__.py`) maps feature names to extractor functions. |
| **Separate `data/` directory** | Static reference data is versioned alongside code. No external database needed. |
| **Models in `models/`** | `Candidate` dataclass ensures type safety. Downstream modules receive typed objects, not raw dicts. |
| **Flat test structure** | One test file per module. Easy to run targeted tests. Phase 9 will expand the test suite. |

---

## 4. Data Flow

### 4.1 End-to-End Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         START PIPELINE                                   │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Step 1: INITIALIZATION                                                  │
│  • Load config (weights, paths, thresholds)                              │
│  • Load reference data (company_db, title_taxonomy, etc.)                │
│  • Open output file handle                                               │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Step 2: LOAD & PARSE (per candidate, streamed)                          │
│                                                                          │
│  ┌────────────┐    ┌──────────────┐    ┌──────────────┐                 │
│  │ Read line  │───→│ Parse JSON   │───→│ Validate &   │                 │
│  │ from JSONL │    │ (json.loads) │    │ Construct    │                 │
│  │            │    │              │    │ Candidate()  │                 │
│  └────────────┘    └──────────────┘    └──────┬───────┘                 │
│                                               │                         │
│                                        [if invalid]                      │
│                                            │                             │
│                                        [skip + log]                      │
│                                               │                         │
│                                               ▼                         │
│                                       Candidate object                   │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Step 3: FEATURE EXTRACTION (per candidate, sequential)                  │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                     Feature Registry                              │   │
│  │                                                                   │   │
│  │  semantic.py ──→ {title_score, headline, summary, title_skill}   │   │
│  │  career_intelligence.py ──→ {shipped, product, ai_ml_dur, ...}    │   │
│  │  behavioral.py ──→ {response_rate, recency, open_to_work, ...}   │   │
│  │  availability.py ──→ {notice, relocation, salary}                │   │
│  │  honeypot.py ──→ {expert_zero, excessive, salary_inv, diversity} │   │
│  │  location.py ──→ {india, preferred_city, work_mode}              │   │
│  │  experience.py ──→ {total_exp, stability, industry, ...}         │   │
│  │  education.py ──→ {degree_relevance, institution, highest_deg}   │   │
│  │  trust.py ──→ {completeness, verification, github}               │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  Output: Feature dict (35 key-value pairs, all in [0,1])                 │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Step 4: SCORE COMPUTATION (per candidate)                               │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  BASE_MATCH = Σ(weight_i × feature_i) for 23 base features       │   │
│  │  BEHAVIORAL = Σ(weight_j × behavioral_j), clamp [0.4, 1.2]      │   │
│  │  CONSULTING = 1.0 (none) / 0.8 (mixed) / 0.3 (all consulting)   │   │
│  │  HONEYPOT   = Σ(penalty_k), clamp [-1.0, 0.0]                   │   │
│  │                                                                   │   │
│  │  FINAL = BASE_MATCH × BEHAVIORAL × CONSULTING - HONEYPOT         │   │
│  │  FINAL = clamp(FINAL, [0.0, 1.0])                                │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  Output: (candidate_id, final_score, feature_dict) for each candidate    │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Step 5: RANKING (batch, after all candidates processed)                 │
│                                                                          │
│  • Collect all (candidate_id, final_score) tuples into array             │
│  • Sort descending by final_score                                        │
│  • Apply tie-breaking cascade if scores are equal                        │
│  • Select top 100                                                        │
│  • Assign ranks 1-100                                                    │
│  • Verify score monotonicity                                             │
│                                                                          │
│  Output: [(rank, candidate_id, final_score)] for top 100                 │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Step 6: REASONING GENERATION (top 100 only)                             │
│                                                                          │
│  • For each top-100 candidate:                                           │
│    1. Read profile data and key feature scores                           │
│    2. Construct 3-part reasoning string                                  │
│    3. Verify uniqueness against all other strings                        │
│    4. If duplicate, append differentiating detail                        │
│                                                                          │
│  Output: [(candidate_id, reasoning_string)] for top 100                  │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Step 7: SUBMISSION OUTPUT                                               │
│                                                                          │
│  • Combine rank, candidate_id, final_score, reasoning into rows          │
│  • Write header: candidate_id,rank,score,reasoning                       │
│  • Write 100 data rows                                                   │
│  • Validate output format (using internal validator)                     │
│  • Close file                                                            │
│                                                                          │
│  Output: submission.csv (100 rows, 4 columns, CSV format)                │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Data Volume at Each Stage

| Stage | Data Held | Candidates in Flight | Size |
|-------|-----------|---------------------|------|
| **Load** | 1 JSON line | 1 | ~2-8 KB |
| **Parse** | 1 Candidate object | 1 | ~10-30 KB |
| **Feature Extraction** | Feature dict | 1 | ~1 KB |
| **Score Computation** | Score tuple | 1 | ~0.2 KB |
| **Ranking** | Score array | 100,000 (full set) | ~3.2 MB |
| **Reasoning** | Top 100 profiles + features | 100 | ~200 KB |
| **Output** | 100 rows | 100 | ~20 KB |

**Critical path**: The ranking stage holds all 100,000 scores in memory (~3.2 MB). This is the peak memory point for score data, but it's still negligible relative to the 16 GB limit.

### 4.3 Error Propagation

```
Loader error (bad line) ──→ skip line, log, continue
Parser error (bad field) ──→ skip candidate, log, continue
Feature error (missing data) ──→ default score 0.0, log warning, continue
Scoring error (NaN) ──→ clamp to 0.0, log, continue
Ranking error (empty set) ──→ fatal (no candidates to rank)
Output error (write failure) ──→ fatal (cannot produce submission)
```

---

## 5. Runtime Estimate

### 5.1 Estimated Processing Time for 100,000 Candidates

| Module | Time (seconds) | Notes |
|--------|---------------|-------|
| **Initialization** (load config/data) | 1-2 | Load company DB, taxonomies into memory |
| **Data Loading** | 2-5 | Buffered JSONL read, I/O bound |
| **Candidate Parsing** | 3-8 | JSON validation, field coercion |
| **Feature Extraction** | | |
| ├─ Semantic Engine | 5-10 | Keyword matching + title classification |
| ├─ Career Intelligence Engine | 15-25 | **Heaviest** — career description text analysis |
| ├─ Behavioral Engine | 2-5 | Pure numeric, fast |
| ├─ Availability Engine | 2-5 | Numeric lookups + simple logic |
| ├─ Honeypot Detector | 3-8 | Skills array scanning |
| ├─ Location Engine | 1-3 | String matching |
| ├─ Experience Engine | 2-5 | Numeric + simple text checks |
| ├─ Education Engine | 1-3 | String matching |
| └─ Trust Engine | 1-3 | Simple lookups |
| **Total Feature Extraction** | **32-67** | Sequential — sum of all engines |
| **Score Computation** | 1-2 | numpy-accelerated |
| **Ranking** (sort 100K) | 0.5-1 | O(n log n), numpy sort |
| **Reasoning Generation** | 5-10 | String formatting for 100 rows |
| **Output Writing** | 0.5-1 | CSV write |
| **Total Pipeline** | **~45-95 seconds** | Well under 5-minute (300s) limit |

### 5.2 Bottlenecks

| Bottleneck | Module | Cause | Impact |
|------------|--------|-------|--------|
| 🔴 **Primary** | Career Intelligence | Scanning career description text (50-200 words × 2-5 entries × 100K candidates = 10M-100M words) | ~40% of total runtime |
| 🟡 **Secondary** | Semantic Engine | Headline/summary keyword matching | ~15% of total runtime |
| 🟡 **Secondary** | Reasoning Generator | 100 unique string constructions | ~10% of total runtime |
| 🔵 **Tertiary** | Honeypot Detector | Skills array scanning for 100K | ~8% of total runtime |

### 5.3 Optimization Opportunities

| Optimization | Module | Expected Gain | Complexity |
|-------------|--------|--------------|------------|
| Pre-compile all regex patterns | Career Intelligence, Semantic | 2-3× faster text scanning | Low |
| Use `numpy` for all score arrays | Scoring | ~10× faster | Low |
| Early-exit on empty description fields | Career Intelligence | Skip 30-50% of text scanning | Low |
| Use `functools.lru_cache` for repeated lookups | Location, Education | Small gain | Low |
| Vectorize title classification with dict lookup | Semantic | O(1) per title | Low |
| Batch feature computation with numpy | All features | Similar to current sequential approach | Medium |
| Parallelize feature engines with `concurrent.futures` | All features | ~2× speedup on multi-core | Medium |
| **Skip early-filter candidates** | Before ranking | **See below** | Medium |

**Early-filter strategy** (optional, Phase 8):

If runtime approaches the 5-minute limit, a pre-filter can reduce 100K → ~10K candidates before full feature extraction:

1. Compute lightweight "surface score" from title (5 features: title, headline, years_exp, country, open_to_work)
2. Keep top 10% (~10K candidates)
3. Run full 35-feature extraction only on the reduced set
4. Final ranking on 10K candidates

**Risk**: May discard good candidates with poor surface scores but strong deep signals (e.g., non-ML title candidate with extensive career ML experience). Only implement if runtime validation shows need.

### 5.4 Runtime Margins

| Constraint | Budget | Estimated | Margin |
|-----------|--------|-----------|--------|
| 5-minute (300s) limit | 300s | 45-95s | **68-85% margin** |
| Worst-case scenario | 300s | 120s | **60% margin** |
| With optimizations | 300s | 30-60s | **80-90% margin** |

✅ **Comfortable margin. Early-filter is unlikely to be needed.**

---

## 6. RAM Estimate

### 6.1 Peak RAM Usage

| Component | RAM (MB) | When Held | Duration |
|-----------|----------|-----------|----------|
| Python interpreter overhead | ~30 | Entire run | Permanent |
| Reference data (taxonomies, DBs) | ~50 | After init | Permanent |
| Config + constants | ~1 | Entire run | Permanent |
| Per-candidate processing (peak) | ~2 | Each candidate | Released per iteration |
| Score array (100K floats) | ~3.2 | During ranking | ~1 second |
| Candidate ID mapping | ~6 | During ranking | ~1 second |
| Top-100 feature cache | ~0.5 | After ranking | ~5 seconds |
| Output buffer | ~0.02 | Write stage | ~1 second |
| **Total Peak RAM** | **~90-95 MB** | | |

### 6.2 Per-Module RAM Usage

| Module | RAM (MB) | Allocation Type | Notes |
|--------|----------|----------------|-------|
| Data Loader | ~1 | Stack (line buffer) | 8 KB per line |
| Candidate Parser | ~2 | Heap (per candidate) | Freed per iteration |
| Semantic Engine | ~50 | Heap (taxonomies) | Retained throughout pipeline |
| Career Intelligence Engine | ~20 | Heap (company DB) | Retained throughout pipeline |
| Behavioral Engine | ~1 | Stack (temporary) | No retained structures |
| Availability Engine | ~0.5 | Stack (temporary) | No retained structures |
| Honeypot Detector | ~2 | Heap (skill taxonomy) | Shared with semantic |
| Location Engine | ~0.5 | Stack (temporary) | No retained structures |
| Experience Engine | ~0.5 | Stack (temporary) | No retained structures |
| Education Engine | ~0.5 | Stack (temporary) | No retained structures |
| Trust Engine | ~0.5 | Stack (temporary) | No retained structures |
| **Feature Total** | **~78** | | Shared taxonomy overlap ~5 MB |
| Scoring Components | ~0.5 | Stack (temporary) | No retained structures |
| Final Ranker | ~10 | Heap (score array) | ~3 seconds duration |
| Reasoning Generator | ~0.5 | Heap (100 strings) | ~5 seconds duration |
| Output Writer | ~0.1 | Stack (buffer) | Minimal |

### 6.3 Memory Profile Over Time

```
RAM (MB)
 110 │
 100 │
  90 │                          ┌───────────────┐
  80 │  ┌──────────────────┐    │   Ranking     │
  70 │  │  Init + Loading   │    │  (peak ~95MB) │
  60 │  │  (steady ~80MB)   │    │               │
  50 │  │                   │    └───────────────┘
  40 │  │  Taxonomies + DB  │    ┌───────────────┐
  30 │  │  (loaded once)    │    │  Post-rank    │
  20 │  │                   │    │  (steady ~80MB)│
  10 │  └───────────────────┘    └───────────────┘
   0 └──────────────────────────────────────────────► Time
     Init   Load   Parse+Extract   Rank   Reason   Output
     (2s)   (5s)   (40-70s)        (1s)   (8s)     (1s)
```

### 6.4 Expected Operation on Target Machines

#### 8 GB Development Laptop

| Metric | Value | Assessment |
|--------|-------|------------|
| Available RAM | ~6 GB (after OS + apps) | ✅ Plenty |
| Peak usage | ~95 MB | **0.1% of available** |
| Typical usage | ~80 MB | Negligible |
| Swap risk | None | ✅ |
| **Conclusion** | ✅ **Comfortable** | No memory concerns at all |

#### 16 GB Competition Machine

| Metric | Value | Assessment |
|--------|-------|------------|
| Available RAM | ~15 GB (after OS) | ✅ Abundant |
| Peak usage | ~95 MB | **0.6% of available** |
| Typical usage | ~80 MB | Negligible |
| Scaling headroom | ~15 GB | Could handle 15M+ candidates |
| **Conclusion** | ✅ **Well within limit** | 16 GB limit is not a constraint |

#### Multi-Candidate Scenario (worst case, no streaming)

If the pipeline were modified to hold all candidates in memory simultaneously:

| Candidates | Memory | Assessment |
|-----------|--------|------------|
| 100K | ~700 MB (raw JSON) + ~80 MB (features) | Would still fit in 8 GB ✅ |
| 500K | ~3.5 GB + ~400 MB | Would still fit in 8 GB ✅ |
| 1M | ~7 GB + ~800 MB | Tight on 8 GB, fine on 16 GB ✅ |

**Conclusion:** Even in the worst case (no streaming), the system fits comfortably in 8 GB RAM. The streaming design is primarily for efficiency, not necessity.

---

## 7. Competition Constraints

### 7.1 Constraint Mapping

| Constraint | Requirement | Architecture Compliance |
|-----------|-------------|------------------------|
| **CPU only** | No GPU allowed | ✅ All modules use pure Python + numpy. No GPU dependencies. No CUDA. |
| **No network access** | Must work offline during ranking | ✅ All reference data (company DB, taxonomies) are local static files loaded at initialization. No API calls. |
| **≤16 GB RAM** | Must not exceed 16 GB | ✅ Peak RAM ~95 MB (0.6% of 16 GB limit). Streaming design ensures minimal footprint. |
| **8 GB laptop compatible** | Must run on development machines | ✅ 95 MB peak on 6 GB available = negligible. No swap needed. |
| **100K candidates** | Must process full dataset | ✅ Streaming pipeline handles any number of candidates. No upper limit on scalability. |
| **5-minute runtime** | Must complete ≤300 seconds | ✅ Estimated 45-95 seconds. Worst-case ~120 seconds with 60% margin. |
| **No LLM per candidate** | No 100K API calls | ✅ No LLM calls at all. Rule-based feature extraction. |
| **Deterministic output** | Same input → same ranking | ✅ No randomness. Tie-breaking is fully deterministic. |
| **Submission format** | Exactly 100 rows, non-increasing scores | ✅ Validated at output stage. Format checker enforces all rules. |
| **Honeypot avoidance** | Honeypot rate <10% in top 100, 0 in top 10 | ✅ Honeypot Detector applies penalties. Spec says natural avoidance is the strategy. |

### 7.2 What the Architecture Does NOT Support

| Feature | Why Not | Mitigation |
|---------|---------|------------|
| **GPU acceleration** | Spec prohibits GPU | CPU optimization is sufficient (95s vs 300s limit) |
| **Real-time ranking** | Not required by challenge | Pipeline runs once, produces submission.csv |
| **Interactive UI** | Not required by challenge | CLI-based: `python -m ranker --candidates ... --out ...` |
| **Embedding models** | Not needed + CPU constraint | Rule-based + keyword scoring is sufficient per analysis |
| **External databases** | Network access prohibited | All data is local JSON files |
| **Hot-reload config** | Not needed | Config loaded once at init |

### 7.3 Scalability Beyond 100K

The architecture can scale far beyond the required 100K:

| Scale | Expected Runtime | RAM | Limiting Factor |
|-------|-----------------|-----|-----------------|
| 100K | ~60-100s | ~95 MB | Career text analysis |
| 1M | ~10-15 min | ~150 MB | Career text analysis (I/O + CPU) |
| 10M | ~2-3 hours | ~500 MB | I/O (10M JSON lines = ~60 GB file read) |

At 10M+ scale, the bottleneck shifts from CPU to I/O. Parallel file chunking would be needed.

---

## 8. Error Handling Strategy

### 8.1 Error Severity Levels

| Level | Behavior | Examples |
|-------|----------|---------|
| **Fatal** | Abort pipeline immediately | File not found, config missing, no valid candidates |
| **Error** | Skip candidate, log, continue | Missing required fields, invalid JSON line |
| **Warning** | Default value used, log, continue | Missing optional field, out-of-range value |
| **Info** | Log only, continue normally | Empty skills array, inverted salary |

### 8.2 Error Counts and Their Impact

| Error Count (out of 100K) | Impact on Ranking | Acceptable? |
|---------------------------|-------------------|-------------|
| 0-100 (0.1%) | Negligible | ✅ Perfect |
| 100-1,000 (1%) | Minor | ✅ Acceptable |
| 1,000-5,000 (5%) | Moderate — may miss some strong candidates | ⚠️ Investigate |
| 5,000+ (5%+) | Significant — ranking quality degrades | 🔴 Investigate urgently |

### 8.3 Recovery Mechanisms

| Scenario | Recovery |
|----------|----------|
| One malformed JSON line | Skip, log line number, continue. Loss of 1 candidate out of 100K. |
| Missing candidate_id | Skip candidate. Cannot rank without ID. |
| Empty career_history | Process candidate with 0 career scores. Profile-only scoring applies. |
| Negative duration_months | Clamp to 0. Log as data anomaly. |
| Null date fields | Leave as None. Compute what we can. |

---

## 9. Design Decisions

### 9.1 Sequential vs. Parallel Feature Extraction

**Decision: Sequential** (feature engines run one after another per candidate)

**Rationale:**
- Simpler implementation and debugging
- No thread-safety concerns with shared reference data
- Per-candidate sequential is fast enough (~40-70s for all 9 engines over 100K)
- True parallelism would require batching, which increases memory and complexity
- Python GIL limits CPU-bound parallel gains with threads; multiprocessing adds overhead

**If optimization needed (Phase 8):** Can convert to batch numpy operations for numeric features.

### 9.2 Feature Extraction Depth

**Decision: Rule-based with keyword matching, NOT embedding models**

**Rationale:**
- CPU-only constraint eliminates GPU-reliant embedding models
- Lightweight sentence-transformers (~all-MiniLM-L6-v2) could fit CPU but adds ~2-3 minutes to runtime
- Rule-based feature extraction is fast (~40-70s), interpretable, and deterministic
- JD analysis confirms that keyword + career-history analysis is sufficient
- Embedding approach described as viable alternative in ANALYSIS_REPORT.md

### 9.3 Top 100 Selection Strategy

**Decision: Full sort of all 100K candidates**

**Rationale:**
- Sorting 100K floats is O(n log n) ≈ 1.7M comparisons — ~0.5s with numpy
- No need for a priority queue or heap-based partial sort
- Full sort gives the correct global ranking, which matters for NDCG@50 and MAP metrics
- Memory for 100K score array is ~3.2 MB — negligible

### 9.4 Reference Data Management

**Decision: Static JSON files loaded at initialization**

**Rationale:**
- Network access is prohibited during ranking
- Company DB and taxonomies are small (~5-10 MB total)
- JSON is human-readable and easily editable
- No database setup needed (pure Python)

### 9.5 Reasoning Generation Approach

**Decision: Template-based string formatting with candidate-specific values**

**Rationale:**
- No LLM calls (network prohibited, too slow)
- Template ensures consistent format across all 100 rows
- Candidate-specific values (scores, stats) ensure uniqueness
- Sample submission analysis confirms pattern: `[Role summary] + [Key stat] + [Notable signal]`

### 9.6 Module Interface Design

**Decision: Dict-based interface between modules (not method calls on shared objects)**

```python
# Example interface pattern
class SemanticEngine:
    def extract(self, candidate: Candidate) -> dict[str, float]:
        """Return feature dict with keys like 'title_semantic_score'."""
        ...
```

**Rationale:**
- Loose coupling — modules can be developed and tested independently
- Simple data contract (dict in, dict out)
- Easy to add new features without changing interfaces
- Feature registry can dispatch dynamically by feature name

---

*End of Architecture Design. See `docs/PHASE_3_SUMMARY.md` for phase completion report.*
