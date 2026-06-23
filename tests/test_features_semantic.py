"""Unit tests for Semantic Engine (src/features/semantic.py).

Covers:
- Initialization and model loading
- JD text loading and fallback behavior
- Feature extraction with valid candidates
- Empty/missing field handling
- Score ranges and clamping
- Integration with FeatureRegistry
- Performance benchmarks (runtime + RAM)
"""

import time
import tracemalloc
from pathlib import Path


import numpy as np
import pytest

from src.features.semantic import SemanticEngine, FALLBACK_JD_TEXT
from src.features.framework import FeatureRegistry
from src.parser.candidate_parser import Candidate, Profile, RedrobSignals, SalaryRange


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def engine() -> SemanticEngine:
    """Create a shared SemanticEngine for all tests in the module.

    The model is loaded once at the class level and shared across
    all test functions, keeping tests fast.
    """
    return SemanticEngine()


@pytest.fixture
def sample_candidate() -> Candidate:
    """Create a candidate with comprehensive profile text."""
    return Candidate(
        candidate_id="CAND_0000001",
        profile=Profile(
            anonymized_name="Test Engineer",
            headline="Senior ML Engineer specializing in retrieval systems and ranking",
            summary=(
                "Experienced machine learning engineer with 7 years building "
                "production ranking and recommendation systems. Proficient in "
                "Python, PyTorch, and embedding-based retrieval."
            ),
            location="Pune",
            country="India",
            years_of_experience=7.0,
            current_title="Senior ML Engineer",
            current_company="TechCorp",
            current_company_size="1001-5000",
            current_industry="Software",
        ),
        career_history=[
            MockCareerEntry(
                "TechCorp",
                "Senior ML Engineer",
                "Built production recommendation system serving 1M+ users. "
                "Designed embedding-based retrieval pipeline with FAISS.",
            ),
            MockCareerEntry(
                "StartupX",
                "ML Engineer",
                "Developed ranking algorithms for job search. "
                "Implemented A/B testing framework for offline evaluation.",
            ),
        ],
        education=[],
        skills=[],
        redrob_signals=MockSignals(),
    )


@pytest.fixture
def candidate_empty_text() -> Candidate:
    """Create a candidate with empty text fields (edge case)."""
    return Candidate(
        candidate_id="CAND_0000002",
        profile=Profile(
            anonymized_name="Minimal",
            headline="",
            summary="",
            location="",
            country="",
            years_of_experience=0.0,
            current_title="",
            current_company="",
            current_company_size="",
            current_industry="",
        ),
        career_history=[],
        education=[],
        skills=[],
        redrob_signals=MockSignals(),
    )


@pytest.fixture
def candidate_non_tech() -> Candidate:
    """Create a candidate with non-technical profile (low similarity expected)."""
    return Candidate(
        candidate_id="CAND_0000003",
        profile=Profile(
            anonymized_name="Marketing Pro",
            headline="Marketing Manager | Brand Strategy | Social Media",
            summary=(
                "Experienced marketing professional with expertise in brand "
                "management, social media strategy, and content creation."
            ),
            location="Mumbai",
            country="India",
            years_of_experience=8.0,
            current_title="Marketing Manager",
            current_company="BrandCorp",
            current_company_size="501-1000",
            current_industry="Marketing",
        ),
        career_history=[
            MockCareerEntry(
                "BrandCorp",
                "Marketing Manager",
                "Led brand strategy for consumer products. Managed social media "
                "campaigns and content marketing initiatives.",
            ),
        ],
        education=[],
        skills=[],
        redrob_signals=MockSignals(),
    )


# ---------------------------------------------------------------------------
# Helper: mock data structures
# ---------------------------------------------------------------------------

class MockCareerEntry:
    """Simplified career entry for test fixtures."""
    def __init__(self, company: str, title: str, description: str):
        self.company = company
        self.title = title
        self.start_date = "2020-01-01"
        self.end_date = None
        self.duration_months = 36
        self.is_current = True
        self.industry = "Tech"
        self.company_size = "1001-5000"
        self.description = description


def MockSignals() -> RedrobSignals:
    """Create a default empty RedrobSignals for tests."""
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


# ---------------------------------------------------------------------------
# Initialization Tests
# ---------------------------------------------------------------------------

class TestSemanticInit:
    """Engine initialization and model loading."""

    def test_name_and_features(self, engine):
        """Engine should expose correct name and features list."""
        assert engine.name == "semantic"
        assert engine.description
        assert "sentence-transformers" in engine.description.lower()
        assert len(engine.features) == 4

    def test_model_loaded(self, engine):
        """Model should be a class-level singleton."""
        assert SemanticEngine._model is not None
        assert SemanticEngine._jd_embedding is not None
        assert SemanticEngine._jd_embedding.shape == (384,)

    def test_multiple_instances_share_model(self):
        """Multiple instances should share the same model and JD embedding."""
        e1 = SemanticEngine()
        e2 = SemanticEngine()
        assert e1._model is e2._model
        assert e1._jd_embedding is e2._jd_embedding

    def test_fallback_jd_text(self, tmp_path):
        """Should use fallback text when JD file is missing."""
        engine = SemanticEngine(jd_path=tmp_path / "nonexistent.txt")
        assert engine._jd_text == FALLBACK_JD_TEXT

    def test_fallback_empty_file(self, tmp_path):
        """Should use fallback text when JD file is empty."""
        jd_file = tmp_path / "empty.txt"
        jd_file.write_text("", encoding="utf-8")
        engine = SemanticEngine(jd_path=jd_file)
        assert engine._jd_text == FALLBACK_JD_TEXT


# ---------------------------------------------------------------------------
# Feature Extraction Tests
# ---------------------------------------------------------------------------

class TestSemanticExtraction:
    """Feature extraction behavior."""

    def test_extract_returns_dict(self, engine, sample_candidate):
        """Extract should return a dict of 4 features."""
        features = engine.extract(sample_candidate)
        assert isinstance(features, dict)
        assert len(features) == 4
        for f in engine.features:
            assert f in features

    def test_scores_in_range(self, engine, sample_candidate):
        """All scores should be between 0.0 and 1.0."""
        features = engine.extract(sample_candidate)
        for name, score in features.items():
            assert 0.0 <= score <= 1.0, (
                f"{name} = {score} outside [0, 1]"
            )

    def test_extract_deterministic(self, engine, sample_candidate):
        """Same candidate should produce same scores."""
        f1 = engine.extract(sample_candidate)
        f2 = engine.extract(sample_candidate)
        for key in f1:
            assert abs(f1[key] - f2[key]) < 1e-6, (
                f"{key} differs: {f1[key]} vs {f2[key]}"
            )

    def test_empty_text_fields(self, engine, candidate_empty_text):
        """Empty text fields should produce 0.0 scores."""
        features = engine.extract(candidate_empty_text)
        for name, score in features.items():
            assert score == 0.0, (
                f"{name} = {score} expected 0.0 for empty text"
            )

    def test_non_tech_lower_than_tech(
        self, engine, sample_candidate, candidate_non_tech
    ):
        """Tech candidate should score higher than non-tech candidate."""
        tech_features = engine.extract(sample_candidate)
        non_tech_features = engine.extract(candidate_non_tech)

        # The overall JD similarity should be higher for tech candidate
        assert tech_features["jd_similarity_score"] >= non_tech_features["jd_similarity_score"], (
            f"Tech ({tech_features['jd_similarity_score']}) < "
            f"Non-tech ({non_tech_features['jd_similarity_score']})"
        )


# ---------------------------------------------------------------------------
# Batch Pre-computation Tests
# ---------------------------------------------------------------------------

class TestSemanticBatch:
    """Batch pre-computation behavior."""

    def test_precompute_populates_cache(
        self, engine, sample_candidate, candidate_non_tech
    ):
        """Precompute should populate embedding caches."""
        engine.clear_cache()
        candidates = [sample_candidate, candidate_non_tech]
        engine.precompute(candidates)

        assert len(engine._combined_embeddings) == 2
        assert len(engine._summary_embeddings) == 2
        assert len(engine._headline_embeddings) == 2
        assert len(engine._career_embeddings) == 2

    def test_precompute_then_extract(
        self, engine, sample_candidate
    ):
        """Extract after precompute should return valid results."""
        engine.clear_cache()
        engine.precompute([sample_candidate])
        features = engine.extract(sample_candidate)

        for score in features.values():
            assert 0.0 <= score <= 1.0

    def test_precompute_empty_list(self, engine):
        """Precompute with empty list should not error."""
        engine.clear_cache()
        engine.precompute([])
        assert len(engine._combined_embeddings) == 0

    def test_cache_clear(self, engine, sample_candidate):
        """Clear should empty all caches."""
        engine.precompute([sample_candidate])
        assert len(engine._combined_embeddings) == 1
        engine.clear_cache()
        assert len(engine._combined_embeddings) == 0
        assert len(engine._summary_embeddings) == 0
        assert len(engine._headline_embeddings) == 0
        assert len(engine._career_embeddings) == 0


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------

class TestSemanticIntegration:
    """Integration with FeatureRegistry."""

    def test_registry_register(self, engine):
        """SemanticEngine should register in FeatureRegistry."""
        registry = FeatureRegistry()
        registry.register(engine)
        assert "semantic" in registry.extractors
        assert registry.feature_count == 4

    def test_registry_extract_single(
        self, engine, sample_candidate
    ):
        """Registry should extract features via SemanticEngine."""
        registry = FeatureRegistry()
        registry.register(engine)
        features = registry.extract_all(sample_candidate)

        assert "jd_similarity_score" in features
        assert "summary_similarity_score" in features
        assert "headline_similarity_score" in features
        assert "career_similarity_score" in features

    def test_registry_extract_batch(
        self, engine, sample_candidate, candidate_non_tech
    ):
        """Registry batch extraction should work with SemanticEngine."""
        registry = FeatureRegistry()
        registry.register(engine)
        results = registry.extract_batch([
            sample_candidate, candidate_non_tech
        ])

        assert len(results) == 2
        for r in results:
            assert len(r) == 4
            for v in r.values():
                assert 0.0 <= v <= 1.0

    def test_full_pipeline_integration(self, engine, sample_candidate):
        """Simulate the full pipeline: precompute → extract → collect."""
        engine.clear_cache()

        # Simulate batch of candidates
        candidates = [sample_candidate] * 3
        # Use different IDs
        candidates[0].candidate_id = "CAND_0000010"
        candidates[1].candidate_id = "CAND_0000011"
        candidates[2].candidate_id = "CAND_0000012"

        engine.precompute(candidates)

        # Extract features for each
        all_features = [engine.extract(c) for c in candidates]
        assert len(all_features) == 3

        # Scores should be identical (identical profiles)
        for key in engine.features:
            scores = [f[key] for f in all_features]
            assert max(scores) - min(scores) < 1e-6, (
                f"{key} varies across identical profiles: {scores}"
            )


# ---------------------------------------------------------------------------
# Disk Cache Tests
# ---------------------------------------------------------------------------

class TestSemanticDiskCache:
    """Save/load embedding cache behavior."""

    def test_save_embeddings(self, engine, sample_candidate, tmp_path):
        """Save should persist all 4 embedding dicts to disk."""
        engine.clear_cache()
        engine.precompute([sample_candidate])
        engine.save_embeddings(tmp_path)

        # Check files exist
        assert (tmp_path / "combined_embeddings.npz").exists()
        assert (tmp_path / "summary_embeddings.npz").exists()
        assert (tmp_path / "headline_embeddings.npz").exists()
        assert (tmp_path / "career_embeddings.npz").exists()
        assert (tmp_path / "jd_embedding.npy").exists()

    def test_load_embeddings(self, engine, sample_candidate, tmp_path):
        """Load should restore embeddings and enable extraction."""
        engine.clear_cache()
        engine.precompute([sample_candidate])
        engine.save_embeddings(tmp_path)

        # Create a fresh engine and load
        fresh_engine = SemanticEngine()
        fresh_engine.clear_cache()
        fresh_engine.load_embeddings(tmp_path)

        # Should have cached candidates
        assert len(fresh_engine._combined_embeddings) == 1
        assert len(fresh_engine._summary_embeddings) == 1
        assert len(fresh_engine._headline_embeddings) == 1
        assert len(fresh_engine._career_embeddings) == 1
        assert fresh_engine._jd_embedding is not None

        # Extract should work without model
        features = fresh_engine.extract(sample_candidate)
        assert len(features) == 4
        for score in features.values():
            assert 0.0 <= score <= 1.0

    def test_save_without_precompute_raises(self, engine, tmp_path):
        """Save without precompute should raise ValueError."""
        engine.clear_cache()
        with pytest.raises(ValueError, match="No embeddings to save"):
            engine.save_embeddings(tmp_path)

    def test_load_nonexistent_directory(self, engine):
        """Load from nonexistent directory should raise FileNotFoundError."""
        from pathlib import Path
        with pytest.raises(FileNotFoundError):
            engine.load_embeddings(Path("/nonexistent/path"))

    def test_load_then_extract_matches_precomputed(
        self, engine, sample_candidate, tmp_path
    ):
        """Scores from loaded embeddings should match original scores."""
        # Get original scores
        engine.clear_cache()
        engine.precompute([sample_candidate])
        original = engine.extract(sample_candidate)

        # Save and reload
        engine.save_embeddings(tmp_path)
        fresh_engine = SemanticEngine()
        fresh_engine.clear_cache()
        fresh_engine.load_embeddings(tmp_path)
        loaded = fresh_engine.extract(sample_candidate)

        # Compare
        for key in original:
            assert abs(original[key] - loaded[key]) < 1e-6, (
                f"{key} differs: {original[key]} vs {loaded[key]}"
            )


# ---------------------------------------------------------------------------
# Performance Benchmarks
# ---------------------------------------------------------------------------

class TestSemanticBenchmarks:
    """Runtime and memory benchmarks."""

    @pytest.mark.parametrize("n_candidates", [10, 100])
    def test_precompute_runtime(self, engine, n_candidates):
        """Measure precompute runtime for N candidates."""
        candidates = [
            Candidate(
                candidate_id=f"CAND_{i:07d}",
                profile=Profile(
                    anonymized_name=f"Test {i}",
                    headline="Software Engineer with ML experience" if i % 2 == 0 else "Marketing professional",
                    summary=(
                        "Engineer with 5 years experience in ML and data science." if i % 2 == 0
                        else "Marketing professional with brand strategy expertise."
                    ),
                    location="Pune",
                    country="India",
                    years_of_experience=5.0,
                    current_title="ML Engineer" if i % 2 == 0 else "Marketing Manager",
                    current_company=f"Company_{i}",
                    current_company_size="1001-5000" if i % 2 == 0 else "51-200",
                    current_industry="Tech" if i % 2 == 0 else "Marketing",
                ),
                career_history=[
                    MockCareerEntry(
                        f"Company_{i}",
                        "Engineer",
                        "Built ML models for production." if i % 2 == 0 else "Managed marketing campaigns.",
                    )
                ],
                education=[],
                skills=[],
                redrob_signals=MockSignals(),
            )
            for i in range(n_candidates)
        ]

        engine.clear_cache()

        start = time.perf_counter()
        engine.precompute(candidates)
        elapsed = time.perf_counter() - start

        per_candidate = elapsed / n_candidates
        print(f"\nPrecompute {n_candidates} candidates: {elapsed:.4f}s total, "
              f"{per_candidate * 1000:.2f}ms per candidate, "
              f"{n_candidates / elapsed:.0f} candidates/sec")

        # Should process at least 5 candidates/sec on CPU
        assert n_candidates / elapsed > 5.0, (
            f"Throughput too low: {n_candidates / elapsed:.1f} cand/s"
        )
        assert elapsed < 60.0, f"Precompute took too long: {elapsed:.1f}s"

    @pytest.mark.parametrize("n_candidates", [10, 100])
    def test_extract_runtime(self, engine, n_candidates, sample_candidate):
        """Measure extract() runtime for N candidates."""
        # Must precompute first
        candidates = [
            Candidate(
                candidate_id=f"CAND_{i:07d}",
                profile=sample_candidate.profile,
                career_history=sample_candidate.career_history,
                education=[],
                skills=[],
                redrob_signals=MockSignals(),
            )
            for i in range(n_candidates)
        ]
        engine.clear_cache()
        engine.precompute(candidates)

        start = time.perf_counter()
        results = [engine.extract(c) for c in candidates]
        elapsed = time.perf_counter() - start

        per_extract = elapsed / n_candidates
        print(f"\nExtract {n_candidates} candidates: {elapsed:.4f}s total, "
              f"{per_extract * 1000:.4f}ms per candidate")

        # extract() should be fast (sub-millisecond per candidate with cache)
        assert per_extract < 0.01, f"Extract too slow: {per_extract * 1000:.2f}ms"

    def test_memory_usage(self, engine, sample_candidate):
        """Measure peak memory during precompute of 100 candidates.

        Note: tracemalloc captures Python-side allocations only.
        The sentence-transformers model weights (~80 MB) are loaded
        via PyTorch native code and are NOT included in this measurement.
        Actual process memory would be approximately 80 MB (model) + peak.
        """
        n = 100
        candidates = [
            Candidate(
                candidate_id=f"CAND_{i:07d}",
                profile=sample_candidate.profile,
                career_history=sample_candidate.career_history,
                education=[],
                skills=[],
                redrob_signals=MockSignals(),
            )
            for i in range(n)
        ]
        engine.clear_cache()

        tracemalloc.start()
        engine.precompute(candidates)
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak / (1024 * 1024)
        print(f"\nMemory for {n} candidates: current={current / 1024:.1f}KB, "
              f"peak={peak_mb:.2f}MB")

        # Peak Python-side allocations should be well under 500 MB.
        # Actual process memory ~80 MB (model) + peak.
        assert peak_mb < 500, f"Peak Python memory too high: {peak_mb:.1f}MB"
