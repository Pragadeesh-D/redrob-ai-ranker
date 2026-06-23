"""Behavioral Intelligence Engine — Redrob behavioral signal scoring.

Computes feature scores from the candidate's Redrob platform signals:
availability (open to work, notice period, recency), demand (profile views,
saved by recruiters), trust (recruiter response rate, interview completion),
and engagement (views, saves, activity recency).

All features are computed directly from structured RedrobSignals fields.
No ML models, no network calls, CPU-only.

Features produced (11 total):
    Availability Score (3):
        availability_score: Composite availability signal
        availability_notice_period: Notice period score (shorter = more available)
        availability_recent_active: Recent activity score

    Demand Score (3):
        demand_score: Composite demand signal
        demand_profile_views: Profile view demand score
        demand_saved_by_recruiters: Saved-by-recruiters demand score

    Trust Score (3):
        trust_score: Composite trust signal
        trust_recruiter_response: Recruiter response rate score
        trust_interview_completion: Interview completion rate score

    Engagement Score (2):
        engagement_score: Composite engagement signal
        engagement_activity_recency: Activity recency score
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from src.features.base import BaseFeatureExtractor
from src.parser.candidate_parser import Candidate

logger = logging.getLogger("redrob-ranker")

# ---------------------------------------------------------------------------
# Normalization constants
# ---------------------------------------------------------------------------

# Demand / Engagement — profile views (typical range ~0-200+)
VIEWS_LOW = 10       # 10 views → ~0.3
VIEWS_MEDIUM = 50    # 50 views → ~0.6
VIEWS_HIGH = 150     # 150+ views → ~1.0

# Demand / Engagement — saved by recruiters (typical range ~0-50+)
SAVES_LOW = 5        # 5 saves → ~0.3
SAVES_MEDIUM = 20    # 20 saves → ~0.6
SAVES_HIGH = 50      # 50+ saves → ~1.0

# Availability — notice period (days)
NOTICE_IMMEDIATE = 0     # 0 days → 1.0
NOTICE_SHORT = 15        # 15 days → 0.75
NOTICE_STANDARD = 30     # 30 days → 0.5
NOTICE_LONG = 60         # 60 days → 0.25
NOTICE_EXTENDED = 90     # 90+ days → 0.0

# Recency — days since last active
ACTIVITY_TODAY = 0       # 0 days → 1.0
ACTIVITY_WEEK = 7        # 7 days → 0.8
ACTIVITY_MONTH = 30      # 30 days → 0.5
ACTIVITY_QUARTER = 90    # 90 days → 0.2
ACTIVITY_STALE = 180     # 180+ days → 0.0

# Trust — recruiter response rate
RATE_LOW = 0.25          # 25% → ~0.3
RATE_MEDIUM = 0.5        # 50% → ~0.6
RATE_HIGH = 0.8          # 80%+ → ~1.0


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------

def _normalize_linear(value: float, x1: float, y1: float, x2: float, y2: float) -> float:
    """Linearly map value from (x1,x2) range to (y1,y2) range, clamped."""
    if x2 == x1:
        return y1
    ratio = (value - x1) / (x2 - x1)
    return max(min(ratio * (y2 - y1) + y1, max(y1, y2)), min(y1, y2))


def _score_views(views: int) -> float:
    """Normalise profile_views_received_30d to 0.0-1.0."""
    if views <= 0:
        return 0.0
    if views <= VIEWS_LOW:
        return _normalize_linear(float(views), 0.0, 0.0, float(VIEWS_LOW), 0.3)
    if views <= VIEWS_MEDIUM:
        return _normalize_linear(float(views), float(VIEWS_LOW), 0.3, float(VIEWS_MEDIUM), 0.6)
    if views <= VIEWS_HIGH:
        return _normalize_linear(float(views), float(VIEWS_MEDIUM), 0.6, float(VIEWS_HIGH), 0.9)
    return min(1.0, 0.9 + (views - VIEWS_HIGH) / VIEWS_HIGH * 0.1)


def _score_saves(saves: int) -> float:
    """Normalise saved_by_recruiters_30d to 0.0-1.0."""
    if saves <= 0:
        return 0.0
    if saves <= SAVES_LOW:
        return _normalize_linear(float(saves), 0.0, 0.0, float(SAVES_LOW), 0.3)
    if saves <= SAVES_MEDIUM:
        return _normalize_linear(float(saves), float(SAVES_LOW), 0.3, float(SAVES_MEDIUM), 0.6)
    if saves <= SAVES_HIGH:
        return _normalize_linear(float(saves), float(SAVES_MEDIUM), 0.6, float(SAVES_HIGH), 0.9)
    return min(1.0, 0.9 + (saves - SAVES_HIGH) / SAVES_HIGH * 0.1)


def _score_notice_period(days: int) -> float:
    """Short notice period = higher availability score."""
    if days <= NOTICE_IMMEDIATE:
        return 1.0
    if days <= NOTICE_SHORT:
        return _normalize_linear(float(days), float(NOTICE_IMMEDIATE), 1.0, float(NOTICE_SHORT), 0.75)
    if days <= NOTICE_STANDARD:
        return _normalize_linear(float(days), float(NOTICE_SHORT), 0.75, float(NOTICE_STANDARD), 0.5)
    if days <= NOTICE_LONG:
        return _normalize_linear(float(days), float(NOTICE_STANDARD), 0.5, float(NOTICE_LONG), 0.25)
    if days <= NOTICE_EXTENDED:
        return _normalize_linear(float(days), float(NOTICE_LONG), 0.25, float(NOTICE_EXTENDED), 0.0)
    return 0.0


def _score_last_active_date(last_active_date: str) -> float:
    """More recent activity = higher score."""
    if not last_active_date or last_active_date.strip() == "":
        return 0.0
    try:
        active = datetime.fromisoformat(last_active_date)
        now = datetime.now(timezone.utc)
        # Ensure naive datetime compatibility
        if active.tzinfo is None:
            diff = now.replace(tzinfo=None) - active
        else:
            diff = now - active
        days = diff.days
    except (ValueError, TypeError):
        logger.debug("Cannot parse last_active_date: %s", last_active_date)
        return 0.0

    if days <= ACTIVITY_TODAY:
        return 1.0
    if days <= ACTIVITY_WEEK:
        return _normalize_linear(float(days), float(ACTIVITY_TODAY), 1.0, float(ACTIVITY_WEEK), 0.8)
    if days <= ACTIVITY_MONTH:
        return _normalize_linear(float(days), float(ACTIVITY_WEEK), 0.8, float(ACTIVITY_MONTH), 0.5)
    if days <= ACTIVITY_QUARTER:
        return _normalize_linear(float(days), float(ACTIVITY_MONTH), 0.5, float(ACTIVITY_QUARTER), 0.2)
    if days <= ACTIVITY_STALE:
        return _normalize_linear(float(days), float(ACTIVITY_QUARTER), 0.2, float(ACTIVITY_STALE), 0.05)
    return 0.0


def _score_recruiter_response_rate(rate: float) -> float:
    """Higher recruiter response rate = higher trust score."""
    if rate <= 0.0:
        return 0.0
    if rate <= RATE_LOW:
        return _normalize_linear(rate, 0.0, 0.0, RATE_LOW, 0.3)
    if rate <= RATE_MEDIUM:
        return _normalize_linear(rate, RATE_LOW, 0.3, RATE_MEDIUM, 0.6)
    if rate <= RATE_HIGH:
        return _normalize_linear(rate, RATE_MEDIUM, 0.6, RATE_HIGH, 0.9)
    return min(1.0, 0.9 + (rate - RATE_HIGH) / (1.0 - RATE_HIGH) * 0.1)


def _score_interview_completion_rate(rate: float) -> float:
    """Higher interview completion rate = higher trust score."""
    if rate <= 0.0:
        return 0.0
    if rate <= RATE_LOW:
        return _normalize_linear(rate, 0.0, 0.0, RATE_LOW, 0.3)
    if rate <= RATE_MEDIUM:
        return _normalize_linear(rate, RATE_LOW, 0.3, RATE_MEDIUM, 0.6)
    if rate <= RATE_HIGH:
        return _normalize_linear(rate, RATE_MEDIUM, 0.6, RATE_HIGH, 0.9)
    return min(1.0, 0.9 + (rate - RATE_HIGH) / (1.0 - RATE_HIGH) * 0.1)


# ---------------------------------------------------------------------------
# BehavioralIntelligence extractor
# ---------------------------------------------------------------------------

class BehavioralIntelligence(BaseFeatureExtractor):
    """Feature extractor computing behavioral signals from Redrob platform data.

    Analyzes the candidate's RedrobSignals to produce scores for:
        - Availability: openness to work, notice period, activity recency
        - Demand: profile visibility and recruiter interest
        - Trust: reliability based on recruiter interactions
        - Engagement: platform engagement signals

    All features are scored 0.0 to 1.0.
    Uses simple normalisation and thresholds — no ML, no network, CPU-only.

    Example:
        bi = BehavioralIntelligence()
        features = bi.extract(candidate)
    """

    features = [
        # Availability (3)
        "availability_score",
        "availability_notice_period",
        "availability_recent_active",
        # Demand (3)
        "demand_score",
        "demand_profile_views",
        "demand_saved_by_recruiters",
        # Trust (3)
        "trust_score",
        "trust_recruiter_response",
        "trust_interview_completion",
        # Engagement (2)
        "engagement_score",
        "engagement_activity_recency",
    ]

    @property
    def name(self) -> str:
        return "behavioral_intelligence"

    @property
    def description(self) -> str:
        return (
            "Behavioral intelligence scoring: evaluates availability (open-to-work, "
            "notice period, activity recency), demand (profile views, saves), "
            "trust (recruiter response rate, interview completion), and "
            "engagement (views, saves, recency) from Redrob platform signals."
        )

    def extract(self, candidate: Candidate) -> dict[str, float]:
        """Extract all behavioral features for a single candidate.

        Args:
            candidate: Parsed Candidate object with RedrobSignals.

        Returns:
            Dict of 11 feature_name -> score (0.0 to 1.0).
        """
        signals = candidate.redrob_signals

        # --- Raw signal extraction with safe defaults ---
        open_to_work: bool = getattr(signals, "open_to_work_flag", False)
        notice_period_days: int = max(0, getattr(signals, "notice_period_days", 0) or 0)
        last_active_date: str = getattr(signals, "last_active_date", "") or ""
        profile_views: int = getattr(signals, "profile_views_received_30d", 0) or 0
        saved_by_recruiters: int = getattr(signals, "saved_by_recruiters_30d", 0) or 0
        recruiter_response_rate: float = getattr(signals, "recruiter_response_rate", 0.0) or 0.0
        interview_completion_rate: float = getattr(signals, "interview_completion_rate", 0.0) or 0.0

        # --- Availability sub-scores ---
        open_to_work_score: float = 1.0 if open_to_work else 0.0
        notice_score: float = _score_notice_period(notice_period_days)
        recency_score: float = _score_last_active_date(last_active_date)

        # Composite: open_to_work is binary, notice period is weighted,
        # recency is weighted. Even if not open_to_work, short notice
        # and recent activity still signal availability.
        availability: float = (
            open_to_work_score * 0.4
            + notice_score * 0.35
            + recency_score * 0.25
        )

        # --- Demand sub-scores ---
        views_score: float = _score_views(profile_views)
        saves_score: float = _score_saves(saved_by_recruiters)

        demand: float = views_score * 0.4 + saves_score * 0.6

        # --- Trust sub-scores ---
        response_score: float = _score_recruiter_response_rate(recruiter_response_rate)
        interview_score: float = _score_interview_completion_rate(interview_completion_rate)

        trust: float = response_score * 0.5 + interview_score * 0.5

        # --- Engagement sub-scores ---
        engagement: float = views_score * 0.3 + saves_score * 0.3 + recency_score * 0.4

        return {
            # Availability
            "availability_score": round(availability, 4),
            "availability_notice_period": round(notice_score, 4),
            "availability_recent_active": round(recency_score, 4),
            # Demand
            "demand_score": round(demand, 4),
            "demand_profile_views": round(views_score, 4),
            "demand_saved_by_recruiters": round(saves_score, 4),
            # Trust
            "trust_score": round(trust, 4),
            "trust_recruiter_response": round(response_score, 4),
            "trust_interview_completion": round(interview_score, 4),
            # Engagement
            "engagement_score": round(engagement, 4),
            "engagement_activity_recency": round(recency_score, 4),
        }

    def __repr__(self) -> str:
        return (
            f"BehavioralIntelligence(name='{self.name}', "
            f"features={len(self.features)})"
        )
