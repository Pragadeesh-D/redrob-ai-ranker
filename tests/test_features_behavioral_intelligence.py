"""Unit tests for Behavioral Intelligence Engine (src/features/behavioral_intelligence.py).

Covers:
- Availability scoring (open_to_work, notice period, recency)
- Demand scoring (profile views, saved by recruiters)
- Trust scoring (recruiter response rate, interview completion)
- Engagement scoring (views, saves, recency)
- Edge cases: missing values, nulls, empty profiles, extreme values
- Integration with FeatureRegistry
- Performance benchmarks (runtime + RAM)
- Regression against Phase 5 and 6
"""

import time
import tracemalloc
from datetime import datetime, timezone

import pytest

from src.features.behavioral_intelligence import (
    BehavioralIntelligence,
    _score_views,
    _score_saves,
    _score_notice_period,
    _score_last_active_date,
    _score_recruiter_response_rate,
    _score_interview_completion_rate,
)
from src.features.framework import FeatureRegistry
from src.parser.candidate_parser import Candidate, Profile, RedrobSignals, SalaryRange


# ============================================================================
# Helpers
# ============================================================================

def _null_signals(
    recruiter_response_rate: float = 0.0,
    last_active_date: str = "",
    open_to_work_flag: bool = False,
    interview_completion_rate: float = 0.0,
    notice_period_days: int = 0,
    profile_views_received_30d: int = 0,
    saved_by_recruiters_30d: int = 0,
) -> RedrobSignals:
    """Create RedrobSignals with specified fields, default zeros/empty for others."""
    return RedrobSignals(
        profile_completeness_score=0.0,
        signup_date="",
        last_active_date=last_active_date,
        open_to_work_flag=open_to_work_flag,
        profile_views_received_30d=profile_views_received_30d,
        applications_submitted_30d=0,
        recruiter_response_rate=recruiter_response_rate,
        avg_response_time_hours=0.0,
        skill_assessment_scores={},
        connection_count=0,
        endorsements_received=0,
        notice_period_days=notice_period_days,
        expected_salary_range_inr_lpa=SalaryRange(min=0.0, max=0.0),
        preferred_work_mode="hybrid",
        willing_to_relocate=False,
        github_activity_score=-1.0,
        search_appearance_30d=0,
        saved_by_recruiters_30d=saved_by_recruiters_30d,
        interview_completion_rate=interview_completion_rate,
        offer_acceptance_rate=-1.0,
        verified_email=False,
        verified_phone=False,
        linkedin_connected=False,
    )


def _make_minimal_candidate(signals: RedrobSignals | None = None) -> Candidate:
    """Create a minimal Candidate with specified signals, default empty profile."""
    return Candidate(
        candidate_id="CAND_0000001",
        profile=Profile(
            anonymized_name="Test", headline="H", summary="S",
            location="L", country="C", years_of_experience=5.0,
            current_title="Engineer", current_company="Corp",
            current_company_size="11-50", current_industry="Tech",
        ),
        career_history=[],
        education=[],
        skills=[],
        redrob_signals=signals or _null_signals(),
    )


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def extractor() -> BehavioralIntelligence:
    return BehavioralIntelligence()


@pytest.fixture
def highly_available_candidate() -> Candidate:
    """Candidate who is open to work, short notice, recently active."""
    return _make_minimal_candidate(_null_signals(
        open_to_work_flag=True,
        notice_period_days=0,
        last_active_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    ))


@pytest.fixture
def highly_demanded_candidate() -> Candidate:
    """Candidate with many profile views and recruiter saves."""
    return _make_minimal_candidate(_null_signals(
        profile_views_received_30d=200,
        saved_by_recruiters_30d=60,
    ))


@pytest.fixture
def highly_trusted_candidate() -> Candidate:
    """Candidate with high response and interview completion rates."""
    return _make_minimal_candidate(_null_signals(
        recruiter_response_rate=0.9,
        interview_completion_rate=0.95,
    ))


@pytest.fixture
def highly_engaged_candidate() -> Candidate:
    """Candidate with high views, saves, and recent activity."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return _make_minimal_candidate(_null_signals(
        profile_views_received_30d=150,
        saved_by_recruiters_30d=40,
        last_active_date=now,
    ))


@pytest.fixture
def unavailable_candidate() -> Candidate:
    """Candidate not open to work, very long notice, inactive for a year."""
    return _make_minimal_candidate(_null_signals(
        open_to_work_flag=False,
        notice_period_days=90,
        last_active_date="2024-01-01",
    ))


@pytest.fixture
def null_signals_candidate() -> Candidate:
    """Candidate with all null/zero signals."""
    return _make_minimal_candidate(_null_signals())


# ============================================================================
# Initialization Tests
# ============================================================================

class TestBehavioralIntelligenceInit:
    """Engine initialization and properties."""

    def test_name_and_features(self, extractor):
        assert extractor.name == "behavioral_intelligence"
        assert extractor.description
        assert "behavioral intelligence" in extractor.description.lower()
        assert len(extractor.features) == 11

    def test_feature_names_are_unique(self, extractor):
        assert len(extractor.features) == len(set(extractor.features))

    def test_feature_names_lowercase(self, extractor):
        for f in extractor.features:
            assert f == f.lower(), f"Feature '{f}' is not lowercase"

    def test_repr(self, extractor):
        assert "BehavioralIntelligence" in repr(extractor)
        assert "behavioral_intelligence" in repr(extractor)
        assert "11" in repr(extractor)


# ============================================================================
# Availability Scoring Tests
# ============================================================================

class TestAvailabilityScore:
    """Availability feature group (availability_score, notice_period, recency)."""

    def test_open_to_work_high(self, extractor, highly_available_candidate):
        """Open to work + zero notice + recent active = high availability."""
        features = extractor.extract(highly_available_candidate)
        assert features["availability_score"] > 0.7
        assert features["availability_notice_period"] == 1.0
        assert features["availability_recent_active"] > 0.9

    def test_not_open_to_work_lower(self, extractor, unavailable_candidate):
        """Not open to work + long notice + stale = low availability."""
        features = extractor.extract(unavailable_candidate)
        assert features["availability_score"] < 0.3
        assert features["availability_notice_period"] == 0.0
        assert features["availability_recent_active"] < 0.1

    def test_notice_period_scoring(self, extractor):
        """Shorter notice period = higher notice period score."""
        zero = _make_minimal_candidate(_null_signals(notice_period_days=0))
        thirty = _make_minimal_candidate(_null_signals(notice_period_days=30))
        ninety = _make_minimal_candidate(_null_signals(notice_period_days=90))

        f_zero = extractor.extract(zero)
        f_thirty = extractor.extract(thirty)
        f_ninety = extractor.extract(ninety)

        assert f_zero["availability_notice_period"] >= f_thirty["availability_notice_period"]
        assert f_thirty["availability_notice_period"] >= f_ninety["availability_notice_period"]
        assert f_ninety["availability_notice_period"] == 0.0

    def test_recency_scoring(self, extractor):
        """More recent activity = higher recency score."""
        today = _make_minimal_candidate(_null_signals(
            last_active_date=datetime.now(timezone.utc).strftime("%Y-%m-%d")
        ))
        last_month = _make_minimal_candidate(_null_signals(
            last_active_date="2026-05-20"
        ))
        last_year = _make_minimal_candidate(_null_signals(
            last_active_date="2024-01-01"
        ))

        f_today = extractor.extract(today)
        f_month = extractor.extract(last_month)
        f_year = extractor.extract(last_year)

        assert f_today["availability_recent_active"] >= f_month["availability_recent_active"]
        assert f_month["availability_recent_active"] >= f_year["availability_recent_active"]

    def test_open_to_work_flag_impact(self, extractor):
        """open_to_work=True should boost availability."""
        not_open = _make_minimal_candidate(_null_signals(
            open_to_work_flag=False, notice_period_days=30,
            last_active_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        ))
        open_willing = _make_minimal_candidate(_null_signals(
            open_to_work_flag=True, notice_period_days=30,
            last_active_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        ))

        f_not = extractor.extract(not_open)
        f_open = extractor.extract(open_willing)

        assert f_open["availability_score"] > f_not["availability_score"]


# ============================================================================
# Demand Scoring Tests
# ============================================================================

class TestDemandScore:
    """Demand feature group (demand_score, profile_views, saves)."""

    def test_high_demand_detected(self, extractor, highly_demanded_candidate):
        """High views + high saves = high demand score."""
        features = extractor.extract(highly_demanded_candidate)
        assert features["demand_score"] > 0.7
        assert features["demand_profile_views"] >= 0.9
        assert features["demand_saved_by_recruiters"] >= 0.9

    def test_low_demand_scoring(self, extractor, null_signals_candidate):
        """Zero views + zero saves = zero demand."""
        features = extractor.extract(null_signals_candidate)
        assert features["demand_score"] == 0.0
        assert features["demand_profile_views"] == 0.0
        assert features["demand_saved_by_recruiters"] == 0.0

    def test_profile_views_scaling(self, extractor):
        """More profile views = higher view score."""
        low = _make_minimal_candidate(_null_signals(profile_views_received_30d=5))
        med = _make_minimal_candidate(_null_signals(profile_views_received_30d=50))
        high = _make_minimal_candidate(_null_signals(profile_views_received_30d=200))

        f_low = extractor.extract(low)
        f_med = extractor.extract(med)
        f_high = extractor.extract(high)

        assert f_low["demand_profile_views"] <= f_med["demand_profile_views"]
        assert f_med["demand_profile_views"] <= f_high["demand_profile_views"]

    def test_saves_scaling(self, extractor):
        """More saves = higher save score."""
        low = _make_minimal_candidate(_null_signals(saved_by_recruiters_30d=2))
        med = _make_minimal_candidate(_null_signals(saved_by_recruiters_30d=20))
        high = _make_minimal_candidate(_null_signals(saved_by_recruiters_30d=80))

        f_low = extractor.extract(low)
        f_med = extractor.extract(med)
        f_high = extractor.extract(high)

        assert f_low["demand_saved_by_recruiters"] <= f_med["demand_saved_by_recruiters"]
        assert f_med["demand_saved_by_recruiters"] <= f_high["demand_saved_by_recruiters"]


# ============================================================================
# Trust Scoring Tests
# ============================================================================

class TestTrustScore:
    """Trust feature group (trust_score, response_rate, interview_completion)."""

    def test_high_trust_detected(self, extractor, highly_trusted_candidate):
        """High response + interview completion = high trust."""
        features = extractor.extract(highly_trusted_candidate)
        assert features["trust_score"] > 0.8
        assert features["trust_recruiter_response"] > 0.8
        assert features["trust_interview_completion"] > 0.8

    def test_zero_trust_for_null(self, extractor, null_signals_candidate):
        """Zero rates = zero trust."""
        features = extractor.extract(null_signals_candidate)
        assert features["trust_score"] == 0.0
        assert features["trust_recruiter_response"] == 0.0
        assert features["trust_interview_completion"] == 0.0

    def test_response_rate_scaling(self, extractor):
        """Higher response rate = higher trust score."""
        low = _make_minimal_candidate(_null_signals(recruiter_response_rate=0.1))
        med = _make_minimal_candidate(_null_signals(recruiter_response_rate=0.5))
        high = _make_minimal_candidate(_null_signals(recruiter_response_rate=0.9))

        f_low = extractor.extract(low)
        f_med = extractor.extract(med)
        f_high = extractor.extract(high)

        assert f_low["trust_recruiter_response"] <= f_med["trust_recruiter_response"]
        assert f_med["trust_recruiter_response"] <= f_high["trust_recruiter_response"]

    def test_interview_rate_scaling(self, extractor):
        """Higher interview completion = higher trust."""
        low = _make_minimal_candidate(_null_signals(interview_completion_rate=0.1))
        med = _make_minimal_candidate(_null_signals(interview_completion_rate=0.5))
        high = _make_minimal_candidate(_null_signals(interview_completion_rate=1.0))

        f_low = extractor.extract(low)
        f_med = extractor.extract(med)
        f_high = extractor.extract(high)

        assert f_low["trust_interview_completion"] <= f_med["trust_interview_completion"]
        assert f_med["trust_interview_completion"] <= f_high["trust_interview_completion"]


# ============================================================================
# Engagement Scoring Tests
# ============================================================================

class TestEngagementScore:
    """Engagement feature group (engagement_score, activity_recency)."""

    def test_high_engagement_detected(self, extractor, highly_engaged_candidate):
        """High views + saves + recent = high engagement."""
        features = extractor.extract(highly_engaged_candidate)
        assert features["engagement_score"] > 0.7
        assert features["engagement_activity_recency"] > 0.9

    def test_zero_engagement_for_null(self, extractor, null_signals_candidate):
        """Zero signals = zero engagement."""
        features = extractor.extract(null_signals_candidate)
        assert features["engagement_score"] == 0.0
        assert features["engagement_activity_recency"] == 0.0


# ============================================================================
# Edge Case Tests
# ============================================================================

class TestEdgeCases:
    """Edge cases — missing, null, extreme, invalid values."""

    def test_missing_last_active_date(self, extractor):
        """Empty last_active_date should not error and score 0."""
        c = _make_minimal_candidate(_null_signals(last_active_date=""))
        features = extractor.extract(c)
        assert features["availability_recent_active"] == 0.0
        assert features["engagement_activity_recency"] == 0.0

    def test_invalid_last_active_date(self, extractor):
        """Invalid date string should not error and score 0."""
        c = _make_minimal_candidate(_null_signals(last_active_date="not-a-date"))
        features = extractor.extract(c)
        assert features["availability_recent_active"] == 0.0
        assert features["engagement_activity_recency"] == 0.0

    def test_negative_notice_period(self, extractor):
        """Negative notice period should be treated as 0."""
        c = _make_minimal_candidate(_null_signals(notice_period_days=-5))
        features = extractor.extract(c)
        assert 0.0 <= features["availability_notice_period"] <= 1.0

    def test_extreme_notice_period(self, extractor):
        """Very long notice period (999 days) should score 0."""
        c = _make_minimal_candidate(_null_signals(notice_period_days=999))
        features = extractor.extract(c)
        assert features["availability_notice_period"] == 0.0

    def test_extreme_profile_views(self, extractor):
        """Very high profile views should cap at 1.0."""
        c = _make_minimal_candidate(_null_signals(profile_views_received_30d=999999))
        features = extractor.extract(c)
        assert features["demand_profile_views"] == 1.0

    def test_extreme_saves(self, extractor):
        """Very high saves should cap at 1.0."""
        c = _make_minimal_candidate(_null_signals(saved_by_recruiters_30d=99999))
        features = extractor.extract(c)
        assert features["demand_saved_by_recruiters"] == 1.0

    def test_negative_response_rate(self, extractor):
        """Negative response rate should be treated as 0."""
        c = _make_minimal_candidate(_null_signals(recruiter_response_rate=-0.5))
        features = extractor.extract(c)
        # _normalize checks for <= 0.0 → returns 0.0
        assert features["trust_recruiter_response"] == 0.0

    def test_negative_interview_rate(self, extractor):
        """Negative interview rate should be treated as 0."""
        c = _make_minimal_candidate(_null_signals(interview_completion_rate=-0.2))
        features = extractor.extract(c)
        assert features["trust_interview_completion"] == 0.0

    def test_very_old_last_active(self, extractor):
        """Very old date should score near 0."""
        c = _make_minimal_candidate(_null_signals(last_active_date="2020-01-01"))
        features = extractor.extract(c)
        assert features["availability_recent_active"] < 0.1
        assert features["engagement_activity_recency"] < 0.1

    def test_empty_signals_object(self, extractor):
        """Candidate with all-zero/null signals should produce valid features.

        Note: availability_score is > 0 even with null signals because
        notice_period_days=0 maps to 'immediately available' (score=1.0)
        which contributes 0.35 to the composite.
        """
        c = _make_minimal_candidate(_null_signals())
        features = extractor.extract(c)
        assert len(features) == 11
        for name, score in features.items():
            assert 0.0 <= score <= 1.0, f"{name} = {score} outside [0, 1]"
        # Zero-demand, zero-trust composites, but availability has
        # a notice-period component (0 days = 1.0 * 0.35 weight)
        assert features["demand_score"] == 0.0
        assert features["trust_score"] == 0.0
        assert features["engagement_score"] == 0.0

    def test_all_scores_in_range(self, extractor, highly_available_candidate):
        """All 11 scores should be in [0, 1] for any candidate."""
        features = extractor.extract(highly_available_candidate)
        for name, score in features.items():
            assert 0.0 <= score <= 1.0, f"{name} = {score} out of range"

    def test_deterministic(self, extractor, highly_available_candidate):
        """Same candidate should produce identical scores."""
        f1 = extractor.extract(highly_available_candidate)
        f2 = extractor.extract(highly_available_candidate)
        for key in f1:
            assert abs(f1[key] - f2[key]) < 1e-6, f"{key} differs"


# ============================================================================
# Normalization Unit Tests
# ============================================================================

class TestNormalizationFunctions:
    """Unit tests for standalone normalization helpers."""

    def test_score_notice_period_zero(self):
        assert _score_notice_period(0) == 1.0

    def test_score_notice_period_high(self):
        assert _score_notice_period(90) == 0.0

    def test_score_notice_period_partial(self):
        score = _score_notice_period(30)
        assert 0.4 <= score <= 0.6, f"30-day notice should be ~0.5, got {score}"

    def test_score_last_active_today(self):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        score = _score_last_active_date(today)
        assert score > 0.9

    def test_score_last_active_empty(self):
        assert _score_last_active_date("") == 0.0

    def test_score_last_active_invalid(self):
        assert _score_last_active_date("garbage") == 0.0

    def test_score_views_zero(self):
        assert _score_views(0) == 0.0

    def test_score_views_low(self):
        s = _score_views(10)
        assert 0.2 <= s <= 0.4, f"10 views should be ~0.3, got {s}"

    def test_score_views_medium(self):
        s = _score_views(50)
        assert 0.5 <= s <= 0.7, f"50 views should be ~0.6, got {s}"

    def test_score_views_high(self):
        s = _score_views(200)
        assert s >= 0.9, f"200 views should be near 1.0, got {s}"

    def test_score_saves_zero(self):
        assert _score_saves(0) == 0.0

    def test_score_saves_high(self):
        s = _score_saves(60)
        assert s >= 0.9, f"60 saves should be near 1.0, got {s}"

    def test_score_recruiter_rate_zero(self):
        assert _score_recruiter_response_rate(0.0) == 0.0

    def test_score_recruiter_rate_full(self):
        assert _score_recruiter_response_rate(1.0) == 1.0

    def test_score_interview_rate_zero(self):
        assert _score_interview_completion_rate(0.0) == 0.0

    def test_score_interview_rate_full(self):
        assert _score_interview_completion_rate(1.0) == 1.0


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration with FeatureRegistry."""

    def test_registry_register(self, extractor):
        """BehavioralIntelligence should register in FeatureRegistry."""
        registry = FeatureRegistry()
        registry.register(extractor)
        assert "behavioral_intelligence" in registry.extractors
        assert registry.feature_count >= 11

    def test_registry_extract(self, extractor, highly_available_candidate):
        """Registry should extract behavioral features."""
        registry = FeatureRegistry()
        registry.register(extractor)
        features = registry.extract_all(highly_available_candidate)
        assert "availability_score" in features
        assert "demand_score" in features
        assert "trust_score" in features
        assert "engagement_score" in features
        assert len(features) >= 11

    def test_registry_extract_batch(self, extractor):
        """Batch extraction should work."""
        registry = FeatureRegistry()
        registry.register(extractor)
        c1 = _make_minimal_candidate(_null_signals(open_to_work_flag=True, notice_period_days=0))
        c2 = _make_minimal_candidate(_null_signals(open_to_work_flag=False, notice_period_days=90))
        results = registry.extract_batch([c1, c2])
        assert len(results) == 2
        # First should be more available
        assert results[0]["availability_score"] > results[1]["availability_score"]

    def test_combined_with_other_extractors(self, extractor):
        """Behavioral should work alongside other extractors without conflict."""
        from src.features.career_intelligence import CareerIntelligence

        registry = FeatureRegistry()
        registry.register(extractor)
        registry.register(CareerIntelligence())

        c = _make_minimal_candidate(_null_signals(
            open_to_work_flag=True, notice_period_days=15,
            profile_views_received_30d=50, saved_by_recruiters_30d=10,
            recruiter_response_rate=0.6, interview_completion_rate=0.7,
            last_active_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        ))
        features = registry.extract_all(c)
        # Should have both behavioral and career features
        assert "availability_score" in features
        assert "product_company_score" in features
        assert len(features) >= 31  # 11 behavioral + 20 career


# ============================================================================
# Performance Benchmarks
# ============================================================================

class TestBehavioralBenchmarks:
    """Runtime and memory benchmarks."""

    @pytest.mark.parametrize("n_candidates", [100, 1000])
    def test_extract_runtime(self, extractor, n_candidates):
        """Measure extract() runtime for N candidates."""
        candidates = [
            _make_minimal_candidate(_null_signals(
                open_to_work_flag=(i % 2 == 0),
                notice_period_days=(i % 30),
                profile_views_received_30d=i % 100,
                saved_by_recruiters_30d=i % 20,
                recruiter_response_rate=(i % 100) / 100.0,
                interview_completion_rate=(i % 100) / 100.0,
            ))
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

        # Behavioral engine is extremely fast (pure math, no string matching)
        assert n_candidates / elapsed > 5000, (
            f"Throughput too low: {n_candidates / elapsed:.0f} cand/s"
        )

    def test_memory_usage(self, extractor):
        """Measure peak memory during extraction of 1000 candidates."""
        n = 1000
        candidates = [
            _make_minimal_candidate(_null_signals(
                open_to_work_flag=True, notice_period_days=30,
                profile_views_received_30d=50, saved_by_recruiters_30d=10,
                recruiter_response_rate=0.5, interview_completion_rate=0.5,
            ))
            for _ in range(n)
        ]

        tracemalloc.start()
        for c in candidates:
            extractor.extract(c)
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak / (1024 * 1024)
        print(f"\nMemory for {n} candidates: current={current / 1024:.1f}KB, "
              f"peak={peak_mb:.2f}MB")

        # Behavioral engine uses no ML models, no keyword lists — very lightweight
        assert peak_mb < 20, f"Peak memory too high: {peak_mb:.1f}MB"


# ============================================================================
# Determinism & Consistency Tests
# ============================================================================

class TestDeterminism:
    """Cross-profile consistency and determinism checks."""

    def test_same_signals_same_scores(self, extractor):
        """Two candidates with same signals should produce same scores."""
        sig = _null_signals(
            open_to_work_flag=True, notice_period_days=15,
            profile_views_received_30d=30, saved_by_recruiters_30d=8,
            recruiter_response_rate=0.4, interview_completion_rate=0.6,
            last_active_date="2026-06-01",
        )
        c1 = _make_minimal_candidate(sig)
        c2 = _make_minimal_candidate(sig)
        f1 = extractor.extract(c1)
        f2 = extractor.extract(c2)
        assert f1 == f2

    def test_different_signals_different_scores(self, extractor):
        """Different signals should produce different composite scores."""
        low = _make_minimal_candidate(_null_signals(
            open_to_work_flag=False, notice_period_days=90,
        ))
        high = _make_minimal_candidate(_null_signals(
            open_to_work_flag=True, notice_period_days=0,
        ))
        f_low = extractor.extract(low)
        f_high = extractor.extract(high)
        assert f_high["availability_score"] > f_low["availability_score"]
        assert f_high["demand_score"] >= f_low["demand_score"]
