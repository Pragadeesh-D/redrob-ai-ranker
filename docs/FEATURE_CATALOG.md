# Feature Catalog — Phase 2 Design Blueprint

> **Phase** 2 — Feature Engineering Blueprint (Design Only)
> **Status:** ✅ Complete
> **No code generated.** No architecture designed. All weights are speculative.

---

## Table of Contents

1. [Semantic Features](#1-semantic-features)
2. [Career Intelligence Features](#2-career-intelligence-features)
3. [Behavioral Features](#3-behavioral-features)
4. [Availability Features](#4-availability-features)
5. [Trust Features](#5-trust-features)
6. [Honeypot Features](#6-honeypot-features)
7. [Location Features](#7-location-features)
8. [Experience Features](#8-experience-features)
9. [Education Features](#9-education-features)
10. [Full Scoring Proposal](#10-full-scoring-proposal)

---

## How to Read This Catalog

Each feature has 9 fields:

| Field | Description |
|-------|-------------|
| **Feature Name** | Unique identifier for the feature |
| **Category** | One of the 9 categories above |
| **Purpose** | What this feature measures and why |
| **Weight Suggestion** | Speculative contribution to final score |
| **Extraction Logic** | How to compute this feature from candidate data |
| **Why It Matters** | Connection to ranking quality and competition metrics |
| **False Positive Risks** | What could go wrong if this feature misfires |
| **Evidence Source** | Where the requirement comes from (JD, spec, dataset analysis) |
| **Confidence Level** | Fact / Inference / Speculation |

---

## 1. Semantic Features

Features that measure how well a candidate's profile text matches the target role.

### F1: Title Semantic Score

| Field | Value |
|-------|-------|
| **Feature Name** | `title_semantic_score` |
| **Category** | Semantic Features |
| **Purpose** | Score how closely a candidate's current title matches "Senior AI Engineer" and related AI/ML roles |
| **Weight Suggestion** | **12%** (Speculative — contributes to base match score) |
| **Extraction Logic** | Compute semantic similarity between candidate's `profile.current_title` and JD target title "Senior AI Engineer" using a lightweight keyword/synonym-based scoring system. AI/ML titles (ML Engineer, AI Engineer, Data Scientist, etc.) get high scores. Non-tech titles (Marketing Manager, Accountant) get low scores. Semi-tech titles (Software Engineer, Backend Engineer) get medium scores. |
| **Why It Matters** | Only 1,126 candidates (1.1%) have AI/ML titles. Title is the strongest surface-level signal. Getting the top 10 right requires identifying these candidates first. |
| **False Positive Risks** | A "Senior AI Engineer" title could be inflated; a "Backend Engineer" could have strong ML experience. Title alone is insufficient — must be combined with career evidence. |
| **Evidence Source** | JD: *"The high-level mandate: own the intelligence layer."* Dataset: Only 1.1% have AI/ML titles. |
| **Confidence Level** | **Inference** — Title importance is logically derived from JD, not explicitly weighted |

### F2: Headline Relevance Score

| Feature | Details |
|---------|---------|
| **Name** | `headline_relevance_score` |
| **Category** | Semantic Features |
| **Purpose** | Score how well the candidate's headline matches the JD's requirements |
| **Weight** | **3%** (Speculative) |
| **Extraction Logic** | Compare candidate's `profile.headline` against JD keywords: "embeddings", "retrieval", "ranking", "LLM", "fine-tuning", "AI", "ML", "machine learning", "deep learning", "NLP", "vector", "search". Count keyword matches weighted by rarity. Headlines containing multiple AI/ML keywords score higher. |
| **Why It Matters** | Headlines are the candidate's self-summary. A headline like "ML Engineer specializing in retrieval systems" is a strong positive signal. |
| **False Positive Risks** | Keyword-stuffed headlines are possible ("AI ML NLP Deep Learning Expert"). Must cross-reference with career history. |
| **Evidence Source** | JD's "skills inventory" lists embeddings, retrieval, ranking, LLMs as core requirements. |
| **Confidence Level** | **Inference** |

### F3: Summary Relevance Score

| Feature | Details |
|---------|---------|
| **Name** | `summary_relevance_score` |
| **Category** | Semantic Features |
| **Purpose** | Score how much the candidate's summary reflects genuine AI/ML experience vs. generic content |
| **Weight** | **5%** (Speculative) |
| **Extraction Logic** | Analyze `profile.summary` for: (1) mentions of production ML systems, (2) career stage indicators (years of experience, progression), (3) AI/ML keywords in context. Penalize summaries that are generic template text ("Professional with X+ years of experience..."). |
| **Why It Matters** | The JD's hackathon note says *"A Tier 5 candidate may not use the words 'RAG' or 'Pinecone' in their profile, but if their career history shows they built a recommendation system..."* — summaries provide context for career history. |
| **False Positive Risks** | Well-written summaries by non-ML candidates may score highly. Generic template summaries are common. |
| **Evidence Source** | JD hackathon note. Dataset analysis shows many generic summaries across non-tech candidates. |
| **Confidence Level** | **Inference** |

---

## 2. Career Intelligence Features

Features that analyze a candidate's work history — the most important signal group per the JD.

### F4: Shipped Systems Score

| Feature | Details |
|---------|---------|
| **Name** | `shipped_systems_score` |
| **Category** | Career Intelligence |
| **Purpose** | Detect evidence of production ML/AI systems shipped to real users — the single most important JD requirement |
| **Weight** | **15%** (Speculative — highest individual feature weight) |
| **Extraction Logic** | Parse all `career_history[].description` entries. Score based on keyword presence: "production", "deployed", "shipped", "ranking", "retrieval", "recommendation", "search", "embedding", "vector", "ML system", "ML pipeline", "inference", "A/B test", "evaluation". Bonus for mentioning specific technologies from JD: "sentence-transformers", "Pinecone", "Qdrant", "Milvus", "FAISS", "OpenSearch", "Elasticsearch". Weight by role duration (longer in ML roles = higher score). |
| **Why It Matters** | JD's #1 requirement: *"Production experience with embeddings-based retrieval systems... deployed to real users."* Also: *"Has shipped at least one end-to-end ranking, search, or recommendation system to real users at meaningful scale."* |
| **False Positive Risks** | Career descriptions may be exaggerated. A candidate mentioning "deployed ML models" could mean a single scikit-learn model in a notebook. Cross-reference with title and company to calibrate. |
| **Evidence Source** | **Fact (JD):** "Things you absolutely need" list + "ideal candidate" description. |
| **Confidence Level** | **Fact** — JD directly states this as a requirement |

### F5: Product Company Score

| Feature | Details |
|---------|---------|
| **Name** | `product_company_score` |
| **Category** | Career Intelligence |
| **Purpose** | Identify candidates who have worked at product/technology companies (vs. pure services/consulting) |
| **Weight** | **8%** (Speculative) |
| **Extraction Logic** | Score each `career_history[].company` against a known company database. Product companies (Ola, Zomato, Razorpay, Swiggy, Flipkart, Amazon, Google, Microsoft, Uber, etc.): +1.0 per role. Consulting firms (TCS, Infosys, Wipro, Accenture, Cognizant, Capgemini, Mindtree, HCL, Tech Mahindra, Mphasis): -0.5 per role. Other companies: 0.0. Normalize by total number of roles. If ALL roles are at consulting firms → strong penalty (consulting-only disqualifier). |
| **Why It Matters** | JD: *"People who have only worked at consulting firms... in their entire career"* — listed under "Things we explicitly do NOT want." The JD desires product-company ML experience. |
| **False Positive Risks** | Some product companies have consulting-like divisions. Some consulting firms have strong ML practices. The JD says *"If you're currently at one of these companies but have prior product-company experience, that's fine."* |
| **Evidence Source** | **Fact (JD):** Consulting-only career is explicitly listed as "not wanted." Dataset: 7,034 consulting-only candidates. |
| **Confidence Level** | **Fact** — JD explicitly lists consulting-only as unwanted |

### F6: AI/ML Role Duration Score

| Feature | Details |
|---------|---------|
| **Name** | `ai_ml_duration_score` |
| **Category** | Career Intelligence |
| **Purpose** | Measure how long the candidate has spent in AI/ML-related roles |
| **Weight** | **5%** (Speculative) |
| **Extraction Logic** | For each `career_history[]`, check if the title or description indicates AI/ML work. Sum `duration_months` for all AI/ML roles. Compute ratio: (months in AI/ML roles) / (total career months). Candidates with 4-5 years in AI/ML roles get the highest score per the JD's ideal profile. |
| **Why It Matters** | JD ideal candidate: *"6-8 years total experience, of which 4-5 are in applied ML/AI roles at product companies."* This directly separates genuine ML engineers from those with tangential experience. |
| **False Positive Risks** | Title inflation ("AI Engineer" with no real ML work). Misclassified roles. |
| **Evidence Source** | **Fact (JD):** "How to read between the lines" section. |
| **Confidence Level** | **Fact** — JD describes this as the ideal profile |

### F7: Role Progression Score

| Feature | Details |
|---------|---------|
| **Name** | `role_progression_score` |
| **Category** | Career Intelligence |
| **Purpose** | Measure career progression toward senior AI/ML roles |
| **Weight** | **3%** (Speculative) |
| **Extraction Logic** | Simplified analysis: (1) Detect junior→senior progression (yes/no: any role with 'Junior' or 'Senior' in title). (2) Detect title inflation (job hops < 18 months with 'Senior'→'Staff'→'Principal' title progression). (3) Detect specialization trend (generic engineer → AI/ML-specialized). Penalize clear title-chaser patterns. |
| **Why It Matters** | JD: *"Title-chasers. If your career trajectory shows you optimizing for 'Senior' → 'Staff' → 'Principal' titles by switching companies every 1.5 years, we're not a fit."* |
| **False Positive Risks** | Genuine fast-promotion candidates may be penalized by job-hopping heuristics. Non-traditional career paths (startup → big company → startup) may look erratic but are valid. |
| **Evidence Source** | **Fact (JD):** "Things we explicitly do NOT want." |
| **Confidence Level** | **Fact** — JD explicitly warns against title-chasers |

### F8: Consulting-Only Penalty

| Feature | Details |
|---------|---------|
| **Name** | `consulting_only_penalty` |
| **Category** | Career Intelligence |
| **Purpose** | Apply a penalty if a candidate's entire career has been at IT services/consulting firms |
| **Weight** | **Multiplicative penalty (×0.3)** — Not additive |
| **Extraction Logic** | Check if ALL `career_history[].company` values belong to the consulting set: TCS, Infosys, Wipro, Accenture, Cognizant, Capgemini, Mindtree, HCL, Tech Mahindra, Mphasis. If yes → apply ×0.3 penalty to base match score. If mixed (some consulting, some product) → apply milder penalty (×0.8). |
| **Why It Matters** | JD lists consulting-only candidates under "Things we explicitly do NOT want." 7,034 consulting-only candidates in dataset must be kept out of top 100. |
| **False Positive Risks** | Some consulting firms have strong internal ML teams. The JD allows exceptions: *"If you're currently at one of these companies but have prior product-company experience, that's fine."* Our logic handles this via the "mixed" path. |
| **Evidence Source** | **Fact (JD):** Consulting-only disqualifier. Dataset: 7,034 consulting-only candidates. |
| **Confidence Level** | **Fact** — Directly from JD |

### F9: Evaluation Experience Score

| Feature | Details |
|---------|---------|
| **Name** | `eval_experience_score` |
| **Category** | Career Intelligence |
| **Purpose** | Detect experience with evaluation frameworks for ranking/ML systems |
| **Weight** | **3%** (Speculative) |
| **Extraction Logic** | Search `career_history[].description` for keywords: "NDCG", "MRR", "MAP", "A/B test", "evaluation", "offline", "online", "metric", "benchmark", "regression". Score based on density of these terms. |
| **Why It Matters** | JD: *"Hands-on experience designing evaluation frameworks for ranking systems — NDCG, MRR, MAP, offline-to-online correlation, A/B test interpretation."* This separates serious ML engineers from hobbyists. |
| **False Positive Risks** | These keywords are uncommon in career descriptions — likely only a handful of matches. May not be a differentiator. |
| **Evidence Source** | **Fact (JD):** "Things you absolutely need." |
| **Confidence Level** | **Fact** — JD lists this as a requirement |

---

## 3. Behavioral Features

Features derived from the 23 Redrob behavioral signals.

### F10: Recruiter Response Rate Score

| Feature | Details |
|---------|---------|
| **Name** | `recruiter_response_rate_score` |
| **Category** | Behavioral Features |
| **Purpose** | Measure candidate's responsiveness to recruiters — direct proxy for availability |
| **Weight** | **8%** (Speculative — part of behavioral modifier) |
| **Extraction Logic** | Use `redrob_signals.recruiter_response_rate` (0.0-1.0). Score = min(1.0, rate / 0.5). A candidate with 0.5 response rate gets 1.0 (baseline). Above 0.5 gets a boost. Below 0.5 gets a penalty. Rate of 0.05 gets 0.1 (heavy penalty). |
| **Why It Matters** | JD: *"a perfect-on-paper candidate who... has a 5% recruiter response rate is, for hiring purposes, not actually available."* Directly cited in JD. |
| **False Positive Risks** | Low response rate could mean candidate is employed and selective, not unavailable. High response rate could mean the candidate is desperate, not quality. |
| **Evidence Source** | **Fact (JD):** Explicitly mentioned in hackathon note. **Fact (signals doc):** Signal #7 in reference table. |
| **Confidence Level** | **Fact** — Both JD and signals doc confirm |

### F11: Profile Recency Score

| Feature | Details |
|---------|---------|
| **Name** | `profile_recency_score` |
| **Category** | Behavioral Features |
| **Purpose** | Measure how recently the candidate was active on the platform |
| **Weight** | **5%** (Speculative — part of behavioral modifier) |
| **Extraction Logic** | Compute days since `redrob_signals.last_active_date`. Score = 1.0 if active within 30 days. Score = 0.7 if active within 90 days. Score = 0.4 if active within 180 days. Score = 0.1 if not active in 180+ days. |
| **Why It Matters** | JD: *"hasn't logged in for 6 months... not actually available."* A stale profile is a strong negative signal. |
| **False Positive Risks** | Candidate may be passive but still open. Last active date may not reflect actual availability. |
| **Evidence Source** | **Fact (JD):** Hackathon note. **Fact (signals doc):** Signal #3. |
| **Confidence Level** | **Fact** |

### F12: Open to Work Score

| Feature | Details |
|---------|---------|
| **Name** | `open_to_work_score` |
| **Category** | Behavioral Features |
| **Purpose** | Check if candidate has explicitly marked themselves as available |
| **Weight** | **3%** (Speculative — part of behavioral modifier) |
| **Extraction Logic** | Boolean: `redrob_signals.open_to_work_flag`. If true → 1.0 (or 1.1 for a small boost). If false → 0.6 (penalty but not exclusion — candidate may be passive but open). |
| **Why It Matters** | Direct availability signal. 35,339 (35.3%) candidates are open to work. Closed candidates may still be persuaded but are harder to recruit. |
| **False Positive Risks** | Candidates may forget to toggle this flag. Open-to-work doesn't guarantee genuine interest in this specific role. |
| **Evidence Source** | **Fact (signals doc):** Signal #4. **Inference (JD):** "down-weight them appropriately" applies to availability signals. |
| **Confidence Level** | **Inference** — JD says to down-weight unavailable candidates, open_to_work is an availability signal |

### F13: Platform Engagement Score

| Feature | Details |
|---------|---------|
| **Name** | `platform_engagement_score` |
| **Category** | Behavioral Features |
| **Purpose** | Composite measure of a candidate's activity on the Redrob platform |
| **Weight** | **2%** (Speculative) |
| **Extraction Logic** | Combine 2 primary signals: (1) `search_appearance_30d` — normalize (linear scale, cap at 200). (2) `saved_by_recruiters_30d` — normalize (linear scale, cap at 20). Secondary signals (`profile_views_received_30d`, `applications_submitted_30d`) reserved for tie-breaking only. |
| **Why It Matters** | Engaged candidates are more likely to respond, interview, and accept. Platform engagement validates that other recruiters find this candidate interesting. |
| **False Positive Risks** | Views could be from random searches. High application count could indicate desperation. |
| **Evidence Source** | **Fact (signals doc):** Signals #5, #6, #17, #18. |
| **Confidence Level** | **Inference** — Not explicitly mentioned in JD but supported by signals doc |

### F14: Skill Assessment Score

| Feature | Details |
|---------|---------|
| **Name** | `skill_assessment_score` |
| **Category** | Behavioral Features |
| **Purpose** | Measure independently verified skill proficiency via platform assessments |
| **Weight** | **3%** (Speculative) |
| **Extraction Logic** | Parse `redrob_signals.skill_assessment_scores` dict. Compute average score across AI/ML skills (if any). If dict is empty → 0.0 (no assessment data). This feature is only available for ~24.5% of candidates — treat as a bonus signal, not a universal feature. |
| **Why It Matters** | *"Per-skill Redrob assessment scores"* — independent verification of claimed skills. A candidate who scored 81/100 on "Object Detection" has verified expertise vs. someone who just listed it as a skill. |
| **False Positive Risks** | Sparse data (only ~24.5% of candidates have assessments). Should not penalize candidates without assessments — only reward those with good scores. |
| **Evidence Source** | **Fact (signals doc):** Signal #9. **Dataset analysis:** ~24.5% sparsity. |
| **Confidence Level** | **Fact** — Signal exists. Sparse availability is a data finding. |

---

## 4. Availability Features

Features that directly measure whether a candidate can actually be hired.

### F15: Notice Period Score

| Feature | Details |
|---------|---------|
| **Name** | `notice_period_score` |
| **Category** | Availability Features |
| **Purpose** | Score based on how quickly the candidate can start |
| **Weight** | **2%** (Speculative — tie-breaker level) |
| **Extraction Logic** | Use `redrob_signals.notice_period_days`. Score: 0-30 days → 1.0. 31-60 days → 0.8. 61-90 days → 0.6. 90+ days → 0.4. Can buy out up to 30 days per JD. |
| **Why It Matters** | JD: *"We'd love sub-30-day notice. We can buy out up to 30 days."* Longer notice periods increase hiring risk. |
| **False Positive Risks** | Notice periods are aspirational — some candidates can negotiate shorter periods. High-value candidates may still be worth waiting for. |
| **Evidence Source** | **Fact (JD):** Notice period preference. |
| **Confidence Level** | **Fact** |

### F16: Willing to Relocate Score

| Feature | Details |
|---------|---------|
| **Name** | `relocation_score` |
| **Category** | Availability Features |
| **Purpose** | Score whether the candidate is willing to relocate (relevant for Pune/Noida preference) |
| **Weight** | **1%** (Speculative — minor signal) |
| **Extraction Logic** | If `redrob_signals.willing_to_relocate` is true → 1.0. If false AND candidate is not already in India → 0.3 (strong penalty for international candidates not willing to relocate). If false AND candidate is in India → 0.7 (minor penalty, could still work hybrid). |
| **Why It Matters** | JD wants candidates in Pune/Noida or willing to relocate there. International without relocation is effectively unavailable. |
| **False Positive Risks** | Relocation willingness may not be realistic. Some candidates say yes but can't actually move. |
| **Evidence Source** | **Fact (JD):** Location preferences. |
| **Confidence Level** | **Fact** |

### F17: Salary Fit Score

| Feature | Details |
|---------|---------|
| **Name** | `salary_fit_score` |
| **Category** | Availability Features |
| **Purpose** | Check if candidate's salary expectations are within range for the role |
| **Weight** | **1%** (Speculative — minor signal, tie-breaker) |
| **Extraction Logic** | Use `redrob_signals.expected_salary_range_inr_lpa`. Compute midpoint: (min + max) / 2. Score based on proximity to expected Senior AI Engineer range (20-40 LPA). Midpoint in range → 1.0. Below 20 LPA → 0.8 (candidate may be underqualified or desperate). Above 40 LPA → 0.5 (too expensive). Inverted salary (min > max) → flag as data anomaly, set score to 0.5. |
| **Why It Matters** | Salary alignment affects hiring feasibility. A candidate expecting 80 LPA is not a realistic hire for this role. |
| **False Positive Risks** | Salary ranges are aspirational. 18,865 candidates have inverted salaries — handle as data anomalies, not scoring signals. |
| **Evidence Source** | **Inference:** JD doesn't state salary but typical Senior AI Engineer range in India is 20-40 LPA. Dataset: 18,865 inverted salaries. |
| **Confidence Level** | **Speculation** — Salary range for the role is not specified in JD |

---

## 5. Trust Features

Features that measure profile authenticity and verification.

### F18: Profile Completeness Score

| Feature | Details |
|---------|---------|
| **Name** | `profile_completeness_score_raw` |
| **Category** | Trust Features |
| **Purpose** | Measure how much of the profile has been filled in |
| **Weight** | **1%** (Speculative — minor modifier) |
| **Extraction Logic** | Use `redrob_signals.profile_completeness_score` (0-100) directly. Score = raw_value / 100. |
| **Why It Matters** | More complete profiles indicate more serious job seekers. Higher completeness = more data for our scoring. |
| **False Positive Risks** | Completeness doesn't correlate with quality. A fully completed profile by a non-ML candidate is still a poor match. |
| **Evidence Source** | **Fact (signals doc):** Signal #1. |
| **Confidence Level** | **Fact** — Signal exists. Importance is **Inference**. |

### F19: Verification Score

| Feature | Details |
|---------|---------|
| **Name** | `verification_score` |
| **Category** | Trust Features |
| **Purpose** | Composite of verified email, phone, and LinkedIn connection |
| **Weight** | **1%** (Speculative — minor modifier) |
| **Extraction Logic** | Sum of: `verified_email` (0.4), `verified_phone` (0.3), `linkedin_connected` (0.3). Range: 0.0 to 1.0. |
| **Why It Matters** | Verified profiles are more trustworthy. LinkedIn connection provides external validation of career history. |
| **False Positive Risks** | Verification doesn't correlate with ML skill. Many legitimate candidates may not have connected LinkedIn. |
| **Evidence Source** | **Fact (signals doc):** Signals #21, #22, #23. |
| **Confidence Level** | **Fact** — Signals exist. Importance is **Inference**. |

### F20: GitHub Activity Score

| Feature | Details |
|---------|---------|
| **Name** | `github_activity_score_raw` |
| **Category** | Trust Features |
| **Purpose** | Measure external validation through open-source contributions |
| **Weight** | **2%** (Speculative — bonus signal) |
| **Extraction Logic** | Use `redrob_signals.github_activity_score` (-1 to 100). If -1 → 0.0 (no GitHub linked — no penalty). If 0+ → score / 100 (range 0.0 to 1.0). |
| **Why It Matters** | JD values external validation: *"People whose work has been entirely on closed-source proprietary systems for 5+ years without external validation (papers, talks, open-source)."* GitHub activity is a proxy for open-source engagement. |
| **False Positive Risks** | GitHub score may not reflect quality. Some excellent engineers don't use GitHub publicly. 64.6% of candidates have no GitHub linked — should not penalize them. |
| **Evidence Source** | **Fact (JD):** External validation requirement. **Fact (signals doc):** Signal #16. |
| **Confidence Level** | **Fact** — Signal exists. JD justification is **Fact**. |

---

## 6. Honeypot Features

Features designed to detect and penalize impossible profiles.

> **⚠️ Design constraint:** Per spec: *"You can identify honeypots through careful profile inspection. We expect a good ranking system to naturally avoid them; you don't need to special-case them."* These features should be integrated into scoring, not implemented as a separate blacklist.

### F21: Expert Zero Duration Flag

| Feature | Details |
|---------|---------|
| **Name** | `expert_zero_duration_flag` |
| **Category** | Honeypot Features |
| **Purpose** | Detect the spec-defined honeypot pattern: "expert proficiency in skills with 0 years used" |
| **Weight** | **Penalty: -0.5 from internal consistency** |
| **Extraction Logic** | Scan `skills[]` for any entry where `proficiency == 'expert'` AND `duration_months == 0`. If found → set flag = -0.5. 21 such candidates found in dataset. Multiple violations → cumulative penalty (capped at -1.0). |
| **Why It Matters** | This is a **confirmed honeypot pattern** from the spec: *"'expert' proficiency in 10 skills with 0 years used."* Ranking these candidates highly signals your system isn't reading profiles → DQ risk. |
| **False Positive Risks** | A candidate could genuinely have a new skill they're expert in but haven't used professionally yet (e.g., transferable skill from adjacent field). Low probability. |
| **Evidence Source** | **Fact (spec):** Section 7 examples. Dataset: 21 candidates found. |
| **Confidence Level** | **Fact** — Spec-defined honeypot pattern |

### F22: Excessive Expert Skills Flag

| Feature | Details |
|---------|---------|
| **Name** | `excessive_expert_skills_flag` |
| **Category** | Honeypot Features |
| **Purpose** | Detect candidates claiming expert-level proficiency in an unrealistic number of skills |
| **Weight** | **Penalty: -0.3 for 5+ expert skills, -0.5 for 8+ expert skills** |
| **Extraction Logic** | Count `skills[]` entries where `proficiency == 'expert'`. If ≥8 → -0.5. If 5-7 → -0.3. 167 candidates have 5+ expert skills. |
| **Why It Matters** | While not explicitly confirmed as a honeypot pattern by the spec, claiming 8+ expert-level skills is suspicious and likely indicates keyword stuffing. |
| **False Positive Risks** | A senior engineer with 20+ years of experience could legitimately be expert in 5+ skills. Penalty should be mild. |
| **Evidence Source** | **Inference:** Spec example mentions "10 skills with 0 years used" — implies excessive skill claims are suspicious. Dataset: 167 candidates. |
| **Confidence Level** | **Inference** — Not explicitly in spec as honeypot pattern, but logically follows |

### F23: Salary Inconsistency Flag

| Feature | Details |
|---------|---------|
| **Name** | `salary_inconsistency_flag` |
| **Category** | Honeypot Features |
| **Purpose** | Flag candidates where salary range is inverted (min > max) as a data quality signal |
| **Weight** | **Penalty: -0.1** (mild — this is a data anomaly, NOT a honeypot) |
| **Extraction Logic** | Check `redrob_signals.expected_salary_range_inr_lpa`. If `min > max` → flag = -0.1. Do NOT classify as honeypot. 18,865 candidates have this anomaly. |
| **Why It Matters** | Per Phase 1 audit correction: Salary inversion is NOT a confirmed honeypot pattern. It's a data integrity issue affecting 18.9% of candidates. Mild penalty to push down, but not treated as hard disqualifier. |
| **False Positive Risks** | Some data systems store salary ranges as (max, min) tuples — inversion may just be a formatting choice. Very mild penalty ensures low impact. |
| **Evidence Source** | **Fact (dataset):** 18,865 candidates affected. **Fact (audit):** This is a data anomaly, NOT a honeypot. |
| **Confidence Level** | **Fact** — Pattern exists. Non-honeypot classification is **Fact** (from Phase 1 correction). |

### F24: Title-Skill Consistency Score

| Feature | Details |
|---------|---------|
| **Name** | `title_skill_consistency_score` |
| **Category** | Honeypot Features |
| **Purpose** | Detect candidates whose title suggests a non-technical role but whose skills suggest advanced ML expertise |
| **Weight** | **3% of base score** (additive to role-fit assessment) |
| **Extraction Logic** | If `profile.current_title` is non-technical (Marketing Manager, HR Manager, Accountant, etc.) AND candidate has 3+ advanced/expert AI/ML skills → consistency_penalty = -0.3. Cross-reference with career history — if career descriptions support AI/ML experience, reduce penalty. |
| **Why It Matters** | JD: *"A candidate who has all the AI keywords listed as skills but whose title is 'Marketing Manager' is not a fit."* This is the explicit keyword-stuffing trap. |
| **False Positive Risks** | Career changers (e.g., Marketing Manager → self-taught ML → AI Engineer) may have this profile but be legitimate. Career history analysis should override this signal if evidence supports ML experience. |
| **Evidence Source** | **Fact (JD):** Hackathon note explicitly warns about this. |
| **Confidence Level** | **Fact** — JD directly describes this pattern |

---

## 7. Location Features

Features that score how well the candidate's location matches the role's preferences.

### F25: India Location Score

| Feature | Details |
|---------|---------|
| **Name** | `india_location_score` |
| **Category** | Location Features |
| **Purpose** | Score candidates based on whether they're in India (preferred for visa reasons) |
| **Weight** | **3%** (Speculative) |
| **Extraction Logic** | If `profile.country == "India"` → 1.0. Otherwise → 0.5 (case-by-case, no visa sponsorship). |
| **Why It Matters** | JD: *"Outside India: case-by-case, but we don't sponsor work visas."* International candidates are at a significant logistical disadvantage. |
| **False Positive Risks** | An exceptional international candidate could be worth the visa hassle. Our scoring still allows them to rank high if other features are strong (0.5 is not exclusionary). |
| **Evidence Source** | **Fact (JD):** Visa and location policy. |
| **Confidence Level** | **Fact** |

### F26: Preferred City Score

| Feature | Details |
|---------|---------|
| **Name** | `preferred_city_score` |
| **Category** | Location Features |
| **Purpose** | Score candidates in or near preferred cities: Pune, Noida, Hyderabad, Mumbai, Delhi NCR |
| **Weight** | **2%** (Speculative) |
| **Extraction Logic** | Parse `profile.location` for preferred cities: Pune, Noida, Hyderabad, Mumbai, Delhi. If candidate is in one of these → 1.0. If in another Indian city (Bangalore, Chennai, etc.) → 0.8. If outside India → 0.5 (already handled by India_Location_Score). 20,956 candidates are in preferred cities. |
| **Why It Matters** | JD: *"Candidates in Hyderabad, Pune, Mumbai, Delhi NCR welcome to apply."* Being in these cities is logistically preferred. |
| **False Positive Risks** | Remote work from other Indian cities is acceptable per JD. This is a preference, not a requirement. |
| **Evidence Source** | **Fact (JD):** Location preferences. Dataset: 20,956 candidates. |
| **Confidence Level** | **Fact** |

### F27: Work Mode Fit Score

| Feature | Details |
|---------|---------|
| **Name** | `work_mode_fit_score` |
| **Category** | Location Features |
| **Purpose** | Score alignment between candidate's preferred work mode and the role's hybrid expectation |
| **Weight** | **1%** (Speculative — minor) |
| **Extraction Logic** | Use `redrob_signals.preferred_work_mode`. Hybrid → 1.0. Onsite → 0.9. Remote → 0.8. Flexible → 1.0. |
| **Why It Matters** | JD: *"Pune/Noida, India (Hybrid — flexible cadence)."* The role is hybrid with flexibility. Candidates open to hybrid are the best fit. |
| **False Positive Risks** | Work mode preferences are not firm. Most candidates will adapt. |
| **Evidence Source** | **Fact (JD):** Work mode listed as hybrid. **Fact (signals doc):** Signal #14. |
| **Confidence Level** | **Fact** |

---

## 8. Experience Features

Features that measure the quantity and quality of a candidate's work experience.

### F28: Total Experience Fit Score

| Feature | Details |
|---------|---------|
| **Name** | `total_experience_fit_score` |
| **Category** | Experience Features |
| **Purpose** | Score how well the candidate's total years of experience match the target band |
| **Weight** | **5%** (Speculative) |
| **Extraction Logic** | Use `profile.years_of_experience`. Apply softened bell curve centered on 7 years: Score = exp(-0.5 × ((years - 7) / 4)²). Clamp min score to 0.3. 5-9 years → 0.8-1.0. 4 years → 0.75. 12 years → 0.7. 2 years → 0.5. 15 years → 0.4. |
| **Why It Matters** | JD: *"6-8 years total experience, of which 4-5 are in applied ML/AI roles."* The ideal candidate has ~7 years total. Note: Bell curve is a scoring heuristic. 4-year prodigies should not be heavily penalized (min score 0.3 ensures fair treatment). |
| **False Positive Risks** | A 4-year prodigy could be better than a 10-year consultant. Our bell curve softens the edges — 4 years still scores 0.7, not zero. |
| **Evidence Source** | **Fact (JD):** "Ideal candidate" description. |
| **Confidence Level** | **Fact** |

### F29: Career Stability Score

| Feature | Details |
|---------|---------|
| **Name** | `career_stability_score` |
| **Category** | Experience Features |
| **Purpose** | Measure job stability — penalize excessive job-hopping |
| **Weight** | **2%** (Speculative) |
| **Extraction Logic** | Compute average tenure per role from `career_history[].duration_months`. Score: avg tenure > 24 months → 1.0. 12-24 months → 0.8. 6-12 months → 0.5. < 6 months → 0.3. Also penalize if candidate has 6+ roles in career (6,580 candidates) — penalty: -0.2.

> **Startup exception:** If company_size is '1-10', '11-50', or '51-200', multiply tenure by 0.8 before scoring (startup tenures are naturally shorter). |
| **Why It Matters** | JD: *"Title-chasers... switching companies every 1.5 years, we're not a fit. We need someone who plans to be here for 3+ years."* Stability signals long-term commitment. |
| **False Positive Risks** | Short tenures at early-stage startups are normal. Contract roles have short duration by nature. |
| **Evidence Source** | **Fact (JD):** "Things we explicitly do NOT want." |
| **Confidence Level** | **Fact** |

### F30: Industry Relevance Score

| Feature | Details |
|---------|---------|
| **Name** | `industry_relevance_score` |
| **Category** | Experience Features |
| **Purpose** | Score how relevant the candidate's industry experience is to AI/ML product development |
| **Weight** | **1%** (Speculative — minor) |
| **Extraction Logic** | Score `profile.current_industry` and `career_history[].industry`. Tech/AI/software → 1.0. Fintech → 0.9. E-commerce → 0.9. IT Services → 0.5. Manufacturing → 0.4. Paper Products → 0.2. |
| **Why It Matters** | Industry experience correlates with relevant ML exposure. A candidate from a software company is more likely to have built production ML systems than one from paper products. |
| **False Positive Risks** | Industry alone doesn't indicate role. A "Software" industry accountant is different from a "Software" industry ML engineer. |
| **Evidence Source** | **Inference:** JD targets AI-native talent intelligence platform. Dataset: IT Services (29.9%) and Software (22.4%) dominate. |
| **Confidence Level** | **Inference** |

---

## 9. Education Features

Features that measure educational background relevance.

### F31: Degree Relevance Score

| Feature | Details |
|---------|---------|
| **Name** | `degree_relevance_score` |
| **Category** | Education Features |
| **Purpose** | Score how relevant the candidate's degree field is to AI/ML |
| **Weight** | **2%** (Speculative) |
| **Extraction Logic** | Score `education[].field_of_study`. Computer Science, ML, AI, Data Science, Statistics, Mathematics → 1.0. Engineering, Electronics, Information Technology → 0.7. Physics, other sciences → 0.5. Business, Marketing, Arts → 0.2. Take max score across all degrees. |
| **Why It Matters** | Education is not the strongest signal (JD says *"Skills are teachable; the rest mostly isn't"*), but relevant education correlates with ML fundamentals. |
| **False Positive Risks** | Many great ML engineers come from non-CS backgrounds (physics, math, self-taught). Low weight ensures this doesn't override stronger signals. |
| **Evidence Source** | **Inference:** JD doesn't emphasize education. Low weight reflects this. |
| **Confidence Level** | **Inference** |

### F32: Institution Tier Score

| Feature | Details |
|---------|---------|
| **Name** | `institution_tier_score` |
| **Category** | Education Features |
| **Purpose** | Score based on institution prestige tier |
| **Weight** | **1%** (Speculative — very minor) |
| **Extraction Logic** | Use `education[].tier`. Tier 1 → 1.0. Tier 2 → 0.8. Tier 3 → 0.6. Tier 4 → 0.4. Unknown → 0.5. Take max across all education entries. |
| **Why It Matters** | Tier 1/2 institutions (IITs, NITs, top global universities) indicate strong foundational training. However, many excellent ML engineers come from Tier 3/4 schools. |
| **False Positive Risks** | Institution tier is a weak proxy for ability. Low weight ensures this doesn't penalize self-taught engineers or those from less prestigious schools. |
| **Evidence Source** | **Fact (schema):** Tier field exists in education. **Inference:** JD doesn't emphasize institution prestige. |
| **Confidence Level** | **Inference** |

### F33: Highest Degree Score

| Feature | Details |
|---------|---------|
| **Name** | `highest_degree_score` |
| **Category** | Education Features |
| **Purpose** | Score based on the candidate's highest degree level |
| **Weight** | **1%** (Speculative — tie-breaker level) |
| **Extraction Logic** | Score `education[].degree`. PhD → 1.0. M.Tech/M.S./M.E. → 0.9. B.Tech/B.E./B.Sc → 0.8. Other → 0.5. Take max. |
| **Why It Matters** | Advanced degrees in ML/AI are positive signals. However, the JD values production experience over academic credentials — low weight reflects this. |
| **False Positive Risks** | PhD candidates may be overqualified or research-oriented (JD disqualifies "pure research"). MS/BS candidates with production experience may be better fits. |
| **Evidence Source** | **Inference:** JD says *"If you've spent your career in pure research environments... we will not move forward."* Advanced degrees without production experience are not valued. |
| **Confidence Level** | **Inference** |

---

### F34: Current Role Tenure Score

| Feature | Details |
|---------|---------|
| **Name** | `current_role_tenure_score` |
| **Category** | Experience Features |
| **Purpose** | Measure tenure at current role — currently employed candidates with stable tenure are more reliable hires |
| **Weight** | **2%** (Speculative) |
| **Extraction Logic** | Find `career_history[]` entry where `is_current == true`. Use `duration_months`. Score: >24 months → 1.0. 12-24 → 0.8. 6-12 → 0.6. <6 → 0.4. If no current role found → 0.5 (candidate may be unemployed, which isn't necessarily negative). |
| **Why It Matters** | Current role tenure indicates stability and likelihood of staying. A candidate who just started a new role ( < 6 months ) may not be actively looking. |
| **False Positive Risks** | Candidates who recently joined may still be open to the right opportunity. Short current tenure doesn't mean disloyalty. |
| **Evidence Source** | **Inference:** JD says *"We need someone who plans to be here for 3+ years"* — current tenure signals this. |
| **Confidence Level** | **Inference** |

### F35: Skill Diversity Penalty

| Feature | Details |
|---------|---------|
| **Name** | `skill_diversity_penalty` |
| **Category** | Honeypot Features |
| **Purpose** | Detect candidates with skills spanning completely unrelated domains — a potential keyword-stuffing signal |
| **Weight** | **Penalty: -0.2** |
| **Extraction Logic** | Categorize all `skills[].name` into domains: ML/AI (NLP, PyTorch, TensorFlow, etc.), Engineering (Python, Java, SQL, etc.), Business (Marketing, Sales, Accounting), Design (Photoshop, Figma, Illustrator), Other. If candidate has skills in 3+ unrelated domains → penalty -0.2. Example: "PyTorch" + "Accounting" + "Photoshop" = 3 domains → penalty applied. |
| **Why It Matters** | Genuine candidates typically have skill sets concentrated in 1-2 related domains. Wide-spanning skills suggest keyword stuffing. |
| **False Positive Risks** | Some legitimate candidates have broad skill sets (e.g., a technical product manager might have ML, engineering, AND business skills). Penalty is mild (-0.2). |
| **Evidence Source** | **Inference:** JD hackathon note warns about keyword stuffing. Wide skill diversity is a heuristic for this. |
| **Confidence Level** | **Inference** |

---

## 10. Full Scoring Proposal

> ⚠️ **SPECULATIVE DESIGN PROPOSAL** — All weights are preliminary hypotheses. They will be validated and tuned during Phase 4 (Scoring Implementation). No code has been written.

### Formula

```
FINAL_SCORE = BASE_MATCH_SCORE × BEHAVIORAL_MODIFIER × CONSULTING_PENALTY - HONEYPOT_PENALTY
```

### Component Breakdown

#### BASE_MATCH_SCORE (0.0 - 1.0)

```
BASE_MATCH_SCORE = 
  0.12 × title_semantic_score (F1)
+ 0.03 × headline_relevance_score (F2)
+ 0.05 × summary_relevance_score (F3)
+ 0.15 × shipped_systems_score (F4)
+ 0.08 × product_company_score (F5)
+ 0.05 × ai_ml_duration_score (F6)
+ 0.04 × role_progression_score (F7)
+ 0.03 × eval_experience_score (F9)
+ 0.03 × title_skill_consistency_score (F24)
+ 0.05 × total_experience_fit_score (F28)
+ 0.02 × career_stability_score (F29)
+ 0.01 × industry_relevance_score (F30)
+ 0.02 × degree_relevance_score (F31)
+ 0.01 × institution_tier_score (F32)
+ 0.01 × highest_degree_score (F33)
+ 0.03 × india_location_score (F25)
+ 0.02 × preferred_city_score (F26)
+ 0.01 × work_mode_fit_score (F27)
+ 0.01 × notice_period_score (F15)
+ 0.01 × relocation_score (F16)
+ 0.01 × salary_fit_score (F17)
+ 0.01 × profile_completeness_score_raw (F18)
+ 0.01 × verification_score (F19)
+ 0.02 × github_activity_score_raw (F20)
---
Sum = 1.00 (100%)
```

#### BEHAVIORAL_MODIFIER (×0.4 to ×1.2)

```
BEHAVIORAL_MODIFIER = 
  0.40 × recruiter_response_rate_score (F10)
+ 0.25 × profile_recency_score (F11)
+ 0.15 × open_to_work_score (F12)
+ 0.15 × platform_engagement_score (F13)
+ 0.05 × skill_assessment_score (F14)
---
Range: 0.4 (worst) to 1.2 (best). Baseline = 1.0
```

**Examples:**
- Strong availability: response_rate=0.8, active_last_week, open_to_work=true, high engagement → ~1.15
- Weak availability: response_rate=0.05, inactive_6_months, not_open_to_work, low engagement → ~0.45

#### CONSULTING_PENALTY (×0.3 to ×1.0)

```
If ALL roles are at consulting firms → penalty = 0.3
If MIXED (some consulting, some product) → penalty = 0.8
If NO consulting roles → penalty = 1.0 (no penalty)
```

#### HONEYPOT_PENALTY (0.0 to -1.0)

```
HONEYPOT_PENALTY = 
  (-0.5 if expert_zero_duration_flag (F21)) +
  (-0.3 if 5+ expert skills, -0.5 if 8+ (F22)) +
  (-0.1 if salary_inconsistency_flag (F23))
---
Range: 0.0 (no flags) to -1.0 (max penalties)
```

### Normalization Strategy

1. **Per-feature normalization:** Each feature is independently normalized to [0.0, 1.0] range
2. **BASE_MATCH_SCORE normalization:** Clamp to [0.0, 1.0] after weighted sum
3. **BEHAVIORAL_MODIFIER normalization:** Clamp to [0.4, 1.2] to prevent extreme modification
4. **HONEYPOT_PENALTY normalization:** Clamp to [-1.0, 0.0]
5. **FINAL_SCORE normalization:** After all modifiers, clamp to [0.0, 1.0]
6. **Ranking order:** Sort by FINAL_SCORE descending, assign ranks 1-100
7. **Score sequence:** Ensure scores are non-increasing (spec requirement: *"score at rank 1 ≥ score at rank 2 ≥ ... ≥ score at rank 100"*)

### Tie-Breaking Strategy

Per spec: *"If two candidates have the same score, you must still assign unique ranks. Break score ties deterministically using a secondary signal from your model, or by candidate_id ascending."*

**Tie-breaker order:**
1. Higher `shipped_systems_score (F4)` — production ML experience breaks ties
2. Higher `recruiter_response_rate_score (F10)` — availability breaks ties
3. Lower `notice_period_days` — sooner availability breaks ties
4. Lower `candidate_id` (ascending) — deterministic final tie-breaker

### Penalty Strategy Summary

| Condition | Penalty Type | Value | Evidence |
|-----------|-------------|-------|----------|
| Consulting-only career | Multiplicative | ×0.3 | **Fact (JD)** |
| Mixed career (some consulting) | Multiplicative | ×0.8 | **Inference** |
| Expert + 0 duration skill | Additive | -0.5 | **Fact (spec)** |
| 5+ expert skills | Additive | -0.3 | **Inference** |
| 8+ expert skills | Additive | -0.5 | **Inference** |
| Salary inverted | Additive | -0.1 | **Inference (data anomaly)** |
| Title-skill mismatch | Within base score | 3% weight | **Fact (JD)** |
| Job hopping (6+ roles) | Within base score | 2% weight | **Fact (JD)** |

### Expected Score Distribution

| Rank Range | Expected Score Range | Typical Profile |
|-----------|---------------------|-----------------|
| 1-10 | 0.85 - 1.00 | AI/ML title, shipped systems, product company, strong signals |
| 11-30 | 0.65 - 0.85 | Tech title with ML, good career history, good signals |
| 31-60 | 0.40 - 0.65 | Adjacent roles, some ML exposure, moderate signals |
| 61-85 | 0.25 - 0.40 | Tech role, limited ML, mixed signals |
| 86-100 | 0.10 - 0.25 | Non-tech, keyword-stuffed, poor signals, anomalies |

### Score Monotonicity Guarantee

After computing all scores:
1. Sort candidates by FINAL_SCORE descending
2. Take top 100
3. Verify: score[i] >= score[i+1] for all i in 1..99
4. If any violation found (floating point edge case), adjust: score[i+1] = min(score[i+1], score[i] - epsilon)

---

## Summary Statistics

| Category | Features | Total Weight | Evidence Facts | Inferences | Speculations |
|----------|----------|-------------|----------------|------------|--------------|
| Semantic | 3 | 20% | 0 | 3 | 0 |
| Career Intelligence | 6 | 37% | 5 | 1 | 0 |
| Behavioral | 5 | 21% | 3 | 2 | 0 |
| Availability | 3 | 4% | 2 | 0 | 1 |
| Trust | 3 | 4% | 1 | 2 | 0 |
| Honeypot | 5 | (penalty) | 2 | 3 | 0 |
| Location | 3 | 6% | 3 | 0 | 0 |
| Experience | 4 | 10% | 2 | 2 | 0 |
| Education | 3 | 4% | 0 | 3 | 0 |
| **Total** | **35** | **100%** | **18** | **16** | **1** |

- **18 features backed by Fact** — Directly from JD, spec, or dataset
- **14 features backed by Inference** — Logical conclusions from multiple evidence sources
- **1 feature backed by Speculation** — Salary fit score (role salary not specified)

---

*End of Feature Catalog. See Phase 2 validation and audit documents for quality assessment.*
