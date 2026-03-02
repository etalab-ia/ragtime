"""Tests for the optional Albert-backed semantic search.

All Albert API calls are mocked — no network access required.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rag_facile.memory.albert_search import (
    AlbertMemoryIndex,
    fuse_search_results,
)
from rag_facile.memory.search import SearchResult


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    """Create a workspace with sample .agent/ files."""
    agent = tmp_path / ".agent"
    agent.mkdir()
    (agent / "MEMORY.md").write_text(
        "## Key Facts\n- Albert API rate limit is 10 req/min\n",
        encoding="utf-8",
    )
    logs = agent / "logs"
    logs.mkdir()
    (logs / "2026-03-01.md").write_text(
        "## 14:30\nDiscussed deployment config\n",
        encoding="utf-8",
    )
    return tmp_path


def _make_mock_client(collection_id: int = 42):
    """Create a mock AlbertClient with create_collection, upload_document, search."""
    mock_client = MagicMock()

    # create_collection
    mock_collection = MagicMock()
    mock_collection.id = collection_id
    mock_client.create_collection.return_value = mock_collection

    # upload_document
    mock_client.upload_document.return_value = MagicMock()

    return mock_client


def _make_mock_search_response(hits: list[dict]):
    """Create a mock SearchResponse with given hits."""
    response = MagicMock()
    data = []
    for h in hits:
        hit = MagicMock()
        hit.score = h["score"]
        hit.chunk = MagicMock()
        hit.chunk.content = h["content"]
        hit.chunk.metadata = h.get("metadata", {})
        data.append(hit)
    response.data = data
    return response


# ── AlbertMemoryIndex tests ───────────────────────────────────────────────────


class TestSync:
    @patch("albert.AlbertClient")
    def test_creates_collection_on_first_sync(self, mock_cls, workspace: Path) -> None:
        mock_client = _make_mock_client(collection_id=99)
        mock_cls.return_value = mock_client

        index = AlbertMemoryIndex(api_key="test-key", api_base="https://api.test")
        index.sync(workspace)

        mock_client.create_collection.assert_called_once()
        assert index._collection_id == 99

    @patch("albert.AlbertClient")
    def test_uploads_md_files(self, mock_cls, workspace: Path) -> None:
        mock_client = _make_mock_client()
        mock_cls.return_value = mock_client

        index = AlbertMemoryIndex(api_key="test-key", api_base="https://api.test")
        index.sync(workspace)

        # Should upload MEMORY.md and logs/2026-03-01.md
        assert mock_client.upload_document.call_count == 2

    @patch("albert.AlbertClient")
    def test_incremental_sync(self, mock_cls, workspace: Path) -> None:
        """Second sync with no changes should skip uploads."""
        mock_client = _make_mock_client()
        mock_cls.return_value = mock_client

        index = AlbertMemoryIndex(api_key="test-key", api_base="https://api.test")
        index.sync(workspace)

        # Reset mock and sync again — no changes
        mock_client.upload_document.reset_mock()
        index._synced = False  # force re-sync
        index.sync(workspace)

        assert mock_client.upload_document.call_count == 0

    @patch("albert.AlbertClient")
    def test_resyncs_changed_files(self, mock_cls, workspace: Path) -> None:
        """Files modified after first sync should be re-uploaded."""
        mock_client = _make_mock_client()
        mock_cls.return_value = mock_client

        index = AlbertMemoryIndex(api_key="test-key", api_base="https://api.test")
        index.sync(workspace)

        # Modify MEMORY.md
        memory = workspace / ".agent" / "MEMORY.md"
        memory.write_text("## Updated\n- New fact\n", encoding="utf-8")

        # Force re-sync
        mock_client.upload_document.reset_mock()
        index._synced = False
        index.sync(workspace)

        # Only the changed file should be uploaded
        assert mock_client.upload_document.call_count == 1

    @patch("albert.AlbertClient")
    def test_saves_state_file(self, mock_cls, workspace: Path) -> None:
        mock_client = _make_mock_client(collection_id=42)
        mock_cls.return_value = mock_client

        index = AlbertMemoryIndex(api_key="test-key", api_base="https://api.test")
        index.sync(workspace)

        state_file = workspace / ".agent" / ".search-state.json"
        assert state_file.exists()
        state = json.loads(state_file.read_text())
        assert state["collection_id"] == 42
        assert "files" in state

    def test_missing_albert_package(self, workspace: Path) -> None:
        """Should gracefully skip when albert isn't installed."""
        index = AlbertMemoryIndex(api_key="test-key", api_base="https://api.test")
        with patch.dict("sys.modules", {"albert": None}):
            # This should not raise
            index.sync(workspace)
        assert not index._synced

    def test_no_agent_dir(self, tmp_path: Path) -> None:
        """Should do nothing if .agent/ doesn't exist."""
        index = AlbertMemoryIndex(api_key="test-key", api_base="https://api.test")
        index.sync(tmp_path)
        assert not index._synced


class TestSearch:
    @patch("albert.AlbertClient")
    def test_returns_results(self, mock_cls, workspace: Path) -> None:
        mock_client = _make_mock_client()
        mock_cls.return_value = mock_client

        # Set up search response
        mock_client.search.return_value = _make_mock_search_response(
            [
                {
                    "score": 0.95,
                    "content": "Albert API rate limit is 10 req/min",
                    "metadata": {"source": "MEMORY.md"},
                },
                {
                    "score": 0.82,
                    "content": "Discussed deployment config\nWith production settings",
                    "metadata": {"source": "logs/2026-03-01.md"},
                },
            ]
        )

        index = AlbertMemoryIndex(api_key="test-key", api_base="https://api.test")
        # Pre-set collection to avoid sync
        index._collection_id = 42
        index._synced = True

        results = index.search("Albert API", workspace)
        assert len(results) == 2
        assert results[0]["score"] == 0.95
        assert results[0]["file"] == "MEMORY.md"

    @patch("albert.AlbertClient")
    def test_no_collection_returns_empty(self, mock_cls, workspace: Path) -> None:
        index = AlbertMemoryIndex(api_key="test-key", api_base="https://api.test")
        index._synced = True  # skip sync
        index._collection_id = None

        results = index.search("anything", workspace)
        assert results == []

    @patch("albert.AlbertClient")
    def test_api_error_returns_empty(self, mock_cls, workspace: Path) -> None:
        mock_client = _make_mock_client()
        mock_cls.return_value = mock_client
        mock_client.search.side_effect = RuntimeError("API error")

        index = AlbertMemoryIndex(api_key="test-key", api_base="https://api.test")
        index._collection_id = 42
        index._synced = True

        results = index.search("anything", workspace)
        assert results == []


# ── RRF fusion tests ──────────────────────────────────────────────────────────


class TestFuseSearchResults:
    def test_fuses_two_lists(self) -> None:
        kw = [
            SearchResult(
                file="MEMORY.md", line_start=1, line_end=2, snippet="fact A", score=1.0
            ),
            SearchResult(
                file="logs/a.md", line_start=5, line_end=7, snippet="fact B", score=0.5
            ),
        ]
        sem = [
            SearchResult(
                file="logs/a.md", line_start=5, line_end=7, snippet="fact B", score=0.9
            ),
            SearchResult(
                file="sessions/s.md",
                line_start=1,
                line_end=3,
                snippet="fact C",
                score=0.8,
            ),
        ]
        fused = fuse_search_results(kw, sem, limit=10)
        # logs/a.md should get double RRF boost (appears in both lists)
        files = [r["file"] for r in fused]
        assert "logs/a.md" in files
        assert len(fused) == 3

    def test_dedup_by_file_and_line(self) -> None:
        kw = [
            SearchResult(
                file="MEMORY.md", line_start=1, line_end=2, snippet="same", score=1.0
            ),
        ]
        sem = [
            SearchResult(
                file="MEMORY.md", line_start=1, line_end=2, snippet="same", score=0.9
            ),
        ]
        fused = fuse_search_results(kw, sem)
        # Should be deduped to one result
        assert len(fused) == 1

    def test_limit_respected(self) -> None:
        kw = [
            SearchResult(
                file=f"file{i}.md",
                line_start=1,
                line_end=1,
                snippet=f"fact {i}",
                score=1.0,
            )
            for i in range(10)
        ]
        fused = fuse_search_results(kw, [], limit=3)
        assert len(fused) == 3

    def test_empty_inputs(self) -> None:
        assert fuse_search_results([], []) == []
