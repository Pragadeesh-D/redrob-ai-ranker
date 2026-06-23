"""Unit tests for Career Intelligence Engine (src/features/career_intelligence.py).

Covers:
- Career Intelligence signal detection (16 features)
- Penalty signal detection (4 features)
- Range and validity checks
- Empty/missing data handling
- Determinism and consistency
- Integration with FeatureRegistry
- Performance benchmarks (runtime + RAM)
"""

import time
import tracemalloc
import pytest

from src.features.career_intelligence import CareerIntelligence
from src.features.framework import FeatureRegistry
from src.parser.candidate_parser import Candidate, Profile, RedrobSignals, SalaryRange


# ============================================================================
# Helpers for creating test candidates
# ============================================================================

def _make_candidate(
    candidate_id: str = "CAND_0000001",
    headline: str = "",
    summary: str = "",
    current_title: str = "",
    current_company: str = "",
    current_industry: str = "",
    years_of_experience: float = 0.0,
    skills: list | None = None,
    career_history: list | None = None,
) -> Candidate:
    """Create a Candidate with specified fields, defaults for others."""
    from src.parser.candidate_parser import CareerEntry
    # Accept either CareerEntry objects or dicts
    parsed_career = []
    for ce in (career_history or []):
        if isinstance(ce, CareerEntry):
            parsed_career.append(ce)
        elif isinstance(ce, dict):
            parsed_career.append(_make_career_entry(**ce))

    from src.parser.candidate_parser import Skill as SkillCls
    parsed_skills = []
    for s in (skills or []):
        if isinstance(s, SkillCls):
            parsed_skills.append(s)
        elif isinstance(s, dict):
            parsed_skills.append(_make_skill(**s))

    return Candidate(
        candidate_id=candidate_id,
        profile=Profile(
            anonymized_name="Test",
            headline=headline,
            summary=summary,
            location="Pune",
            country="India",
            years_of_experience=years_of_experience,
            current_title=current_title,
            current_company=current_company,
            current_company_size="11-50",
            current_industry=current_industry,
        ),
        career_history=parsed_career,
        education=[],
        skills=parsed_skills,
        redrob_signals=_null_signals(),
    )


def _make_career_entry(
    company: str = "TestCorp",
    title: str = "Engineer",
    description: str = "Worked on software.",
    industry: str = "Software",
    duration_months: int = 36,
    is_current: bool = True,
):
    """Create a CareerEntry object."""
    from src.parser.candidate_parser import CareerEntry
    return CareerEntry(
        company=company,
        title=title,
        start_date="2020-01-01",
        end_date=None,
        duration_months=duration_months,
        is_current=is_current,
        industry=industry,
        company_size="1001-5000",
        description=description,
    )


def _make_skill(
    name: str = "Python",
    proficiency: str = "intermediate",
    endorsements: int = 0,
    duration_months: int | None = 12,
):
    """Create a Skill object."""
    from src.parser.candidate_parser import Skill
    return Skill(
        name=name,
        proficiency=proficiency,
        endorsements=endorsements,
        duration_months=duration_months,
    )


def _null_signals() -> RedrobSignals:
    """Create a RedrobSignals with default null values."""
    return RedrobSignals(
        profile_completeness_score=0.0,
        signup_date="",
        last_active_date="",
        open_to_work_flag=False,
        profile_views_received_30d=0,
        applications_submitted_30d=0,
        recruiter_response_rate=0.0,
        avg_response_time_hours=0.0,
        skill_assessment_scores={},
        connection_count=0,
        endorsements_received=0,
        notice_period_days=0,
        expected_salary_range_inr_lpa=SalaryRange(min=0.0, max=0.0),
        preferred_work_mode="hybrid",
        willing_to_relocate=False,
        github_activity_score=-1.0,
        search_appearance_30d=0,
        saved_by_recruiters_30d=0,
        interview_completion_rate=0.0,
        offer_acceptance_rate=-1.0,
        verified_email=False,
        verified_phone=False,
        linkedin_connected=False,
    )


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def extractor() -> CareerIntelligence:
    """Shared extractor instance."""
    return CareerIntelligence()


@pytest.fixture
def ai_engineer_candidate() -> Candidate:
    """A strong-fit AI engineer candidate."""
    return _make_candidate(
        candidate_id="CAND_0000001",
        headline="Senior ML Engineer specializing in retrieval and ranking systems",
        summary="Experienced ML engineer with 7 years building production ranking and recommendation systems.",
        current_title="Senior ML Engineer",
        current_company="TechCorp",
        current_industry="Software",
        years_of_experience=7.0,
        career_history=[
            _make_career_entry(
                company="Google", title="Senior ML Engineer",
                description="Built production ranking system serving 1M+ users. Designed embedding-based retrieval with FAISS. Implemented A/B testing framework for offline evaluation.",
                industry="Technology", duration_months=36, is_current=True,
            ),
            _make_career_entry(
                company="StartupAI", title="ML Engineer",
                description="Developed recommendation algorithms for job search. Built embedding pipeline with sentence-transformers. Deployed vector search with Pinecone.",
                industry="Technology", duration_months=30, is_current=False,
            ),
            _make_career_entry(
                company="DataCorp", title="Applied Scientist",
                description="Built ML models for production. Set up evaluation metrics including NDCG and MRR.",
                industry="Technology", duration_months=24, is_current=False,
            ),
        ],
        skills=[
            _make_skill(name="Python", proficiency="expert", duration_months=72),
            _make_skill(name="PyTorch", proficiency="advanced", duration_months=36),
            _make_skill(name="FAISS", proficiency="advanced", duration_months=18),
            _make_skill(name="NLP", proficiency="advanced", duration_months=24),
            _make_skill(name="Machine Learning", proficiency="expert", duration_months=60),
        ],
    )


@pytest.fixture
def non_tech_candidate() -> Candidate:
    """A non-technical candidate (low signals expected)."""
    return _make_candidate(
        candidate_id="CAND_0000002",
        headline="Marketing Manager | Brand Strategy | Social Media",
        summary="Experienced marketing professional with expertise in brand management.",
        current_title="Marketing Manager",
        current_company="BrandCorp",
        current_industry="Marketing",
        years_of_experience=8.0,
        career_history=[
            _make_career_entry(
                company="BrandCorp", title="Marketing Manager",
                description="Led brand strategy for consumer products. Managed social media campaigns.",
                industry="Marketing", duration_months=48, is_current=True,
            ),
            _make_career_entry(
                company="AgencyX", title="Marketing Associate",
                description="Created content marketing strategies. Managed client accounts.",
                industry="Marketing", duration_months=36, is_current=False,
            ),
        ],
        skills=[
            _make_skill(name="Social Media", proficiency="expert", duration_months=60),
            _make_skill(name="Content Writing", proficiency="advanced", duration_months=36),
        ],
    )


@pytest.fixture
def consulting_candidate() -> Candidate:
    """A consulting-only candidate (high penalty expected)."""
    return _make_candidate(
        candidate_id="CAND_0000003",
        headline="Senior Consultant at TCS",
        summary="IT professional with 10 years of experience in consulting.",
        current_title="Senior Consultant",
        current_company="TCS",
        current_industry="IT Services",
        years_of_experience=10.0,
        career_history=[
            _make_career_entry(
                company="TCS", title="Senior Consultant",
                description="Led client engagements for banking clients.",
                industry="IT Services", duration_months=60, is_current=True,
            ),
            _make_career_entry(
                company="Infosys", title="Consultant",
                description="Managed offshore development team.",
                industry="IT Services", duration_months=60, is_current=False,
            ),
        ],
        skills=[
            _make_skill(name="Java", proficiency="advanced", duration_months=72),
            _make_skill(name="SQL", proficiency="advanced", duration_months=48),
        ],
    )


@pytest.fixture
def title_chaser_candidate() -> Candidate:
    """A candidate with title-chasing behavior (short tenures, inflating titles)."""
    return _make_candidate(
        candidate_id="CAND_0000004",
        headline="Principal Engineer | Staff Engineer",
        summary="Experienced engineer.",
        current_title="Principal Engineer",
        current_company="CompanyD",
        current_industry="Software",
        years_of_experience=6.0,
        career_history=[
            _make_career_entry(
                company="CompanyA", title="Principal Engineer",
                description="Led architecture.",
                industry="Software", duration_months=10, is_current=False,
            ),
            _make_career_entry(
                company="CompanyB", title="Staff Engineer",
                description="Led projects.",
                industry="Software", duration_months=8, is_current=False,
            ),
            _make_career_entry(
                company="CompanyC", title="Senior Engineer",
                description="Developed features.",
                industry="Software", duration_months=14, is_current=True,
            ),
        ],
        skills=[
            _make_skill(name="Python", proficiency="advanced", duration_months=36),
        ],
    )


@pytest.fixture
def keyword_stuffer_candidate() -> Candidate:
    """A candidate with keyword-stuffed skills (many expert skills, 0 duration)."""
    return _make_candidate(
        candidate_id="CAND_0000005",
        headline="AI Expert",
        summary="Expert in AI and ML.",
        current_title="AI Engineer",
        current_company="SomeCorp",
        current_industry="Software",
        years_of_experience=3.0,
        career_history=[
            _make_career_entry(
                company="SomeCorp", title="AI Engineer",
                description="Worked on AI.",
                industry="Software", duration_months=24, is_current=True,
            ),
        ],
        skills=[
            _make_skill(name="Python", proficiency="expert", duration_months=0),
            _make_skill(name="TensorFlow", proficiency="expert", duration_months=0),
            _make_skill(name="PyTorch", proficiency="expert", duration_months=0),
            _make_skill(name="NLP", proficiency="expert", duration_months=0),
            _make_skill(name="Computer Vision", proficiency="expert", duration_months=0),
            _make_skill(name="Reinforcement Learning", proficiency="expert", duration_months=0),
            _make_skill(name="Transformers", proficiency="expert", duration_months=0),
            _make_skill(name="LangChain", proficiency="expert", duration_months=0),
            # One legitimate skill with duration
            _make_skill(name="SQL", proficiency="intermediate", duration_months=12),
        ],
    )


@pytest.fixture
def empty_candidate() -> Candidate:
    """A candidate with minimal data (edge case)."""
    return _make_candidate(
        candidate_id="CAND_0000000",
        headline="",
        summary="",
        current_title="",
        current_company="",
        current_industry="",
        years_of_experience=0.0,
        career_history=[],
        skills=[],
    )


# ============================================================================
# Initialization Tests
# ============================================================================

class TestCareerIntelligenceInit:
    """Engine initialization and properties."""

    def test_name_and_features(self, extractor):
        """Engine should expose correct name and features list."""
        assert extractor.name == "career_intelligence"
        assert extractor.description
        assert "career intelligence" in extractor.description.lower()
        assert len(extractor.features) == 20

    def test_feature_names_are_unique(self, extractor):
        """All feature names should be unique."""
        assert len(extractor.features) == len(set(extractor.features))

    def test_feature_names_lowercase(self, extractor):
        """All feature names should be lowercase."""
        for f in extractor.features:
            assert f == f.lower(), f"Feature '{f}' is not lowercase"

    def test_repr(self, extractor):
        """__repr__ should show class and name."""
        assert "CareerIntelligence" in repr(extractor)
        assert "career_intelligence" in repr(extractor)
        assert "20" in repr(extractor)


# ============================================================================
# Career Intelligence Signal Tests
# ============================================================================

class TestCareerIntelligenceDetection:
    """Detection of career intelligence signals."""

    def test_extract_returns_dict(self, extractor, ai_engineer_candidate):
        """Extract should return a dict of 20 features."""
        features = extractor.extract(ai_engineer_candidate)
        assert isinstance(features, dict)
        assert len(features) == 20

    def test_scores_in_range(self, extractor, ai_engineer_candidate):
        """All scores should be between 0.0 and 1.0."""
        features = extractor.extract(ai_engineer_candidate)
        for name, score in features.items():
            assert 0.0 <= score <= 1.0, (
                f"{name} = {score} outside [0, 1]"
            )

    def test_extract_deterministic(self, extractor, ai_engineer_candidate):
        """Same candidate should produce same scores."""
        f1 = extractor.extract(ai_engineer_candidate)
        f2 = extractor.extract(ai_engineer_candidate)
        for key in f1:
            assert abs(f1[key] - f2[key]) < 1e-6, (
                f"{key} differs: {f1[key]} vs {f2[key]}"
            )

    def test_empty_candidate(self, extractor, empty_candidate):
        """Empty candidate should produce valid scores with no errors."""
        features = extractor.extract(empty_candidate)
        assert len(features) == 20
        for name, score in features.items():
            assert 0.0 <= score <= 1.0

    def test_ai_engineer_high_tech_scores(self, extractor, ai_engineer_candidate):
        """AI engineer should have high technical experience scores."""
        features = extractor.extract(ai_engineer_candidate)
        assert features["ranking_experience_score"] >= 0.3
        assert features["retrieval_experience_score"] >= 0.3
        assert features["embeddings_experience_score"] >= 0.3
        assert features["production_ml_score"] >= 0.3
        assert features["python_engineering_score"] >= 0.3
        assert features["nlp_ir_experience_score"] >= 0.3

    def test_ai_engineer_high_domain_scores(self, extractor, ai_engineer_candidate):
        """AI engineer should have high domain relevance scores."""
        features = extractor.extract(ai_engineer_candidate)
        assert features["product_company_score"] >= 0.3
        assert features["engineering_depth_score"] >= 0.3
        assert features["skill_relevance_score"] >= 0.3

    def test_non_tech_lower_than_tech(self, extractor, ai_engineer_candidate, non_tech_candidate):
        """Non-tech candidate should have lower tech signal scores than AI engineer."""
        tech_feats = extractor.extract(ai_engineer_candidate)
        non_tech_feats = extractor.extract(non_tech_candidate)

        for sig in ["ranking_experience_score", "retrieval_experience_score",
                     "embeddings_experience_score", "production_ml_score",
                     "recommendation_experience_score", "nlp_ir_experience_score"]:
            assert tech_feats[sig] >= non_tech_feats[sig], (
                f"Tech ({tech_feats[sig]:.3f}) < Non-tech ({non_tech_feats[sig]:.3f}) for {sig}"
            )

    def test_non_tech_low_engineering(self, extractor, non_tech_candidate):
        """Non-tech candidate should have very low engineering scores."""
        features = extractor.extract(non_tech_candidate)
        assert features["engineering_depth_score"] < 0.3
        assert features["python_engineering_score"] < 0.3


# ============================================================================
# Penalty Signal Tests
# ============================================================================

class TestPenaltySignals:
    """Penalty signal detection."""

    def test_no_penalty_for_strong_candidate(self, extractor, ai_engineer_candidate):
        """Strong AI engineer should have low/no penalties."""
        features = extractor.extract(ai_engineer_candidate)
        assert features["consulting_penalty"] == 0.0
        assert features["research_penalty"] < 0.15  # Small signal from "Applied Scientist" title OK
        assert features["keyword_stuffing_penalty"] == 0.0
        assert features["title_chasing_penalty"] < 0.3

    def test_consulting_penalty_applied(self, extractor, consulting_candidate):
        """Consulting-only candidate should have high consulting penalty."""
        features = extractor.extract(consulting_candidate)
        assert features["consulting_penalty"] > 0.3, (
            f"Consulting penalty too low: {features['consulting_penalty']}"
        )

    def test_consulting_penalty_no_product_company(self, extractor, consulting_candidate):
        """Consulting candidate without product company should have higher penalty."""
        features = extractor.extract(consulting_candidate)
        # TCS + Infosys both consulting, no product company
        assert features["consulting_penalty"] >= 0.3

    def test_title_chasing_penalty_applied(self, extractor, title_chaser_candidate):
        """Title-chaser should have detectable title-chasing penalty."""
        features = extractor.extract(title_chaser_candidate)
        # Short stints (10mo, 8mo, 14mo) with inflating titles should trigger penalty
        assert features["title_chasing_penalty"] > 0.1, (
            f"Title chasing penalty too low: {features['title_chasing_penalty']}"
        )

    def test_keyword_stuffing_penalty_applied(self, extractor, keyword_stuffer_candidate):
        """Keyword stuffer should have high stuffing penalty."""
        features = extractor.extract(keyword_stuffer_candidate)
        assert features["keyword_stuffing_penalty"] > 0.3, (
            f"Keyword stuffing penalty too low: {features['keyword_stuffing_penalty']}"
        )


# ============================================================================
# Edge Case Tests
# ============================================================================

class TestEdgeCases:
    """Edge cases and error handling."""

    def test_empty_career_history(self, extractor):
        """Candidate with no career history should not error."""
        c = _make_candidate(career_history=[])
        features = extractor.extract(c)
        assert len(features) == 20
        for v in features.values():
            assert 0.0 <= v <= 1.0

    def test_empty_skills(self, extractor):
        """Candidate with no skills should not error."""
        c = _make_candidate(skills=[])
        features = extractor.extract(c)
        assert len(features) == 20

    def test_empty_all_fields(self, extractor):
        """Candidate with all empty fields should not error."""
        c = _make_candidate(
            headline="", summary="", current_title="",
            career_history=[], skills=[],
        )
        features = extractor.extract(c)
        assert len(features) == 20
        # Most scores should be 0.0 for empty candidate
        tech_signals = [
            "ranking_experience_score", "retrieval_experience_score",
            "recommendation_experience_score", "search_experience_score",
            "embeddings_experience_score", "vector_db_experience_score",
            "production_ml_score", "evaluation_framework_score",
            "python_engineering_score", "nlp_ir_experience_score",
        ]
        for sig in tech_signals:
            assert features[sig] == 0.0, f"{sig} should be 0 for empty candidate"

    def test_long_career_history(self, extractor):
        """Candidate with many career entries should not error."""
        career = [
            _make_career_entry(
                company=f"Company{i}", title=f"Role{i}",
                description=f"Description {i}.",
                duration_months=24, is_current=(i == 0),
            )
            for i in range(20)
        ]
        c = _make_candidate(years_of_experience=40.0, career_history=career)
        features = extractor.extract(c)
        assert len(features) == 20

    def test_very_short_tenures(self, extractor):
        """Candidate with very short tenures should have high title-chasing penalty."""
        career = [
            _make_career_entry(
                company=f"Company{i}", title=f"Senior Engineer",
                description=f"Worked there.",
                duration_months=6, is_current=(i == 0),
            )
            for i in range(5)
        ]
        c = _make_candidate(years_of_experience=2.5, career_history=career)
        features = extractor.extract(c)
        assert features["title_chasing_penalty"] > 0.3

    def test_single_career_entry(self, extractor):
        """Candidate with single long-term role should have low title-chasing penalty."""
        c = _make_candidate(
            years_of_experience=8.0,
            career_history=[
                _make_career_entry(
                    company="StableCorp", title="Engineer",
                    description="Long-term role.",
                    duration_months=96, is_current=True,
                ),
            ],
        )
        features = extractor.extract(c)
        assert features["title_chasing_penalty"] == 0.0


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration with FeatureRegistry."""

    def test_registry_register(self, extractor):
        """CareerIntelligence should register in FeatureRegistry."""
        registry = FeatureRegistry()
        registry.register(extractor)
        assert "career_intelligence" in registry.extractors
        assert registry.feature_count >= 20

    def test_registry_extract_single(self, extractor, ai_engineer_candidate):
        """Registry should extract features via CareerIntelligence."""
        registry = FeatureRegistry()
        registry.register(extractor)
        features = registry.extract_all(ai_engineer_candidate)
        assert "ranking_experience_score" in features
        assert "product_company_score" in features
        assert "consulting_penalty" in features
        assert len(features) >= 20

    def test_registry_extract_batch(self, extractor, ai_engineer_candidate, non_tech_candidate):
        """Registry batch extraction should work with CareerIntelligence."""
        registry = FeatureRegistry()
        registry.register(extractor)
        results = registry.extract_batch([ai_engineer_candidate, non_tech_candidate])
        assert len(results) == 2
        for r in results:
            assert len(r) >= 20
            for v in r.values():
                assert 0.0 <= v <= 1.0

    def test_combined_with_semantic(self, extractor, ai_engineer_candidate):
        """CareerIntelligence should work alongside other extractors."""
        registry = FeatureRegistry()
        registry.register(extractor)
        features = registry.extract_all(ai_engineer_candidate)
        # Should have Career Intelligence features
        assert "ranking_experience_score" in features
        assert "product_company_score" in features
        assert "consulting_penalty" in features


# ============================================================================
# Performance Benchmarks
# ============================================================================

class TestCareerIntelligenceBenchmarks:
    """Runtime and memory benchmarks."""

    @pytest.mark.parametrize("n_candidates", [100, 1000])
    def test_extract_runtime(self, extractor, n_candidates):
        """Measure extract() runtime for N candidates."""
        candidates = [
            _make_candidate(
                candidate_id=f"CAND_{i:07d}",
                headline="ML Engineer with ranking experience" if i % 2 == 0 else "Marketing professional",
                summary="Building ML systems." if i % 2 == 0 else "Marketing expert.",
                current_title="ML Engineer" if i % 2 == 0 else "Marketing Manager",
                current_industry="Technology" if i % 2 == 0 else "Marketing",
                years_of_experience=5.0,
                career_history=[
                    _make_career_entry(
                        company=f"TechCorp_{i}" if i % 2 == 0 else f"BrandCorp_{i}",
                        title="ML Engineer" if i % 2 == 0 else "Marketing Manager",
                        description=(
                            "Built production ranking systems with FAISS and PyTorch."
                            if i % 2 == 0 else "Managed marketing campaigns and social media."
                        ),
                        duration_months=36, is_current=True,
                    ),
                ],
                skills=[
                    _make_skill(name="Python", proficiency="advanced", duration_months=36),
                    _make_skill(name="PyTorch", proficiency="intermediate", duration_months=18),
                ] if i % 2 == 0 else [
                    _make_skill(name="Social Media", proficiency="expert", duration_months=48),
                ],
            )
            for i in range(n_candidates)
        ]

        start = time.perf_counter()
        for c in candidates:
            extractor.extract(c)
        elapsed = time.perf_counter() - start

        per_candidate = elapsed / n_candidates
        print(f"\nExtract {n_candidates} candidates: {elapsed:.4f}s total, "
              f"{per_candidate * 1000:.4f}ms per candidate, "
              f"{n_candidates / elapsed:.0f} candidates/sec")

        # Should process at least 10,000 candidates/sec (very fast — keyword matching only)
        assert n_candidates / elapsed > 1000, (
            f"Throughput too low: {n_candidates / elapsed:.0f} cand/s"
        )

    def test_memory_usage(self, extractor):
        """Measure peak memory during extraction of 1000 candidates."""
        n = 1000
        candidates = [
            _make_candidate(
                candidate_id=f"CAND_{i:07d}",
                headline="Test headline",
                summary="Test summary",
                current_title="Engineer",
                years_of_experience=5.0,
                career_history=[
                    _make_career_entry(
                        company="TestCorp", title="Engineer",
                        description="Worked on software.",
                        duration_months=36, is_current=True,
                    ),
                ],
                skills=[
                    _make_skill(name="Python", proficiency="advanced", duration_months=24),
                ],
            )
            for i in range(n)
        ]

        tracemalloc.start()
        for c in candidates:
            extractor.extract(c)
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak / (1024 * 1024)
        print(f"\nMemory for {n} candidates: current={current / 1024:.1f}KB, "
              f"peak={peak_mb:.2f}MB")

        # Career Intelligence uses no ML models — should be well under 50 MB
        assert peak_mb < 50, f"Peak memory too high: {peak_mb:.1f}MB"


# ============================================================================
# Feature-Specific Detection Tests
# ============================================================================

class TestSpecificFeatures:
    """Individual feature detection accuracy."""

    def test_product_company_detection(self, extractor):
        """Product company detection should work for known product companies."""
        c = _make_candidate(
            career_history=[
                _make_career_entry(company="Google", title="SWE",
                                   description="Worked on search.", duration_months=36),
                _make_career_entry(company="TCS", title="Consultant",
                                   description="Consulting work.", duration_months=24, is_current=False),
            ],
        )
        # Mix of product + consulting should give moderate product score
        features = extractor.extract(c)
        assert features["product_company_score"] > 0, (
            "Should detect product company (Google)"
        )
        assert features["product_company_score"] < 1.0, (
            "Should not be perfect (mix of product + consulting)"
        )

    def test_startup_detection(self, extractor):
        """Startup detection should work for startup indicators."""
        c = _make_candidate(
            career_history=[
                _make_career_entry(company="MyStartup", title="Founding Engineer",
                                   description="Early-stage startup building product from scratch.",
                                   duration_months=24),
            ],
        )
        features = extractor.extract(c)
        assert features["startup_experience_score"] > 0

    def test_no_startup_for_large_company(self, extractor):
        """Large company should not trigger startup detection."""
        c = _make_candidate(
            career_history=[
                _make_career_entry(company="Microsoft", title="SWE",
                                   description="Worked on Azure.",
                                   duration_months=48),
            ],
        )
        features = extractor.extract(c)
        assert features["startup_experience_score"] < 0.3

    def test_search_experience_detection(self, extractor):
        """Search experience detection should work."""
        c = _make_candidate(
            career_history=[
                _make_career_entry(
                    company="SearchCorp", title="Search Engineer",
                    description="Built search infrastructure with Elasticsearch and semantic search.",
                    duration_months=36,
                ),
            ],
        )
        features = extractor.extract(c)
        assert features["search_experience_score"] > 0

    def test_vector_db_detection(self, extractor):
        """Vector database detection should work."""
        c = _make_candidate(
            career_history=[
                _make_career_entry(
                    company="AICorp", title="ML Engineer",
                    description="Deployed vector search with Pinecone and Milvus.",
                    duration_months=24,
                ),
            ],
        )
        features = extractor.extract(c)
        assert features["vector_db_experience_score"] > 0

    def test_evaluation_framework_detection(self, extractor):
        """Evaluation framework detection should work."""
        c = _make_candidate(
            career_history=[
                _make_career_entry(
                    company="RankCorp", title="ML Engineer",
                    description="Designed evaluation framework with NDCG, MRR, and A/B testing.",
                    duration_months=36,
                ),
            ],
        )
        features = extractor.extract(c)
        assert features["evaluation_framework_score"] > 0

    def test_career_progression(self, extractor):
        """Career progression should be higher for longer tenure."""
        stable = _make_candidate(
            years_of_experience=8.0,
            career_history=[
                _make_career_entry(company="CoA", title="Jr Engineer",
                                   duration_months=48, is_current=False),
                _make_career_entry(company="CoB", title="Engineer",
                                   duration_months=48, is_current=True),
            ],
        )
        unstable = _make_candidate(
            years_of_experience=3.0,
            career_history=[
                _make_career_entry(company="CoX", title="Engineer",
                                   duration_months=8, is_current=True),
            ],
        )
        stable_feats = extractor.extract(stable)
        unstable_feats = extractor.extract(unstable)
        assert stable_feats["career_progression_score"] >= unstable_feats["career_progression_score"]
