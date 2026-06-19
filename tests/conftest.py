"""Pytest fixtures and test data helpers."""

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Generator

import pytest

SAMPLE_CANDIDATE = {
    "candidate_id": "CAND_0000001",
    "profile": {
        "anonymized_name": "Test Candidate",
        "headline": "Backend Engineer | SQL, Spark, Cloud",
        "summary": "Software professional with 6.9 years of experience.",
        "location": "Toronto",
        "country": "Canada",
        "years_of_experience": 6.9,
        "current_title": "Backend Engineer",
        "current_company": "Mindtree",
        "current_company_size": "10001+",
        "current_industry": "IT Services"
    },
    "career_history": [
        {
            "company": "Mindtree",
            "title": "Backend Engineer",
            "start_date": "2024-03-08",
            "end_date": None,
            "duration_months": 27,
            "is_current": True,
            "industry": "IT Services",
            "company_size": "10001+",
            "description": "Implemented streaming data pipelines."
        },
        {
            "company": "Dunder Mifflin",
            "title": "Analytics Engineer",
            "start_date": "2019-07-03",
            "end_date": "2024-01-08",
            "duration_months": 55,
            "is_current": False,
            "industry": "Paper Products",
            "company_size": "201-500",
            "description": "Built data pipelines on Apache Airflow."
        }
    ],
    "education": [
        {
            "institution": "Test University",
            "degree": "B.E.",
            "field_of_study": "Computer Science",
            "start_year": 2017,
            "end_year": 2020,
            "grade": "8.24 CGPA",
            "tier": "tier_3"
        }
    ],
    "skills": [
        {"name": "Python", "proficiency": "advanced", "endorsements": 15, "duration_months": 36},
        {"name": "Spark", "proficiency": "intermediate", "endorsements": 10, "duration_months": 24}
    ],
    "certifications": [],
    "languages": [
        {"language": "English", "proficiency": "professional"},
        {"language": "Hindi", "proficiency": "conversational"}
    ],
    "redrob_signals": {
        "profile_completeness_score": 86.9,
        "signup_date": "2025-10-16",
        "last_active_date": "2026-05-20",
        "open_to_work_flag": True,
        "profile_views_received_30d": 23,
        "applications_submitted_30d": 2,
        "recruiter_response_rate": 0.34,
        "avg_response_time_hours": 177.8,
        "skill_assessment_scores": {"NLP": 38.8},
        "connection_count": 356,
        "endorsements_received": 35,
        "notice_period_days": 60,
        "expected_salary_range_inr_lpa": {"min": 18.7, "max": 36.1},
        "preferred_work_mode": "onsite",
        "willing_to_relocate": False,
        "github_activity_score": 9.2,
        "search_appearance_30d": 249,
        "saved_by_recruiters_30d": 4,
        "interview_completion_rate": 0.71,
        "offer_acceptance_rate": 0.58,
        "verified_email": True,
        "verified_phone": True,
        "linkedin_connected": False
    }
}

# Minimal candidate with only required fields (for testing defaults)
MINIMAL_CANDIDATE = {
    "candidate_id": "CAND_9999999",
    "profile": {
        "anonymized_name": "Minimal",
        "headline": "Test",
        "summary": "A test candidate.",
        "location": "Test City",
        "country": "Test Country",
        "years_of_experience": 5.0,
        "current_title": "Engineer",
        "current_company": "Test Corp",
        "current_company_size": "11-50",
        "current_industry": "Software"
    },
    "career_history": [
        {
            "company": "Test Corp",
            "title": "Engineer",
            "start_date": "2020-01-01",
            "end_date": None,
            "duration_months": 60,
            "is_current": True,
            "industry": "Software",
            "company_size": "11-50",
            "description": "Test role."
        }
    ],
    "education": [
        {
            "institution": "Test University",
            "degree": "B.Sc",
            "field_of_study": "Computer Science",
            "start_year": 2010,
            "end_year": 2014
        }
    ],
    "skills": [
        {"name": "Python", "proficiency": "intermediate", "endorsements": 5}
    ],
    "redrob_signals": {
        "profile_completeness_score": 50.0,
        "signup_date": "2024-01-01",
        "last_active_date": "2026-01-01",
        "open_to_work_flag": True,
        "profile_views_received_30d": 10,
        "applications_submitted_30d": 1,
        "recruiter_response_rate": 0.5,
        "avg_response_time_hours": 24.0,
        "skill_assessment_scores": {},
        "connection_count": 100,
        "endorsements_received": 10,
        "notice_period_days": 30,
        "expected_salary_range_inr_lpa": {"min": 10.0, "max": 20.0},
        "preferred_work_mode": "hybrid",
        "willing_to_relocate": True,
        "github_activity_score": -1,
        "search_appearance_30d": 50,
        "saved_by_recruiters_30d": 5,
        "interview_completion_rate": 0.8,
        "offer_acceptance_rate": 0.5,
        "verified_email": True,
        "verified_phone": True,
        "linkedin_connected": True
    }
}


@pytest.fixture
def sample_candidate_data() -> dict:
    """Return a valid sample candidate dict."""
    return dict(SAMPLE_CANDIDATE)


@pytest.fixture
def minimal_candidate_data() -> dict:
    """Return a minimal valid candidate dict."""
    return dict(MINIMAL_CANDIDATE)


@pytest.fixture
def jsonl_file(sample_candidate_data) -> Generator[Path, None, None]:
    """Create a temporary JSONL file with sample data."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        f.write(json.dumps(sample_candidate_data) + "\n")
        f.write(json.dumps(sample_candidate_data) + "\n")
        f.write(json.dumps(sample_candidate_data) + "\n")
        f.write("\n")  # blank line
        f.write("invalid json\n")  # malformed
        f.write(json.dumps(sample_candidate_data) + "\n")
        tmp_path = f.name

    yield Path(tmp_path)

    try:
        os.unlink(tmp_path)
    except OSError:
        pass


@pytest.fixture
def large_jsonl_file(request) -> Generator[Path, None, None]:
    """Create a larger JSONL file with N candidates for performance testing."""
    n = getattr(request, "param", 1000)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        for i in range(n):
            candidate = dict(SAMPLE_CANDIDATE)
            candidate["candidate_id"] = f"CAND_{i:07d}"
            f.write(json.dumps(candidate) + "\n")
        tmp_path = f.name

    yield Path(tmp_path)

    try:
        os.unlink(tmp_path)
    except OSError:
        pass
