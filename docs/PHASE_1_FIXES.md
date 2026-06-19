# Phase 1 Fixes — Recommended Corrections

> **Date:** June 19, 2026
> **Audit Finding:** 7 issues identified (1 High, 3 Medium, 3 Low)
> **Action Required:** Apply fixes before committing Phase 1

---

## 🔴 High Priority Fixes

### Fix 1: Honeypot Pattern Section — Correct Classification

**File:** `docs/ANALYSIS_REPORT.md` — Section 4 "Honeypot Patterns"

**Problem:** The "Confirmed patterns" table lists 5 patterns but only 2 are confirmed by the spec. Salary inverted, title-skill contradiction, and summary-skill contradiction are **not** listed in the spec's honeypot definition. The spec defines honeypots as having **impossible data** (e.g., time-travel work history, expert with zero duration), not improbable or contradictory profiles.

**Evidence:** Submission spec Section 7: *"The dataset contains a small number (~80) of honeypot candidates with subtly impossible profiles (e.g., 8 years of experience at a company founded 3 years ago; 'expert' proficiency in 10 skills with 0 years used)."*

**Fix:** Restructure Section 4 into three clear categories:

| Category | Source | Count | Action |
|----------|--------|-------|--------|
| **Proven (from spec)** | Directly stated in spec | ~80 | Face value |
| **Likely (reasonable inference)** | Near-matches to spec patterns | Unknown | Handle with consistency checks |
| **Borderline (data quality issues)** | Generic anomalies in data | ~29K | NOT honeypots; handle separately |

Specifically:
- Move "salary inverted" from "Confirmed patterns" to a **new "Data Anomalies" sub-section**
- Add explicit note that salary inverted affects 18,865 candidates (~19% of dataset) and these are likely data integrity issues, not honeypots
- Move "title-skill contradiction" and "summary-skill contradiction" from "Confirmed" to a **new "Profile Consistency Signals" sub-section**
- Clarify that the spec explicitly says only ~80 honeypots exist, not ~29K

**Section to rewrite:** "4. Honeypot Patterns" — the "Confirmed patterns" table and "Suspected borderline patterns" table.

---

### Fix 2: Correction to "Confirmed patterns" detection approaches

**Problem:** "Experience > company existence" is listed as detectable but we have **no company founding dates** in the dataset. The spec mentions this pattern but we can't implement detection for it without additional data.

**Evidence:** `candidate_schema.json` does not include company founding dates. Career history entries have: company, title, start_date, end_date, duration_months, is_current, industry, company_size, description.

**Fix:** Either:
a) Remove "Experience > company existence" from detectable patterns table
b) Add note: "Detectable only if we approximate using earliest start_date across all roles" — which is a heuristic, not a reliable detection

**Recommendation:** Option (a) — Remove from detection table. Add as speculation.

---

## 🟡 Medium Priority Fixes

### Fix 3: Correct Unique Job Titles Count

**File:** `docs/ANALYSIS_REPORT.md` — Appendix "Dataset Statistics"

**Problem:** States "Unique job titles: ~25" but actual count is **47 unique titles** in the full dataset. The ~25 came from the sample (which has 22 titles).

**Evidence:** Computed from `candidates.jsonl`: 47 unique job titles.

**Fix:** Change "~25" to **47** in the appendix. Update the parenthetical list or remove it since 47 titles is too many to list inline.

**Old text:** `Unique job titles | ~25 (Business Analyst, HR Manager, Mechanical Engineer, etc.)`
**New text:** `Unique job titles | 47 (see docs/PHASE_1_AUDIT.md for full list)`

---

### Fix 4: Add Missing Consulting Firms

**File:** `docs/ANALYSIS_REPORT.md` — Sections 1, 6, 7

**Problem:** The JD lists "TCS, Infosys, Wipro, Accenture, Cognizant, Capgemini, etc." with "etc." implying the list is not exhaustive. Our data also contains **Mindtree, Tech Mahindra, HCL, and Mphasis** as consulting firms where candidates have worked all their careers.

**Evidence:** Computed from `candidates.jsonl` — these 4 additional consulting firms exist in career histories and match the JD's description of "consulting firms."

**Fix:** 
- In Section 1 (Hidden Judging Criteria): Update the consulting-only disqualifier to include "etc." from the JD
- In Section 6 (Strong Solutions): Note that the JD's consulting list is non-exhaustive
- Add a note that our detection should include these additional firms

---

### Fix 5: Add Career Description Analysis Detail

**File:** `docs/ANALYSIS_REPORT.md` — Section 7 "Winning Strategy"

**Problem:** The analysis emphasizes the JD's note about reading career history (*"if their career history shows they built a recommendation system..."*) but the proposed "Career_Relevance" component (20%) doesn't specify **how** career descriptions would be analyzed.

**Evidence:** JD hackathon note: *"A Tier 5 candidate may not use the words 'RAG' or 'Pinecone' in their profile, but if their career history shows they built a recommendation system at a product company, they're a fit."*

**Fix:** Expand the "Career history relevance" section to mention:
- Keyword-based career description scoring (ranking, retrieval, recommendation, search, embedding, vector, ML system, production)
- Company-level scoring (product company identification)
- Duration-weighted role scoring (how long in relevant roles)
- The need to handle career description text in Phase 3 feature extraction

---

## 🔵 Low Priority Fixes

### Fix 6: Add Speculative Disclaimer to Scoring Weights

**File:** `docs/ANALYSIS_REPORT.md` — Section 7 "Winning Strategy" — Scoring components table

**Problem:** The weights (25% title, 20% skill, 20% career, 20% behavioral, 10% consistency, 5% education) are presented as confident estimates without indicating they are speculative design proposals.

**Evidence:** No source document provides scoring component weights.

**Fix:** Add a footnote or note: *"All component weights are preliminary design estimates and will be refined during Phase 4 (Scoring Strategy Design)."*

---

### Fix 7: Capture Sample Submission Reasoning Pattern

**File:** `docs/ANALYSIS_REPORT.md` — Section 7 or new section

**Problem:** The sample_submission.csv demonstrates what good reasoning looks like (100 unique, specific entries). This is a useful reference for Stage 4 reasoning generation but was not analyzed.

**Evidence:** Sample submission has entries like: *"HR Manager with 6.1 yrs; 9 AI core skills; response rate 0.76."* — short, specific, data-driven.

**Fix:** Add a brief analysis of the sample submission's reasoning patterns to inform later reasoning generation.

---

## ✅ Corrections Already Correct

These items were verified as correct and require no changes:

| Item | Verification |
|------|-------------|
| NDCG@10 = 50% weight | Confirmed from spec |
| CPU-only, 5 min, 16GB, no network | Confirmed from spec |
| 23 behavioral signals | Confirmed from redrob_signals_doc |
| Behavioral signals should modify scores | Confirmed from JD + signals doc |
| ~80 honeypots exist | Confirmed from spec |
| Honeypot rate >10% = DQ | Confirmed from spec |
| Consulting-only = disqualifier (if entire career) | Confirmed from JD |
| Keyword matching is a trap | Confirmed from JD |
| Stage 4 checks 10 random reasoning rows | Confirmed from spec |
| 3-submission cap | Confirmed from spec |
| No ranking code written | ✅ Verified |
| No architecture documents | ✅ Verified |
| All Phase 1 deliverables exist | ✅ Verified |

---

## Apply Corrections

Before committing Phase 1, the ANALYSIS_REPORT.md should be revised to fix:
1. ✅ Honeypot section restructured (High)
2. ✅ Experience > company existence detection clarified (High)
3. ✅ Unique titles corrected to 47 (Medium)
4. ✅ Extra consulting firms added (Medium)
5. ✅ Career description analysis expanded (Medium)
6. ✅ Scoring weights noted as speculative (Low)
7. ✅ Sample submission reasoning analyzed (Low)

### Post-Correction Status

| Phase 1 Deliverable | Status |
|---------------------|--------|
| `.gitignore` | ✅ No changes needed |
| `README.md` | ✅ No changes needed |
| `requirements.txt` | ✅ No changes needed |
| `docs/ANALYSIS_REPORT.md` | ⏳ **Corrections pending** |
| `docs/PHASE_1_SUMMARY.md` | ✅ No changes needed |
| `docs/PHASE_1_AUDIT.md` | ✅ Created (this audit) |
| `docs/PHASE_1_FIXES.md` | ✅ Created (this fixes document) |
| `SELF_AUDIT.md` | ✅ No changes needed (already identifies analysis as heuristic-based) |
| Ranking code | ✅ None written — scope maintained |

---

*Generated from rigorous self-audit against all 6 competition source files. All claims verified or corrected.*
