# Phase 1 Audit — Evidence Verification Report

> **Date:** June 19, 2026
> **Status:** Audit Complete — Issues Found (see PHASE_1_FIXES.md)
> **Phase 1 Gate:** ⏳ Pending corrections

---

## Audit Methodology

Every major conclusion in `docs/ANALYSIS_REPORT.md` was traced back to its source in the competition files. Each claim is classified as:

- **Fact** — Directly stated in source documents or computed from dataset
- **Inference** — Logical conclusion from multiple pieces of evidence
- **Speculation** — Reasonable guess without direct evidence

Confidence levels:
- **High** — Direct evidence from source files
- **Medium** — Strong inference supported by multiple signals
- **Low** — Speculative or unsupported claim

---

## 1. JD Extraction Audit

### Evidence Source: `job_description.docx`

| Claim in Analysis Report | Source Verification | Exact Quote from JD | Confidence | Type |
|--------------------------|-------------------|-------------------|------------|------|
| "5–9 years experience is a range, not a cutoff" | ✅ Verified | *"This is a range, not a requirement. Some people hit 'senior engineer' judgment at 4 years; some never hit it after 15."* | High | Fact |
| "Production ML experience required" | ✅ Verified | *"Production experience with embeddings-based retrieval systems... deployed to real users."* | High | Fact |
| "LangChain-only 'AI experience' is disqualifying" | ✅ Verified | *"If your 'AI experience' consists primarily of recent (under 12 months) projects using LangChain to call OpenAI — we will probably not move forward"* | High | Fact |
| "Consulting-only career is disqualifying" | ✅ Verified | *"People who have only worked at consulting firms (TCS, Infosys, Wipro, Accenture, Cognizant, Capgemini, etc.) in their entire career."* | High | Fact |
| "Pure research background is disqualifying" | ✅ Verified | *"If you've spent your career in pure research environments... without any production deployment — we will not move forward."* | High | Fact |
| "CV/Speech/Robotics specialists without NLP/IR exposure" | ✅ Verified | *"People whose primary expertise is computer vision, speech, or robotics without significant NLP/IR exposure."* | High | Fact |
| "No production code in 18 months" | ✅ Verified | *"If you are a senior engineer who hasn't written production code in the last 18 months"* | High | Fact |
| "Closed-source hermits without external validation" | ✅ Verified | *"People whose work has been entirely on closed-source proprietary systems for 5+ years without external validation"* | High | Fact |
| "India location preference" | ✅ Verified | *"Candidates in Hyderabad, Pune, Mumbai, Delhi NCR welcome to apply. Outside India: case-by-case, but we don't sponsor work visas."* | High | Fact |
| "Sub-30 day notice preferred" | ✅ Verified | *"We'd love sub-30-day notice. We can buy out up to 30 days."* | High | Fact |
| "Ideal candidate: 6-8 years, 4-5 in applied ML" | ✅ Verified | *"6-8 years total experience, of which 4-5 are in applied ML/AI roles at product companies (not pure services)."* | High | Fact |
| "Shipped ranking/search/recommendation system" | ✅ Verified | *"Has shipped at least one end-to-end ranking, search, or recommendation system to real users at meaningful scale."* | High | Fact |
| "Evaluation framework knowledge needed" | ✅ Verified | *"Hands-on experience designing evaluation frameworks for ranking systems — NDCG, MRR, MAP, offline-to-online correlation, A/B test interpretation."* | High | Fact |
| "Behavioral signals should be weighed" | ✅ Verified | *"Your ranking system should also weigh behavioral signals"* | High | Fact |
| "Keyword matching is a trap" | ✅ Verified | *"The 'right answer' to this JD is not 'find candidates whose skills section contains the most AI keywords.' That's a trap we've explicitly built into the dataset."* | High | Fact |

---

## 2. Ground Truth Assumptions Audit

### Evidence Source: `submission_spec.docx` (Section 4)

| Claim in Analysis Report | Source Verification | Evidence | Confidence | Type |
|--------------------------|-------------------|---------|------------|------|
| "NDCG@10 = 50% weight" | ✅ Verified | *"Final composite = 0.50 × NDCG@10 + 0.30 × NDCG@50 + 0.15 × MAP + 0.05 × P@10"* | High | Fact |
| "NDCG@50 = 30% weight" | ✅ Verified | Same quote | High | Fact |
| "MAP = 15% weight" | ✅ Verified | Same quote | High | Fact |
| "P@10 = 5% weight" | ✅ Verified | Same quote | High | Fact |
| "No live leaderboard" | ✅ Verified | *"The leaderboard is hidden during the competition."* | High | Fact |
| "Hidden ground truth exists" | ✅ Verified | *"Your top-100 ranking is scored against the hidden ground truth"* | High | Fact |
| "Ground truth has relevance tiers" | ✅ Verified | *"These are forced to relevance tier 0 in the ground truth"* — implies tier 0 exists, thus multiple tiers | High | Fact |
| "Ground truth was created by expert labeling" | ❌ Unsupported | No document describes ground truth creation methodology | Low | Speculation |
| "Relevance Tier 5 count = ~10-15" | ❌ Unsupported | No population count provided in any document | Low | Speculation |
| "Relevance Tier 4 count = ~15-30" | ❌ Unsupported | Same as above | Low | Speculation |
| "Optimizing NDCG@10 is the primary objective" | ✅ Inference | 50% weight supports this, but not explicitly stated as primary objective | Medium | Inference |
| "Ground truth penalizes non-technical titles ranking high" | ✅ Inference | JD explicitly says marketing managers with AI keywords are not a fit, so ground truth likely penalizes this | Medium | Inference |
| "Ground truth rewards shipped ranking systems" | ✅ Inference | JD ideal profile describes this, ground truth likely matches JD | Medium | Inference |

---

## 3. Honeypot Evidence Audit

### Evidence Source: `submission_spec.docx` (Section 7)

| Claim in Analysis Report | Source Verification | Exact Quote | Confidence | Type |
|--------------------------|-------------------|-------------|------------|------|
| "~80 honeypot candidates exist" | ✅ Verified | *"a small number (~80) of honeypot candidates"* | High | Fact |
| "Honeypots have impossible profiles" | ✅ Verified | *"subtly impossible profiles"* | High | Fact |
| "Example: 8 years experience at company founded 3 years ago" | ✅ Verified | *"e.g., 8 years of experience at a company founded 3 years ago"* | High | Fact |
| "Example: expert in 10 skills with 0 years used" | ✅ Verified | *"'expert' proficiency in 10 skills with 0 years used"* | High | Fact |
| "Honeypots are forced to relevance tier 0" | ✅ Verified | *"These are forced to relevance tier 0 in the ground truth."* | High | Fact |
| "Honeypots in top 10 = disqualification signal" | ✅ Verified | *"If your submission ranks honeypots in the top 10, this is a strong signal that your system isn't reading profiles"* | High | Fact |
| "Honeypot rate > 10% in top 100 = DQ" | ✅ Verified | *"submissions with honeypot rate > 10% in top 100 are disqualified"* | High | Fact |
| "Salary inverted (min > max) is a confirmed honeypot pattern" | ⚠️ **INCORRECT** | Salary inversion is NOT in the spec's honeypot examples. The spec only gives the two examples above. | **Low** | **Speculation presented as fact** |
| "Title-skill contradiction is a confirmed honeypot pattern" | ⚠️ **INCORRECT** | The JD says this isn't a fit for the role, but the spec's honeypots are about **impossible profiles**, not poor fit. | **Low** | **Speculation presented as fact** |
| "Summary-skill contradiction is a confirmed honeypot pattern" | ⚠️ **INCORRECT** | Same reasoning as above. Not mentioned in spec's honeypot section. | **Low** | **Speculation presented as fact** |
| "Experience > company existence is confirmed" | ✅ Verified (in spec) but ⚠️ **undetectable from data** | The spec gives this example, but we have no company founding dates in the dataset to detect it. | Medium | Fact (stated) / Low (detectable) |
| "Don't special-case honeypots" | ✅ Verified | *"You can identify honeypots through careful profile inspection. We expect a good ranking system to naturally avoid them; you don't need to special-case them."* | High | Fact |

### ⚠️ Critical Finding: Honeypot Confusion in Analysis Report

The ANALYSIS_REPORT.md section "Confirmed patterns (matching spec: ~80 honeypots)" lists 5 patterns, but **only 2 are actually from the spec**. The other 3 (salary inverted, title-skill contradiction, summary-skill contradiction) are **not** confirmed honeypot patterns — they are inferred.

The spec's honeypot definition is **profiles with impossible data**, not profiles with improbable skill combinations. Salary inversion (18,865 occurrences) is clearly a data integrity issue affecting ~19% of the dataset, not a deliberate honeypot.

**This is the most significant error in the analysis** — conflating "impossible data" (honeypots, ~80) with "improbable patterns" (data anomalies, ~29K).

---

## 4. Behavioral Signal Analysis Audit

### Evidence Source: `redrob_signals_doc.docx` (text + table)

| Claim in Analysis Report | Source Verification | Evidence | Confidence | Type |
|--------------------------|-------------------|---------|------------|------|
| "23 behavioral signals exist" | ✅ Verified | Table lists 23 signals | High | Fact |
| Signal #1: profile_completeness_score | ✅ Verified | Table row 1 | High | Fact |
| Signal #7: recruiter_response_rate | ✅ Verified | Table row 7 | High | Fact |
| Signal #3: last_active_date | ✅ Verified | Table row 3 | High | Fact |
| Signal #4: open_to_work_flag | ✅ Verified | Table row 4 | High | Fact |
| Signal #9: skill_assessment_scores | ✅ Verified | Table row 9 | High | Fact |
| All other 18 signals (table rows) | ✅ Verified | Table rows 2-23 | High | Fact |
| "Signals document says they should be used as multiplier/modifier" | ✅ Verified | *"incorporate them as a multiplier or modifier on top of skill-match scoring"* | High | Fact |
| "Signals are often more predictive than static profile" | ✅ Verified | *"These behavioral signals are often more predictive of whether a candidate can actually be hired than their static profile."* | High | Fact |
| "Exact formula: 0.80×rate + 0.10×recency + 0.10×flag" | ❌ Unsupported | No formula provided in any document | Low | Speculation |
| "Modifier range of 0.5-1.5x" | ❌ Unsupported | JD says "down-weight them appropriately" — no range specified | Low | Speculation |
| Signal importance ranking (1-23) | ❌ Unsupported | No importance ranking exists in documents. The ranking is our inference. | Low | Speculation |

---

## 5. Scoring Strategy Audit

### Evidence Source: None — this is our proposed strategy

| Claim in Analysis Report | Source Verification | Evidence | Confidence | Type |
|--------------------------|-------------------|---------|------------|------|
| "Title relevance = 25% weight" | ❌ Unsupported | No weight document exists. Our design choice. | Low | Speculation |
| "Skill relevance = 20% weight" | ❌ Unsupported | Same | Low | Speculation |
| "Career relevance = 20% weight" | ❌ Unsupported | Same | Low | Speculation |
| "Behavioral modifier = 20% weight" | ❌ Unsupported | Same | Low | Speculation |
| "Education relevance = 5% weight" | ❌ Unsupported | Same | Low | Speculation |
| "Internal consistency = 10% weight" | ❌ Unsupported | Same | Low | Speculation |
| "Score = Base_Match_Score × Behavioral_Modifier × Consistency_Penalty" | ❌ Unsupported | Design choice, not in source | Low | Speculation |

**Note:** All scoring weights are currently speculative. They are **reasonable design choices** informed by the analysis, but they have no direct evidence in the source files. This is acceptable for Phase 1 (analysis only), but must be clarified as design proposals, not facts.

---

## 6. Dataset Statistics Audit

### Evidence Source: Computed from `candidates.jsonl`

| Claim in Analysis Report | Source Verification | Computed Value | Confidence | Type |
|--------------------------|-------------------|----------------|------------|------|
| "Total candidates: 100,000" | ✅ Verified | 100,000 lines | High | Fact |
| "Unique job titles: ~25" | ❌ **WRONG** | **47 unique titles** (not ~25) | **Low** | **Factual Error** |
| "Tech titles: 42,542" | ✅ Verified | 42,542 | High | Fact |
| "AI/ML titles: 1,126" | ✅ Verified | 1,126 | High | Fact |
| "India-based: 75,113" | ✅ Verified | 75,113 | High | Fact |
| "Open to work: 35,339" | ✅ Verified | 35,339 | High | Fact |
| "Has GitHub linked: 35,363" | ✅ Verified | 35,363 (github_activity_score >= 0) | High | Fact |
| "Consulting-only career: 7,034" | ✅ Verified | 7,034 | High | Fact |
| "Salary inverted: 18,865" | ✅ Verified | 18,865 | High | Fact |
| "5+ expert skills: 167" | ✅ Verified | 167 | High | Fact |
| "Estimated honeypots: ~80" | ✅ Verified | Per spec: *"a small number (~80)"* | High | Fact |
| "Senior AI Engineer count: 4" | ✅ Verified | 4 candidates | High | Fact |

### ⚠️ Appendix Error
The ANALYSIS_REPORT.md appendix states: *"Unique job titles: ~25 (Business Analyst, HR Manager, Mechanical Engineer, etc.)"*

**Actual count: 47 unique titles.** The "~25" came from the sample data (22 titles in sample). This is a factual error — the report should say 47, not ~25.

---

## 7. Phase Scope Audit

| Claim | Verification | Result |
|-------|-------------|--------|
| "No ranking code written" | ✅ Verified via file inspection | PASS |
| "No architecture documents created" | ✅ FEATURE_CATALOG.md and ARCHITECTURE.md do not exist | PASS |
| "Only Phase 1 deliverables created" | ✅ All files are Phase 1 scope | PASS |
| "README.md phase table says future phases are 'Pending'" | ✅ Verified | PASS |
| "No code in repository beyond docs and config" | ✅ Only config (.gitignore, requirements.txt) and docs exist | PASS |

---

## 8. Missing Insights Audit

### Insights MISSING from ANALYSIS_REPORT.md

| Missing Insight | Importance | Why Missed |
|----------------|------------|------------|
| **Extra consulting firms beyond JD's list** | Medium | JD says "TCS, Infosys, Wipro, Accenture, Cognizant, Capgemini, etc." — data also contains Mindtree, Tech Mahindra, HCL, Mphasis as consulting firms. These should be included in the consulting detection logic. |
| **Only 24.5% of first 1000 candidates have skill_assessment_scores** | Medium | The assessment scores are sparse. Most candidates have empty `{}` assessments. Should not be relied upon as a universal signal. |
| **Sample submission reasoning is surprisingly specific** | Medium | The sample_submission.csv has 100 unique reasoning strings, each mentioning specific details. This sets a high bar for Stage 4 review. |
| **47 unique titles, heavily skewed distribution** | Low | Top 12 non-tech titles (Business Analyst through Marketing Manager) each have ~5,700+ candidates. Tech titles are fewer and more diverse. |
| **The JD's "etc." in consulting list is meaningful** | Medium | The presence of Mindtree, HCL, Tech Mahindra, Mphasis indicates the "etc." is deliberately broad. |
| **Career description analysis is under-developed** | High | The JD's *"if their career history shows they built a recommendation system at a product company, they're a fit"* implies career description text analysis is essential, yet the report only allocates 20% to "Career_Relevance" without detailing how career text would be analyzed. |
| **No analysis of sample_submission.csv reasoning quality** | Medium | The sample has detailed reasoning. We should analyze what "good" reasoning looks like. |

---

## 9. Strategy Comparison Audit

### Evidence Source: Inference from spec constraints + JD

| Strategy | Verdict | Evidence from Files |
|----------|---------|-------------------|
| Keyword matching | Would fail (honeypot trap) | JD: *"That's a trap we've explicitly built into the dataset."* |
| Embedding-only | Would fail (no behavioral signals) | JD: *"weigh behavioral signals"* — embedding-only can't do this |
| LLM-per-candidate | Would fail (compute constraint) | Spec: *"100,000 candidates will not fit the 5-minute CPU budget"* |
| Hybrid feature-based | Recommended | Spec: *"Plan for a small ranker over precomputed features"* |

---

## 10. Confidence Re-Scoring

| Dimension | Previous Score | Audited Score | Reason |
|-----------|---------------|---------------|--------|
| Winning probability | Not stated | ~40-50% | Strong strategy but weights untested; competition from other teams unknown |
| Technical risk | Not stated | Medium | Feature-based scoring is low-risk; embedding integration is medium-risk |
| Reproducibility risk | Not stated | Low | Feature-based scoring trivially fits 5-min CPU constraint |
| Honeypot risk | Not stated | **Medium-High** | Honeypot confusion in analysis could lead to incorrect detection strategy. Must fix before Phase 2. |

---

## Summary of Issues Found

| Severity | Count | Description |
|----------|-------|-------------|
| 🔴 Critical | 0 | — |
| 🟠 High | 1 | Honeypot patterns section conflates "impossible data" (spec's definition) with "improbable patterns" (our inference) |
| 🟡 Medium | 3 | Unique titles counted as ~25 instead of 47; missing consulting firms; under-developed career description analysis |
| 🔵 Low | 3 | Scoring weights presented without disclaimers; behavioral modifier formula over-specific; missing sample_submission.csv analysis |

---

*End of Audit. See docs/PHASE_1_FIXES.md for recommended corrections.*
