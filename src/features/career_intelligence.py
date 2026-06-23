"""Career Intelligence Engine — career-pattern detection and scoring.

Analyzes candidate career history, skills, and profile fields to detect
signals aligned with the target job description (Senior AI Engineer,
Founding Team). Produces both positive signals (relevant experience)
and penalties (misaligned career patterns).

All features are computed via keyword/pattern matching on structured
candidate data. No new ML models, no network calls, CPU-only.

Features produced (20 total):
    Career Intelligence Signals:
        product_company_score: Product company experience presence
        startup_experience_score: Startup/early-stage experience
        engineering_depth_score: Software engineering depth
        relevant_tech_experience_score: Relevant technical experience
        career_progression_score: Career progression quality
        skill_relevance_score: Skill relevance to target role
        ranking_experience_score: Ranking systems experience
        retrieval_experience_score: Retrieval systems experience
        recommendation_experience_score: Recommendation systems experience
        search_experience_score: Search systems experience
        embeddings_experience_score: Embeddings experience
        vector_db_experience_score: Vector database experience
        production_ml_score: Production ML deployment experience
        evaluation_framework_score: Evaluation framework experience
        python_engineering_score: Python/engineering experience
        nlp_ir_experience_score: NLP/IR experience

    Penalty Signals:
        consulting_penalty: Consulting-only career penalty (0 = no penalty)
        research_penalty: Pure research career penalty (0 = no penalty)
        keyword_stuffing_penalty: Keyword stuffing penalty (0 = no penalty)
        title_chasing_penalty: Title-chasing behavior penalty (0 = no penalty)
"""

import logging
import re
from typing import Optional

from src.features.base import BaseFeatureExtractor
from src.parser.candidate_parser import Candidate, CareerEntry

logger = logging.getLogger("redrob-ranker")


# ============================================================================
# Keyword registries — organized categories for detection
# ============================================================================

# --- Ranking & Retrieval Keywords ---

RANKING_KEYWORDS = [
    "ranking", "ranker", "ranked", "reranking", "re-ranking", "reranker",
    "learning to rank", "ltr", "ndcg", "mrr", "map",
    "candidate ranking", "search ranking", "relevance ranking",
    "score", "scoring engine", "scoring model",
]

RETRIEVAL_KEYWORDS = [
    "retrieval", "retriever", "hybrid retrieval", "dense retrieval",
    "sparse retrieval", "information retrieval", "ir system",
    "embedding-based retrieval", "neural retrieval",
    "bm25", "tf-idf", "vector search", "semantic search",
]

RECOMMENDATION_KEYWORDS = [
    "recommendation", "recommender", "recommendation system",
    "recommendation engine", "collaborative filtering",
    "content-based filtering", "recommendation model",
    "personalization", "personalized recommendations",
]

SEARCH_KEYWORDS = [
    "search engine", "search system", "search infrastructure",
    "search relevance", "elasticsearch", "opensearch",
    "full-text search", "hybrid search", "semantic search",
    "search pipeline", "query understanding",
]

EMBEDDINGS_KEYWORDS = [
    "embedding", "sentence-transformers", "openai embedding",
    "bge embedding", "e5 embedding", "bert embedding",
    "embedding-based", "embedding model", "embedding index",
    "dense embedding", "vector embedding",
]

VECTOR_DB_KEYWORDS = [
    "pinecone", "weaviate", "qdrant", "milvus", "faiss",
    "vector database", "vector store", "vector index",
    "hybrid search", "ann index", "approximate nearest neighbor",
    "similarity search", "vector search",
]

PRODUCTION_ML_KEYWORDS = [
    "production", "deployed", "shipped", "launched",
    "a/b test", "ab test", "ab testing",
    "evaluation framework", "offline evaluation", "online evaluation",
    "inference", "model serving", "ml pipeline",
    "real users", "at scale", "production system",
    "monitoring", "model monitoring", "drift detection",
]

EVALUATION_KEYWORDS = [
    "ndcg", "mrr", "map", "precision", "recall", "f1",
    "evaluation framework", "evaluation pipeline",
    "offline benchmark", "online experiment",
    "a/b test", "ab test", "a/b testing",
    "metrics", "evaluation metric", "ranking metric",
    "judgment list", "relevance judgments", "ground truth",
]

PYTHON_ENGINEERING_KEYWORDS = [
    "python", "software engineer", "software development",
    "backend engineer", "backend development",
    "api design", "system design", "distributed system",
    "microservice", "rest api", "pipeline",
    "production code", "code quality", "code review",
]

NLP_IR_KEYWORDS = [
    "nlp", "natural language processing", "information retrieval",
    "text mining", "text classification", "named entity recognition",
    "sentiment analysis", "question answering", "text understanding",
    "language model", "llm", "transformer", "bert", "gpt",
    "tokenization", "text processing",
]

# --- Company/Industry Classification ---

PRODUCT_COMPANY_INDICATORS = [
    # Product companies known for internal ML/AI products
    "google", "meta", "facebook", "amazon", "apple", "microsoft",
    "netflix", "uber", "lyft", "airbnb", "linkedin", "twitter",
    "pinterest", "spotify", "stripe", "square", "shopify",
    "salesforce", "oracle", "adobe", "intuit", "palantir",
    "databricks", "snowflake", "confluent", "elastic",
    "mongodb", "redis", "hashicorp", "github", "gitlab",
    # Indian product companies
    "flipkart", "myntra", "swiggy", "zomato", "ola",
    "paytm", "phonepe", "razorpay", "cred", "groww",
    "zerodha", "urban company", "oyorooms", "makemytrip",
    "naukri", "redrob", "byju", "unacademy",
    # AI/ML product companies
    "openai", "anthropic", "cohere", "hugging face",
    "scale ai", "labelbox", "snorkel ai", "algorithmia",
]

CONSULTING_FIRMS = [
    "tcs", "infosys", "wipro", "accenture", "cognizant",
    "capgemini", "hcl", "tech mahindra", "ltimindtree",
    "ibm services", "deloitte", "pwc", "ey", "kpmg",
    "genpact", "wipro digital", "mindtree", "mphasis",
    "hexaware", "persistent", "cyient", "zensar",
]

STARTUP_INDICATORS = [
    "startup", "early-stage", "seed stage", "series a",
    "series b", "founding team", "founding engineer",
    "early employee", "first engineer",
    "fast-growing", "hypergrowth",
]

TITLE_CHASING_PATTERNS = [
    r"senior\s+\w+\s+engineer",
    r"staff\s+\w+\s+engineer",
    r"principal\s+\w+\s+engineer",
    r"lead\s+\w+\s+engineer",
    r"principal\s+\w+\s+scientist",
    r"senior\s+\w+\s+scientist",
    r"head of",
    r"director of",
    r"vp of",
    r"chief \w+ officer",
]


class CareerIntelligence(BaseFeatureExtractor):
    """Feature extractor computing career intelligence signals from
    candidate profile data.

    Analyzes career history descriptions, skills, headline, and summary
    to detect signals relevant to the target JD. Uses keyword/pattern
    matching — no ML models, no network calls, CPU only.

    Features are scored 0.0 to 1.0 where higher = stronger signal.
    Penalty features are scored where 0.0 = no penalty, 1.0 = maximum penalty.

    Example:
        ci = CareerIntelligence()
        features = ci.extract(candidate)
    """

    features = [
        # Career Intelligence Signals (16)
        "product_company_score",
        "startup_experience_score",
        "engineering_depth_score",
        "relevant_tech_experience_score",
        "career_progression_score",
        "skill_relevance_score",
        "ranking_experience_score",
        "retrieval_experience_score",
        "recommendation_experience_score",
        "search_experience_score",
        "embeddings_experience_score",
        "vector_db_experience_score",
        "production_ml_score",
        "evaluation_framework_score",
        "python_engineering_score",
        "nlp_ir_experience_score",
        # Penalty Signals (4)
        "consulting_penalty",
        "research_penalty",
        "keyword_stuffing_penalty",
        "title_chasing_penalty",
    ]

    # ==================================================================
    # BaseFeatureExtractor interface
    # ==================================================================

    @property
    def name(self) -> str:
        return "career_intelligence"

    @property
    def description(self) -> str:
        return (
            "Career intelligence scoring: detects ranking/retrieval/embedding/search "
            "experience, product company and startup background, production ML deployment, "
            "evaluation framework expertise, and applies penalties for consulting-only, "
            "research-only, keyword stuffing, and title-chasing career patterns."
        )

    def extract(self, candidate: Candidate) -> dict[str, float]:
        """Extract all Career Intelligence features for a single candidate.

        Args:
            candidate: Parsed Candidate object.

        Returns:
            Dict of 20 feature_name -> score (0.0 to 1.0).
        """
        # Build text corpora from candidate fields
        career_text = self._build_career_text(candidate)
        all_career_text = career_text  # Keep reference for penalty detection
        headline = candidate.profile.headline or ""
        summary = candidate.profile.summary or ""
        combined = f"{headline} {summary} {career_text}".lower()

        # Extract skills info
        skill_names = [s.name.lower() for s in candidate.skills]
        skill_proficiencies = {s.name.lower(): s.proficiency for s in candidate.skills}
        skill_durations = {s.name.lower(): s.duration_months for s in candidate.skills if s.duration_months is not None}

        # Companies from career history
        companies = [ce.company.lower() for ce in candidate.career_history if ce.company]
        industries = [ce.industry.lower() for ce in candidate.career_history if ce.industry]
        titles = [ce.title.lower() for ce in candidate.career_history if ce.title]

        # Duration info
        career_entries = candidate.career_history
        total_years = candidate.profile.years_of_experience or 0.0

        # ==============================================================
        # Career Intelligence Signal Scores
        # ==============================================================

        product_company = self._score_product_company(companies)
        startup_exp = self._score_startup_experience(companies, titles, career_text)
        engineering_depth = self._score_engineering_depth(titles, career_text, skill_names)

        # Relevant tech experience = weighted combo of domain signals
        ranking_exp = self._keyword_match_score(career_text, RANKING_KEYWORDS)
        retrieval_exp = self._keyword_match_score(career_text, RETRIEVAL_KEYWORDS)
        recommendation_exp = self._keyword_match_score(career_text, RECOMMENDATION_KEYWORDS)
        search_exp = self._keyword_match_score(career_text, SEARCH_KEYWORDS)
        embeddings_exp = self._keyword_match_score(career_text, EMBEDDINGS_KEYWORDS)
        vector_db_exp = self._keyword_match_score(career_text, VECTOR_DB_KEYWORDS)
        production_ml = self._keyword_match_score(career_text, PRODUCTION_ML_KEYWORDS)
        eval_framework = self._keyword_match_score(career_text, EVALUATION_KEYWORDS)
        python_eng = self._keyword_match_score(career_text + headline, PYTHON_ENGINEERING_KEYWORDS)
        nlp_ir = self._keyword_match_score(career_text + summary + headline, NLP_IR_KEYWORDS)

        # Relevant tech experience = combined domain signal
        tech_signals = [ranking_exp, retrieval_exp, recommendation_exp, search_exp,
                        embeddings_exp, vector_db_exp, production_ml]
        relevant_tech = sum(tech_signals) / len(tech_signals) if tech_signals else 0.0

        # Career progression = stability + growth + increasing responsibility
        career_prog = self._score_career_progression(career_entries, total_years)

        # Skill relevance = fraction of JD-relevant skills
        skill_relevance = self._score_skill_relevance(skill_names, skill_proficiencies)

        # ==============================================================
        # Penalty Scores
        # ==============================================================

        consulting = self._score_consulting_penalty(companies, total_years, product_company)
        research = self._score_research_penalty(career_text, titles, production_ml)
        keyword_stuffing = self._score_keyword_stuffing_penalty(skill_names, skill_durations, skill_proficiencies)
        title_chasing = self._score_title_chasing_penalty(titles, total_years, career_entries)

        return {
            # Career Intelligence
            "product_company_score": product_company,
            "startup_experience_score": startup_exp,
            "engineering_depth_score": engineering_depth,
            "relevant_tech_experience_score": relevant_tech,
            "career_progression_score": career_prog,
            "skill_relevance_score": skill_relevance,
            "ranking_experience_score": ranking_exp,
            "retrieval_experience_score": retrieval_exp,
            "recommendation_experience_score": recommendation_exp,
            "search_experience_score": search_exp,
            "embeddings_experience_score": embeddings_exp,
            "vector_db_experience_score": vector_db_exp,
            "production_ml_score": production_ml,
            "evaluation_framework_score": eval_framework,
            "python_engineering_score": python_eng,
            "nlp_ir_experience_score": nlp_ir,
            # Penalties
            "consulting_penalty": consulting,
            "research_penalty": research,
            "keyword_stuffing_penalty": keyword_stuffing,
            "title_chasing_penalty": title_chasing,
        }

    # ==================================================================
    # Scoring methods
    # ==================================================================

    def _keyword_match_score(self, text: str, keywords: list[str]) -> float:
        """Score a text against a keyword list based on match ratio.

        Returns 0.0-1.0 based on how many keywords match.
        """
        if not text or not keywords:
            return 0.0
        text_lower = text.lower()
        matches = sum(1 for kw in keywords if kw.lower() in text_lower)
        # Score scales with match count but saturates
        ratio = matches / len(keywords)
        # Amplify: 10% keyword match = ~0.5, 50%+ = 1.0
        score = min(1.0, ratio * 5.0)
        return score

    def _score_product_company(self, companies: list[str]) -> float:
        """Score based on presence of product company names in career history."""
        if not companies:
            return 0.0
        matched = sum(1 for c in companies if any(pc in c for pc in PRODUCT_COMPANY_INDICATORS))
        # Score based on fraction of roles at product companies
        score = matched / len(companies)
        return score

    def _score_startup_experience(self, companies: list[str], titles: list[str],
                                   career_text: str) -> float:
        """Score based on startup indicators in career history."""
        score = 0.0
        # Check company names and titles for startup indicators
        all_text = " ".join(companies + titles).lower()
        score += self._keyword_match_score(all_text, STARTUP_INDICATORS)
        # Check career text
        score += self._keyword_match_score(career_text, STARTUP_INDICATORS)
        # Average
        return min(1.0, score / 2.0)

    def _score_engineering_depth(self, titles: list[str], career_text: str,
                                  skill_names: list[str]) -> float:
        """Score based on engineering depth signals."""
        score = 0.0
        # Engineering titles
        eng_title_kw = ["engineer", "developer", "architect", "sde", "software"]
        title_matches = sum(1 for t in titles for kw in eng_title_kw if kw in t)
        score += min(1.0, title_matches / 3.0)

        # Engineering skills
        eng_skill_kw = ["python", "java", "cpp", "c++", "scala", "go", "rust",
                       "sql", "nosql", "aws", "gcp", "azure", "docker", "kubernetes",
                       "system design", "distributed systems", "microservices"]
        skill_matches = sum(1 for s in skill_names for kw in eng_skill_kw if kw in s)
        score += min(1.0, skill_matches / 5.0)

        return min(1.0, score / 2.0)

    def _score_career_progression(self, entries: list[CareerEntry],
                                   total_years: float) -> float:
        """Score career progression quality."""
        if not entries or total_years <= 0:
            return 0.0

        score = 0.0

        # Factor 1: Average tenure (stability)
        if len(entries) > 0:
            avg_tenure = total_years * 12 / len(entries)  # in months
            if avg_tenure >= 24:  # 2+ years average = stable
                score += 0.4
            elif avg_tenure >= 12:
                score += 0.2

        # Factor 2: Multiple roles (career growth)
        if len(entries) >= 3:
            score += 0.3
        elif len(entries) >= 2:
            score += 0.15

        # Factor 3: Current role is recent (active career)
        if entries and any(e.is_current for e in entries):
            score += 0.3

        return min(1.0, score)

    def _score_skill_relevance(self, skill_names: list[str],
                                skill_proficiencies: dict[str, str]) -> float:
        """Score skill relevance to the target AI Engineer role."""
        if not skill_names:
            return 0.0

        # Core AI/ML skills that match the JD
        core_skills = [
            "machine learning", "deep learning", "nlp", "natural language processing",
            "python", "pytorch", "tensorflow", "transformers", "bert",
            "embedding", "sentence transformers", "retrieval", "ranking",
            "vector database", "elasticsearch", "faiss", "pinecone",
            "llm", "large language model", "fine tuning", "rag",
            "a/b testing", "evaluation", "ndcg", "mrr",
            "data science", "mlops", "ml pipeline",
        ]

        # Check how many core skills are present
        matched = sum(1 for s in skill_names for cs in core_skills if cs in s)
        base_score = min(1.0, matched / 8.0)

        # Boost for advanced/expert proficiency
        proficiency_boost = 0.0
        for name, prof in skill_proficiencies.items():
            if prof in ("advanced", "expert"):
                for cs in core_skills:
                    if cs in name:
                        proficiency_boost += 0.05
                        break

        return min(1.0, base_score + proficiency_boost)

    def _score_consulting_penalty(self, companies: list[str], total_years: float,
                                   product_company_score: float) -> float:
        """Score consulting-only career penalty.

        0.0 = no penalty (has product company experience).
        1.0 = maximum penalty (all roles at consulting firms, no product experience).
        """
        if not companies or total_years <= 0:
            return 0.0

        # Count consulting-only roles
        consulting_roles = sum(1 for c in companies
                               for cf in CONSULTING_FIRMS if cf in c)

        if consulting_roles == 0:
            return 0.0

        consulting_ratio = consulting_roles / len(companies)

        # If they have product company experience, reduce penalty
        if product_company_score > 0.5:
            consulting_ratio *= 0.3  # 70% penalty reduction

        # Only penalize if most career is at consulting firms
        if consulting_ratio < 0.5:
            return 0.0

        return min(1.0, consulting_ratio)

    def _score_research_penalty(self, career_text: str, titles: list[str],
                                 production_ml_score: float) -> float:
        """Score pure research career penalty.

        Penalizes candidates whose career is research-focused
        without production deployment evidence.
        """
        # Research indicators
        research_kw = [
            "research", "researcher", "research scientist",
            "academic", "university", "lab", "laboratory",
            "phd", "postdoc", "post-doc",
        ]

        research_score = self._keyword_match_score(career_text, research_kw)

        # Check titles for research-only patterns (exclude data scientist which is applied ML)
        # Only pure research titles (no "data" prefix) count
        pure_research_titles = sum(1 for t in titles
                                   if ("research" in t and "data" not in t)
                                   or "postdoc" in t or "phd" in t)
        title_ratio = pure_research_titles / len(titles) if titles else 0

        combined_research = max(research_score, title_ratio)

        # If they have high production ML score, reduce research penalty
        if production_ml_score >= 0.4:
            return max(0.0, combined_research * 0.2)

        # Moderate production ML -> partial penalty
        if production_ml_score >= 0.2:
            return max(0.0, combined_research * 0.5)

        return combined_research

    def _score_keyword_stuffing_penalty(self, skill_names: list[str],
                                         skill_durations: dict[str, int],
                                         skill_proficiencies: dict[str, str]) -> float:
        """Score keyword stuffing penalty.

        Detects candidates with many expert-level skills but zero
        duration months — the pattern described in the honeypot spec.
        """
        if not skill_names:
            return 0.0

        # Count skills with 0 duration but high proficiency
        suspicious = 0
        for name in skill_names:
            duration = skill_durations.get(name, 0)
            proficiency = skill_proficiencies.get(name, "beginner")
            if duration == 0 and proficiency in ("advanced", "expert"):
                suspicious += 1

        # If more than 20% of skills are suspicious
        if len(skill_names) == 0:
            return 0.0
        suspicious_ratio = suspicious / len(skill_names)

        if suspicious_ratio <= 0.1:
            return 0.0
        if suspicious_ratio <= 0.25:
            return 0.3
        if suspicious_ratio <= 0.5:
            return 0.6
        return 1.0

    def _score_title_chasing_penalty(self, titles: list[str], total_years: float,
                                      entries: list[CareerEntry]) -> float:
        """Score title-chasing behavior penalty.

        Detects candidates with frequent title inflation and
        short average tenures.
        """
        if len(titles) < 2 or total_years <= 0:
            return 0.0

        score = 0.0

        # Factor 1: Average tenure < 18 months
        avg_tenure_months = total_years * 12 / len(titles)
        if avg_tenure_months < 12:
            score += 0.5
        elif avg_tenure_months < 18:
            score += 0.3

        # Factor 2: Patterns of title inflation
        senior_titles = sum(1 for t in titles
                           for pat in TITLE_CHASING_PATTERNS
                           if re.search(pat, t))
        if senior_titles > 0 and avg_tenure_months < 18:
            score += 0.3

        # Factor 3: Very short stints (< 1 year, non-current)
        short_stints = sum(1 for e in entries
                          if not e.is_current and e.duration_months < 12)
        if len(entries) > 0:
            short_ratio = short_stints / len(entries)
            if short_ratio > 0.3:
                score += 0.2

        return min(1.0, score)

    # ==================================================================
    # Text builders
    # ==================================================================

    @staticmethod
    def _build_career_text(candidate: Candidate) -> str:
        """Build career history text from all career entries."""
        parts = []
        for ce in candidate.career_history:
            parts.append(ce.title or "")
            parts.append(ce.company or "")
            parts.append(ce.description or "")
            parts.append(ce.industry or "")
        return " ".join(p for p in parts if p)

    def __repr__(self) -> str:
        return (
            f"CareerIntelligence(name='{self.name}', "
            f"features={len(self.features)})"
        )
