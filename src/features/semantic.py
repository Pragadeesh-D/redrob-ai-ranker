"""Semantic Engine — embedding-based candidate-JD similarity scoring.

Computes semantic similarity between candidate profile text fields and
the target job description using sentence-transformers/all-MiniLM-L6-v2.

Features produced:
    jd_similarity_score: Overall profile-JD cosine similarity
    summary_similarity_score: Profile summary vs JD
    headline_similarity_score: Professional headline vs JD
    career_similarity_score: Career history vs JD
"""

import logging
from pathlib import Path
from typing import Optional

import numpy as np
from sentence_transformers import SentenceTransformer, util

from src.features.base import BaseFeatureExtractor
from src.parser.candidate_parser import Candidate

logger = logging.getLogger("redrob-ranker")

DEFAULT_JD_PATH = Path("job_description.txt")
DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
FALLBACK_JD_TEXT = (
    "Senior AI Engineer role requiring production experience with "
    "embeddings, retrieval, ranking, and LLMs. Needs strong Python skills, "
    "experience with vector databases, evaluation frameworks (NDCG, MRR, MAP), "
    "and a track record of shipping ML systems to production."
)


class SemanticEngine(BaseFeatureExtractor):
    """Feature extractor computing semantic similarity between candidate
    profile fields and the target job description.

    Uses sentence-transformers/all-MiniLM-L6-v2 for CPU-only embedding
    and cosine similarity scoring. Supports batch pre-computation for
    efficient processing of large candidate lists.

    Example:
        engine = SemanticEngine()
        engine.precompute(candidates)   # batch encode all candidates
        features = engine.extract(candidate)  # per-candidate lookup
    """

    features = [
        "jd_similarity_score",
        "summary_similarity_score",
        "headline_similarity_score",
        "career_similarity_score",
    ]

    # Class-level model/embedding cache (shared across instances)
    _model: Optional[SentenceTransformer] = None
    _jd_embedding: Optional[np.ndarray] = None

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def __init__(
        self,
        jd_path: Path = DEFAULT_JD_PATH,
        model_name: str = DEFAULT_MODEL_NAME,
        batch_size: int = 64,
    ) -> None:
        self.jd_path = Path(jd_path)
        self.model_name = model_name
        self.batch_size = batch_size

        # Load JD text
        self._jd_text = self._load_jd_text()

        # Load model and pre-compute JD embedding (class-level singletons)
        self._ensure_model()
        self._ensure_jd_embedding()

        # Per-instance embedding caches (populated by precompute())
        self._combined_embeddings: dict[str, np.ndarray] = {}
        self._summary_embeddings: dict[str, np.ndarray] = {}
        self._headline_embeddings: dict[str, np.ndarray] = {}
        self._career_embeddings: dict[str, np.ndarray] = {}

    # ------------------------------------------------------------------
    # BaseFeatureExtractor interface
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "semantic"

    @property
    def description(self) -> str:
        return (
            "Embedding-based semantic similarity scoring using "
            "sentence-transformers/all-MiniLM-L6-v2. Computes cosine similarity "
            "between candidate profile fields (summary, headline, career history) "
            "and the target job description."
        )

    def extract(self, candidate: Candidate) -> dict[str, float]:
        """Extract semantic similarity features for a single candidate.

        Uses pre-computed embeddings from precompute() for efficiency.
        Falls back to on-the-fly encoding if precompute() was not called.

        Args:
            candidate: Parsed Candidate object.

        Returns:
            Dict of feature_name -> score (clamped 0.0 to 1.0).
        """
        cid = candidate.candidate_id
        jd_emb = self._jd_embedding

        # Use pre-computed embeddings if available
        if self._combined_embeddings and cid in self._combined_embeddings:
            combined_sim = float(
                util.cos_sim(self._combined_embeddings[cid], jd_emb).item()
            )
            summary_sim = float(
                util.cos_sim(self._summary_embeddings[cid], jd_emb).item()
            )
            headline_sim = float(
                util.cos_sim(self._headline_embeddings[cid], jd_emb).item()
            )
            career_sim = float(
                util.cos_sim(self._career_embeddings[cid], jd_emb).item()
            )
        else:
            # Fallback: encode on-the-fly (slower, per-candidate)
            combined_sim = self._encode_and_sim(
                self._build_combined_text(candidate)
            )
            summary_sim = self._encode_and_sim(
                candidate.profile.summary or ""
            )
            headline_sim = self._encode_and_sim(
                candidate.profile.headline or ""
            )
            career_sim = self._encode_and_sim(
                self._build_career_text(candidate)
            )

        # Cosine similarity ranges [-1, 1]; clamp to [0, 1] for scoring
        return {
            "jd_similarity_score": max(0.0, min(1.0, combined_sim)),
            "summary_similarity_score": max(0.0, min(1.0, summary_sim)),
            "headline_similarity_score": max(0.0, min(1.0, headline_sim)),
            "career_similarity_score": max(0.0, min(1.0, career_sim)),
        }

    # ------------------------------------------------------------------
    # Batch pre-computation (call once before iterating)
    # ------------------------------------------------------------------

    def precompute(self, candidates: list[Candidate]) -> None:
        """Pre-compute embeddings for all candidates in batches.

        Encodes summary, headline, career history, and combined profile
        text for each candidate. Must be called before extract() for
        efficient per-candidate scoring.

        Args:
            candidates: List of parsed Candidate objects.
        """
        if not candidates:
            return

        logger.info(
            "Pre-computing embeddings for %d candidates (batch_size=%d)...",
            len(candidates), self.batch_size,
        )

        valid_ids = []
        combined_texts = []
        summary_texts = []
        headline_texts = []
        career_texts = []

        for c in candidates:
            valid_ids.append(c.candidate_id)

            combined_texts.append(self._build_combined_text(c))
            summary_texts.append(c.profile.summary or "")
            headline_texts.append(c.profile.headline or "")
            career_texts.append(self._build_career_text(c))

        # Encode all four text fields in batch calls
        self._combined_embeddings = self._batch_encode(
            combined_texts, valid_ids
        )
        self._summary_embeddings = self._batch_encode(
            summary_texts, valid_ids
        )
        self._headline_embeddings = self._batch_encode(
            headline_texts, valid_ids
        )
        self._career_embeddings = self._batch_encode(
            career_texts, valid_ids
        )

        logger.info(
            "Embeddings pre-computed for %d candidates", len(valid_ids)
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _batch_encode(
        self, texts: list[str], ids: list[str]
    ) -> dict[str, np.ndarray]:
        """Encode a list of texts and return an id->embedding dict."""
        embeddings = self._model.encode(
            texts,
            batch_size=self.batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return dict(zip(ids, embeddings))

    def _encode_and_sim(self, text: str) -> float:
        """Encode a single text and compute cosine similarity to JD."""
        if not text.strip():
            return 0.0
        emb = self._model.encode(
            text, convert_to_numpy=True, normalize_embeddings=True
        )
        return float(util.cos_sim(emb, self._jd_embedding).item())

    @staticmethod
    def _build_combined_text(candidate: Candidate) -> str:
        """Build combined profile text for overall JD similarity."""
        parts = [
            candidate.profile.headline or "",
            candidate.profile.summary or "",
            candidate.profile.current_title or "",
        ]
        return " ".join(parts)

    @staticmethod
    def _build_career_text(candidate: Candidate) -> str:
        """Build career history text from all career entries."""
        parts = [
            ce.description for ce in candidate.career_history if ce.description
        ]
        return " ".join(parts) if parts else ""

    def _load_jd_text(self) -> str:
        """Read the job description text from file."""
        if not self.jd_path.exists():
            logger.warning(
                "JD file not found at %s, using fallback text", self.jd_path
            )
            return FALLBACK_JD_TEXT
        text = self.jd_path.read_text(encoding="utf-8").strip()
        if not text:
            logger.warning(
                "JD file is empty at %s, using fallback text", self.jd_path
            )
            return FALLBACK_JD_TEXT
        return text

    def _ensure_model(self) -> None:
        """Load the sentence-transformers model (class-level singleton)."""
        if self.__class__._model is None:
            logger.info("Loading model: %s", self.model_name)
            self.__class__._model = SentenceTransformer(
                self.model_name, device="cpu"
            )
            logger.info("Model loaded successfully")

    def _ensure_jd_embedding(self) -> None:
        """Pre-compute the JD embedding once (class-level singleton)."""
        if self.__class__._jd_embedding is None:
            logger.info("Computing JD embedding...")
            self.__class__._jd_embedding = self._model.encode(
                self._jd_text,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
            logger.info("JD embedding computed (dim=%d)",
                        self._jd_embedding.shape[0])

    # ------------------------------------------------------------------
    # Disk cache for pre-computed embeddings
    # ------------------------------------------------------------------

    def save_embeddings(self, directory: Path) -> None:
        """Save pre-computed embeddings to disk as .npz files.

        Saves all 4 embedding dicts and the JD embedding to the specified
        directory. The model does not need to be loaded when loading
        embeddings later — only the JD embedding and candidate embeddings
        are needed for scoring.

        Args:
            directory: Path to directory where embeddings will be saved.
                Directory will be created if it does not exist.

        Raises:
            ValueError: If no embeddings have been pre-computed.
        """
        if not self._combined_embeddings:
            raise ValueError(
                "No embeddings to save. Call precompute(candidates) first."
            )

        save_dir = Path(directory)
        save_dir.mkdir(parents=True, exist_ok=True)

        def _save_dict(emb_dict: dict[str, np.ndarray], name: str) -> None:
            if not emb_dict:
                logger.warning("Empty embedding dict '%s', skipping save", name)
                return
            ids = list(emb_dict.keys())
            embeddings = np.array([emb_dict[i] for i in ids])
            np.savez(
                save_dir / f"{name}.npz",
                ids=np.array(ids, dtype=object),
                embeddings=embeddings,
            )
            logger.info("Saved %d embeddings to '%s.npz'", len(ids), name)

        _save_dict(self._combined_embeddings, "combined_embeddings")
        _save_dict(self._summary_embeddings, "summary_embeddings")
        _save_dict(self._headline_embeddings, "headline_embeddings")
        _save_dict(self._career_embeddings, "career_embeddings")

        # Save JD embedding
        np.save(save_dir / "jd_embedding.npy", self._jd_embedding)
        logger.info("Saved JD embedding to 'jd_embedding.npy'")

        logger.info("All embeddings saved to %s", save_dir)

    def load_embeddings(self, directory: Path) -> None:
        """Load pre-computed embeddings from disk.

        Restores all 4 embedding dicts and the JD embedding. After loading,
        extract() works immediately without needing the model or encoding.

        The model is NOT loaded — only the JD embedding is restored.
        This is the fast path for the ranking phase.

        Args:
            directory: Path to directory containing saved .npz files.

        Raises:
            FileNotFoundError: If embedding files are not found.
        """
        load_dir = Path(directory)

        if not load_dir.exists():
            raise FileNotFoundError(
                f"Embedding directory not found: {load_dir}"
            )

        def _load_dict(name: str) -> dict[str, np.ndarray]:
            npz_path = load_dir / f"{name}.npz"
            if not npz_path.exists():
                logger.warning("Embedding file not found: %s", npz_path)
                return {}
            data = np.load(npz_path, allow_pickle=True)
            ids = data["ids"]
            embeddings = data["embeddings"]
            result = {str(i): embeddings[idx] for idx, i in enumerate(ids)}
            logger.info("Loaded %d embeddings from '%s'", len(result), name)
            return result

        self._combined_embeddings = _load_dict("combined_embeddings")
        self._summary_embeddings = _load_dict("summary_embeddings")
        self._headline_embeddings = _load_dict("headline_embeddings")
        self._career_embeddings = _load_dict("career_embeddings")

        # Load JD embedding
        jd_path = load_dir / "jd_embedding.npy"
        if jd_path.exists():
            self.__class__._jd_embedding = np.load(jd_path)
            logger.info("Loaded JD embedding from 'jd_embedding.npy'")
        else:
            logger.warning("JD embedding file not found: %s", jd_path)

        logger.info("All embeddings loaded from %s", load_dir)

    # ------------------------------------------------------------------
    # Memory management
    # ------------------------------------------------------------------

    def clear_cache(self) -> None:
        """Clear per-instance embedding caches to free memory."""
        self._combined_embeddings.clear()
        self._summary_embeddings.clear()
        self._headline_embeddings.clear()
        self._career_embeddings.clear()
        logger.info("Semantic engine cache cleared")

    @classmethod
    def unload_model(cls) -> None:
        """Unload the shared model and JD embedding to free memory."""
        cls._model = None
        cls._jd_embedding = None
        logger.info("Semantic engine model unloaded")

    def __repr__(self) -> str:
        return (
            f"SemanticEngine(name='{self.name}', model='{self.model_name}', "
            f"cached={len(self._combined_embeddings)})"
        )
