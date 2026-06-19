"""Streaming JSONL data loader with chunk-based processing support.

Handles line-by-line reading of large JSONL files with configurable
chunk sizes, error tolerance, and progress tracking.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Generator, Optional

logger = logging.getLogger("redrob-ranker")


@dataclass
class DataLoaderConfig:
    """Configuration for the DataLoader.

    Attributes:
        chunk_size: Number of candidates to accumulate before yielding a chunk.
        max_errors: Maximum number of parse errors before aborting.
        encoding: File encoding (default: utf-8).
        skip_blank_lines: Whether to skip empty lines silently.
    """

    chunk_size: int = 1
    max_errors: int = 100
    encoding: str = "utf-8"
    skip_blank_lines: bool = True


class DataLoader:
    """Streaming JSONL data loader.

    Reads a JSONL file line-by-line, parsing each line as a JSON object.
    Supports both line-by-line iteration and chunk-based batch iteration.

    Args:
        file_path: Path to the JSONL file.
        config: Optional configuration overrides.

    Raises:
        FileNotFoundError: If the file does not exist.
    """

    def __init__(self, file_path: Path, config: Optional[DataLoaderConfig] = None) -> None:
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"Candidate file not found: {self.file_path}")

        self.config = config or DataLoaderConfig()
        self._total_read: int = 0
        self._total_valid: int = 0
        self._total_errors: int = 0
        self._error_lines: list[int] = []

    @property
    def total_read(self) -> int:
        """Total lines read from file."""
        return self._total_read

    @property
    def total_valid(self) -> int:
        """Total successfully parsed candidates."""
        return self._total_valid

    @property
    def total_errors(self) -> int:
        """Total parse errors encountered."""
        return self._total_errors

    @property
    def error_lines(self) -> list[int]:
        """Line numbers where errors occurred."""
        return list(self._error_lines)

    def stream(self) -> Generator[dict[str, Any], None, None]:
        """Yield parsed candidate dicts one at a time.

        Skips blank lines and malformed JSON. Tracks error count.
        Raises RuntimeError if error threshold is exceeded.

        Yields:
            Parsed JSON dict for each valid candidate.
        """
        self._reset_counters()

        with open(self.file_path, "r", encoding=self.config.encoding) as f:
            for line_no, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    if not self.config.skip_blank_lines:
                        self._handle_error(line_no, "Blank line encountered")
                    continue

                try:
                    candidate = json.loads(line)
                    if not isinstance(candidate, dict):
                        self._handle_error(line_no, "JSON value is not an object")
                        continue
                    self._total_read += 1
                    self._total_valid += 1
                    yield candidate
                except json.JSONDecodeError as e:
                    self._handle_error(line_no, f"JSON decode error: {e}")
                    if self._total_errors > self.config.max_errors:
                        raise RuntimeError(
                            f"Exceeded max error threshold ({self.config.max_errors}) "
                            f"at line {line_no}. Last error: {e}"
                        )

    def stream_chunks(self) -> Generator[list[dict[str, Any]], None, None]:
        """Yield parsed candidate dicts in batches of config.chunk_size.

        Yields:
            Lists of parsed JSON dicts (size = chunk_size, except last).
        """
        chunk: list[dict[str, Any]] = []
        for candidate in self.stream():
            chunk.append(candidate)
            if len(chunk) >= self.config.chunk_size:
                yield chunk
                chunk = []
        if chunk:
            yield chunk

    def load_all(self) -> list[dict[str, Any]]:
        """Load all candidates into memory as a single list.

        Warning: For large datasets, prefer stream() to avoid memory issues.
        """
        return list(self.stream())

    def _handle_error(self, line_no: int, message: str) -> None:
        """Record a parse error."""
        self._total_errors += 1
        self._error_lines.append(line_no)
        logger.warning("Line %d: %s", line_no, message)

    def _reset_counters(self) -> None:
        """Reset all counters for a fresh iteration."""
        self._total_read = 0
        self._total_valid = 0
        self._total_errors = 0
        self._error_lines = []

    def __repr__(self) -> str:
        return (
            f"DataLoader(file={self.file_path.name}, "
            f"read={self._total_read}, valid={self._total_valid}, "
            f"errors={self._total_errors})"
        )
