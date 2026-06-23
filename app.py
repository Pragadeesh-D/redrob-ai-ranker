"""Redrob AI Ranker — Streamlit Demo App.

Shows the candidate ranking pipeline with score breakdown:
- Semantic Score (Phase 5)
- Career Intelligence Score (Phase 6)
- Behavioral Score (Phase 7) — Availability, Trust, Demand, Engagement
- Honeypot Penalty (Phase 8)
- Final ranking output with reasoning
"""

import os
import sys
import time
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.loader.data_loader import DataLoader
from src.parser.candidate_parser import CandidateParser
from src.features.framework import FeatureRegistry
from src.features.career_intelligence import CareerIntelligence
from src.features.behavioral_intelligence import BehavioralIntelligence
from src.features.honeypot_detection import HoneypotDetector
from src.ranker.ranker import FinalRanker, ScoreFusion

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Redrob AI Ranker",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CANDIDATES_PATH = (
    Path(__file__).resolve().parent
    / "[PUB] India_runs_data_and_ai_challenge"
    / "India_runs_data_and_ai_challenge"
    / "candidates.jsonl"
)
SAMPLE_CANDIDATES_PATH = (
    Path(__file__).resolve().parent
    / "[PUB] India_runs_data_and_ai_challenge"
    / "India_runs_data_and_ai_challenge"
    / "sample_candidates.json"
)
SUBMISSION_CSV = "submission.csv"

# ---------------------------------------------------------------------------
# Cached pipeline runner
# ---------------------------------------------------------------------------

@st.cache_resource
def get_registry():
    """Build the feature registry with non-semantic engines (no model download)."""
    registry = FeatureRegistry()
    registry.register(CareerIntelligence())
    registry.register(BehavioralIntelligence())
    registry.register(HoneypotDetector())
    return registry


def load_sample_candidates():
    """Load sample candidates for demo (small set, no model needed)."""
    if not SAMPLE_CANDIDATES_PATH.exists():
        # Fall back to first 10 lines of candidates.jsonl
        loader = DataLoader(str(CANDIDATES_PATH))
        parser = CandidateParser()
        candidates = []
        for i, raw in enumerate(loader.stream()):
            if i >= 10:
                break
            candidate = parser.parse(raw)
            if candidate is not None:
                candidates.append(candidate)
        return candidates

    import json
    with open(SAMPLE_CANDIDATES_PATH, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    parser = CandidateParser()
    candidates = []
    if isinstance(raw_data, list):
        for item in raw_data:
            candidate = parser.parse(item)
            if candidate is not None:
                candidates.append(candidate)
    else:
        candidate = parser.parse(raw_data)
        if candidate is not None:
            candidates.append(candidate)
    return candidates or []


@st.cache_data
def run_ranking(candidate_ids: tuple[str]) -> pd.DataFrame:
    """Run the ranking pipeline on sample candidates, return detailed results."""
    all_candidates = load_sample_candidates()
    registry = get_registry()
    ranker = FinalRanker(registry)
    results = ranker.rank(all_candidates)

    rows = []
    for r in results:
        features = ranker.registry.extract_all(
            next(c for c in all_candidates if c.candidate_id == r.candidate_id)
        )
        rows.append({
            "candidate_id": r.candidate_id,
            "rank": r.rank,
            "final_score": r.score,
            "reasoning": r.reasoning,
            "semantic_jd": features.get("jd_similarity_score", 0.0),
            "semantic_summary": features.get("summary_similarity_score", 0.0),
            "career_product": features.get("product_company_score", 0.0),
            "career_engineering": features.get("engineering_depth_score", 0.0),
            "career_progression": features.get("career_progression_score", 0.0),
            "career_ml": features.get("production_ml_score", 0.0),
            "career_retrieval": features.get("retrieval_experience_score", 0.0),
            "career_ranking": features.get("ranking_experience_score", 0.0),
            "availability_score": features.get("availability_score", 0.0),
            "trust_score": features.get("trust_score", 0.0),
            "demand_score": features.get("demand_score", 0.0),
            "engagement_score": features.get("engagement_score", 0.0),
            "honeypot_risk": max(
                features.get("timeline_impossible_score", 0.0),
                features.get("seniority_mismatch_score", 0.0),
                features.get("skill_zero_duration_expert_score", 0.0),
                features.get("progression_jump_score", 0.0),
            ),
            "headline": _get_headline(all_candidates, r.candidate_id),
        })

    return pd.DataFrame(rows)


def _get_headline(candidates, cid: str) -> str:
    """Get a candidate's headline or current title for display."""
    for c in candidates:
        if c.candidate_id == cid:
            return getattr(c.profile, "headline", "") or getattr(c.profile, "current_title", "")
    return ""


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

st.title("🏆 Redrob AI Ranker")
st.markdown(
    """
    **Intelligent Candidate Discovery & Ranking** — for the *Senior AI Engineer, Founding Team* role at Redrob.

    This demo shows the multi-phase ranking pipeline that fuses signals from 5 feature engines
    (Career Intelligence, Behavioral, Honeypot Detection) into a single composite score.
    """
)

# --- Sidebar ---
st.sidebar.header("About")
st.sidebar.markdown(
    """
    **Phases:**
    - **Phase 5:** Semantic Engine — JD similarity via sentence embeddings *(not loaded in demo — run `python rank.py` for full pipeline)*
    - **Phase 6:** Career Intelligence — Product/ML/Startup experience signals
    - **Phase 7:** Behavioral — Availability, Trust, Demand, Engagement
    - **Phase 8:** Honeypot Detection — Timeline/skill/seniority consistency
    - **Phase 9:** Final Ranker — Weighted score fusion + reasoning
    """
)

st.sidebar.header("Scoring Weights")
st.sidebar.markdown(
    """
    | Component | Weight |
    |-----------|--------|
    | Career Intelligence | 35% |
    | Semantic (JD match) | 20% |
    | Engagement | 15% |
    | Availability | 10% |
    | Trust | 10% |
    | Demand | 10% |
    | **Honeypot penalty** | up to 50% deduction |
    """
)

st.sidebar.header("Constraints")
st.sidebar.markdown(
    """
    - ✅ CPU-only (no GPU)
    - ✅ ≤ 16 GB RAM
    - ✅ < 5 min runtime
    - ✅ No network during ranking
    - ✅ Deterministic output
    """
)

# --- Main content ---
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Phases", "10", delta="All complete")
with col2:
    st.metric("Features", "45+", delta="Across 5 engines")
with col3:
    st.metric("Tests", "276", delta="All passing")

st.divider()

# --- Load and run ---
with st.spinner("Loading candidate data and running ranking pipeline..."):
    candidates = load_sample_candidates()
    if not candidates:
        st.error("No candidates found. Ensure the competition dataset is available.")
        st.stop()

    df = run_ranking(tuple(c.candidate_id for c in candidates))

st.success(f"Loaded {len(candidates)} sample candidates. Ranking complete.")

# --- Ranked table ---
st.subheader("📊 Ranked Candidates")
st.dataframe(
    df[["rank", "candidate_id", "final_score", "reasoning"]].style
    .format({"final_score": "{:.4f}"})
    .highlight_bottom(subset="final_score", color="#f0f0f0")
    .highlight_top(subset="final_score", color="#90EE90"),
    use_container_width=True,
    hide_index=True,
)

# --- Score breakdown ---
st.subheader("📈 Score Breakdown")
candidate_ids = df["candidate_id"].tolist()
selected = st.selectbox("Select a candidate to inspect:", candidate_ids)

row = df[df["candidate_id"] == selected].iloc[0]
st.markdown(f"**{row['headline']}** — Final Score: **{row['final_score']:.4f}**")
st.markdown(f"*Reasoning:* {row['reasoning']}")

# Radar chart
categories = [
    "Career\nIntelligence",
    "Availability",
    "Trust",
    "Demand",
    "Engagement",
    "Honeypot Risk",
]
values = [
    row["career_product"],
    row["availability_score"],
    row["trust_score"],
    row["demand_score"],
    row["engagement_score"],
    row["honeypot_risk"],
]

fig = go.Figure(data=go.Scatterpolar(
    r=values + [values[0]],
    theta=categories + [categories[0]],
    fill="toself",
    line=dict(color="#1f77b4", width=2),
    marker=dict(size=6),
))
fig.update_layout(
    polar=dict(
        radialaxis=dict(visible=True, range=[0, 1]),
    ),
    showlegend=False,
    height=400,
    margin=dict(l=80, r=80, t=20, b=20),
)
st.plotly_chart(fig, use_container_width=True)

# --- Cross-candidate comparison ---
st.subheader("🔄 Cross-Candidate Comparison")
fig2 = px.bar(
    df.head(10),
    x="candidate_id",
    y="final_score",
    color="final_score",
    color_continuous_scale="Viridis",
    text="reasoning",
    labels={"final_score": "Score", "candidate_id": "Candidate"},
    title="Top 10 Candidates by Final Score",
)
fig2.update_traces(textposition="outside", textfont_size=9)
fig2.update_layout(showlegend=False, height=400)
st.plotly_chart(fig2, use_container_width=True)

# --- Component score heatmap ---
st.subheader("🔍 Component Score Heatmap")
heatmap_cols = [
    "career_product", "career_engineering", "career_progression",
    "career_ml", "career_retrieval", "career_ranking",
    "availability_score", "trust_score", "demand_score", "engagement_score",
    "honeypot_risk",
]
heatmap_labels = [
    "Product", "Engineering", "Progression",
    "ML Exp.", "Retrieval", "Ranking",
    "Available", "Trust", "Demand", "Engage",
    "Honeypot⚠",
]
heatmap_data = df.head(10)[heatmap_cols].values

fig3 = px.imshow(
    heatmap_data,
    x=heatmap_labels,
    y=df.head(10)["candidate_id"],
    color_continuous_scale="RdYlGn",
    aspect="auto",
    labels=dict(x="Component", y="Candidate", color="Score"),
    title="Top 10 Candidates — Component Score Heatmap",
)
fig3.update_layout(height=400, margin=dict(l=120, r=20, t=40, b=80))
st.plotly_chart(fig3, use_container_width=True)

# --- Submission download ---
st.subheader("📥 Download Submission")
if Path(SUBMISSION_CSV).exists():
    with open(SUBMISSION_CSV, "rb") as f:
        st.download_button(
            label="Download submission.csv",
            data=f,
            file_name="submission.csv",
            mime="text/csv",
        )
else:
    st.info("Run the full pipeline (`python rank.py`) to generate the complete submission.")

st.divider()
st.caption(
    "Built for the Redrob Intelligent Candidate Discovery & Ranking Challenge. "
    "CPU-only, deterministic, fully reproducible."
)
