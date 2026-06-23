"""Final Ranker Engine — weighted score fusion, ranking, and submission generation.

Combines features from all previous phases into a single composite score:

    Inputs (from FeatureRegistry):
        Semantic Score     (Phase 5) — 4 features
        Career Intelligence (Phase 6) — 20 features
        Behavioral          (Phase 7) — 11 features
        Honeypot Detection  (Phase 8) — 10 features

    Scoring Pipeline:
        1. Run all registered extractors via FeatureRegistry
        2. Compute group-level sub-scores from individual features
        3. Compute final composite score with honeypot penalty
        4. Rank candidates by score (descending)
        5. Generate reasoning and output submission.csv

    Constraints:
        CPU-only, no GPU, no network, ≤16 GB RAM, <5 min runtime.
"""

import csv
import logging
import math
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from src.features.framework import FeatureRegistry
from src.parser.candidate_parser import Candidate

logger = logging.getLogger("redrob-ranker")

# ---------------------------------------------------------------------------
# Weight configuration
# ---------------------------------------------------------------------------

# Weights for the 5 scoring dimensions (must sum to 1.0)
WEIGHT_SEMANTIC = 0.20       # JD similarity match
WEIGHT_CAREER_INTELLIGENCE = 0.35   # Career domain signals
WEIGHT_AVAILABILITY = 0.10   # Availability/recency
WEIGHT_TRUST = 0.10          # Trust/reliability
WEIGHT_DEMAND = 0.10         # Demand/market signal
WEIGHT_ENGAGEMENT = 0.15     # Platform engagement
# Penalty coefficient: how much honeypot risk reduces the score
# score_final = base_score * (1 - honeypot_risk * PENALTY_COEF)
PENALTY_COEF = 0.5

# Output paths
SUBMISSION_CSV = "submission.csv"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class RankedCandidate:
    """A single ranked candidate result ready for CSV output."""
    candidate_id: str
    rank: int
    score: float
    reasoning: str


@dataclass
class FusionConfig:
    """Configuration for the score fusion process."""
    weight_semantic: float = WEIGHT_SEMANTIC
    weight_career_intelligence: float = WEIGHT_CAREER_INTELLIGENCE
    weight_availability: float = WEIGHT_AVAILABILITY
    weight_trust: float = WEIGHT_TRUST
    weight_demand: float = WEIGHT_DEMAND
    weight_engagement: float = WEIGHT_ENGAGEMENT
    penalty_coefficient: float = PENALTY_COEF

    def validate(self) -> None:
        """Ensure weights are valid."""
        positive = (
            self.weight_semantic + self.weight_career_intelligence
            + self.weight_availability + self.weight_trust
            + self.weight_demand + self.weight_engagement
        )
        if not (0.99 <= positive <= 1.01):
            logger.warning(
                "Positive weights sum to %.4f (expected ~1.0)", positive
            )


# ---------------------------------------------------------------------------
# Score Fusion Engine
# ---------------------------------------------------------------------------

class ScoreFusion:
    """Combines features from all extractors into a single composite score.

    Uses a weighted fusion model with honeypot penalty deduction.
    All intermediate scores are normalized to [0, 1].
    """

    def __init__(self, config: Optional[FusionConfig] = None) -> None:
        self.config = config or FusionConfig()
        self.config.validate()

    def compute(self, features: dict[str, float]) -> float:
        """Compute final composite score from all extracted features.

        Args:
            features: Full feature dict from FeatureRegistry.extract_all().

        Returns:
            Composite score in [0, 1] (higher = better fit).
        """
        cfg = self.config

        # ---- Semantic Score (Phase 5) ----
        semantic_scores = [
            features.get("jd_similarity_score", 0.0),
            features.get("summary_similarity_score", 0.0),
            features.get("headline_similarity_score", 0.0),
            features.get("career_similarity_score", 0.0),
        ]
        semantic = sum(semantic_scores) / len(semantic_scores) if semantic_scores else 0.0

        # ---- Career Intelligence (Phase 6) ----
        # Positive signals (16 features)
        career_positives = [
            features.get("product_company_score", 0.0),
            features.get("startup_experience_score", 0.0),
            features.get("engineering_depth_score", 0.0),
            features.get("relevant_tech_experience_score", 0.0),
            features.get("career_progression_score", 0.0),
            features.get("skill_relevance_score", 0.0),
            features.get("ranking_experience_score", 0.0),
            features.get("retrieval_experience_score", 0.0),
            features.get("recommendation_experience_score", 0.0),
            features.get("search_experience_score", 0.0),
            features.get("embeddings_experience_score", 0.0),
            features.get("vector_db_experience_score", 0.0),
            features.get("production_ml_score", 0.0),
            features.get("evaluation_framework_score", 0.0),
            features.get("python_engineering_score", 0.0),
            features.get("nlp_ir_experience_score", 0.0),
        ]
        career_positive = sum(career_positives) / len(career_positives) if career_positives else 0.0

        # Penalties (4 features) — subtract from career score
        career_penalties = [
            features.get("consulting_penalty", 0.0),
            features.get("research_penalty", 0.0),
            features.get("keyword_stuffing_penalty", 0.0),
            features.get("title_chasing_penalty", 0.0),
        ]
        career_penalty = sum(career_penalties) / len(career_penalties) if career_penalties else 0.0

        career = max(0.0, career_positive - career_penalty * 0.5)

        # ---- Behavioral Scores (Phase 7) ----
        availability = features.get("availability_score", 0.0)
        trust = features.get("trust_score", 0.0)
        demand = features.get("demand_score", 0.0)
        engagement = features.get("engagement_score", 0.0)

        # ---- Honeypot Penalty (Phase 8) ----
        honeypot_scores = [
            features.get("timeline_overlap_score", 0.0),
            features.get("timeline_gap_score", 0.0),
            features.get("timeline_impossible_score", 0.0),
            features.get("skill_zero_duration_expert_score", 0.0),
            features.get("skill_prolific_score", 0.0),
            features.get("progression_jump_score", 0.0),
            features.get("progression_rapid_churn_score", 0.0),
            features.get("seniority_mismatch_score", 0.0),
            features.get("title_experience_mismatch_score", 0.0),
            features.get("pattern_uniform_score", 0.0),
        ]
        honeypot_risk = max(honeypot_scores) if honeypot_scores else 0.0

        # ---- Final composite score ----
        base_score = (
            cfg.weight_semantic * semantic
            + cfg.weight_career_intelligence * career
            + cfg.weight_availability * availability
            + cfg.weight_trust * trust
            + cfg.weight_demand * demand
            + cfg.weight_engagement * engagement
        )

        # Apply honeypot penalty as multiplicative deduction
        penalty = honeypot_risk * cfg.penalty_coefficient
        final_score = base_score * (1.0 - penalty)

        return max(0.0, min(1.0, final_score))


# ---------------------------------------------------------------------------
# Reasoning Generator
# ---------------------------------------------------------------------------

class ReasoningGenerator:
    """Generates deterministic, concise reasoning for each candidate.

    Uses a template-based approach that selects the most informative
    signals from available features. No LLM, no external API, CPU-only.
    """

    def generate(self, features: dict[str, float], top_k_signals: int = 3) -> str:
        """Generate a 1-2 sentence reasoning summary.

        Args:
            features: Full feature dict from extraction.
            top_k_signals: Number of top signals to include.

        Returns:
            Concise string summary (max ~150 chars).
        """
        parts: list[str] = []

        # 1. Career signal (most informative)
        headline = self._format_career_signal(features)
        if headline:
            parts.append(headline)

        # 2. Top non-obvious strengths
        strengths = self._top_strengths(features, count=2)
        if strengths:
            parts.extend(strengths)

        # 3. Notable flags (if any)
        flags = self._notable_flags(features)
        if flags:
            parts.append(flags)

        return "; ".join(parts) if parts else "No strong signals."

    def _format_career_signal(self, f: dict[str, float]) -> str:
        """Extract the most informative career signal."""
        prod = f.get("product_company_score", 0.0)
        startup = f.get("startup_experience_score", 0.0)
        eng = f.get("engineering_depth_score", 0.0)
        ml = f.get("production_ml_score", 0.0)
        retrieval = f.get("retrieval_experience_score", 0.0)
        ranking = f.get("ranking_experience_score", 0.0)
        skill_rel = f.get("skill_relevance_score", 0.0)
        sim = f.get("jd_similarity_score", 0.0)

        # Find the strongest signal
        signals = [
            ("Ranking/Retrieval exp", max(ranking, retrieval), max(ranking, retrieval) > 0.3),
            ("Production ML", ml, ml > 0.3),
            ("Product company", prod, prod > 0.3),
            ("Engineering depth", eng, eng > 0.3),
            ("Startup exp", startup, startup > 0.3),
            ("Skill relevance", skill_rel, skill_rel > 0.3),
        ]

        active = [(label, score) for label, score, cond in signals if cond]
        if active:
            best = max(active, key=lambda x: x[1])
            score_val = f"{best[1]:.0%}"
            name = best[0]
            return f"{name} {score_val}"

        # Fallback: mention JD similarity
        if sim > 0.3:
            return f"JD match {sim:.0%}"
        return ""

    def _top_strengths(self, f: dict[str, float], count: int = 2) -> list[str]:
        """Identify top non-career strengths."""
        candidates = [
            ("Available", f.get("availability_score", 0.0), 0.3),
            ("Trust", f.get("trust_score", 0.0), 0.3),
            ("Demand", f.get("demand_score", 0.0), 0.3),
        ]
        active = [(label, score) for label, score, thresh in candidates if score > thresh]
        active.sort(key=lambda x: x[1], reverse=True)
        return [f"{label} {score:.0%}" for label, score in active[:count]]

    def _notable_flags(self, f: dict[str, float]) -> str:
        """Flag notable concerns (honeypot, consulting, etc)."""
        honeypot = max(
            f.get("timeline_impossible_score", 0.0),
            f.get("seniority_mismatch_score", 0.0),
            f.get("skill_zero_duration_expert_score", 0.0),
        )
        consulting = f.get("consulting_penalty", 0.0)
        research = f.get("research_penalty", 0.0)

        if honeypot > 0.5:
            return "⚠ High risk profile"
        if consulting > 0.5:
            return "Consulting background"
        if research > 0.3:
            return "Research-focused"
        return ""


# ---------------------------------------------------------------------------
# Final Ranker — orchestrates extraction → fusion → ranking → output
# ---------------------------------------------------------------------------

class FinalRanker:
    """Complete ranking pipeline: extract features, fuse scores, rank, output.

    Usage:
        registry = FeatureRegistry()
        registry.register(SemanticEngine())
        registry.register(CareerIntelligence())
        registry.register(BehavioralIntelligence())
        registry.register(HoneypotDetector())

        ranker = FinalRanker(registry)
        results = ranker.rank(candidates)
        ranker.save_submission(results, "submission.csv")
    """

    def __init__(
        self,
        registry: FeatureRegistry,
        fusion: Optional[ScoreFusion] = None,
        reasoning_gen: Optional[ReasoningGenerator] = None,
    ) -> None:
        self.registry = registry
        self.fusion = fusion or ScoreFusion()
        self.reasoning_gen = reasoning_gen or ReasoningGenerator()

    def rank(self, candidates: list[Candidate]) -> list[RankedCandidate]:
        """Run the full pipeline: extract → fuse → rank.

        Args:
            candidates: List of parsed Candidate objects.

        Returns:
            List of RankedCandidate sorted by score descending.
        """
        if not candidates:
            return []

        results: list[RankedCandidate] = []

        for c in candidates:
            features = self.registry.extract_all(c)
            score = self.fusion.compute(features)
            reasoning = self.reasoning_gen.generate(features)
            results.append(RankedCandidate(
                candidate_id=c.candidate_id,
                rank=0,  # assigned below
                score=round(score, 4),
                reasoning=reasoning,
            ))

        # Sort by score descending, assign ranks
        results.sort(key=lambda r: r.score, reverse=True)
        for i, r in enumerate(results):
            r.rank = i + 1

        return results

    def rank_batch(self, candidates: list[Candidate]) -> list[RankedCandidate]:
        """Alias for rank() for batch processing clarity."""
        return self.rank(candidates)

    def save_submission(
        self, results: list[RankedCandidate],
        output_path: str | Path = SUBMISSION_CSV,
    ) -> Path:
        """Save ranked candidates as submission.csv.

        Args:
            results: List of RankedCandidate from rank().
            output_path: Path to save CSV file.

        Returns:
            Path to the saved file.
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["candidate_id", "rank", "score", "reasoning"])
            for r in results:
                writer.writerow([r.candidate_id, r.rank, f"{r.score:.4f}", r.reasoning])

        logger.info("Saved %d ranked candidates to %s", len(results), path)
        return path.absolute()

    def load_submission(self, path: str | Path = SUBMISSION_CSV) -> list[RankedCandidate]:
        """Load a previously saved submission file.

        Args:
            path: Path to submission CSV.

        Returns:
            List of RankedCandidate.
        """
        results: list[RankedCandidate] = []
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                results.append(RankedCandidate(
                    candidate_id=row["candidate_id"],
                    rank=int(row["rank"]),
                    score=float(row["score"]),
                    reasoning=row["reasoning"],
                ))
        return results

    def __repr__(self) -> str:
        return (
            f"FinalRanker(extractors={self.registry.extractor_names}, "
            f"total_features={self.registry.feature_count})"
        )
