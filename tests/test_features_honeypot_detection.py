"""Unit tests for Honeypot Detection Engine (src/features/honeypot_detection.py).

Covers:
- Timeline consistency: overlaps, gaps, impossible patterns
- Skill-Experience: zero-duration experts, prolific experts
- Career progression: unrealistic title jumps, rapid churn
- Role-seniority: seniority mismatch, title-experience mismatch
- Pattern uniformity: suspiciously uniform profiles
- Adversarial profile simulations
- Edge cases: empty history, no skills, extreme values
- Integration with FeatureRegistry
- Performance benchmarks (runtime + RAM)
- Regression against Phases 5, 6, 7
"""

import time
import tracemalloc

import pytest

from src.features.honeypot_detection import HoneypotDetector
from src.features.framework import FeatureRegistry
from src.parser.candidate_parser import Candidate, Profile, RedrobSignals, SalaryRange, CareerEntry, Skill


# ============================================================================
# Helpers
# ============================================================================

def _null_signals() -> RedrobSignals:
    """Create a RedrobSignals with default null values."""
    return RedrobSignals(
        profile_completeness_score=0.0, signup_date="", last_active_date="",
        open_to_work_flag=False, profile_views_received_30d=0,
        applications_submitted_30d=0, recruiter_response_rate=0.0,
        avg_response_time_hours=0.0, skill_assessment_scores={},
        connection_count=0, endorsements_received=0, notice_period_days=0,
        expected_salary_range_inr_lpa=SalaryRange(min=0.0, max=0.0),
        preferred_work_mode="hybrid", willing_to_relocate=False,
        github_activity_score=-1.0, search_appearance_30d=0,
        saved_by_recruiters_30d=0, interview_completion_rate=0.0,
        offer_acceptance_rate=-1.0, verified_email=False, verified_phone=False,
        linkedin_connected=False,
    )


def _make_candidate(
    candidate_id: str = "CAND_0000001",
    headline: str = "",
    summary: str = "",
    current_title: str = "",
    current_company: str = "",
    current_industry: str = "",
    years_of_experience: float = 0.0,
    career_history: list | None = None,
    skills: list | None = None,
) -> Candidate:
    """Create a Candidate with specified fields, defaults for others."""
    parsed_career = []
    for ce in (career_history or []):
        if isinstance(ce, CareerEntry):
            parsed_career.append(ce)
        elif isinstance(ce, dict):
            parsed_career.append(CareerEntry(**ce))

    parsed_skills = []
    for s in (skills or []):
        if isinstance(s, Skill):
            parsed_skills.append(s)
        elif isinstance(s, dict):
            parsed_skills.append(Skill(**s))

    return Candidate(
        candidate_id=candidate_id,
        profile=Profile(
            anonymized_name="Test", headline=headline, summary=summary,
            location="Pune", country="India", years_of_experience=years_of_experience,
            current_title=current_title, current_company=current_company,
            current_company_size="11-50", current_industry=current_industry,
        ),
        career_history=parsed_career,
        education=[],
        skills=parsed_skills,
        redrob_signals=_null_signals(),
    )


def _ce(
    company: str = "TestCorp",
    title: str = "Engineer",
    description: str = "Worked on software development.",
    industry: str = "Software",
    start_date: str = "2020-01-01",
    end_date: str | None = None,
    duration_months: int = 36,
    is_current: bool = True,
    company_size: str = "1001-5000",
) -> CareerEntry:
    """Create a CareerEntry with specified fields."""
    return CareerEntry(
        company=company, title=title, start_date=start_date,
        end_date=end_date, duration_months=duration_months,
        is_current=is_current, industry=industry,
        company_size=company_size, description=description,
    )


def _sk(name: str = "Python", proficiency: str = "intermediate",
        endorsements: int = 0, duration_months: int | None = 12) -> Skill:
    """Create a Skill with specified fields."""
    return Skill(name=name, proficiency=proficiency, endorsements=endorsements,
                  duration_months=duration_months)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def extractor() -> HoneypotDetector:
    return HoneypotDetector()


@pytest.fixture
def normal_candidate() -> Candidate:
    """A realistic normal candidate (low honeypot risk)."""
    return _make_candidate(
        candidate_id="CAND_0000001",
        headline="Senior Software Engineer with ML experience",
        summary="7 years building production systems.",
        current_title="Senior Software Engineer",
        current_company="TechCorp",
        current_industry="Software",
        years_of_experience=7.0,
        career_history=[
            _ce(company="TechCorp", title="Senior Software Engineer",
                description="Built production ML systems.",
                start_date="2022-01-01", duration_months=30, is_current=True),
            _ce(company="MidCorp", title="Software Engineer",
                description="Developed backend services.",
                start_date="2018-06-01", end_date="2021-12-31",
                duration_months=43, is_current=False),
            _ce(company="StartupX", title="Junior Developer",
                description="Full-stack web development.",
                start_date="2016-01-01", end_date="2018-05-31",
                duration_months=29, is_current=False),
        ],
        skills=[
            _sk(name="Python", proficiency="advanced", duration_months=60),
            _sk(name="PyTorch", proficiency="intermediate", duration_months=24),
            _sk(name="SQL", proficiency="advanced", duration_months=36),
            _sk(name="AWS", proficiency="intermediate", duration_months=18),
        ],
    )


@pytest.fixture
def honeypot_candidate() -> Candidate:
    """A high-risk honeypot candidate with multiple red flags."""
    return _make_candidate(
        candidate_id="CAND_9999999",
        headline="Principal Engineer | Staff Engineer | AI Expert",
        summary="Expert in everything.",
        current_title="Principal Engineer",
        current_company="FakeCorp",
        current_industry="Software",
        years_of_experience=2.5,
        career_history=[
            _ce(company="ACorp", title="Principal Engineer",
                description="Worked on projects.",
                start_date="2025-01-01", duration_months=8, is_current=True),
            _ce(company="BCorp", title="Staff Engineer",
                description="Worked on stuff.",
                start_date="2024-06-01", end_date="2024-12-31",
                duration_months=7, is_current=False, company_size="10001+"),
            _ce(company="CCorp", title="Senior Engineer",
                description="Responsible for things.",
                start_date="2024-01-01", end_date="2024-05-31",
                duration_months=5, is_current=False, company_size="10001+"),
            _ce(company="DCorp", title="Junior Developer",
                description="Worked on projects.",
                start_date="2023-08-01", end_date="2023-12-31",
                duration_months=5, is_current=False, company_size="10001+"),
            _ce(company="ECorp", title="Senior ML Engineer",
                description="Worked with the team.",
                start_date="2023-03-01", end_date="2023-07-31",
                duration_months=5, is_current=False, company_size="10001+"),
        ],
        skills=[
            _sk(name="Python", proficiency="expert", duration_months=0),
            _sk(name="TensorFlow", proficiency="expert", duration_months=0),
            _sk(name="PyTorch", proficiency="expert", duration_months=0),
            _sk(name="NLP", proficiency="expert", duration_months=0),
            _sk(name="Computer Vision", proficiency="expert", duration_months=0),
            _sk(name="Reinforcement Learning", proficiency="expert", duration_months=0),
            _sk(name="Transformers", proficiency="expert", duration_months=0),
            _sk(name="Docker", proficiency="expert", duration_months=0),
            _sk(name="Kubernetes", proficiency="expert", duration_months=0),
            _sk(name="AWS", proficiency="expert", duration_months=0),
        ],
    )


@pytest.fixture
def empty_candidate() -> Candidate:
    """Candidate with minimal data (edge case)."""
    return _make_candidate(
        candidate_id="CAND_0000000",
        headline="", summary="",
        career_history=[], skills=[],
    )


# ============================================================================
# Initialization Tests
# ============================================================================

class TestHoneypotDetectorInit:
    """Engine initialization and properties."""

    def test_name_and_features(self, extractor):
        assert extractor.name == "honeypot_detection"
        assert extractor.description
        assert "honeypot" in extractor.description.lower()
        assert len(extractor.features) == 10

    def test_feature_names_are_unique(self, extractor):
        assert len(extractor.features) == len(set(extractor.features))

    def test_feature_names_lowercase(self, extractor):
        for f in extractor.features:
            assert f == f.lower(), f"Feature '{f}' is not lowercase"

    def test_repr(self, extractor):
        assert "HoneypotDetector" in repr(extractor)
        assert "honeypot_detection" in repr(extractor)
        assert "features=10" in repr(extractor)


# ============================================================================
# Timeline Consistency Tests
# ============================================================================

class TestTimelineConsistency:
    """Timeline overlap, gap, and impossible pattern detection."""

    def test_normal_candidate_low_overlap(self, extractor, normal_candidate):
        """Normal candidate should have low timeline overlap."""
        features = extractor.extract(normal_candidate)
        assert features["timeline_overlap_score"] == 0.0

    def test_normal_candidate_low_impossible(self, extractor, normal_candidate):
        """Normal candidate should have zero impossible timelines."""
        features = extractor.extract(normal_candidate)
        assert features["timeline_impossible_score"] == 0.0

    def test_overlapping_entries_detected(self, extractor):
        """Overlapping career entries should be detected."""
        c = _make_candidate(
            career_history=[
                _ce(company="ACorp", title="Engineer",
                    start_date="2020-01-01", end_date="2023-06-30",
                    duration_months=42, is_current=False),
                _ce(company="BCorp", title="Engineer",
                    start_date="2023-01-01",  # Overlaps with ACorp
                    duration_months=18, is_current=True),
            ],
        )
        features = extractor.extract(c)
        assert features["timeline_overlap_score"] > 0

    def test_no_overlap_when_sequential(self, extractor):
        """Sequential non-overlapping entries should score 0."""
        c = _make_candidate(
            career_history=[
                _ce(company="ACorp", title="Engineer",
                    start_date="2020-01-01", end_date="2022-12-31",
                    duration_months=36, is_current=False),
                _ce(company="BCorp", title="Engineer",
                    start_date="2023-01-01",
                    duration_months=18, is_current=True),
            ],
        )
        features = extractor.extract(c)
        assert features["timeline_overlap_score"] == 0.0

    def test_large_gap_detected(self, extractor):
        """Large career gaps should be detected."""
        c = _make_candidate(
            years_of_experience=7.0,
            career_history=[
                _ce(company="ACorp", title="Engineer",
                    start_date="2020-01-01", end_date="2020-12-31",
                    duration_months=12, is_current=False),
                _ce(company="BCorp", title="Engineer",
                    start_date="2023-01-01",  # 2-year gap
                    duration_months=12, is_current=True),
            ],
        )
        features = extractor.extract(c)
        assert features["timeline_gap_score"] > 0.3

    def test_impossible_negative_duration(self, extractor):
        """Negative duration should be flagged."""
        c = _make_candidate(
            career_history=[
                _ce(company="ACorp", title="Engineer",
                    duration_months=-6, is_current=True),
            ],
        )
        features = extractor.extract(c)
        assert features["timeline_impossible_score"] > 0

    def test_impossible_end_before_start(self, extractor):
        """End date before start date should be flagged."""
        c = _make_candidate(
            career_history=[
                _ce(company="ACorp", title="Engineer",
                    start_date="2023-01-01", end_date="2022-01-01",
                    duration_months=12, is_current=False),
            ],
        )
        features = extractor.extract(c)
        assert features["timeline_impossible_score"] > 0

    def test_current_role_with_end_date(self, extractor):
        """Current role with end_date should be flagged."""
        c = _make_candidate(
            career_history=[
                _ce(company="ACorp", title="Engineer",
                    start_date="2020-01-01", end_date="2024-01-01",
                    duration_months=48, is_current=True),
            ],
        )
        features = extractor.extract(c)
        assert features["timeline_impossible_score"] > 0


# ============================================================================
# Skill-Experience Tests
# ============================================================================

class TestSkillExperience:
    """Skill-experience alignment checks."""

    def test_normal_skills_low_penalty(self, extractor, normal_candidate):
        """Normal candidate should have low skill-experience penalties."""
        features = extractor.extract(normal_candidate)
        assert features["skill_zero_duration_expert_score"] == 0.0
        assert features["skill_prolific_score"] == 0.0

    def test_zero_duration_experts_detected(self, extractor):
        """Expert skills with zero duration should be flagged."""
        c = _make_candidate(
            years_of_experience=5.0,
            skills=[
                _sk(name="Python", proficiency="expert", duration_months=0),
                _sk(name="PyTorch", proficiency="expert", duration_months=0),
                _sk(name="NLP", proficiency="expert", duration_months=0),
                _sk(name="SQL", proficiency="intermediate", duration_months=12),
            ],
        )
        features = extractor.extract(c)
        assert features["skill_zero_duration_expert_score"] > 0.5

    def test_prolific_experts_high(self, extractor, honeypot_candidate):
        """Honeypot candidate should have high prolific expert score."""
        features = extractor.extract(honeypot_candidate)
        assert features["skill_prolific_score"] > 0.3


# ============================================================================
# Career Progression Tests
# ============================================================================

class TestCareerProgression:
    """Career progression checks."""

    def test_normal_progression_low(self, extractor, normal_candidate):
        """Normal candidate should have low progression penalties."""
        features = extractor.extract(normal_candidate)
        assert features["progression_jump_score"] < 0.3
        assert features["progression_rapid_churn_score"] < 0.3

    def test_junior_to_senior_jump_detected(self, extractor):
        """Unrealistic junior -> senior jump should be flagged."""
        c = _make_candidate(
            years_of_experience=1.5,
            career_history=[
                _ce(company="ACorp", title="Junior Developer",
                    start_date="2024-01-01", end_date="2024-12-31",
                    duration_months=12, is_current=False),
                _ce(company="BCorp", title="Senior Engineer",
                    start_date="2025-01-01",
                    duration_months=6, is_current=True),
            ],
        )
        features = extractor.extract(c)
        assert features["progression_jump_score"] > 0

    def test_rapid_churn_detected(self, extractor, honeypot_candidate):
        """Multiple very short stints should be flagged."""
        features = extractor.extract(honeypot_candidate)
        assert features["progression_rapid_churn_score"] > 0.3


# ============================================================================
# Role-Seniority Tests
# ============================================================================

class TestRoleSeniority:
    """Role-seniority mismatch checks."""

    def test_normal_seniority_low(self, extractor, normal_candidate):
        """Normal candidate should have low seniority mismatch."""
        features = extractor.extract(normal_candidate)
        assert features["seniority_mismatch_score"] < 0.3
        assert features["title_experience_mismatch_score"] < 0.3

    def test_principal_engineer_low_exp(self, extractor):
        """Principal Engineer with 2 years experience should be flagged."""
        c = _make_candidate(
            current_title="Principal Engineer",
            years_of_experience=2.0,
            career_history=[
                _ce(company="ACorp", title="Principal Engineer",
                    duration_months=24, is_current=True),
            ],
        )
        features = extractor.extract(c)
        assert features["seniority_mismatch_score"] > 0.3

    def test_all_senior_titles_low_exp(self, extractor):
        """All senior titles with < 3 years experience should be flagged."""
        c = _make_candidate(
            headline="Senior Engineer",
            current_title="Senior Engineer",
            years_of_experience=2.0,
            career_history=[
                _ce(company="ACorp", title="Senior Engineer",
                    duration_months=12, is_current=False),
                _ce(company="BCorp", title="Senior Engineer",
                    duration_months=12, is_current=True),
            ],
        )
        features = extractor.extract(c)
        assert features["title_experience_mismatch_score"] > 0


# ============================================================================
# Pattern Uniformity Tests
# ============================================================================

class TestPatternUniformity:
    """Pattern uniformity checks."""

    def test_normal_pattern_low(self, extractor, normal_candidate):
        """Normal candidate should have low pattern uniformity score."""
        features = extractor.extract(normal_candidate)
        assert features["pattern_uniform_score"] < 0.5

    def test_uniform_company_sizes_detected(self, extractor):
        """All roles with same company size should contribute to score."""
        c = _make_candidate(
            career_history=[
                _ce(company="ACorp", title="E1", company_size="10001+",
                    duration_months=12, is_current=False),
                _ce(company="BCorp", title="E2", company_size="10001+",
                    duration_months=12, is_current=False),
                _ce(company="CCorp", title="E3", company_size="10001+",
                    duration_months=12, is_current=True),
            ],
        )
        features = extractor.extract(c)
        assert features["pattern_uniform_score"] > 0

    def test_all_expert_skills_flagged(self, extractor):
        """All skills at advanced/expert should be flagged."""
        c = _make_candidate(
            years_of_experience=5.0,
            skills=[
                _sk(name="Python", proficiency="expert", duration_months=36),
                _sk(name="PyTorch", proficiency="advanced", duration_months=24),
                _sk(name="NLP", proficiency="expert", duration_months=18),
                _sk(name="SQL", proficiency="advanced", duration_months=24),
                _sk(name="Docker", proficiency="expert", duration_months=12),
            ],
        )
        features = extractor.extract(c)
        assert features["pattern_uniform_score"] > 0


# ============================================================================
# Edge Case Tests
# ============================================================================

class TestEdgeCases:
    """Edge cases — empty, missing, extreme data."""

    def test_empty_candidate(self, extractor, empty_candidate):
        """Empty candidate should produce valid features with no errors."""
        features = extractor.extract(empty_candidate)
        assert len(features) == 10
        for name, score in features.items():
            assert 0.0 <= score <= 1.0, f"{name} = {score} outside [0, 1]"

    def test_empty_career_history(self, extractor):
        """Candidate with no career history should not error."""
        c = _make_candidate(career_history=[])
        features = extractor.extract(c)
        assert len(features) == 10
        # Most scores should be 0 for empty history
        assert features["timeline_overlap_score"] == 0.0
        assert features["timeline_gap_score"] == 0.0
        assert features["timeline_impossible_score"] == 0.0

    def test_empty_skills(self, extractor):
        """Candidate with no skills should not error."""
        c = _make_candidate(years_of_experience=5.0, skills=[])
        features = extractor.extract(c)
        assert len(features) == 10
        assert features["skill_zero_duration_expert_score"] == 0.0
        assert features["skill_prolific_score"] == 0.0

    def test_single_career_entry(self, extractor):
        """Candidate with single career entry should not error."""
        c = _make_candidate(
            years_of_experience=5.0,
            career_history=[
                _ce(company="ACorp", title="Engineer",
                    duration_months=60, is_current=True),
            ],
        )
        features = extractor.extract(c)
        assert len(features) == 10
        assert features["progression_jump_score"] == 0.0  # needs 2+ entries
        assert features["progression_rapid_churn_score"] == 0.0  # needs 2+ entries

    def test_all_scores_in_range(self, extractor, honeypot_candidate):
        """All scores should be in [0, 1] for any candidate."""
        features = extractor.extract(honeypot_candidate)
        for name, score in features.items():
            assert 0.0 <= score <= 1.0, f"{name} = {score} out of range"

    def test_deterministic(self, extractor, honeypot_candidate):
        """Same candidate should produce identical scores."""
        f1 = extractor.extract(honeypot_candidate)
        f2 = extractor.extract(honeypot_candidate)
        for key in f1:
            assert abs(f1[key] - f2[key]) < 1e-6, f"{key} differs"

    def test_missing_dates(self, extractor):
        """Candidates with missing dates should not error."""
        c = _make_candidate(
            career_history=[
                _ce(company="ACorp", title="Engineer",
                    start_date="", end_date="",
                    duration_months=12, is_current=True),
            ],
        )
        features = extractor.extract(c)
        assert len(features) == 10

    def test_no_current_role(self, extractor):
        """Candidate with no current role should not error."""
        c = _make_candidate(
            career_history=[
                _ce(company="ACorp", title="Engineer",
                    start_date="2020-01-01", end_date="2022-12-31",
                    duration_months=36, is_current=False),
            ],
        )
        features = extractor.extract(c)
        assert len(features) == 10


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration with FeatureRegistry."""

    def test_registry_register(self, extractor):
        """HoneypotDetector should register in FeatureRegistry."""
        registry = FeatureRegistry()
        registry.register(extractor)
        assert "honeypot_detection" in registry.extractors
        assert registry.feature_count >= 10

    def test_registry_extract(self, extractor, normal_candidate):
        """Registry should extract honeypot features."""
        registry = FeatureRegistry()
        registry.register(extractor)
        features = registry.extract_all(normal_candidate)
        assert "timeline_overlap_score" in features
        assert "skill_zero_duration_expert_score" in features
        assert "seniority_mismatch_score" in features
        assert len(features) >= 10

    def test_registry_extract_batch(self, extractor, normal_candidate, honeypot_candidate):
        """Batch extraction should work."""
        registry = FeatureRegistry()
        registry.register(extractor)
        results = registry.extract_batch([normal_candidate, honeypot_candidate])
        assert len(results) == 2
        # Honeypot should have higher overall risk score
        normal_avg = sum(results[0].values()) / len(results[0])
        honeypot_avg = sum(results[1].values()) / len(results[1])
        assert honeypot_avg > normal_avg

    def test_combined_with_all_extractors(self, extractor):
        """Honeypot should work alongside all other extractors."""
        from src.features.career_intelligence import CareerIntelligence
        from src.features.behavioral_intelligence import BehavioralIntelligence

        registry = FeatureRegistry()
        registry.register(extractor)
        registry.register(CareerIntelligence())
        registry.register(BehavioralIntelligence())

        c = _make_candidate(
            candidate_id="CAND_0000001",
            headline="Engineer",
            current_title="Engineer",
            years_of_experience=5.0,
            career_history=[
                _ce(company="ACorp", title="Engineer",
                    duration_months=60, is_current=True),
            ],
            skills=[
                _sk(name="Python", proficiency="advanced", duration_months=36),
            ],
        )
        features = registry.extract_all(c)
        # Should have features from all engines
        assert "timeline_overlap_score" in features  # Phase 8
        assert "product_company_score" in features  # Phase 6
        assert "availability_score" in features  # Phase 7
        # Total: 10 + 20 + 11 = 41+
        assert len(features) >= 41


# ============================================================================
# Adversarial Profile Tests
# ============================================================================

class TestAdversarialProfiles:
    """Known adversarial profile simulations."""

    def test_keyword_stuffed_profile(self, extractor):
        """Keyword-stuffed profile should trigger honeypot detection."""
        c = _make_candidate(
            current_title="AI Expert Engineer",
            years_of_experience=3.0,
            career_history=[
                _ce(company="ACorp", title="Senior AI Engineer",
                    description="Worked on ML projects and models.",
                    duration_months=36, is_current=True),
            ],
            skills=[
                _sk(name="Python", proficiency="expert", duration_months=0),
                _sk(name="TensorFlow", proficiency="expert", duration_months=0),
                _sk(name="PyTorch", proficiency="expert", duration_months=0),
                _sk(name="NLP", proficiency="expert", duration_months=0),
                _sk(name="Computer Vision", proficiency="expert", duration_months=0),
                _sk(name="Transformers", proficiency="expert", duration_months=0),
                _sk(name="LangChain", proficiency="expert", duration_months=0),
                _sk(name="Docker", proficiency="expert", duration_months=0),
            ],
        )
        features = extractor.extract(c)
        # Should have high skill-related scores (zero-duration + prolific + all-expert)
        assert features["skill_zero_duration_expert_score"] > 0.5
        assert features["skill_prolific_score"] > 0
        # Pattern uniform due to all-skills-expert
        assert features["pattern_uniform_score"] > 0

    def test_fabricated_rapid_promotion(self, extractor):
        """Fabricated rapid promotion profile with impossible timeline."""
        c = _make_candidate(
            current_title="VP of Engineering",
            years_of_experience=3.0,
            career_history=[
                _ce(company="ACorp", title="Junior Developer",
                    start_date="2023-01-01", end_date="2023-06-30",
                    duration_months=6, is_current=False),
                _ce(company="ACorp", title="Senior Engineer",
                    start_date="2023-07-01", end_date="2024-06-30",
                    duration_months=12, is_current=False),
                _ce(company="ACorp", title="VP of Engineering",
                    start_date="2024-07-01", is_current=True,
                    duration_months=12),
            ],
        )
        features = extractor.extract(c)
        # Should flag seniority mismatch (VP with 3 years exp)
        assert features["seniority_mismatch_score"] > 0
        # Should flag progression (Junior -> VP in 3 roles)
        assert features["progression_jump_score"] > 0

    def test_impossible_timeline_profile(self, extractor):
        """Profile with negative duration and date overlaps."""
        c = _make_candidate(
            years_of_experience=2.0,
            career_history=[
                _ce(company="ACorp", title="Engineer",
                    start_date="2024-01-01", end_date="2023-12-31",
                    duration_months=-2, is_current=False),  # end before start, negative duration
                _ce(company="BCorp", title="Engineer",
                    start_date="2023-06-01",  # overlaps with ACorp
                    duration_months=24, is_current=True),
            ],
        )
        features = extractor.extract(c)
        assert features["timeline_impossible_score"] > 0
        assert features["timeline_overlap_score"] > 0

    def test_senior_inflated_profile(self, extractor):
        """Profile with inflated titles and uniform characteristics."""
        c = _make_candidate(
            current_title="Principal Engineer",
            years_of_experience=2.0,
            career_history=[
                _ce(company="ACorp", title="Principal Engineer",
                    company_size="11-50",
                    description="Worked on projects.",
                    duration_months=12, is_current=False),
                _ce(company="BCorp", title="Staff Engineer",
                    company_size="11-50",
                    description="Responsible for things.",
                    duration_months=12, is_current=True),
            ],
            skills=[
                _sk(name="Python", proficiency="expert", duration_months=0),
                _sk(name="ML", proficiency="expert", duration_months=0),
                _sk(name="AI", proficiency="expert", duration_months=0),
            ],
        )
        features = extractor.extract(c)
        # Principal with 2 years
        assert features["seniority_mismatch_score"] > 0.3
        # All expert skills with zero duration
        assert features["skill_zero_duration_expert_score"] > 0
        # All-senior-titles with low exp
        assert features["title_experience_mismatch_score"] > 0


# ============================================================================
# Performance Benchmarks
# ============================================================================

class TestHoneypotBenchmarks:
    """Runtime and memory benchmarks."""

    @pytest.mark.parametrize("n_candidates", [100, 1000])
    def test_extract_runtime(self, extractor, n_candidates):
        """Measure extract() runtime for N candidates."""
        candidates = [
            _make_candidate(
                candidate_id=f"CAND_{i:07d}",
                current_title="Engineer" if i % 2 == 0 else "Principal Engineer",
                years_of_experience=5.0 + (i % 3),
                career_history=[
                    _ce(company=f"ACorp_{j}", title="Engineer",
                        start_date="2020-01-01", end_date="2022-12-31",
                        duration_months=24, is_current=False)
                    for j in range(2)
                ] + [
                    _ce(company=f"BCorp_{i}", title="Engineer",
                        start_date="2023-01-01",
                        duration_months=18, is_current=True),
                ],
                skills=[
                    _sk(name=f"Skill_{j}", proficiency="advanced", duration_months=24)
                    for j in range(5)
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

        assert n_candidates / elapsed > 5000, (
            f"Throughput too low: {n_candidates / elapsed:.0f} cand/s"
        )

    def test_memory_usage(self, extractor):
        """Measure peak memory during extraction of 1000 candidates."""
        n = 1000
        candidates = [
            _make_candidate(
                candidate_id=f"CAND_{i:07d}",
                current_title="Engineer",
                years_of_experience=5.0,
                career_history=[
                    _ce(company="ACorp", title="Engineer",
                        duration_months=36, is_current=True),
                ],
                skills=[
                    _sk(name="Python", proficiency="advanced", duration_months=24),
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

        assert peak_mb < 20, f"Peak memory too high: {peak_mb:.1f}MB"


# ============================================================================
# Determinism & Consistency Tests
# ============================================================================

class TestDeterminism:
    """Cross-profile consistency and determinism checks."""

    def test_same_candidate_same_scores(self, extractor, normal_candidate):
        """Same candidate should produce identical scores every time."""
        f1 = extractor.extract(normal_candidate)
        f2 = extractor.extract(normal_candidate)
        assert f1 == f2

    def test_honeypot_higher_than_normal(self, extractor, normal_candidate, honeypot_candidate):
        """Honeypot should have higher overall suspicion than normal."""
        normal = extractor.extract(normal_candidate)
        honeypot = extractor.extract(honeypot_candidate)
        # Honeypot should be higher on most metrics
        honeypot_flagged = sum(1 for v in honeypot.values() if v > 0.3)
        normal_flagged = sum(1 for v in normal.values() if v > 0.3)
        assert honeypot_flagged >= normal_flagged
