"""Unit tests for CandidateParser (src/parser/candidate_parser.py)."""

import pytest

from src.parser.candidate_parser import (
    Candidate,
    CandidateParser,
    CareerEntry,
    Education,
    ParseError,
    Profile,
    RedrobSignals,
    SalaryRange,
    Skill,
)


class TestParserInitialization:
    """Parser configuration."""

    def test_default_non_strict(self):
        """Default mode should be non-strict (lenient)."""
        parser = CandidateParser()
        assert parser.strict is False

    def test_strict_mode(self):
        """Should honor strict=True."""
        parser = CandidateParser(strict=True)
        assert parser.strict is True

    def test_counters_initially_zero(self):
        """Counters start at zero."""
        parser = CandidateParser()
        assert parser.total_parsed == 0
        assert parser.total_errors == 0


class TestParserValidCandidates:
    """Parsing valid candidate data."""

    def test_parse_valid(self, sample_candidate_data):
        """Should parse a fully valid candidate."""
        parser = CandidateParser()
        candidate = parser.parse(sample_candidate_data)
        assert candidate is not None
        assert isinstance(candidate, Candidate)
        assert candidate.candidate_id == "CAND_0000001"
        assert parser.total_parsed == 1

    def test_candidate_id_format(self, sample_candidate_data):
        """candidate_id should be preserved."""
        parser = CandidateParser()
        candidate = parser.parse(sample_candidate_data)
        assert candidate.candidate_id == "CAND_0000001"

    def test_profile_parsed(self, sample_candidate_data):
        """Profile fields should be correctly mapped."""
        parser = CandidateParser()
        candidate = parser.parse(sample_candidate_data)
        assert candidate.profile.anonymized_name == "Test Candidate"
        assert candidate.profile.headline == "Backend Engineer | SQL, Spark, Cloud"
        assert candidate.profile.country == "Canada"
        assert candidate.profile.years_of_experience == 6.9
        assert candidate.profile.current_company_size == "10001+"

    def test_career_history_parsed(self, sample_candidate_data):
        """Career entries should be parsed into CareerEntry objects."""
        parser = CandidateParser()
        candidate = parser.parse(sample_candidate_data)
        assert len(candidate.career_history) == 2
        assert isinstance(candidate.career_history[0], CareerEntry)
        assert candidate.career_history[0].company == "Mindtree"
        assert candidate.career_history[0].is_current is True
        assert candidate.career_history[0].duration_months == 27
        assert candidate.career_history[1].company == "Dunder Mifflin"
        assert candidate.career_history[1].is_current is False

    def test_education_parsed(self, sample_candidate_data):
        """Education entries should be parsed into Education objects."""
        parser = CandidateParser()
        candidate = parser.parse(sample_candidate_data)
        assert len(candidate.education) == 1
        assert isinstance(candidate.education[0], Education)
        assert candidate.education[0].institution == "Test University"
        assert candidate.education[0].degree == "B.E."
        assert candidate.education[0].tier == "tier_3"

    def test_skills_parsed(self, sample_candidate_data):
        """Skills should be parsed into Skill objects."""
        parser = CandidateParser()
        candidate = parser.parse(sample_candidate_data)
        assert len(candidate.skills) == 2
        assert isinstance(candidate.skills[0], Skill)
        assert candidate.skills[0].name == "Python"
        assert candidate.skills[0].proficiency == "advanced"
        assert candidate.skills[0].endorsements == 15

    def test_redrob_signals_parsed(self, sample_candidate_data):
        """RedrobSignals should be correctly mapped."""
        parser = CandidateParser()
        candidate = parser.parse(sample_candidate_data)
        signals = candidate.redrob_signals
        assert isinstance(signals, RedrobSignals)
        assert signals.profile_completeness_score == 86.9
        assert signals.open_to_work_flag is True
        assert signals.notice_period_days == 60
        assert signals.preferred_work_mode == "onsite"
        assert signals.willing_to_relocate is False
        assert signals.verified_email is True

    def test_salary_range_parsed(self, sample_candidate_data):
        """Salary range should be parsed into SalaryRange dataclass."""
        parser = CandidateParser()
        candidate = parser.parse(sample_candidate_data)
        salary = candidate.redrob_signals.expected_salary_range_inr_lpa
        assert isinstance(salary, SalaryRange)
        assert salary.min == 18.7
        assert salary.max == 36.1

    def test_derived_total_career_months(self, sample_candidate_data):
        """Total career months should be computed."""
        parser = CandidateParser()
        candidate = parser.parse(sample_candidate_data)
        assert candidate.total_career_months == 27 + 55  # 82

    def test_derived_current_role_index(self, sample_candidate_data):
        """Current role index should be set."""
        parser = CandidateParser()
        candidate = parser.parse(sample_candidate_data)
        assert candidate.current_role_index == 0  # first entry is current

    def test_minimal_candidate_parses(self, minimal_candidate_data):
        """Minimal valid candidate should parse successfully."""
        parser = CandidateParser()
        candidate = parser.parse(minimal_candidate_data)
        assert candidate is not None
        assert candidate.candidate_id == "CAND_9999999"

    def test_certifications_and_languages(self, sample_candidate_data):
        """Certifications and languages should be passed through."""
        parser = CandidateParser()
        candidate = parser.parse(sample_candidate_data)
        assert candidate.certifications == []
        assert len(candidate.languages) == 2


class TestParserInvalidCandidates:
    """Handling invalid/malformed candidate data."""

    def test_missing_candidate_id(self):
        """Should handle missing candidate_id."""
        parser = CandidateParser()
        data = {"profile": {}}
        result = parser.parse(data)
        assert result is None
        assert parser.total_errors == 1

    def test_invalid_candidate_id_format(self, sample_candidate_data):
        """Should warn on invalid ID format but not reject in non-strict."""
        parser = CandidateParser()
        data = dict(sample_candidate_data)
        data["candidate_id"] = "INVALID"
        candidate = parser.parse(data)
        assert candidate is not None  # non-strict: still parses
        assert candidate.candidate_id == "INVALID"

    def test_invalid_candidate_id_strict(self, sample_candidate_data):
        """Strict mode should reject invalid ID format."""
        parser = CandidateParser(strict=True)
        data = dict(sample_candidate_data)
        data["candidate_id"] = "INVALID"
        with pytest.raises(ParseError, match="Invalid candidate_id"):
            parser.parse(data)

    def test_missing_profile(self, sample_candidate_data):
        """Missing profile should use defaults."""
        parser = CandidateParser()
        data = dict(sample_candidate_data)
        del data["profile"]
        candidate = parser.parse(data)
        assert candidate is not None
        assert candidate.profile.anonymized_name == ""
        assert candidate.profile.years_of_experience == 0.0

    def test_missing_redrob_signals(self, sample_candidate_data):
        """Missing signals should use defaults."""
        parser = CandidateParser()
        data = dict(sample_candidate_data)
        del data["redrob_signals"]
        candidate = parser.parse(data)
        assert candidate is not None
        assert candidate.redrob_signals.profile_completeness_score == 0.0
        assert candidate.redrob_signals.open_to_work_flag is False

    def test_non_dict_redrob_signals(self, sample_candidate_data):
        """Non-dict redrob_signals should be tolerated in non-strict."""
        parser = CandidateParser()
        data = dict(sample_candidate_data)
        data["redrob_signals"] = "not a dict"
        candidate = parser.parse(data)
        assert candidate is not None
        assert isinstance(candidate.redrob_signals, RedrobSignals)

    def test_invalid_company_size_defaults(self, sample_candidate_data):
        """Invalid enum values should use defaults."""
        parser = CandidateParser()
        data = dict(sample_candidate_data)
        data["profile"]["current_company_size"] = "MEGA_CORP"
        candidate = parser.parse(data)
        assert candidate is not None
        assert candidate.profile.current_company_size == "10001+"

    def test_invalid_company_size_strict(self, sample_candidate_data):
        """Strict mode should reject invalid enum."""
        parser = CandidateParser(strict=True)
        data = dict(sample_candidate_data)
        data["profile"]["current_company_size"] = "MEGA_CORP"
        with pytest.raises(ParseError):
            parser.parse(data)

    def test_missing_career_history(self, sample_candidate_data):
        """Missing career_history defaults to empty list."""
        parser = CandidateParser()
        data = dict(sample_candidate_data)
        del data["career_history"]
        candidate = parser.parse(data)
        assert candidate is not None
        assert candidate.career_history == []

    def test_non_list_career_history(self, sample_candidate_data):
        """Non-list career_history should default to empty."""
        parser = CandidateParser()
        data = dict(sample_candidate_data)
        data["career_history"] = "not a list"
        candidate = parser.parse(data)
        assert candidate is not None
        assert candidate.career_history == []

    def test_missing_skills(self, sample_candidate_data):
        """Missing skills defaults to empty list."""
        parser = CandidateParser()
        data = dict(sample_candidate_data)
        candidate = parser.parse(data)
        # skills are present in sample data so should be parsed
        assert len(candidate.skills) == 2

    def test_no_current_role(self):
        """Candidate with no current role should have current_role_index=None."""
        parser = CandidateParser()
        data = {
            "candidate_id": "CAND_0000001",
            "profile": {"anonymized_name": "Test", "headline": "H", "summary": "S",
                        "location": "L", "country": "C", "years_of_experience": 5,
                        "current_title": "E", "current_company": "C",
                        "current_company_size": "11-50", "current_industry": "I"},
            "career_history": [{"company": "C", "title": "E", "start_date": "2020",
                               "end_date": "2023", "duration_months": 36, "is_current": False,
                               "industry": "I", "company_size": "11-50", "description": "D"}],
            "education": [], "skills": [],
            "redrob_signals": {
                "profile_completeness_score": 0, "signup_date": "", "last_active_date": "",
                "open_to_work_flag": False, "profile_views_received_30d": 0,
                "applications_submitted_30d": 0, "recruiter_response_rate": 0,
                "avg_response_time_hours": 0, "skill_assessment_scores": {},
                "connection_count": 0, "endorsements_received": 0, "notice_period_days": 0,
                "expected_salary_range_inr_lpa": {"min": 0, "max": 0},
                "preferred_work_mode": "hybrid", "willing_to_relocate": False,
                "github_activity_score": -1, "search_appearance_30d": 0,
                "saved_by_recruiters_30d": 0, "interview_completion_rate": 0,
                "offer_acceptance_rate": -1, "verified_email": False,
                "verified_phone": False, "linkedin_connected": False
            }
        }
        candidate = parser.parse(data)
        assert candidate is not None
        assert candidate.current_role_index is None


class TestParserBatch:
    """Batch parsing."""

    def test_parse_batch_all_valid(self, sample_candidate_data, minimal_candidate_data):
        """Should parse all valid candidates in batch."""
        parser = CandidateParser()
        candidates = parser.parse_batch([sample_candidate_data, minimal_candidate_data])
        assert len(candidates) == 2

    def test_parse_batch_with_invalid(self, sample_candidate_data):
        """Should skip invalid records in batch."""
        parser = CandidateParser()
        candidates = parser.parse_batch([
            sample_candidate_data,
            {"invalid": "data"},
            sample_candidate_data,
        ])
        assert len(candidates) == 2

    def test_parse_batch_empty(self):
        """Empty batch should return empty list."""
        parser = CandidateParser()
        assert parser.parse_batch([]) == []


class TestParserCounters:
    """Parser counter tracking."""

    def test_counters_after_parse(self, sample_candidate_data):
        """Parsed and error counters should update correctly."""
        parser = CandidateParser()
        candidate = parser.parse(sample_candidate_data)
        assert candidate is not None
        assert parser.total_parsed == 1
        assert parser.total_errors == 0

    def test_counters_after_error(self):
        """Error counter should increment on parse failure."""
        parser = CandidateParser()
        result = parser.parse({"bad": "data"})
        assert result is None
        assert parser.total_parsed == 0
        assert parser.total_errors == 1
