"""Unit tests for DataLoader (src/loader/data_loader.py)."""

import json
import tempfile
from pathlib import Path

import pytest

from src.loader.data_loader import DataLoader, DataLoaderConfig


class TestDataLoaderInit:
    """DataLoader initialization and file validation."""

    def test_file_not_found(self):
        """Should raise FileNotFoundError for nonexistent file."""
        with pytest.raises(FileNotFoundError):
            DataLoader(Path("/nonexistent/file.jsonl"))

    def test_default_config(self, jsonl_file):
        """Should use default config when none provided."""
        loader = DataLoader(jsonl_file)
        assert loader.config.chunk_size == 1
        assert loader.config.max_errors == 100
        assert loader.config.encoding == "utf-8"
        assert loader.config.skip_blank_lines is True

    def test_custom_config(self, jsonl_file):
        """Should accept custom config."""
        config = DataLoaderConfig(chunk_size=10, max_errors=5)
        loader = DataLoader(jsonl_file, config=config)
        assert loader.config.chunk_size == 10
        assert loader.config.max_errors == 5


class TestDataLoaderStream:
    """Line-by-line streaming behavior."""

    def test_stream_valid_candidates(self, jsonl_file):
        """Should yield all valid candidates."""
        loader = DataLoader(jsonl_file)
        candidates = list(loader.stream())
        assert len(candidates) == 4  # 3 + 1 (after blank + invalid)
        assert loader.total_valid == 4
        assert loader.total_read == 4

    def test_stream_tracks_errors(self, jsonl_file):
        """Should track parse errors without raising."""
        loader = DataLoader(jsonl_file)
        list(loader.stream())
        assert loader.total_errors == 1  # the "invalid json" line
        assert len(loader.error_lines) == 1

    def test_stream_empty_file(self):
        """Should yield nothing for empty file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
            tmp_path = f.name
        try:
            loader = DataLoader(Path(tmp_path))
            candidates = list(loader.stream())
            assert len(candidates) == 0
            assert loader.total_read == 0
            assert loader.total_valid == 0
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_stream_blank_lines_skipped_by_default(self, jsonl_file):
        """Blank lines should be skipped silently by default."""
        loader = DataLoader(jsonl_file)
        list(loader.stream())
        assert loader.total_errors == 1  # only the malformed json, not the blank line

    def test_stream_empty_json_objects(self):
        """Should handle lines that are valid JSON but not dicts."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
            f.write('{"a": 1}\n')
            f.write('"a string"\n')
            f.write('123\n')
            f.write('{"b": 2}\n')
            tmp_path = f.name
        try:
            loader = DataLoader(Path(tmp_path))
            candidates = list(loader.stream())
            assert len(candidates) == 2  # only the dict objects
            assert loader.total_errors == 2  # string and number are not dicts
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_stream_multiple_valid_candidates(self):
        """Should parse multiple valid candidates."""
        records = [
            {"candidate_id": "CAND_0000001", "name": "Alice"},
            {"candidate_id": "CAND_0000002", "name": "Bob"},
            {"candidate_id": "CAND_0000003", "name": "Charlie"},
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")
            tmp_path = f.name
        try:
            loader = DataLoader(Path(tmp_path))
            candidates = list(loader.stream())
            assert len(candidates) == 3
            assert candidates[0]["candidate_id"] == "CAND_0000001"
            assert candidates[2]["candidate_id"] == "CAND_0000003"
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_stream_error_threshold(self):
        """Should raise RuntimeError when error threshold exceeded."""
        config = DataLoaderConfig(max_errors=2)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
            for _ in range(5):
                f.write("not json\n")
            tmp_path = f.name
        try:
            loader = DataLoader(Path(tmp_path), config=config)
            with pytest.raises(RuntimeError, match="Exceeded max error threshold"):
                list(loader.stream())
        finally:
            Path(tmp_path).unlink(missing_ok=True)


class TestDataLoaderChunks:
    """Chunk-based batch processing."""

    def test_chunk_size_one(self, jsonl_file):
        """Each chunk should contain 1 candidate with chunk_size=1."""
        loader = DataLoader(jsonl_file, DataLoaderConfig(chunk_size=1))
        chunks = list(loader.stream_chunks())
        assert all(len(c) == 1 for c in chunks)
        assert len(chunks) == 4  # 4 valid candidates

    def test_chunk_size_larger_than_dataset(self):
        """Single chunk when chunk_size > total candidates."""
        records = [{"id": i} for i in range(3)]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")
            tmp_path = f.name
        try:
            loader = DataLoader(Path(tmp_path), DataLoaderConfig(chunk_size=100))
            chunks = list(loader.stream_chunks())
            assert len(chunks) == 1
            assert len(chunks[0]) == 3
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_chunk_sizes_even(self):
        """Exact multiples of chunk_size."""
        records = [{"id": i} for i in range(6)]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")
            tmp_path = f.name
        try:
            loader = DataLoader(Path(tmp_path), DataLoaderConfig(chunk_size=2))
            chunks = list(loader.stream_chunks())
            assert len(chunks) == 3
            assert all(len(c) == 2 for c in chunks)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_chunk_sizes_uneven(self):
        """Last chunk smaller when total not multiple of chunk_size."""
        records = [{"id": i} for i in range(5)]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")
            tmp_path = f.name
        try:
            loader = DataLoader(Path(tmp_path), DataLoaderConfig(chunk_size=2))
            chunks = list(loader.stream_chunks())
            assert len(chunks) == 3
            assert len(chunks[0]) == 2
            assert len(chunks[2]) == 1
        finally:
            Path(tmp_path).unlink(missing_ok=True)


class TestDataLoaderLoadAll:
    """Bulk loading."""

    def test_load_all(self, jsonl_file):
        """load_all should return all valid candidates."""
        loader = DataLoader(jsonl_file)
        candidates = loader.load_all()
        assert len(candidates) == 4

    def test_load_all_empty(self):
        """load_all on empty file returns empty list."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
            tmp_path = f.name
        try:
            loader = DataLoader(Path(tmp_path))
            assert loader.load_all() == []
        finally:
            Path(tmp_path).unlink(missing_ok=True)


class TestDataLoaderCounters:
    """Counter and property tracking."""

    def test_counters_reset_on_iteration(self, jsonl_file):
        """Counters should reset when stream() is called again."""
        loader = DataLoader(jsonl_file)
        list(loader.stream())
        assert loader.total_read == 4
        # Call again — counters reset
        list(loader.stream())
        assert loader.total_read == 4  # fresh count after reset

    def test_error_lines_tracked(self, jsonl_file):
        """Error line numbers should be recorded."""
        loader = DataLoader(jsonl_file)
        list(loader.stream())
        assert 5 in loader.error_lines  # the "invalid json" on line 5

    def test_repr(self, jsonl_file):
        """__repr__ should give meaningful description."""
        loader = DataLoader(jsonl_file)
        list(loader.stream())
        rep = repr(loader)
        assert "DataLoader" in rep
        assert jsonl_file.name in rep
