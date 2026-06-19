# Analysis Report — Redrob Intelligent Candidate Discovery & Ranking

> **Phase 1 Deliverable** | Target Role: Senior AI Engineer, Founding Team at Redrob AI

---

## Table of Contents

1. [Hidden Judging Criteria](#1-hidden-judging-criteria)
2. [Ground Truth Assumptions](#2-ground-truth-assumptions)
3. [Relevance Tiers](#3-relevance-tiers)
4. [Honeypot Patterns](#4-honeypot-patterns)
5. [Weak Solutions](#5-weak-solutions)
6. [Strong Solutions](#6-strong-solutions)
7. [Winning Strategy](#7-winning-strategy)
8. [Risk Analysis](#8-risk-analysis)

---

## 1. Hidden Judging Criteria

> **Evidence classification:** The competition uses objective metrics (NDCG@10, NDCG@50, MAP, P@10) scored against a hidden ground truth. The criteria below are extracted from explicit statements in the JD and spec. **Fact** = direct quote. **Inference** = logical conclusion from multiple facts.

### What the JD *actually* values (vs. what it says)

| Says | Means | Evidence |
|------|-------|----------|
| "5–9 years experience" | Experience band, not a hard cutoff. 4 years at a product company > 10 years at a consultancy. | **Fact:** JD: *"This is a range, not a requirement."* |
| "Production ML experience" | Must have shipped ML systems to real users. Research-only and tutorial-only candidates are disqualified. | **Fact:** JD: *"If you've spent your career in pure research environments... without any production deployment — we will not move forward."* |
| "Strong Python" | Code quality matters. A ranker that treats this as a keyword-matching exercise reveals lack of engineering judgment. | **Inference:** JD says *"Strong Python. Yes really, we care about code quality."* |
| "Embeddings, retrieval, ranking" | Needs understanding of the full stack, not just familiarity. | **Fact:** JD: *"Production experience with embeddings-based retrieval systems... deployed to real users."* |
| "Evaluation frameworks" | Knows NDCG, MRR, MAP and can reason about offline-to-online correlation. | **Fact:** JD: *"Hands-on experience designing evaluation frameworks for ranking systems — NDCG, MRR, MAP."* |
| "Shipper > researcher" | Prefers pragmatic deployment over theoretical purity. | **Fact:** JD: *"We'd rather you tilt slightly toward shipper than toward researcher."* |
| "Pune/Noida preferred" | Location is a signal — Indian candidates especially from preferred cities get priority. International candidates need exceptional profiles (no visa sponsorship). | **Fact:** JD: *"Candidates in Hyderabad, Pune, Mumbai, Delhi NCR welcome to apply. Outside India: case-by-case, but we don't sponsor work visas."* |

### Explicit disqualifiers from the JD

1. **Pure research background** — academic or research-only roles without production deployment
2. **LangChain-only "AI experience"** — less than 12 months of only API-calling experience
3. **No production code in 18 months** — architecture/lead roles only without hands-on coding
4. **Consulting-only career** — exclusively TCS, Infosys, Wipro, Accenture, Cognizant, Capgemini, Mindtree, HCL, Tech Mahindra, Mphasis, or similar IT services firms
   > **Note:** The JD says *"people who have only worked at consulting firms (TCS, Infosys, Wipro, Accenture, Cognizant, Capgemini, **etc.**)"*. The "etc." is meaningful — our dataset also contains Mindtree, HCL, Tech Mahindra, and Mphasis as consulting firms where candidates have consulting-only careers (7,034 total such candidates).
5. **CV/Speech/Robotics specialists** — without significant NLP/IR exposure
6. **Closed-source hermits** — 5+ years without any external validation (papers, talks, OSS)

### Behavioral signals that matter (from the JD directly)

> *"A perfect-on-paper candidate who hasn't logged in for 6 months and has a 5% recruiter response rate is, for hiring purposes, not actually available."* — **Fact (JD hackathon note)**

This is an explicit instruction to down-weight candidates with:
- Low recruiter response rate
- Old last_active_date
- Not open_to_work
- Long notice periods
- No platform engagement

### Stage 4 reasoning evaluation

> **Fact (spec Section 3):** At Stage 4, 10 random rows are manually checked.

**Penalized:**
- Empty reasoning
- All-identical reasoning strings
- Templated reasoning (just inserts the candidate's name)
- Hallucinated skills (not in candidate's profile)
- Reasoning contradicting the rank

**Rewarded:**
- Plain-language reasoning demonstrating actual understanding of the candidate's profile

### The honeypot filter

> **Fact (spec Section 7):** *"submissions with honeypot rate > 10% in top 100 are disqualified."*

**Margin of error:** 0 honeypots in top 10 (strong signal), ≤10 in top 100 (to stay under 10% threshold).

---

## 2. Ground Truth Assumptions

> **Evidence classification:** The hidden ground truth is not provided. All statements about its content are **inferences** or **speculation** unless directly supported by the scoring formula.

### What is confirmed

| Statement | Evidence | Type |
|-----------|----------|------|
| Metrics: NDCG@10 (50%), NDCG@50 (30%), MAP (15%), P@10 (5%) | Spec Section 4: *"Final composite = 0.50 × NDCG@10 + 0.30 × NDCG@50 + 0.15 × MAP + 0.05 × P@10"* | **Fact** |
| Hidden ground truth exists | Spec: *"scored against the hidden ground truth"* | **Fact** |
| Relevance tiers exist (at least 0) | Spec: *"forced to relevance tier 0"* — implying tier 0, thus tier 1+ exist | **Fact** |
| Honeypots are tier 0 | Same source | **Fact** |
| No live leaderboard, no feedback | Spec: *"The leaderboard is hidden during the competition."* | **Fact** |

### What is inferred

| Statement | Supporting Evidence | Type |
|-----------|-------------------|------|
| Ground truth penalizes non-technical titles ranking highly | JD explicitly says marketing managers with AI keywords are not a fit. NDCG discounting means wrong high-rank matches are heavily penalized. | **Inference** |
| Ground truth rewards shipped ranking/recommendation systems | JD "ideal candidate" profile describes this. Spec metrics favor this. | **Inference** |
| Ground truth assigns graded relevance (not binary) | Multiple NDCG metrics at different cutoffs imply graded relevance scoring. | **Inference** |
| Top 10 optimization is highest leverage | 50% weight on NDCG@10; 10 positions carry half the total score. | **Inference** |

### What is speculative

| Statement | Reason | Type |
|-----------|--------|------|
| "Ground truth was created by expert labeling of 500-1000 candidates" | No document describes ground truth creation methodology | **Speculation** |
| "Exact relevance tier population counts (Tier 5 = ~10-15, etc.)" | No population counts provided in any document | **Speculation** |

---

## 3. Relevance Tiers

> **Evidence classification:** Tier structure is **inferred** from the spec's mention of "relevance tier 0" and the JD's spectrum of candidate fit. Exact population counts are **speculation**.

### Inferred relevance tiers

| Tier | Label | Expected Count (Speculative) | Profile Characteristics |
|------|-------|------------------------------|----------------------|
| **5** | Perfect Match | ~10–15 | AI/ML title, 5-9 yrs experience, product company, shipped ranking/retrieval systems, strong behavioral signals, India-based |
| **4** | Strong Match | ~15–30 | Tech title with ML focus, 4-12 yrs, some production ML, mixed company background, good behavioral signals |
| **3** | Moderate Match | ~30–50 | Adjacent roles (data engineering, MLOps), 3-12 yrs, transitioning to ML, acceptable signals |
| **2** | Weak Match | ~20–30 | Tech role, limited ML, some relevant skills, mixed signals |
| **1** | Poor Match | ~10–20 | Non-tech role, keyword-stuffed skills, poor signals, long notice period |
| **0** | Honeypot | ~80 (per spec) | Impossible profiles — forced to bottom regardless of keyword match |

---

## 4. Honeypot Patterns

> **Evidence classification:** This section has been corrected per Phase 1 audit. Three categories are now clearly separated. See `docs/PHASE_1_AUDIT.md` for the full audit trail.

### Category A: Confirmed Honeypots (Spec-Defined)

These are patterns directly stated in the competition specification. The spec says there are **~80 such candidates**.

| Pattern | Spec Quote | Detectable? |
|---------|-----------|-------------|
| **Experience > company existence** (time travel) | *"8 years of experience at a company founded 3 years ago"* | ⚠️ **Not directly detectable** — we have no company founding dates in the dataset. Could be approximated using earliest start_date heuristic. |
| **Expert proficiency with 0 years used** | *"'expert' proficiency in 10 skills with 0 years used"* | ✅ **Detectable** — found 21 candidates with expert proficiency + 0 duration |
| **Extreme skill count with impossible configuration** | The spec's example implies 10+ expert skills with 0 duration | ✅ **Detectable** — 167 candidates have 5+ expert skills |

**Spec quote (Section 7):** *"The dataset contains a small number (~80) of honeypot candidates with subtly impossible profiles (e.g., 8 years of experience at a company founded 3 years ago; 'expert' proficiency in 10 skills with 0 years used)."*

**Key constraint:** *"We expect a good ranking system to naturally avoid them; you don't need to special-case them."*

### Category B: Data Anomalies (Not Honeypots)

These are patterns that indicate data quality issues but are **NOT confirmed as honeypots** by the spec. They affect ~29,000 candidates and should be handled as data quality signals, not honeypot detection.

| Pattern | Count | Analysis |
|---------|-------|----------|
| **Salary inverted (min > max)** | 18,865 (18.9%) | Likely data integrity issue. A candidate whose salary range is "16.0-7.3 LPA" has an error, but this isn't an "impossible profile" in the spec's sense. **Do not classify as honeypot.** |
| **Too many skills (>15)** | 6,650 (6.7%) | Possible keyword stuffing, but not necessarily impossible. |
| **Many jobs (6+ career entries)** | 6,580 (6.6%) | Job-hopping pattern, not an impossible profile. |

### Category C: Role-Fit Inconsistencies (Not Honeypots)

These patterns indicate a candidate is **not a good fit for the role** based on the JD, but they are NOT honeypots (impossible profiles). The JD explicitly warns that keyword-stuffed non-technical candidates are a trap.

| Pattern | JD Reference | Recommended Handling |
|---------|-------------|---------------------|
| **Non-tech title + advanced AI skills** | *"A candidate who has all the AI keywords listed as skills but whose title is 'Marketing Manager' is not a fit"* | **Inference:** Score as poor role fit. Natural demotion via Relevance Tier assignment. |
| **Consulting-only career** | *"People who have only worked at consulting firms... entire career"* — listed under "Things we explicitly do NOT want" | **Fact:** Down-weight via scoring components. |
| **Summary says "marketing" / "operations" but has advanced ML skills** | Both JD examples (marketing manager with AI keywords) and JD's explicit trap warning | **Inference:** Penalize via consistency features in scoring. |
| **CV/speech/robotics specialists without NLP/IR** | *"People whose primary expertise is computer vision, speech, or robotics without significant NLP/IR exposure"* | **Fact:** Down-weight. Score NLP/IR skills higher than CV/speech. |

### ⚠️ Critical Distinction

| Concept | Definition | Count | Consequence |
|---------|-----------|-------|-------------|
| **Honeypots** (spec-defined) | Subtly impossible profiles | ~80 | Must not appear in top 10; rate must be <10% in top 100 |
| **Data anomalies** | Data integrity issues (salary, skill counts) | ~29K | Handle as quality signals, not honeypots |
| **Role-fit issues** | Poor match to JD (non-tech titles, wrong skills) | ~58K non-tech titles | Handle via scoring weights, not honeypot detection |

### Why keyword-matching rankers fail on honeypots

> **Fact (JD hackathon note):** *"The 'right answer' to this JD is not 'find candidates whose skills section contains the most AI keywords.' That's a trap we've explicitly built into the dataset."*

A naive TF-IDF or embedding-only ranker will rank honeypots highly because they're designed to match keywords while being internally impossible. The spec explicitly warns that ranking honeypots in the top 10 signals a system "isn't reading profiles."

---

## 5. Weak Solutions

These approaches will likely fail at Stage 3 (reproduction) or produce poor rankings:

### ❌ Pure keyword TF-IDF matching
- **Why it fails:** Ranks keyword-stuffed honeypots highly; ignores behavioral signals; no understanding of the JD's subtext
- **Honeypot rate:** Very high (likely >10% → disqualification)
- **Evidence:** JD explicitly calls this a trap

### ❌ Simple embedding cosine similarity (single-vector)
- **Why it fails:** No behavioral signal integration; can't distinguish between genuine AI engineers and keyword-stuffed marketing managers
- **Honeypot rate:** High
- **Evidence:** JD says *"weigh behavioral signals"* — embedding-only can't do this

### ❌ LLM-per-candidate ranking
- **Why it fails:** 100,000 API calls at 5 minutes = impossible; no network allowed
- **Stage 3 filter:** Fails reproduction
- **Evidence (spec):** *"running an LLM call for each of 100,000 candidates will not fit the 5-minute CPU budget"*

### ❌ Rule-based only (hardcoded thresholds)
- **Why it fails:** Doesn't understand nuanced disqualifiers; can't weigh tradeoffs; brittle

### ❌ Title-only matching
- **Why it fails:** Misses candidates with relevant experience but different titles

### ❌ Consulting-firm blanket exclusion
- **Why it fails:** JD says exclude *only if entire career* is at consulting firms. Having worked at a consulting firm is fine if they have product-company experience too.

### Common failure patterns

| Failure | Consequence |
|---------|-------------|
| Ranks honeypots in top 10 | Disqualification at Stage 3 |
| Empty/templated reasoning | Low Stage 4 score |
| Cannot reproduce on CPU in 5 min | Disqualification at Stage 3 |
| 99 or 101 rows | Auto-rejection at Stage 1 |
| Duplicate IDs or ranks | Auto-rejection at Stage 1 |
| Scores not non-increasing | Auto-rejection at Stage 1 |

---

## 6. Strong Solutions

### ✅ Hybrid scoring pipeline
- **Approach:** Multi-component score combining title alignment, skill relevance (weighted by proficiency × endorsements × duration), career history analysis, education tier, and behavioral signal modifier
- **Advantages:** Fast (no network), interpretable (easy reasoning generation), avoids honeypot traps naturally via consistency checks
- **Honeypot resistance:** High — internal consistency checks naturally demote impossible profiles

### ✅ Career-history-driven analysis (JD-Recommended)
- **Approach:** Analyze career descriptions for evidence of shipped ML systems, not just skill keywords
- **Key insight from JD:** *"A Tier 5 candidate may not use the words 'RAG' or 'Pinecone' in their profile, but if their career history shows they built a recommendation system at a product company, they're a fit."*
- **Implementation idea (Phase 3):** Score career descriptions by:
  - Presence of shipping keywords: "ranking", "retrieval", "recommendation", "search", "embedding", "vector", "ML system", "production", "deployed"
  - Company-type scoring: product companies (Ola, Zomato, Razorpay) > consulting firms (TCS, Infosys, Wipro)
  - Role-duration weighting: more time in relevant roles = higher score
- **Why this wins:** Directly addresses JD's explicit instruction to read beyond skill lists

### ✅ Embedding + rule-based hybrid (Alternative)
- **Approach:** Lightweight embedding model (e.g., sentence-transformers/all-MiniLM-L6-v2) for semantic matching of JD to profile summary + career descriptions, combined with rule-based behavioral and consistency scoring
- **Challenges:** Must batch efficiently; embedding 100K profiles needs ~2-3 minutes on CPU

### ✅ Multi-stage cascading ranker
- **Approach:** 
  1. Fast pre-filter (rule-based) to reduce 100K → ~1K candidates
  2. Richer scoring on the subset (embedding similarity + behavioral modifier)
  3. Final ranking with tie-breaking
- **Advantages:** Efficient, allows more compute on relevant candidates

### Key design principles for strong solutions

| Principle | Rationale | Evidence |
|-----------|-----------|----------|
| Read the entire profile, not just skills | JD explicitly warns against keyword matching | **Fact** |
| Weigh behavioral signals as a modifier | JD says unavailable candidates should be down-weighted | **Fact** |
| Check internal consistency | Naturally demotes impossible profiles without special-casing | **Inference** |
| Generate specific, honest reasoning | Stage 4 manual review checks 10 random rows | **Fact** |
| Optimize for NDCG@10 (50% weight) | Top 10 accuracy carries half the composite score | **Fact** |
| Design for CPU-only reproduction | Must pass Stage 3 sandbox test | **Fact** |
| Keep it under 5 minutes | Hard constraint from spec | **Fact** |
| Analyze career descriptions deeply | JD says career history evidence should outweigh keyword matching | **Fact** |

---

## 7. Winning Strategy

> ⚠️ **SPECULATIVE DESIGN PROPOSAL**  
> The strategy below is based on analysis of competition documents and dataset patterns. All component weights and formulas are preliminary design estimates and will be validated/refined during Phase 4 (Scoring Strategy Design).

### Core architecture: Hybrid Feature-Based Ranker

```
                          ┌──────────────────────┐
                          │  Candidate Data       │
                          │  (100K JSONL, stream) │
                          └──────────┬───────────┘
                                     ▼
                          ┌──────────────────────┐
                          │  Feature Extraction   │
                          │  (Phase 3-4)          │
                          │  • Title features     │
                          │  • Skill features     │
                          │  • Career history     │
                          │  • Education          │
                          │  • Behavioral signals │
                          └──────────┬───────────┘
                                     ▼
                          ┌──────────────────────┐
                          │  Scoring Engine       │
                          │  (Phase 5)            │
                          │  • Component scoring  │
                          │  • Behavioral mod.    │
                          │  • Consistency check  │
                          └──────────┬───────────┘
                                     ▼
                          ┌──────────────────────┐
                          │  submission.csv       │
                          │  (top 100 ranked)     │
                          └──────────────────────┘
```

### Scoring components — PRELIMINARY WEIGHTS (IMPLEMENTATION HYPOTHESIS)

> All weights below are **initial design estimates** that will be tuned during Phase 4. They represent a hypothesis about what will maximize NDCG@10 and NDCG@50, not confirmed values.

| Component | Preliminary Weight | What It Measures | Evidence Basis |
|-----------|-------------------|-----------------|---------------|
| Title relevance score | **25%** | How closely current/past titles match "Senior AI Engineer" and related roles | **Inference:** Title is strongest surface signal. Only 1,126 candidates (1.1%) have AI/ML titles. |
| Skill relevance score | **20%** | AI/ML skill match weighted by proficiency × duration × endorsements | **Inference:** JD lists AI/ML skills as requirement. But JD also warns keyword stuffing is a trap. |
| Career history relevance | **20%** | Companies, roles, and durations at product companies doing ML work. Career description text analysis for shipped systems. | **Fact (JD):** *"if their career history shows they built a recommendation system at a product company, they're a fit."* |
| Behavioral signal modifier | **20%** | Multiplicative modifier based on recruiter_response_rate, last_active_date, open_to_work_flag | **Fact (JD + signals doc):** Both documents confirm behavioral signals should modify scores. |
| Education relevance | **5%** | Degree relevance + institution tier | **Inference:** JD mentions education only indirectly. Low priority. |
| Internal consistency | **10%** | Penalty for suspicious patterns | **Inference:** Helps naturally demote impossible profiles. |

### Why this strategy may maximize NDCG@10 and NDCG@50

> **IMPLEMENTATION HYPOTHESIS** — these are predictions, not confirmed facts.

1. **NDCG@10 (50% weight):** Title_Relevance (25%) + Skill_Relevance (20%) + Career_Relevance (20%) = **65% weight on profile-match components** that directly identify genuine AI/ML engineers. The Behavioral_Modifier ensures top 10 aren't just "paper perfect" but are actually available and responsive.

2. **NDCG@50 (30% weight):** Broader weights (Experience_Fit, Education) help differentiate mid-tier candidates. The Consistency check ensures impossible profiles fall below rank 50.

3. **Score normalization:** Final scores normalized to [0, 1] range, guaranteed non-increasing per spec requirement.

### Career history analysis — critical detail

The JD emphasizes that **career description text** is the strongest signal of genuine AI/ML experience:

> *"A Tier 5 candidate may not use the words 'RAG' or 'Pinecone' in their profile, but if their career history shows they built a recommendation system at a product company, they're a fit."*

This means our career history analysis must:
- Parse career descriptions for evidence of **shipped ML systems** (keywords: deployed, production, ranking, retrieval, recommendation, search, embedding, vector, ML pipeline)
- Identify **product companies** vs. consulting firms (cross-reference company names)
- Weight **recent, relevant roles** higher than distant, unrelated roles
- Apply **duration weighting** — longer in relevant roles = stronger signal

### Sample submission reasoning analysis

> **Evidence source:** `sample_submission.csv`

The sample submission demonstrates what Stage 4 expects for the reasoning column:

| Attribute | Sample Pattern | Implication |
|-----------|---------------|-------------|
| **Length** | 50-80 characters per entry | Concise. Not verbose. |
| **Tone** | Factual, data-driven | *"Content Writer with 8.3 yrs; 8 AI core skills; response rate 0.72."* |
| **Structure** | [Role] + [years] + [key stats] + [notable signal] | Three-part structure: identity, qualification, behavioral signal |
| **Evidence** | Mentions specific numbers from profile | Years, skill count, response rate all drawn from actual data |
| **Variety** | 100/100 unique reasoning strings | **No templates** — each entry is specific to the candidate |
| **Specificity** | Mentions exact values (not ranges) | "8.3 yrs" not "~8 years" |

**Key takeaway for reasoning generation:** Short, specific, data-driven, unique per candidate. Avoid templates, avoid hallucination.

---

## 8. Risk Analysis

### High-risk items

| Risk | Likelihood | Impact | Mitigation | Evidence |
|------|-----------|--------|------------|----------|
| Honeypots in top 10 | Medium | Critical (DQ) | Build internal consistency checks; test against known patterns; verify output before submission | **Fact (spec)** |
| Cannot reproduce under 5 min | Medium | Critical (DQ) | Profile runtime early; optimize bottlenecks; use streaming JSONL | **Fact (spec)** |
| Reasoning fails Stage 4 review | Medium | High | Generate specific, profile-aware reasoning; avoid templates; check for hallucination | **Fact (spec)** |
| Hidden ground truth doesn't match assumptions | Medium | High | Build modular scoring that can be reweighted; cross-validate multiple configurations | **Inference** |
| Memory exceeds 16GB | Low | Critical (DQ) | Stream JSONL line-by-line; release data between stages | **Fact (spec)** |

### Medium-risk items

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Title-based scoring too aggressive | Medium | Medium | Use title as strong signal but not sole signal; career description analysis can catch candidates with non-ML titles who have relevant experience |
| Behavioral modifier too aggressive | Medium | Medium | Conservative modifier range; don't zero out candidates on signals alone |
| Overlooked non-obvious good candidate | Medium | Medium | Career description analysis should catch relevant experience even with non-matching title |

### Low-risk items

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Auto-rejection (format errors) | Low | Critical | Validate locally before every submission |
| Three-submission cap | Low | High | Thorough local testing and cross-validation before any submission |

---

## Appendix: Dataset Statistics

> **Source:** Computed from `candidates.jsonl` (100,000 records)

| Metric | Value |
|--------|-------|
| Total candidates | 100,000 |
| Unique job titles | 47 (see docs/PHASE_1_AUDIT.md for full list) |
| Tech titles | 42,542 (42.5%) |
| AI/ML titles | 1,126 (1.1%) |
| India-based | 75,113 (75.1%) |
| Open to work | 35,339 (35.3%) |
| Has GitHub linked (github_activity_score >= 0) | 35,363 (35.4%) |
| Consulting-only career | 7,034 (7.0%) |
| Salary inverted (min > max) | 18,865 (18.9%) — **data anomaly, NOT honeypot** |
| 5+ expert-level skills | 167 (0.17%) |
| Estimated honeypots | ~80 (per spec, 0.08%) |
| Senior AI Engineer (exact title) | 4 |
| Candidates with ranking/retrieval/recommendation in career descriptions | 21,702 (21.7%) |
| Candidates in preferred cities (Pune/Noida/Hyderabad/Mumbai/Delhi NCR) | 20,956 (20.9%) |

### Experience Distribution

| Band | Count |
|------|-------|
| 0-2 years | 7,470 |
| 2-5 years | 26,400 |
| 5-8 years | 25,896 |
| 8-12 years | 25,363 |
| 12+ years | 14,871 |

### Country Distribution

| Country | Count |
|---------|-------|
| India | 75,113 |
| USA | 9,978 |
| Australia | 2,579 |
| Canada | 2,506 |
| UK | 2,472 |
| Germany | 2,469 |
| Singapore | 2,453 |
| UAE | 2,430 |

---

*Analysis performed June 19, 2026 — Phase 1 of 10-phase roadmap.  
Correction pass applied per self-audit (see docs/PHASE_1_AUDIT.md).  
All speculative elements marked as 🔮 SPECULATION or ⚠️ IMPLEMENTATION HYPOTHESIS.*
