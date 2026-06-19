"""Feature registry — manages registration and dispatch of feature extractors.

The FeatureRegistry allows:
- Registering extractors by name
- Looking up extractors
- Running all registered extractors against a candidate
- Collecting results into a single feature dict
"""

import logging

from src.features.base import BaseFeatureExtractor
from src.parser.candidate_parser import Candidate

logger = logging.getLogger("redrob-ranker")


class FeatureRegistry:
    """Registry of feature extractors with batch dispatch support.

    Example:
        registry = FeatureRegistry()
        registry.register(MyExtractor())
        features = registry.extract_all(candidate)
    """

    def __init__(self) -> None:
        self._extractors: dict[str, BaseFeatureExtractor] = {}

    @property
    def extractors(self) -> dict[str, BaseFeatureExtractor]:
        """Return registered extractors dict (name -> extractor)."""
        return dict(self._extractors)

    @property
    def extractor_names(self) -> list[str]:
        """Return sorted list of registered extractor names."""
        return sorted(self._extractors.keys())

    @property
    def feature_count(self) -> int:
        """Total number of feature names declared by all registered extractors.

        Relies on the optional `features` class attribute; if not declared,
        falls back to 1 per extractor as a minimum estimate.
        """
        if not self._extractors:
            return 0
        total = 0
        for ext in self._extractors.values():
            declared = getattr(ext, "features", None)
            if isinstance(declared, (list, set, tuple)):
                total += len(declared)
            else:
                # Minimum estimate — extractors not declaring features
                # are assumed to produce at least 1 feature
                total += 1
        return total

    def register(self, extractor: BaseFeatureExtractor) -> None:
        """Register a feature extractor.

        Args:
            extractor: Instance of a BaseFeatureExtractor subclass.

        Raises:
            ValueError: If an extractor with the same name is already registered.
        """
        if extractor.name in self._extractors:
            raise ValueError(
                f"Extractor '{extractor.name}' is already registered. "
                f"Use replace() to overwrite."
            )
        self._extractors[extractor.name] = extractor
        logger.info("Registered extractor: %s", extractor.name)

    def replace(self, extractor: BaseFeatureExtractor) -> None:
        """Register or replace a feature extractor.

        Unlike register(), this will silently overwrite an existing extractor.
        """
        self._extractors[extractor.name] = extractor
        logger.info("Replaced extractor: %s", extractor.name)

    def unregister(self, name: str) -> None:
        """Remove a registered extractor by name."""
        self._extractors.pop(name, None)
        logger.info("Unregistered extractor: %s", name)

    def get(self, name: str) -> BaseFeatureExtractor:
        """Get a registered extractor by name.

        Raises:
            KeyError: If extractor is not registered.
        """
        if name not in self._extractors:
            raise KeyError(f"Extractor '{name}' not found. Registered: {self.extractor_names}")
        return self._extractors[name]

    def extract_all(self, candidate: Candidate) -> dict[str, float]:
        """Run all registered extractors and merge results.

        Args:
            candidate: Parsed Candidate object.

        Returns:
            Single dict of all feature_name -> score pairs.
        """
        features: dict[str, float] = {}
        for name, extractor in self._extractors.items():
            try:
                result = extractor.extract(candidate)
                if not isinstance(result, dict):
                    logger.warning("Extractor '%s' returned non-dict: %s", name, type(result).__name__)
                    continue
                # Validate all values are numeric
                for key, value in result.items():
                    if not isinstance(value, (int, float)):
                        logger.warning(
                            "Extractor '%s' returned non-numeric value for '%s': %s",
                            name, key, type(value).__name__
                        )
                        continue
                    features[key] = float(value)
            except Exception as e:
                logger.error("Extractor '%s' failed: %s", name, e)

        return features

    def extract_batch(self, candidates: list[Candidate]) -> list[dict[str, float]]:
        """Run all extractors on a batch of candidates.

        Args:
            candidates: List of parsed Candidate objects.

        Returns:
            List of feature dicts, one per candidate.
        """
        return [self.extract_all(c) for c in candidates]

    def clear(self) -> None:
        """Remove all registered extractors."""
        self._extractors.clear()
        logger.info("Feature registry cleared")
