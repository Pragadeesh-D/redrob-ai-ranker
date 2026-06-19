"""Unit tests for Feature Extraction Framework (src/features/)."""

import pytest

from src.features.base import BaseFeatureExtractor
from src.features.framework import FeatureRegistry
from src.parser.candidate_parser import Candidate, Profile, RedrobSignals, SalaryRange


# ---------------------------------------------------------------------------
# Dummy extractors for testing
# ---------------------------------------------------------------------------

class DummyExtractor(BaseFeatureExtractor):
    """Simple extractor that returns constant features."""

    features = ["dummy_score", "dummy_confidence"]

    @property
    def name(self) -> str:
        return "dummy"

    @property
    def description(self) -> str:
        return "Dummy test extractor"

    def extract(self, candidate: Candidate) -> dict[str, float]:
        return {"dummy_score": 0.85, "dummy_confidence": 1.0}


class AnotherExtractor(BaseFeatureExtractor):
    """Another extractor with different features."""

    features = ["another_score"]

    @property
    def name(self) -> str:
        return "another"

    @property
    def description(self) -> str:
        return "Another test extractor"

    def extract(self, candidate: Candidate) -> dict[str, float]:
        return {"another_score": 0.42}


class FailingExtractor(BaseFeatureExtractor):
    """Extractor that raises an exception."""

    @property
    def name(self) -> str:
        return "failing"

    @property
    def description(self) -> str:
        return "Failing test extractor"

    def extract(self, candidate: Candidate) -> dict[str, float]:
        raise RuntimeError("Something went wrong")


class NonDictExtractor(BaseFeatureExtractor):
    """Extractor that returns a non-dict value."""

    @property
    def name(self) -> str:
        return "non_dict"

    @property
    def description(self) -> str:
        return "Returns non-dict"

    def extract(self, candidate: Candidate) -> dict[str, float]:
        return "not a dict"  # type: ignore


class NonNumericExtractor(BaseFeatureExtractor):
    """Extractor that returns non-numeric values."""

    @property
    def name(self) -> str:
        return "non_numeric"

    @property
    def description(self) -> str:
        return "Returns non-numeric values"

    def extract(self, candidate: Candidate) -> dict[str, float]:
        return {"valid_score": 0.9, "invalid_score": "bad"}  # type: ignore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def dummy_candidate() -> Candidate:
    """Create a minimal Candidate for feature extraction tests."""
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
        redrob_signals=RedrobSignals(
            profile_completeness_score=0, signup_date="", last_active_date="",
            open_to_work_flag=False, profile_views_received_30d=0,
            applications_submitted_30d=0, recruiter_response_rate=0,
            avg_response_time_hours=0, skill_assessment_scores={},
            connection_count=0, endorsements_received=0, notice_period_days=0,
            expected_salary_range_inr_lpa=SalaryRange(min=0, max=0),
            preferred_work_mode="hybrid", willing_to_relocate=False,
            github_activity_score=-1, search_appearance_30d=0,
            saved_by_recruiters_30d=0, interview_completion_rate=0,
            offer_acceptance_rate=-1, verified_email=False,
            verified_phone=False, linkedin_connected=False,
        ),
    )


@pytest.fixture
def registry() -> FeatureRegistry:
    """Empty registry."""
    return FeatureRegistry()


# ---------------------------------------------------------------------------
# BaseFeatureExtractor tests
# ---------------------------------------------------------------------------

class TestBaseExtractor:
    """Base abstract class behavior."""

    def test_cannot_instantiate_abstract(self):
        """Should not be able to instantiate BaseFeatureExtractor directly."""
        with pytest.raises(TypeError):
            BaseFeatureExtractor()  # type: ignore

    def test_dummy_extractor_properties(self):
        """Concrete extractor should expose name and description."""
        ext = DummyExtractor()
        assert ext.name == "dummy"
        assert ext.description == "Dummy test extractor"

    def test_dummy_extract(self, dummy_candidate):
        """Extract should return expected features."""
        ext = DummyExtractor()
        features = ext.extract(dummy_candidate)
        assert features["dummy_score"] == 0.85
        assert features["dummy_confidence"] == 1.0

    def test_repr(self):
        """__repr__ should show class and name."""
        ext = DummyExtractor()
        assert "DummyExtractor" in repr(ext)
        assert "dummy" in repr(ext)


# ---------------------------------------------------------------------------
# FeatureRegistry tests
# ---------------------------------------------------------------------------

class TestRegistryRegistration:
    """Register, replace, unregister, get."""

    def test_register_extractor(self, registry):
        """Should register an extractor."""
        registry.register(DummyExtractor())
        assert "dummy" in registry.extractors
        assert registry.extractor_names == ["dummy"]

    def test_register_duplicate_raises(self, registry):
        """Duplicate registration should raise ValueError."""
        registry.register(DummyExtractor())
        with pytest.raises(ValueError, match="already registered"):
            registry.register(DummyExtractor())

    def test_replace_same_name_overwrites(self, registry):
        """Replace should overwrite extractor with the same name."""
        registry.register(DummyExtractor())
        registry.replace(DummyExtractor())  # same name, different instance
        assert "dummy" in registry.extractors
        assert len(registry.extractors) == 1

    def test_replace_different_name_adds(self, registry):
        """Replace with different name should add alongside existing."""
        registry.register(DummyExtractor())
        registry.replace(AnotherExtractor())
        assert "dummy" in registry.extractors
        assert "another" in registry.extractors
        assert len(registry.extractors) == 2

    def test_unregister_removes(self, registry):
        """Unregister should remove extractor."""
        registry.register(DummyExtractor())
        registry.unregister("dummy")
        assert "dummy" not in registry.extractors

    def test_unregister_nonexistent(self, registry):
        """Unregistering nonexistent extractor should not raise."""
        registry.unregister("nonexistent")  # no error

    def test_get_returns_extractor(self, registry):
        """get() should return the extractor instance."""
        ext = DummyExtractor()
        registry.register(ext)
        assert registry.get("dummy") is ext

    def test_get_nonexistent_raises(self, registry):
        """get() on missing name should raise KeyError."""
        with pytest.raises(KeyError, match="not found"):
            registry.get("missing")

    def test_clear_removes_all(self, registry):
        """clear() should remove all extractors."""
        registry.register(DummyExtractor())
        registry.register(AnotherExtractor())
        registry.clear()
        assert registry.extractor_names == []

    def test_extractor_names_sorted(self, registry):
        """extractor_names should be sorted alphabetically."""
        registry.register(AnotherExtractor())
        registry.register(DummyExtractor())
        assert registry.extractor_names == ["another", "dummy"]


class TestRegistryExtraction:
    """Feature extraction via registry."""

    def test_extract_all_empty(self, registry, dummy_candidate):
        """Empty registry should return empty features."""
        features = registry.extract_all(dummy_candidate)
        assert features == {}

    def test_extract_all_single(self, registry, dummy_candidate):
        """Should extract from single registered extractor."""
        registry.register(DummyExtractor())
        features = registry.extract_all(dummy_candidate)
        assert features == {"dummy_score": 0.85, "dummy_confidence": 1.0}

    def test_extract_all_multiple(self, registry, dummy_candidate):
        """Should merge features from multiple extractors."""
        registry.register(DummyExtractor())
        registry.register(AnotherExtractor())
        features = registry.extract_all(dummy_candidate)
        assert features["dummy_score"] == 0.85
        assert features["another_score"] == 0.42
        assert len(features) == 3

    def test_extract_all_skips_failing(self, registry, dummy_candidate):
        """Failing extractor should be skipped, others should run."""
        registry.register(DummyExtractor())
        registry.register(FailingExtractor())
        features = registry.extract_all(dummy_candidate)
        assert "dummy_score" in features
        assert len(features) == 2  # only dummy features

    def test_extract_all_skips_non_dict(self, registry, dummy_candidate):
        """Non-dict return should be skipped."""
        registry.register(NonDictExtractor())
        features = registry.extract_all(dummy_candidate)
        assert features == {}

    def test_extract_all_skips_non_numeric(self, registry, dummy_candidate):
        """Non-numeric values should be skipped."""
        registry.register(NonNumericExtractor())
        features = registry.extract_all(dummy_candidate)
        assert features == {"valid_score": 0.9}

    def test_extract_batch(self, registry, dummy_candidate):
        """extract_batch should return list of feature dicts."""
        registry.register(DummyExtractor())
        results = registry.extract_batch([dummy_candidate, dummy_candidate])
        assert len(results) == 2
        assert results[0]["dummy_score"] == 0.85


class TestRegistryFeatureCount:
    """Feature counting."""

    def test_feature_count_empty(self, registry):
        """Empty registry should have 0 features."""
        assert registry.feature_count == 0

    def test_feature_count_with_extractor(self, registry):
        """Should count features from registered extractors."""
        registry.register(DummyExtractor())
        assert registry.feature_count == 2

    def test_feature_count_multiple(self, registry):
        """Should sum features from multiple extractors."""
        registry.register(DummyExtractor())
        registry.register(AnotherExtractor())
        assert registry.feature_count == 3
