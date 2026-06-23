#!/usr/bin/env python3
"""Redrob AI Ranker — reproducible ranking pipeline.

Usage:
    python rank.py --candidates <candidates.jsonl> --out <submission.csv>

Produces:
    submission.csv with columns: candidate_id, rank, score, reasoning
    Exactly 100 rows (top 100 candidates), ranked 1-100.

Constraints:
    - CPU-only (no GPU)
    - ≤ 16 GB RAM
    - ≤ 5 minutes runtime
    - No network access during ranking phase
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path

# Ensure src/ is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.loader.data_loader import DataLoader
from src.parser.candidate_parser import CandidateParser
from src.features.framework import FeatureRegistry
from src.features.career_intelligence import CareerIntelligence
from src.features.behavioral_intelligence import BehavioralIntelligence
from src.features.honeypot_detection import HoneypotDetector
from src.features.semantic import SemanticEngine
from src.ranker.ranker import FinalRanker, ScoreFusion, ReasoningGenerator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("redrob-ranker")

CANDIDATES_PATH = (
    Path(__file__).resolve().parent
    / "[PUB] India_runs_data_and_ai_challenge"
    / "India_runs_data_and_ai_challenge"
    / "candidates.jsonl"
)
EMBEDDINGS_DIR = Path("./embeddings")
SUBMISSION_CSV = "submission.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Redrob AI Ranker — rank candidates for Senior AI Engineer role."
    )
    parser.add_argument(
        "--candidates",
        default=str(CANDIDATES_PATH),
        help="Path to candidates.jsonl (default: competition dataset)",
    )
    parser.add_argument(
        "--out",
        default=SUBMISSION_CSV,
        help="Output path for submission.csv (default: ./submission.csv)",
    )
    parser.add_argument(
        "--embeddings",
        default=str(EMBEDDINGS_DIR),
        help="Directory for cached embeddings (default: ./embeddings/)",
    )
    parser.add_argument(
        "--no-semantic",
        action="store_true",
        help="Skip SemanticEngine (no model download, no embeddings)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=100,
        help="Number of top candidates to output (default: 100)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    t_start = time.perf_counter()

    # -----------------------------------------------------------------------
    # 1. Load & parse candidates (streaming)
    # -----------------------------------------------------------------------
    t0 = time.perf_counter()
    candidates_path = Path(args.candidates)
    if not candidates_path.exists():
        logger.error("Candidates file not found: %s", candidates_path)
        sys.exit(1)

    loader = DataLoader(str(candidates_path))
    parser = CandidateParser()

    all_candidates = []
    for raw in loader.stream():
        candidate = parser.parse(raw)
        if candidate is not None:
            all_candidates.append(candidate)

    t_parse = time.perf_counter() - t0
    logger.info(
        "Loaded %d candidates in %.2fs (%.0f cand/s)",
        len(all_candidates), t_parse, len(all_candidates) / t_parse if t_parse > 0 else 0,
    )

    # -----------------------------------------------------------------------
    # 2. Build feature registry with all engines
    # -----------------------------------------------------------------------
    registry = FeatureRegistry()

    # Phase 6 — Career Intelligence (no model, no network)
    registry.register(CareerIntelligence())

    # Phase 7 — Behavioral Intelligence (no model, no network)
    registry.register(BehavioralIntelligence())

    # Phase 8 — Honeypot Detection (no model, no network)
    registry.register(HoneypotDetector())

    # Phase 5 — Semantic Engine (model downloaded during build phase)
    if not args.no_semantic:
        embeddings_dir = Path(args.embeddings)
        engine = SemanticEngine()
        cache_path = embeddings_dir / "embeddings_cache.pkl"

        if cache_path.exists():
            # Load cached embeddings — no model needed, no network
            t_load = time.perf_counter()
            engine.load_embeddings(str(embeddings_dir))
            logger.info(
                "Loaded embeddings cache in %.2fs", time.perf_counter() - t_load,
            )
        else:
            # Pre-compute and cache embeddings
            logger.info("Pre-computing embeddings for %d candidates...", len(all_candidates))
            t_pre = time.perf_counter()
            engine.precompute(all_candidates)
            embeddings_dir.mkdir(parents=True, exist_ok=True)
            engine.save_embeddings(str(embeddings_dir))
            logger.info(
                "Pre-computed embeddings in %.2fs", time.perf_counter() - t_pre,
            )

        registry.register(engine)
    else:
        logger.info("SemanticEngine disabled via --no-semantic")

    # -----------------------------------------------------------------------
    # 3. Rank candidates
    # -----------------------------------------------------------------------
    ranker = FinalRanker(registry)

    t_rank = time.perf_counter()
    all_results = ranker.rank(all_candidates)
    t_rank = time.perf_counter() - t_rank

    logger.info(
        "Ranked %d candidates in %.2fs (%.0f cand/s)",
        len(all_results), t_rank, len(all_results) / t_rank if t_rank > 0 else 0,
    )

    # -----------------------------------------------------------------------
    # 4. Output top-K submission
    # -----------------------------------------------------------------------
    top_k = min(args.top_k, len(all_results))
    top_results = all_results[:top_k]

    # Re-assign ranks 1..K
    for i, r in enumerate(top_results):
        r.rank = i + 1

    output_path = Path(args.out)
    ranker.save_submission(top_results, str(output_path))

    t_total = time.perf_counter() - t_start
    logger.info(
        "Pipeline complete in %.2fs. Top-%d candidates saved to %s",
        t_total, top_k, output_path,
    )

    # Print summary of top 10
    print(f"\n{'='*80}")
    print(f"  Redrob AI Ranker — Top {top_k} Candidates")
    print(f"{'='*80}")
    print(f"  {'Rank':<6} {'Candidate ID':<18} {'Score':<8} {'Reasoning'}")
    print(f"  {'-'*6} {'-'*18} {'-'*8} {'-'*40}")
    for r in top_results[:10]:
        rid = r.candidate_id
        reasoning = r.reasoning[:75] + "..." if len(r.reasoning) > 75 else r.reasoning
        print(f"  {r.rank:<6} {rid:<18} {r.score:<8.4f} {reasoning}")
    if top_k > 10:
        print(f"  ... ({top_k - 10} more candidates in {output_path})")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
