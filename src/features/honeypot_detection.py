"""Honeypot Detection Engine — disqualification-risk signal detection.

Detects suspicious candidate profiles that may be honeypots or adversarially
constructed to manipulate rankings. Checks include:

    1. Timeline Consistency — overlapping jobs, impossible dates, career gaps
    2. Skill-Experience Alignment — expert skills with zero duration
    3. Career Progression — unrealistic title jumps, rapid role changes
    4. Role-Seniority Mismatch — inflated titles with minimal experience
    5. Pattern Inconsistencies — generic descriptions, uniform company sizes

All features are computed from structured Candidate fields only.
No ML models, no network calls, CPU-only. Reuses Candidate data model
shared with Phase 6 (CareerIntelligence) and Phase 7 (BehavioralIntelligence).

Features produced (10 total):
    Timeline (3):
        timeline_overlap_score: Overlapping career entries detected
        timeline_gap_score: Career gaps detected
        timeline_impossible_score: Impossible timeline patterns

    Skill-Experience (2):
        skill_zero_duration_expert_score: Expert skills with zero duration
        skill_prolific_score: Unrealistically many expert skills vs career length

    Career Progression (2):
        progression_jump_score: Unrealistic title jumps
        progression_rapid_churn_score: Very short tenures across roles

    Role-Seniority (2):
        seniority_mismatch_score: Senior title with junior experience
        title_experience_mismatch_score: Title vs experience inconsistency

    Pattern (1):
        pattern_uniform_score: Suspiciously uniform profile characteristics
"""

import logging
import re
from datetime import datetime
from typing import Any, Optional

from src.features.base import BaseFeatureExtractor
from src.parser.candidate_parser import Candidate, CareerEntry, Skill

logger = logging.getLogger("redrob-ranker")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Minimum years of experience expected for senior-level titles
SENIORITY_MAP: dict[str, float] = {
    "junior": 0.0,
    "senior": 4.0,
    "staff": 7.0,
    "principal": 10.0,
    "lead": 6.0,
    "head of": 10.0,
    "director": 10.0,
    "vp": 12.0,
    "chief": 15.0,
    "manager": 4.0,
}

# Title keywords suggesting a senior role
SENIOR_TITLE_PATTERNS = [
    r"\bsenior\b.*\bengineer\b",
    r"\bstaff\b.*\bengineer\b",
    r"\bprincipal\b.*\bengineer\b",
    r"\blead\b.*\bengineer\b",
    r"\bhead of\b",
    r"\bdirector\b.*\b(engineering|ml|ai|science)\b",
    r"\bvp\b.*\b(engineering|ml|ai|science)\b",
    r"\bchief\b.*\b\w+\b.*\bofficer\b",
    r"\barchitect\b",
]

# Title keywords suggesting junior/early roles
JUNIOR_TITLE_PATTERNS = [
    r"\bjunior\b",
    r"\bintern\b",
    r"\bfresher\b",
    r"\bentry[- ]level\b",
    r"\btrainee\b",
    r"\bassociate\b",
]

# Generic description keywords (low information content)
GENERIC_DESCRIPTION_KEYWORDS = [
    "worked on", "responsible for", "involved in", "handled",
    "good knowledge", "basic knowledge", "familiar with",
    "worked as", "worked with", "assisted",
    "part of the team", "team player",
]

# Maximum number of roles before suspicion
MAX_REASONABLE_ROLES = 8
# Minimum average tenure (months) before suspicion
MIN_AVG_TENURE_MONTHS = 6    # Minimum years for senior titles
MIN_YEARS_FOR_SENIOR = 3.0
MIN_YEARS_FOR_STAFF = 6.0
MIN_YEARS_FOR_PRINCIPAL = 9.0
MIN_YEARS_FOR_DIRECTOR = 10.0
MIN_YEARS_FOR_VP = 12.0


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse an ISO-format date string, or return None."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str)
    except (ValueError, TypeError):
        return None


def _contains_title_pattern(text: str, patterns: list[str]) -> bool:
    """Check if text matches any regex pattern (case-insensitive)."""
    text_lower = text.lower()
    for pat in patterns:
        if re.search(pat, text_lower):
            return True
    return False


def _normalize(value: float, x1: float, y1: float, x2: float, y2: float) -> float:
    """Linearly map value from (x1,x2) range to (y1,y2) range, clamped."""
    if x2 == x1:
        return y1
    ratio = (value - x1) / (x2 - x1)
    return max(min(ratio * (y2 - y1) + y1, max(y1, y2)), min(y1, y2))


# ---------------------------------------------------------------------------
# HoneypotDetector extractor
# ---------------------------------------------------------------------------

class HoneypotDetector(BaseFeatureExtractor):
    """Feature extractor detecting honeypot/disqualification signals.

    Analyzes candidate profile data for suspicious patterns that suggest
    an adversarially constructed profile. Produces penalty-style scores
    where 0.0 = no suspicion, 1.0 = highly suspicious.

    All checks use deterministic rule-based logic on structured fields.
    No ML models, no network calls, CPU-only.

    Example:
        hd = HoneypotDetector()
        features = hd.extract(candidate)
    """

    features = [
        # Timeline (3)
        "timeline_overlap_score",
        "timeline_gap_score",
        "timeline_impossible_score",
        # Skill-Experience (2)
        "skill_zero_duration_expert_score",
        "skill_prolific_score",
        # Career Progression (2)
        "progression_jump_score",
        "progression_rapid_churn_score",
        # Role-Seniority (2)
        "seniority_mismatch_score",
        "title_experience_mismatch_score",
        # Pattern (1)
        "pattern_uniform_score",
    ]

    @property
    def name(self) -> str:
        return "honeypot_detection"

    @property
    def description(self) -> str:
        return (
            "Honeypot detection: identifies suspicious profiles with impossible "
            "timelines, skill-experience contradictions, unrealistic title jumps, "
            "role-seniority mismatches, and suspiciously uniform patterns. "
            "Produces penalty scores (0 = legitimate, 1 = highly suspicious)."
        )

    def extract(self, candidate: Candidate) -> dict[str, float]:
        """Extract all honeypot detection features for a single candidate.

        Args:
            candidate: Parsed Candidate object.

        Returns:
            Dict of 10 feature_name -> score (0.0 to 1.0).
        """
        # ---------------------------------------------------------------
        # Timeline checks
        # ---------------------------------------------------------------
        overlap_score = self._detect_overlaps(candidate)
        gap_score = self._detect_gaps(candidate)
        impossible_score = self._detect_impossible_timelines(candidate)

        # ---------------------------------------------------------------
        # Skill-Experience checks
        # ---------------------------------------------------------------
        zero_duration_expert = self._detect_zero_duration_experts(candidate)
        prolific = self._detect_prolific_experts(candidate)

        # ---------------------------------------------------------------
        # Career progression checks
        # ---------------------------------------------------------------
        jump_score = self._detect_title_jumps(candidate)
        churn_score = self._detect_rapid_churn(candidate)

        # ---------------------------------------------------------------
        # Role-seniority checks
        # ---------------------------------------------------------------
        seniority_mismatch = self._detect_seniority_mismatch(candidate)
        title_exp_mismatch = self._detect_title_experience_mismatch(candidate)

        # ---------------------------------------------------------------
        # Pattern checks
        # ---------------------------------------------------------------
        uniform_score = self._detect_uniform_patterns(candidate)

        return {
            "timeline_overlap_score": round(overlap_score, 4),
            "timeline_gap_score": round(gap_score, 4),
            "timeline_impossible_score": round(impossible_score, 4),
            "skill_zero_duration_expert_score": round(zero_duration_expert, 4),
            "skill_prolific_score": round(prolific, 4),
            "progression_jump_score": round(jump_score, 4),
            "progression_rapid_churn_score": round(churn_score, 4),
            "seniority_mismatch_score": round(seniority_mismatch, 4),
            "title_experience_mismatch_score": round(title_exp_mismatch, 4),
            "pattern_uniform_score": round(uniform_score, 4),
        }

    # ==================================================================
    # Timeline Checks
    # ==================================================================

    def _detect_overlaps(self, candidate: Candidate) -> float:
        """Detect overlapping career entries.

        Overlaps suggest fabricated or copied career histories.
        Score based on number of overlapping entries detected.
        """
        entries = candidate.career_history
        if len(entries) < 2:
            return 0.0

        # Parse start/end dates for each entry
        date_ranges: list[tuple[Optional[datetime], Optional[datetime], int]] = []
        for entry in entries:
            start = _parse_date(entry.start_date)
            end = _parse_date(entry.end_date)
            date_ranges.append((start, end, id(entry)))

        overlaps = 0
        for i in range(len(date_ranges)):
            s1, e1, _ = date_ranges[i]
            if s1 is None:
                continue
            for j in range(i + 1, len(date_ranges)):
                s2, e2, _ = date_ranges[j]
                if s2 is None:
                    continue
                # Check for overlap: A starts before B ends and B starts before A ends
                e1_actual = e1 or datetime.now()
                e2_actual = e2 or datetime.now()
                if s1 < e2_actual and s2 < e1_actual:
                    overlaps += 1

        if overlaps == 0:
            return 0.0
        return min(1.0, overlaps * 0.33)

    def _detect_gaps(self, candidate: Candidate) -> float:
        """Detect unusually large gaps between career entries.

        Large unexplained gaps (1+ year) are suspicious, especially
        multiple consecutive gaps.
        """
        entries = candidate.career_history
        if len(entries) < 2:
            return 0.0

        gaps: list[int] = []
        for i in range(len(entries) - 1):
            curr = entries[i]
            nxt = entries[i + 1]
            # Current entry's end date to next entry's start date
            curr_end = _parse_date(curr.end_date)
            nxt_start = _parse_date(nxt.start_date)
            if curr_end and nxt_start:
                gap_days = (nxt_start - curr_end).days
                if gap_days > 0:
                    gaps.append(gap_days)

        if not gaps:
            return 0.0

        # Count gaps exceeding thresholds
        large_gaps = sum(1 for g in gaps if g > 365)  # > 1 year
        very_large_gaps = sum(1 for g in gaps if g > 730)  # > 2 years

        if very_large_gaps >= 2:
            return 1.0
        if large_gaps >= 2:
            return 0.8
        if large_gaps == 1:
            return 0.4
        return 0.1

    def _detect_impossible_timelines(self, candidate: Candidate) -> float:
        """Detect impossible timeline patterns.

        Examples:
        - Negative duration in a role
        - End date before start date
        - Current role with end_date (not None)
        """
        entries = candidate.career_history
        if not entries:
            return 0.0

        issues = 0
        total = len(entries)

        for entry in entries:
            start = _parse_date(entry.start_date)
            end = _parse_date(entry.end_date)

            # Negative duration
            if entry.duration_months < 0:
                issues += 1

            # End date before start date (only if both are valid)
            if start and end and end < start:
                issues += 1

            # Current role with an end date (should be None)
            if entry.is_current and entry.end_date is not None and entry.end_date != "":
                issues += 1

        if issues == 0:
            return 0.0
        ratio = issues / total
        return min(1.0, ratio)

    # ==================================================================
    # Skill-Experience Checks
    # ==================================================================

    def _detect_zero_duration_experts(self, candidate: Candidate) -> float:
        """Detect skills claimed as expert/advanced with zero duration.

        Similar to Phase 6 keyword_stuffing_penalty but independent.
        Many such skills suggest a stuffed profile.
        """
        skills = candidate.skills
        if not skills:
            return 0.0

        suspicious = sum(
            1 for s in skills
            if s.proficiency in ("advanced", "expert")
            and (s.duration_months is None or s.duration_months == 0)
        )

        ratio = suspicious / len(skills)
        if ratio <= 0.1:
            return 0.0
        if ratio <= 0.25:
            return 0.3
        if ratio <= 0.5:
            return 0.6
        return 1.0

    def _detect_prolific_experts(self, candidate: Candidate) -> float:
        """Detect profiles with too many expert skills for their career length.

        E.g., 20 expert skills but only 3 years of experience.
        """
        skills = candidate.skills
        total_years = candidate.profile.years_of_experience or 0.0
        if not skills or total_years <= 0:
            return 0.0

        expert_count = sum(1 for s in skills if s.proficiency in ("advanced", "expert"))
        total_count = len(skills)

        # Expect at most ~2 expert skills per year of experience
        max_reasonable_experts = max(3, int(total_years * 2))
        if expert_count <= max_reasonable_experts:
            return 0.0

        # Excessive expert count penalty
        excess_ratio = (expert_count - max_reasonable_experts) / expert_count
        score = min(1.0, excess_ratio)

        # Also penalize if >80% of skills are expert-level
        if total_count > 5 and expert_count / total_count > 0.8:
            score = max(score, 0.5)

        return score

    # ==================================================================
    # Career Progression Checks
    # ==================================================================

    def _detect_title_jumps(self, candidate: Candidate) -> float:
        """Detect unrealistic title progression jumps.

        E.g., 'Intern' -> 'Senior Engineer' in 1 year,
        or 'Junior' -> 'Director' in 2 years.
        """
        entries = candidate.career_history
        if len(entries) < 2:
            return 0.0

        titles = [e.title.lower() for e in entries if e.title]
        if not titles:
            return 0.0

        # Check for huge jumps: from junior to senior in 2+ levels
        jumps_detected = 0
        total_pairs = 0

        for i in range(len(titles) - 1):
            curr = titles[i]
            nxt = titles[i + 1]
            total_pairs += 1

            # Junior role followed by senior role in next position
            # (skipping intermediate roles)
            is_junior = any(kw in curr for kw in ["junior", "intern", "trainee", "entry"])
            is_senior_now = any(kw in nxt for kw in ["senior", "staff", "principal", "lead", "head", "director", "vp", "chief"])

            if is_junior and is_senior_now:
                jumps_detected += 1

            # Check how fast: if the combined duration is < 3 years
            # and we see a big title jump
            if is_junior and is_senior_now and i < len(entries):
                combined_months = (entries[i].duration_months or 0) + (entries[i + 1].duration_months or 0)
                if combined_months < 36:  # < 3 years
                    jumps_detected += 1

        if total_pairs == 0:
            return 0.0
        return min(1.0, jumps_detected * 0.5 / total_pairs)

    def _detect_rapid_churn(self, candidate: Candidate) -> float:
        """Detect extremely rapid role churn.

        Many short roles (< 6 months) suggests resume stuffing
        or fabricated career history.
        """
        entries = candidate.career_history
        if len(entries) < 2:
            return 0.0

        total_years = candidate.profile.years_of_experience or 0.0
        if total_years <= 0:
            return 0.0

        # Count very short stints
        very_short = sum(1 for e in entries
                        if not e.is_current
                        and e.duration_months is not None
                        and e.duration_months < 6)

        short_ratio = very_short / len(entries)

        # Also check number of roles per year of experience
        roles_per_year = len(entries) / total_years
        # More than 2 roles per year = suspicious
        if roles_per_year > 2:
            return min(1.0, short_ratio + 0.3)

        if very_short == 0:
            return 0.0
        return min(1.0, short_ratio)

    # ==================================================================
    # Role-Seniority Checks
    # ==================================================================

    def _detect_seniority_mismatch(self, candidate: Candidate) -> float:
        """Detect senior/principal/staff titles with limited experience.

        E.g., 'Principal Engineer' with 3 years of experience.
        """
        entries = candidate.career_history
        total_years = candidate.profile.years_of_experience or 0.0

        if not entries or total_years <= 0:
            return 0.0

        # Check current title
        current_title = (candidate.profile.current_title or "").lower()
        mismatch_score = 0.0

        # Check current title against experience
        if re.search(r"\bprincipal\b.*\b(engineer|architect)\b", current_title):
            if total_years < MIN_YEARS_FOR_PRINCIPAL:
                gap = MIN_YEARS_FOR_PRINCIPAL - total_years
                mismatch_score = max(mismatch_score, min(1.0, gap / MIN_YEARS_FOR_PRINCIPAL))
        elif re.search(r"\bstaff\b.*\bengineer\b", current_title):
            if total_years < MIN_YEARS_FOR_STAFF:
                gap = MIN_YEARS_FOR_STAFF - total_years
                mismatch_score = max(mismatch_score, min(1.0, gap / MIN_YEARS_FOR_STAFF))
        elif re.search(r"\bsenior\b.*\b(engineer|scientist|developer)\b", current_title):
            if total_years < MIN_YEARS_FOR_SENIOR:
                gap = MIN_YEARS_FOR_SENIOR - total_years
                mismatch_score = max(mismatch_score, min(1.0, gap / MIN_YEARS_FOR_SENIOR))
        elif re.search(r"\bvp\b.*\b(engineering|ml|ai|science|product)\b", current_title):
            if total_years < MIN_YEARS_FOR_VP:
                gap = MIN_YEARS_FOR_VP - total_years
                mismatch_score = max(mismatch_score, min(1.0, gap / MIN_YEARS_FOR_VP))
        elif re.search(r"\bdirector\b.*\b(engineering|ml|ai|science|product|data)\b", current_title):
            if total_years < MIN_YEARS_FOR_DIRECTOR:
                gap = MIN_YEARS_FOR_DIRECTOR - total_years
                mismatch_score = max(mismatch_score, min(1.0, gap / MIN_YEARS_FOR_DIRECTOR))

        # Check historical titles for seniority mismatch
        title_text = " ".join(e.title.lower() for e in entries if e.title)
        has_any_senior = re.search(r"\b(principal|staff|senior|lead|head|director|vp|chief)\b", title_text)
        if has_any_senior and total_years < 2.0:
            mismatch_score = max(mismatch_score, 0.8)

        return mismatch_score

    def _detect_title_experience_mismatch(self, candidate: Candidate) -> float:
        """Detect title vs experience inconsistency across career history.

        E.g., All roles are "Senior" something with < 5 years total experience.
        """
        entries = candidate.career_history
        total_years = candidate.profile.years_of_experience or 0.0

        if not entries or total_years <= 0:
            return 0.0

        titles = [e.title.lower() for e in entries if e.title]
        if not titles:
            return 0.0

        # Count senior-level titles
        senior_count = sum(1 for t in titles if _contains_title_pattern(t, SENIOR_TITLE_PATTERNS))
        junior_count = sum(1 for t in titles if _contains_title_pattern(t, JUNIOR_TITLE_PATTERNS))

        # If all roles are senior-level but junior in age
        if senior_count > 0 and junior_count == 0 and total_years < 3.0:
            return 0.7

        # If all titles are senior/principal but only < 5 years experience
        if senior_count >= len(titles) and total_years < 5.0:
            return _normalize(float(5 - total_years), 0.0, 0.0, 5.0, 0.8)

        return 0.0

    # ==================================================================
    # Pattern Checks
    # ==================================================================

    def _detect_uniform_patterns(self, candidate: Candidate) -> float:
        """Detect suspiciously uniform profile characteristics.

        E.g., All roles have the same company size, same industry,
        or all descriptions are generic.
        """
        entries = candidate.career_history
        skills = candidate.skills
        score = 0.0

        # Check 1: All roles same company size (too uniform)
        if len(entries) >= 3:
            company_sizes = set(e.company_size for e in entries if e.company_size)
            if len(company_sizes) == 1:
                score += 0.3

        # Check 2: All roles same industry (unlikely for diverse career)
        if len(entries) >= 4:
            industries = set(e.industry.lower() for e in entries if e.industry)
            if len(industries) == 1:
                score += 0.2

        # Check 3: Generic descriptions
        if entries:
            generic_descriptions = sum(
                1 for e in entries
                if e.description
                and sum(1 for kw in GENERIC_DESCRIPTION_KEYWORDS if kw in e.description.lower()) >= 2
            )
            if len(entries) > 0:
                generic_ratio = generic_descriptions / len(entries)
                if generic_ratio > 0.5:
                    score += 0.3

        # Check 4: Too many roles (suggests fabricated history)
        if len(entries) > MAX_REASONABLE_ROLES:
            excess = len(entries) - MAX_REASONABLE_ROLES
            score += min(0.3, excess * 0.05)

        # Check 5: All skills are advanced/expert (too perfect)
        if len(skills) >= 5:
            all_expert = all(s.proficiency in ("advanced", "expert") for s in skills)
            if all_expert:
                score += 0.3

        return min(1.0, score)

    def __repr__(self) -> str:
        return (
            f"HoneypotDetector(name='{self.name}', "
            f"features={len(self.features)})"
        )
