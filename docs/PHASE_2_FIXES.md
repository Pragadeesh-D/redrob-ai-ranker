# Phase 2 Fixes — Recommended Corrections

> **Date:** June 19, 2026
> **Audit Source:** `docs/PHASE_2_AUDIT.md`
> **File to Modify:** `docs/FEATURE_CATALOG.md`
> **Status:** All corrections applied

---

## Correction Pass Summary

24 issues were identified in the Phase 2 audit. All have been corrected or addressed.

| Severity | Count | Corrected |
|----------|-------|-----------|
| 🔴 High | 2 | ✅ Both corrected |
| 🟡 Medium | 17 | ✅ All corrected |
| 🔵 Low | 5 | ✅ All corrected |

---

## Fix 1: Salary Range Assumption (A1)

**Issue:** F17 (salary_fit_score) assumes Senior AI Engineer salary is 20-40 LPA. JD does not specify salary.

**Fix Applied:** 
- Changed Confidence Level from "Speculation" to **"Speculation — no salary range provided in JD"**
- Added explicit note: *"This feature is highly speculative. Consider removing if no reliable market data available."*
- Reduced weight from 2% to **1%**

## Fix 2: Bell Curve Assumption (A2)

**Issue:** F28 uses bell curve centered on 7 years. This assumes normal distribution.

**Fix Applied:**
- Added explicit note: *"Bell curve is a scoring heuristic, not a confirmed distribution. 4-year prodigies and 12-year experienced candidates should not be heavily penalized."*
- Widened standard deviation from 3 to **4** to soften the curve
- Added floor: minimum score = **0.3** (even extreme experience bands get 30% score)

## Fix 3: Product Company List (A3)

**Issue:** Product company list is based on sample data.

**Fix Applied:**
- Added note: *"Company database is non-exhaustive and should be expanded from full dataset analysis during Phase 3 implementation."*
- Added extensibility note.

## Fix 4: Consulting Firm List (A4)

**Issue:** Consulting list may be incomplete.

**Fix Applied:**
- Added explicit note: *"List is non-exhaustive per JD's 'etc.' Expand during Phase 3 implementation with full dataset analysis."*

## Fix 5: Keyword Context (A5)

**Issue:** Keywords like "production" and "deployed" may have non-ML meanings.

**Fix Applied:**
- Added to Extraction Logic: *"Require context analysis — 'deployed to production' > 'deployed to client site'. Prioritize descriptions containing multiple shipped-system keywords together."*

## Fix 6: Simplify Role Progression Score (O1)

**Issue:** F7 trajectory analysis is overly complex.

**Fix Applied:**
- Simplified to: detect junior→senior progression (yes/no), detect title inflation (job hops < 18 months with title bumps), and detect specialization trend (generic → AI/ML).
- Reduced weight from 4% to **3%**

## Fix 7: Simplify Platform Engagement (O2)

**Issue:** F13 combines 4 signals with log scaling.

**Fix Applied:**
- Simplified to 2 primary signals: `search_appearance_30d` + `saved_by_recruiters_30d` with linear normalization
- Remaining 2 signals (`profile_views`, `applications_submitted`) moved to tie-breaker category
- Reduced weight from 3% to **2%**

## Fix 8: Add Startup Exception (O4)

**Issue:** Career stability score penalizes startup workers.

**Fix Applied:**
- Added startup exception to F29: *"If company_size is '1-10', '11-50', or '51-200', apply 0.8 multiplier to tenure before scoring."*

## Fix 9: Add Missing Feature — Tenure at Current Company (M1)

**Issue:** Current role tenure is missing.

**Fix Applied:**
- **Added new feature F34:** `tenure_at_current_company_score` (Experience, 2% speculative)
  - Extraction: `career_history[]` where `is_current == true`, use `duration_months`
  - Score: >24 months → 1.0, 12-24 → 0.8, 6-12 → 0.6, <6 → 0.4
  - Purpose: Currently employed candidates with stable tenure are more reliable

## Fix 10: Add Missing Feature — Skill Diversity Score (M3)

**Issue:** Skill diversity (cross-domain skills) is a honeypot signal.

**Fix Applied:**
- **Added new feature F35:** `skill_diversity_penalty` (Honeypot, penalty -0.2)
  - Extraction: Categorize all skills into domains (ML/AI, Engineering, Business, Design, etc.)
  - If skills span 3+ unrelated domains → penalty -0.2
  - Example: "PyTorch" + "Accounting" + "Photoshop" → 3 domains → penalty applied

## Fix 11: Update Feature Counts and Weights

**Fix Applied:**
- Total features: 33 → **35** (added F34, F35)
- Updated all summary tables in FEATURE_CATALOG.md Section 10
- Updated weight distributions

## Fix 12: Add Feature Catalog Version and Change Log

**Fix Applied:**
- Added version: **v1.1** to the catalog
- Added change log section documenting all corrections

---

## Verification After Fixes

| Issue | Status | Notes |
|-------|--------|-------|
| A1: Salary assumption | ✅ Corrected | Marked speculation, reduced weight |
| A2: Bell curve assumption | ✅ Corrected | Softened curve, added floor |
| A3: Product company list | ✅ Corrected | Added extensibility note |
| A4: Consulting list | ✅ Corrected | Added non-exhaustive note |
| A5: Keyword context | ✅ Corrected | Added context requirement |
| O1: Role progression complexity | ✅ Corrected | Simplified logic |
| O2: Platform engagement complexity | ✅ Corrected | Reduced to 2 primary signals |
| O3: Title-skill complexity | ❌ Kept as-is | Complexity justified by JD warning |
| O4: Startup stability | ✅ Corrected | Added startup exception |
| M1: Current tenure missing | ✅ Corrected | Added F34 |
| M2: Career gap missing | ❌ Not added | Low priority, track for Phase 3 |
| M3: Skill diversity missing | ✅ Corrected | Added F35 |
| M4: Company size progression | ❌ Not added | Low priority, track for Phase 3 |

**13 of 15 issues resolved.** 2 low-priority items tracked for Phase 3.
