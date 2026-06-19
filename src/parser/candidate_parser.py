"""Candidate dataclasses and parser with schema validation.

Parses raw JSON candidate objects into typed Candidate dataclass instances,
validating required fields, types, and value constraints.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger("redrob-ranker")

# Pattern for candidate_id validation
CANDIDATE_ID_PATTERN = re.compile(r"^CAND_[0-9]{7}$")

# Valid enums from the schema
VALID_COMPANY_SIZES = {"1-10", "11-50", "51-200", "201-500", "501-1000", "1001-5000", "5001-10000", "10001+"}
VALID_PROFICIENCIES = {"beginner", "intermediate", "advanced", "expert"}
VALID_INSTITUTION_TIERS = {"tier_1", "tier_2", "tier_3", "tier_4", "unknown"}
VALID_WORK_MODES = {"remote", "hybrid", "onsite", "flexible"}
VALID_LANGUAGE_PROFICIENCIES = {"basic", "conversational", "professional", "native"}

# Required top-level fields per schema
REQUIRED_TOP_LEVEL = {"candidate_id", "profile", "career_history", "education", "skills", "redrob_signals"}

# Required profile fields per schema
REQUIRED_PROFILE_FIELDS = {
    "anonymized_name", "headline", "summary", "location", "country",
    "years_of_experience", "current_title", "current_company",
    "current_company_size", "current_industry"
}

# Required career entry fields per schema
REQUIRED_CAREER_FIELDS = {
    "company", "title", "start_date", "end_date", "duration_months",
    "is_current", "industry", "company_size", "description"
}

# Required education fields per schema
REQUIRED_EDUCATION_FIELDS = {"institution", "degree", "field_of_study", "start_year", "end_year"}

# Required skill fields per schema
REQUIRED_SKILL_FIELDS = {"name", "proficiency", "endorsements"}

# Required redrob_signals fields per schema
REQUIRED_SIGNALS_FIELDS = {
    "profile_completeness_score", "signup_date", "last_active_date",
    "open_to_work_flag", "profile_views_received_30d", "applications_submitted_30d",
    "recruiter_response_rate", "avg_response_time_hours", "skill_assessment_scores",
    "connection_count", "endorsements_received", "notice_period_days",
    "expected_salary_range_inr_lpa", "preferred_work_mode", "willing_to_relocate",
    "github_activity_score", "search_appearance_30d", "saved_by_recruiters_30d",
    "interview_completion_rate", "offer_acceptance_rate", "verified_email",
    "verified_phone", "linkedin_connected"
}


@dataclass
class SalaryRange:
    """Expected salary range in INR Lakhs Per Annum."""
    min: float
    max: float


@dataclass
class Skill:
    """A single skill entry from the candidate profile."""
    name: str
    proficiency: str
    endorsements: int
    duration_months: Optional[int] = None


@dataclass
class Education:
    """A single education entry."""
    institution: str
    degree: str
    field_of_study: str
    start_year: int
    end_year: int
    grade: Optional[str] = None
    tier: Optional[str] = None


@dataclass
class CareerEntry:
    """A single career history entry."""
    company: str
    title: str
    start_date: str
    end_date: Optional[str]
    duration_months: int
    is_current: bool
    industry: str
    company_size: str
    description: str


@dataclass
class Profile:
    """Candidate profile information."""
    anonymized_name: str
    headline: str
    summary: str
    location: str
    country: str
    years_of_experience: float
    current_title: str
    current_company: str
    current_company_size: str
    current_industry: str


@dataclass
class RedrobSignals:
    """Platform activity and engagement signals."""
    profile_completeness_score: float
    signup_date: str
    last_active_date: str
    open_to_work_flag: bool
    profile_views_received_30d: int
    applications_submitted_30d: int
    recruiter_response_rate: float
    avg_response_time_hours: float
    skill_assessment_scores: dict[str, float]
    connection_count: int
    endorsements_received: int
    notice_period_days: int
    expected_salary_range_inr_lpa: SalaryRange
    preferred_work_mode: str
    willing_to_relocate: bool
    github_activity_score: float
    search_appearance_30d: int
    saved_by_recruiters_30d: int
    interview_completion_rate: float
    offer_acceptance_rate: float
    verified_email: bool
    verified_phone: bool
    linkedin_connected: bool


@dataclass
class Candidate:
    """Complete typed representation of a candidate profile.

    This is the primary data object passed through the pipeline.
    """
    candidate_id: str
    profile: Profile
    career_history: list[CareerEntry]
    education: list[Education]
    skills: list[Skill]
    redrob_signals: RedrobSignals
    certifications: list[dict[str, Any]] = field(default_factory=list)
    languages: list[dict[str, Any]] = field(default_factory=list)

    # Derived fields computed during parsing
    total_career_months: int = 0
    current_role_index: Optional[int] = None
    career_gap_months: float = 0.0


class ParseError(Exception):
    """Raised when a candidate cannot be parsed due to schema violations."""
    pass


class CandidateParser:
    """Parses raw JSON dicts into validated Candidate objects.

    Args:
        strict: If True, raise on validation errors.
                If False, log warnings and use defaults.
    """

    def __init__(self, strict: bool = False) -> None:
        self.strict = strict
        self._total_parsed: int = 0
        self._total_errors: int = 0

    @property
    def total_parsed(self) -> int:
        return self._total_parsed

    @property
    def total_errors(self) -> int:
        return self._total_errors

    def parse(self, data: dict[str, Any]) -> Optional[Candidate]:
        """Parse a raw JSON dict into a Candidate object.

        Args:
            data: Raw JSON candidate dict from DataLoader.

        Returns:
            Candidate object if valid, None if invalid (non-strict mode).

        Raises:
            ParseError: If validation fails in strict mode.
        """
        try:
            self._validate_top_level(data)
            candidate_id = self._parse_candidate_id(data["candidate_id"])
            profile = self._parse_profile(data.get("profile", {}))
            career_history = self._parse_career_history(data.get("career_history", []))
            education = self._parse_education(data.get("education", []))
            skills = self._parse_skills(data.get("skills", []))
            signals = self._parse_signals(data.get("redrob_signals", {}))
            certifications = data.get("certifications", [])
            languages = data.get("languages", [])

            # Compute derived fields
            total_career_months = sum(ce.duration_months for ce in career_history)
            current_role_index = next(
                (i for i, ce in enumerate(career_history) if ce.is_current),
                None
            )

            candidate = Candidate(
                candidate_id=candidate_id,
                profile=profile,
                career_history=career_history,
                education=education,
                skills=skills,
                redrob_signals=signals,
                certifications=certifications if isinstance(certifications, list) else [],
                languages=languages if isinstance(languages, list) else [],
                total_career_months=total_career_months,
                current_role_index=current_role_index,
            )
            self._total_parsed += 1
            return candidate

        except ParseError:
            self._total_errors += 1
            raise
        except Exception as e:
            self._total_errors += 1
            if self.strict:
                raise ParseError(f"Unexpected parse error: {e}") from e
            logger.warning("Parse error for candidate: %s", e)
            return None

    def parse_batch(self, records: list[dict[str, Any]]) -> list[Candidate]:
        """Parse a batch of raw JSON dicts.

        Args:
            records: List of raw JSON candidate dicts.

        Returns:
            List of successfully parsed Candidate objects (non-strict mode).
        """
        candidates: list[Candidate] = []
        for data in records:
            candidate = self.parse(data)
            if candidate is not None:
                candidates.append(candidate)
        return candidates

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def _validate_top_level(self, data: dict[str, Any]) -> None:
        """Check that all required top-level fields exist."""
        missing = REQUIRED_TOP_LEVEL - set(data.keys())
        if missing:
            msg = f"Missing required top-level fields: {sorted(missing)}"
            if self.strict:
                raise ParseError(msg)
            logger.warning(msg)

    def _parse_candidate_id(self, value: str) -> str:
        """Validate candidate_id format."""
        value = str(value).strip()
        if not CANDIDATE_ID_PATTERN.match(value):
            msg = f"Invalid candidate_id format: '{value}' (expected CAND_XXXXXXX)"
            if self.strict:
                raise ParseError(msg)
            logger.warning(msg)
        return value

    def _parse_profile(self, data: dict[str, Any]) -> Profile:
        """Parse profile section."""
        missing = REQUIRED_PROFILE_FIELDS - set(data.keys())
        if missing and self.strict:
            raise ParseError(f"Profile missing required fields: {sorted(missing)}")

        return Profile(
            anonymized_name=str(data.get("anonymized_name", "")),
            headline=str(data.get("headline", "")),
            summary=str(data.get("summary", "")),
            location=str(data.get("location", "")),
            country=str(data.get("country", "")),
            years_of_experience=float(data.get("years_of_experience", 0)),
            current_title=str(data.get("current_title", "")),
            current_company=str(data.get("current_company", "")),
            current_company_size=self._validate_enum(
                data.get("current_company_size"), VALID_COMPANY_SIZES, "current_company_size", "10001+"
            ),
            current_industry=str(data.get("current_industry", "")),
        )

    def _parse_career_history(self, entries: list[dict[str, Any]]) -> list[CareerEntry]:
        """Parse career_history array."""
        if not isinstance(entries, list):
            if self.strict:
                raise ParseError("career_history must be an array")
            return []

        result: list[CareerEntry] = []
        for i, entry in enumerate(entries):
            if not isinstance(entry, dict):
                logger.warning("Career entry %d is not a dict, skipping", i)
                continue
            try:
                result.append(self._parse_career_entry(entry, i))
            except ParseError:
                if self.strict:
                    raise
                logger.warning("Skipping career entry %d due to parse error", i)
        return result

    def _parse_career_entry(self, data: dict[str, Any], index: int) -> CareerEntry:
        """Parse a single career history entry."""
        description = data.get("description")
        return CareerEntry(
            company=str(data.get("company", "")),
            title=str(data.get("title", "")),
            start_date=str(data.get("start_date", "")),
            end_date=data.get("end_date"),
            duration_months=self._validate_int(data.get("duration_months"), "career[%d].duration_months" % index),
            is_current=bool(data.get("is_current", False)),
            industry=str(data.get("industry", "")),
            company_size=self._validate_enum(
                data.get("company_size"), VALID_COMPANY_SIZES, "career[%d].company_size" % index, "10001+"
            ),
            description=str(description) if description else "",
        )

    def _parse_education(self, entries: list[dict[str, Any]]) -> list[Education]:
        """Parse education array."""
        if not isinstance(entries, list):
            return []
        result: list[Education] = []
        for data in entries:
            if not isinstance(data, dict):
                continue
            result.append(Education(
                institution=str(data.get("institution", "")),
                degree=str(data.get("degree", "")),
                field_of_study=str(data.get("field_of_study", "")),
                start_year=self._validate_int(data.get("start_year"), "education.start_year"),
                end_year=self._validate_int(data.get("end_year"), "education.end_year"),
                grade=data.get("grade"),
                tier=self._validate_enum(data.get("tier"), VALID_INSTITUTION_TIERS, "education.tier", "unknown"),
            ))
        return result

    def _parse_skills(self, entries: list[dict[str, Any]]) -> list[Skill]:
        """Parse skills array."""
        if not isinstance(entries, list):
            return []
        result: list[Skill] = []
        for data in entries:
            if not isinstance(data, dict):
                continue
            result.append(Skill(
                name=str(data.get("name", "")),
                proficiency=self._validate_enum(
                    data.get("proficiency"), VALID_PROFICIENCIES, "skill.proficiency", "beginner"
                ),
                endorsements=self._validate_int(data.get("endorsements"), "skill.endorsements"),
                duration_months=self._validate_int(data.get("duration_months"), "skill.duration_months"),
            ))
        return result

    def _parse_signals(self, data: dict[str, Any]) -> RedrobSignals:
        """Parse redrob_signals section."""
        if not isinstance(data, dict):
            if self.strict:
                raise ParseError("redrob_signals must be an object")
            data = {}

        salary = data.get("expected_salary_range_inr_lpa", {})
        if not isinstance(salary, dict):
            salary = {}

        skill_scores = data.get("skill_assessment_scores", {})
        if not isinstance(skill_scores, dict):
            skill_scores = {}

        return RedrobSignals(
            profile_completeness_score=float(data.get("profile_completeness_score", 0)),
            signup_date=str(data.get("signup_date", "")),
            last_active_date=str(data.get("last_active_date", "")),
            open_to_work_flag=bool(data.get("open_to_work_flag", False)),
            profile_views_received_30d=self._validate_int(data.get("profile_views_received_30d"), "profile_views_received_30d"),
            applications_submitted_30d=self._validate_int(data.get("applications_submitted_30d"), "applications_submitted_30d"),
            recruiter_response_rate=float(data.get("recruiter_response_rate", 0)),
            avg_response_time_hours=float(data.get("avg_response_time_hours", 0)),
            skill_assessment_scores={k: float(v) for k, v in skill_scores.items()},
            connection_count=self._validate_int(data.get("connection_count"), "connection_count"),
            endorsements_received=self._validate_int(data.get("endorsements_received"), "endorsements_received"),
            notice_period_days=self._validate_int(data.get("notice_period_days"), "notice_period_days"),
            expected_salary_range_inr_lpa=SalaryRange(
                min=float(salary.get("min", 0)),
                max=float(salary.get("max", 0)),
            ),
            preferred_work_mode=self._validate_enum(
                data.get("preferred_work_mode"), VALID_WORK_MODES, "preferred_work_mode", "hybrid"
            ),
            willing_to_relocate=bool(data.get("willing_to_relocate", False)),
            github_activity_score=float(data.get("github_activity_score", -1)),
            search_appearance_30d=self._validate_int(data.get("search_appearance_30d"), "search_appearance_30d"),
            saved_by_recruiters_30d=self._validate_int(data.get("saved_by_recruiters_30d"), "saved_by_recruiters_30d"),
            interview_completion_rate=float(data.get("interview_completion_rate", 0)),
            offer_acceptance_rate=float(data.get("offer_acceptance_rate", -1)),
            verified_email=bool(data.get("verified_email", False)),
            verified_phone=bool(data.get("verified_phone", False)),
            linkedin_connected=bool(data.get("linkedin_connected", False)),
        )

    def _validate_int(self, value: Any, field_name: str) -> int:
        """Validate and coerce to int."""
        if value is None:
            return 0
        try:
            return int(value)
        except (ValueError, TypeError):
            if self.strict:
                raise ParseError(f"Field '{field_name}': expected int, got {type(value).__name__}")
            logger.warning("Field '%s': expected int, got %s", field_name, type(value).__name__)
            return 0

    def _validate_enum(self, value: Any, valid_set: set[str], field_name: str, default: str = "") -> str:
        """Validate value is in the enum set, or return default."""
        if value is None or str(value) not in valid_set:
            if value is not None and self.strict:
                raise ParseError(f"Field '{field_name}': invalid value '{value}', expected one of {sorted(valid_set)}")
            return default
        return str(value)
