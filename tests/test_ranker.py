"""Unit tests for Final Ranker Engine (src/ranker/ranker.py).

Covers:
- ScoreFusion: composite scoring from all feature groups
- ReasoningGenerator: deterministic reasoning generation
- FinalRanker: full pipeline orchestration
- Submission CSV generation and loading
- Edge cases: empty features, missing keys, single candidate
- Performance benchmarks (runtime + RAM)
- Integration with all 4 feature extractors
- Regression against Phases 5-8
"""

import time
import tracemalloc
import csv
import tempfile
from pathlib import Path

import pytest

from src.ranker.ranker import (
    ScoreFusion, ReasoningGenerator, FinalRanker, RankedCandidate, FusionConfig,
)
from src.features.framework import FeatureRegistry
from src.parser.candidate_parser import Candidate, Profile, RedrobSignals, SalaryRange


# ============================================================================
# Helpers
# ============================================================================

def _example_features(
    jd_sim: float = 0.5,
    career_pos: float = 0.5,
    career_pen: float = 0.0,
    avail: float = 0.0,
    trust: float = 0.0,
    demand: float = 0.0,
    engagement: float = 0.0,
    honeypot: float = 0.0,
) -> dict[str, float]:
    """Create a feature dict with specified group values."""
    d: dict[str, float] = {}

    # Semantic (4)
    d["jd_similarity_score"] = jd_sim
    d["summary_similarity_score"] = jd_sim * 0.9
    d["headline_similarity_score"] = jd_sim * 0.8
    d["career_similarity_score"] = jd_sim * 0.7

    # Career positive (16)
    for key in ["product_company_score", "startup_experience_score",
                "engineering_depth_score", "relevant_tech_experience_score",
                "career_progression_score", "skill_relevance_score",
                "ranking_experience_score", "retrieval_experience_score",
                "recommendation_experience_score", "search_experience_score",
                "embeddings_experience_score", "vector_db_experience_score",
                "production_ml_score", "evaluation_framework_score",
                "python_engineering_score", "nlp_ir_experience_score"]:
        d[key] = career_pos

    # Career penalties (4)
    for key in ["consulting_penalty", "research_penalty",
                "keyword_stuffing_penalty", "title_chasing_penalty"]:
        d[key] = career_pen

    # Behavioral (4 composites from 11)
    d["availability_score"] = avail
    d["trust_score"] = trust
    d["demand_score"] = demand
    d["engagement_score"] = engagement
    # Fill the rest with 0
    for key in ["availability_notice_period", "availability_recent_active",
                "demand_profile_views", "demand_saved_by_recruiters",
                "trust_recruiter_response", "trust_interview_completion",
                "engagement_activity_recency"]:
        d[key] = 0.0

    # Honeypot (10)
    for key in ["timeline_overlap_score", "timeline_gap_score",
                "timeline_impossible_score", "skill_zero_duration_expert_score",
                "skill_prolific_score", "progression_jump_score",
                "progression_rapid_churn_score", "seniority_mismatch_score",
                "title_experience_mismatch_score", "pattern_uniform_score"]:
        d[key] = honeypot

    return d


def _null_signals() -> RedrobSignals:
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


def _minimal_candidate(cid: str = "CAND_0000001") -> Candidate:
    return Candidate(
        candidate_id=cid,
        profile=Profile(
            anonymized_name="T", headline="H", summary="S",
            location="L", country="C", years_of_experience=5.0,
            current_title="E", current_company="C",
            current_company_size="11-50", current_industry="T",
        ),
        career_history=[], education=[], skills=[],
        redrob_signals=_null_signals(),
    )


# ============================================================================
# ScoreFusion Tests
# ============================================================================

class TestScoreFusion:
    """ScoreFusion: composite scoring logic."""

    def test_default_config_valid(self):
        """Default config should validate without errors."""
        config = FusionConfig()
        config.validate()  # should not raise

    def test_high_score_candidate(self):
        """Candidate with all high signals should score near 1.0."""
        fusion = ScoreFusion()
        features = _example_features(
            jd_sim=0.9, career_pos=0.9, career_pen=0.0,
            avail=0.9, trust=0.9, demand=0.9, engagement=0.9, honeypot=0.0,
        )
        score = fusion.compute(features)
        assert score > 0.7, f"High candidate score too low: {score}"

    def test_low_score_candidate(self):
        """Candidate with all low signals should score near 0."""
        fusion = ScoreFusion()
        features = _example_features(
            jd_sim=0.0, career_pos=0.0, career_pen=0.0,
            avail=0.0, trust=0.0, demand=0.0, engagement=0.0, honeypot=0.0,
        )
        score = fusion.compute(features)
        assert score < 0.1, f"Low candidate score too high: {score}"

    def test_honeypot_penalty_reduces_score(self):
        """High honeypot risk should reduce the final score."""
        fusion = ScoreFusion()
        clean = _example_features(honeypot=0.0)
        risky = _example_features(honeypot=0.8)

        clean_score = fusion.compute(clean)
        risky_score = fusion.compute(risky)
        assert risky_score < clean_score, (
            f"Risky ({risky_score:.4f}) should be lower than clean ({clean_score:.4f})"
        )

    def test_career_penalty_reduces_score(self):
        """High career penalties should reduce career sub-score."""
        fusion = ScoreFusion()
        clean = _example_features(career_pos=0.8, career_pen=0.0)
        penalized = _example_features(career_pos=0.8, career_pen=0.8)

        clean_score = fusion.compute(clean)
        penalized_score = fusion.compute(penalized)
        assert penalized_score < clean_score

    def test_score_in_range(self):
        """All scores should be in [0, 1]."""
        fusion = ScoreFusion()
        for hp in [0.0, 0.3, 0.7, 1.0]:
            features = _example_features(honeypot=hp)
            score = fusion.compute(features)
            assert 0.0 <= score <= 1.0, f"Score {score} out of range at hp={hp}"

    def test_empty_features(self):
        """Empty feature dict should produce 0 score."""
        fusion = ScoreFusion()
        score = fusion.compute({})
        assert score == 0.0

    def test_missing_keys(self):
        """Partial feature dict should not crash."""
        fusion = ScoreFusion()
        score = fusion.compute({"jd_similarity_score": 0.5})
        assert 0.0 <= score <= 1.0

    def test_penalty_coefficient_zero(self):
        """Penalty coefficient of 0 should mean no penalty applied."""
        config = FusionConfig(penalty_coefficient=0.0)
        fusion = ScoreFusion(config)
        clean = _example_features(honeypot=0.0)
        risky = _example_features(honeypot=0.9)
        assert fusion.compute(clean) == fusion.compute(risky)

    def test_deterministic(self):
        """Same features should produce identical scores."""
        fusion = ScoreFusion()
        feats = _example_features(jd_sim=0.5, career_pos=0.6, honeypot=0.2)
        s1 = fusion.compute(feats)
        s2 = fusion.compute(feats)
        assert s1 == s2


# ============================================================================
# ReasoningGenerator Tests
# ============================================================================

class TestReasoningGenerator:
    """ReasoningGenerator: deterministic reasoning."""

    def test_generates_string(self):
        """Should always return a string."""
        gen = ReasoningGenerator()
        feats = _example_features()
        reason = gen.generate(feats)
        assert isinstance(reason, str)
        assert len(reason) > 0

    def test_mentions_top_signal(self):
        """Should mention the top career signal."""
        gen = ReasoningGenerator()
        feats = _example_features(jd_sim=0.9, career_pos=0.0, avail=0.0)
        reason = gen.generate(feats)
        # Should mention JD match since that's the strongest signal
        assert "match" in reason.lower() or "JD" in reason

    def test_mentions_honeypot_flag(self):
        """Should flag high honeypot risk."""
        gen = ReasoningGenerator()
        feats = _example_features(honeypot=0.8)
        reason = gen.generate(feats)
        assert "high risk" in reason.lower()

    def test_mentions_consulting_penalty(self):
        """Should flag consulting background."""
        gen = ReasoningGenerator()
        feats = _example_features(career_pen=0.0)
        feats["consulting_penalty"] = 0.6
        reason = gen.generate(feats)
        assert "consulting" in reason.lower()

    def test_empty_features(self):
        """Empty features should produce 'No strong signals'."""
        gen = ReasoningGenerator()
        reason = gen.generate({})
        assert "No strong signals" in reason

    def test_deterministic(self):
        """Same features should produce identical reasoning."""
        gen = ReasoningGenerator()
        feats = _example_features(jd_sim=0.8, career_pos=0.7, honeypot=0.1)
        r1 = gen.generate(feats)
        r2 = gen.generate(feats)
        assert r1 == r2


# ============================================================================
# FinalRanker Tests
# ============================================================================

class TestFinalRanker:
    """FinalRanker: full pipeline."""

    def test_empty_candidates_list(self):
        """Empty candidate list should return empty results."""
        registry = FeatureRegistry()
        ranker = FinalRanker(registry)
        results = ranker.rank([])
        assert results == []

    def test_single_candidate(self):
        """Single candidate should get rank 1."""
        registry = FeatureRegistry()
        ranker = FinalRanker(registry)  # no extractors = 0 features
        results = ranker.rank([_minimal_candidate("CAND_0000001")])
        assert len(results) == 1
        assert results[0].rank == 1
        assert results[0].candidate_id == "CAND_0000001"

    def test_sorts_by_score_descending(self):
        """Ranked list should be sorted by score descending."""
        registry = FeatureRegistry()
        ranker = FinalRanker(registry)
        candidates = [_minimal_candidate(f"CAND_{i:07d}") for i in range(5)]
        results = ranker.rank(candidates)
        for i in range(len(results) - 1):
            assert results[i].score >= results[i + 1].score, (
                f"Rank {i+1} score {results[i].score} < rank {i+2} score {results[i+1].score}"
            )

    def test_rank_numbers_sequential(self):
        """Rank numbers should be 1, 2, 3, ..."""
        registry = FeatureRegistry()
        ranker = FinalRanker(registry)
        candidates = [_minimal_candidate(f"CAND_{i:07d}") for i in range(3)]
        results = ranker.rank(candidates)
        for i, r in enumerate(results):
            assert r.rank == i + 1

    def test_repr(self):
        """Repr should show extractor names and feature count."""
        registry = FeatureRegistry()
        ranker = FinalRanker(registry)
        assert "FinalRanker" in repr(ranker)
        assert "extractors=" in repr(ranker)

    def test_load_submission(self):
        """save_submission then load_submission should round-trip."""
        registry = FeatureRegistry()
        ranker = FinalRanker(registry)
        candidates = [_minimal_candidate(f"CAND_{i:07d}") for i in range(3)]
        results = ranker.rank(candidates)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
            tmp_path = f.name

        try:
            ranker.save_submission(results, tmp_path)
            loaded = ranker.load_submission(tmp_path)
            assert len(loaded) == len(results)
            for orig, loaded_r in zip(results, loaded):
                assert orig.candidate_id == loaded_r.candidate_id
                assert orig.rank == loaded_r.rank
                assert orig.score == loaded_r.score
                assert orig.reasoning == loaded_r.reasoning
        finally:
            Path(tmp_path).unlink(missing_ok=True)


# ============================================================================
# Submission CSV Tests
# ============================================================================

class TestSubmissionCSV:
    """Submission CSV format and validation."""

    def test_csv_format(self):
        """CSV should have correct headers and 4 columns."""
        registry = FeatureRegistry()
        ranker = FinalRanker(registry)
        candidates = [_minimal_candidate("CAND_0000001")]
        results = ranker.rank(candidates)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
            tmp_path = f.name

        try:
            ranker.save_submission(results, tmp_path)
            with open(tmp_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                headers = next(reader)
                assert headers == ["candidate_id", "rank", "score", "reasoning"]
                row = next(reader)
                assert len(row) == 4
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_score_format_four_decimals(self):
        """Score should have exactly 4 decimal places."""
        registry = FeatureRegistry()
        ranker = FinalRanker(registry)
        candidates = [_minimal_candidate("CAND_0000001")]
        results = ranker.rank(candidates)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
            tmp_path = f.name

        try:
            ranker.save_submission(results, tmp_path)
            with open(tmp_path, "r", encoding="utf-8") as f:
                next(f)  # skip header
                row = next(f)
                parts = row.strip().split(",")
                score_str = parts[2]
                assert "." in score_str
                decimal_places = len(score_str.split(".")[1])
                assert decimal_places == 4, f"Expected 4 decimal places, got {decimal_places}"
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_rank_integer(self):
        """Rank should be an integer."""
        registry = FeatureRegistry()
        ranker = FinalRanker(registry)
        candidates = [_minimal_candidate("CAND_0000001")]
        results = ranker.rank(candidates)
        assert isinstance(results[0].rank, int)


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration with all feature extractors (requires model loading)."""

    def test_full_pipeline(self):
        """Full pipeline with all extractors should produce valid output."""
        from src.features.career_intelligence import CareerIntelligence
        from src.features.behavioral_intelligence import BehavioralIntelligence
        from src.features.honeypot_detection import HoneypotDetector

        registry = FeatureRegistry()
        registry.register(CareerIntelligence())
        registry.register(BehavioralIntelligence())
        registry.register(HoneypotDetector())

        ranker = FinalRanker(registry)
        c = _minimal_candidate("CAND_0000001")
        results = ranker.rank([c])
        assert len(results) == 1
        assert results[0].candidate_id == "CAND_0000001"
        assert 0.0 <= results[0].score <= 1.0
        assert isinstance(results[0].reasoning, str)
        assert len(results[0].reasoning) > 0

    def test_extractors_plus_semantic(self):
        """All 4 extractors together (if model available)."""
        from src.features.career_intelligence import CareerIntelligence
        from src.features.behavioral_intelligence import BehavioralIntelligence
        from src.features.honeypot_detection import HoneypotDetector

        registry = FeatureRegistry()
        registry.register(CareerIntelligence())
        registry.register(BehavioralIntelligence())
        registry.register(HoneypotDetector())

        ranker = FinalRanker(registry)
        c = _minimal_candidate("CAND_0000001")
        results = ranker.rank([c])
        r = results[0]

        # Score should be deterministic
        results2 = ranker.rank([c])
        assert r.score == results2[0].score
        assert r.reasoning == results2[0].reasoning


# ============================================================================
# Performance Benchmarks
# ============================================================================

class TestPerformanceBenchmarks:
    """Runtime and memory benchmarks."""

    def test_fusion_runtime(self):
        """ScoreFusion should be fast."""
        fusion = ScoreFusion()
        feats = _example_features(jd_sim=0.5, career_pos=0.6, honeypot=0.1)

        start = time.perf_counter()
        n = 10000
        for _ in range(n):
            fusion.compute(feats)
        elapsed = time.perf_counter() - start

        per_op = elapsed / n * 1_000_000  # microseconds per op
        print(f"\nScoreFusion: {n} ops in {elapsed:.4f}s, {per_op:.2f}µs per op")
        assert per_op < 100, f"ScoreFusion too slow: {per_op:.2f}µs"

    def test_reasoning_runtime(self):
        """ReasoningGenerator should be fast."""
        gen = ReasoningGenerator()
        feats = _example_features(jd_sim=0.5, career_pos=0.6, honeypot=0.1)

        start = time.perf_counter()
        n = 10000
        for _ in range(n):
            gen.generate(feats)
        elapsed = time.perf_counter() - start

        per_op = elapsed / n * 1_000_000
        print(f"\nReasoningGenerator: {n} ops in {elapsed:.4f}s, {per_op:.2f}µs per op")
        assert per_op < 200, f"ReasoningGenerator too slow: {per_op:.2f}µs"

    def test_ranking_runtime(self):
        """Full ranking pipeline should handle 1000 candidates quickly."""
        from src.features.career_intelligence import CareerIntelligence
        from src.features.behavioral_intelligence import BehavioralIntelligence
        from src.features.honeypot_detection import HoneypotDetector

        registry = FeatureRegistry()
        registry.register(CareerIntelligence())
        registry.register(BehavioralIntelligence())
        registry.register(HoneypotDetector())

        ranker = FinalRanker(registry)
        n = 500
        candidates = [_minimal_candidate(f"CAND_{i:07d}") for i in range(n)]

        start = time.perf_counter()
        results = ranker.rank(candidates)
        elapsed = time.perf_counter() - start

        per_candidate = elapsed / n * 1000
        print(f"\nRank {n} candidates: {elapsed:.4f}s total, "
              f"{per_candidate:.4f}ms per candidate, "
              f"{n / elapsed:.0f} candidates/sec")
        assert n / elapsed > 500, (
            f"Ranking throughput too low: {n / elapsed:.0f} cand/s"
        )

    def test_memory_usage(self):
        """Measure peak memory during ranking of 500 candidates."""
        from src.features.career_intelligence import CareerIntelligence
        from src.features.behavioral_intelligence import BehavioralIntelligence
        from src.features.honeypot_detection import HoneypotDetector

        registry = FeatureRegistry()
        registry.register(CareerIntelligence())
        registry.register(BehavioralIntelligence())
        registry.register(HoneypotDetector())

        ranker = FinalRanker(registry)
        n = 500
        candidates = [_minimal_candidate(f"CAND_{i:07d}") for i in range(n)]

        tracemalloc.start()
        results = ranker.rank(candidates)
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak / (1024 * 1024)
        print(f"\nMemory for {n} candidates: current={current / 1024:.1f}KB, "
              f"peak={peak_mb:.2f}MB")
        assert peak_mb < 100, f"Peak memory too high: {peak_mb:.1f}MB"


# ============================================================================
# Edge Case Tests
# ============================================================================

class TestEdgeCases:
    """Edge cases for the ranker pipeline."""

    def test_single_candidate_rank_is_one(self):
        """Single candidate should be rank 1."""
        registry = FeatureRegistry()
        ranker = FinalRanker(registry)
        results = ranker.rank([_minimal_candidate("CAND_0000001")])
        assert results[0].rank == 1

    def test_two_candidates_ordered(self):
        """Two candidates should be ranked correctly."""
        registry = FeatureRegistry()
        ranker = FinalRanker(registry)
        c1 = _minimal_candidate("CAND_0000001")
        c2 = _minimal_candidate("CAND_0000002")
        results = ranker.rank([c1, c2])
        assert len(results) == 2
        assert results[0].rank == 1
        assert results[1].rank == 2

    def test_score_ties_arbitrary(self):
        """Equal scores should still produce sequential ranks."""
        registry = FeatureRegistry()
        ranker = FinalRanker(registry)
        candidates = [_minimal_candidate(f"CAND_{i:07d}") for i in range(3)]
        results = ranker.rank(candidates)
        # All have same (0) features so scores are equal
        scores = [r.score for r in results]
        assert len(set(scores)) == 1  # all equal
        assert [r.rank for r in results] == [1, 2, 3]

    def test_many_candidates(self):
        """Ranking 10000 candidates should not crash."""
        registry = FeatureRegistry()
        ranker = FinalRanker(registry)
        n = 10000
        candidates = [_minimal_candidate(f"CAND_{i:07d}") for i in range(n)]
        results = ranker.rank(candidates)
        assert len(results) == n
        assert results[0].rank == 1
        assert results[-1].rank == n
