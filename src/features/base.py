"""Base class for all feature extractors.

Each feature engine (Semantic, Career Intelligence, Behavioral, etc.)
extends BaseFeatureExtractor and implements the extract() method
to produce a dict of feature scores for a given Candidate.
"""

from abc import ABC, abstractmethod

from src.parser.candidate_parser import Candidate


class BaseFeatureExtractor(ABC):
    """Abstract base class for feature extraction modules.

    Subclasses must define:
        name: Human-readable name (e.g., "semantic", "career_intelligence")
        description: Brief description of what the extractor computes

    Subclasses must implement:
        extract(candidate) -> dict[str, float]
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name identifier for this extractor."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of this extractor."""
        pass

    @abstractmethod
    def extract(self, candidate: Candidate) -> dict[str, float]:
        """Extract features from a Candidate object.

        Args:
            candidate: Fully parsed Candidate object.

        Returns:
            Dict mapping feature name -> score value (typically 0.0-1.0).
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"
