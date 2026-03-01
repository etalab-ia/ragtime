"""Tests for conflict detection and deduplication."""

from rag_facile.memory.consolidation import (
    consolidate_entry,
    find_conflicting_entry,
)


class TestFindConflictingEntry:
    def test_detects_overlapping_entries(self):
        existing = [
            "- [2026-03-01] Preset configuration uses balanced mode",
            "- [2026-03-01] Language preference is French",
        ]
        idx = find_conflicting_entry(
            existing, "Preset configuration uses accurate mode"
        )
        assert idx == 0  # shares "preset", "configuration", "uses", "mode"

    def test_returns_none_for_unrelated(self):
        existing = [
            "- [2026-03-01] Uses Albert API for embeddings",
        ]
        idx = find_conflicting_entry(existing, "Chunking set to 1024")
        assert idx is None

    def test_returns_none_for_short_entry(self):
        existing = ["- [2026-03-01] Test"]
        idx = find_conflicting_entry(existing, "Hi")
        assert idx is None

    def test_handles_empty_list(self):
        assert find_conflicting_entry([], "New fact") is None


class TestConsolidateEntry:
    def test_replaces_conflicting(self):
        existing = [
            "- [2026-03-01] Preset configuration uses balanced mode",
            "- [2026-03-01] Language preference is French",
        ]
        result = consolidate_entry(existing, "Preset configuration uses accurate mode")
        assert len(result) == 2
        assert "accurate" in result[0]
        assert "French" in result[1]

    def test_appends_when_no_conflict(self):
        existing = [
            "- [2026-03-01] Language: French",
        ]
        result = consolidate_entry(existing, "New topic entirely different")
        assert len(result) == 2

    def test_preserves_order(self):
        existing = [
            "- Item A is about chunking strategy",
            "- Item B is about embedding model",
            "- Item C is about retrieval top_k",
        ]
        result = consolidate_entry(existing, "Embedding model updated to v2")
        assert len(result) == 3  # replaced, not appended
        assert "v2" in result[1]  # replaced item B
