"""Tests for hybrid search and result formatting."""

import pytest

from rag_facile.memory.index import MemoryChunk, MemoryIndex, SearchResult
from rag_facile.memory.search import _fuse_rrf, format_search_results, hybrid_search


@pytest.fixture()
def index(tmp_path):
    idx = MemoryIndex(tmp_path)
    chunks = [
        MemoryChunk(
            content="Le chunking est le processus de découpage des documents en morceaux.",
            source_file="memory.md",
            section="Key Facts",
            line_start=10,
            line_end=12,
        ),
        MemoryChunk(
            content="L'embedding transforme le texte en vecteurs numériques.",
            source_file="memory.md",
            section="Key Facts",
            line_start=13,
            line_end=15,
        ),
        MemoryChunk(
            content="Le preset balanced offre un bon compromis qualité/vitesse.",
            source_file="logs/2026-03-01.md",
            section="Discussion",
            line_start=5,
            line_end=7,
        ),
    ]
    idx.upsert_chunks(chunks, updated_at="2026-03-01")
    yield idx
    idx.close()


class TestHybridSearch:
    def test_keyword_only(self, index):
        results = hybrid_search(index, "chunking")
        assert len(results) > 0
        assert any("chunking" in r.content.lower() for r in results)

    def test_returns_empty_for_no_match(self, index):
        results = hybrid_search(index, "xyznonexistent")
        assert results == []

    def test_respects_limit(self, index):
        results = hybrid_search(index, "le", limit=1)
        assert len(results) <= 1

    def test_with_embeddings(self, index):
        # Store dummy embeddings
        for chunk_hash, emb in [
            ("hash1", [1.0, 0.0, 0.0]),
            ("hash2", [0.0, 1.0, 0.0]),
        ]:
            index.store_embedding(chunk_hash, emb)

        # With query embedding — should run hybrid
        results = hybrid_search(index, "chunking", query_embedding=[1.0, 0.0, 0.0])
        assert isinstance(results, list)


class TestRRFFusion:
    def test_merges_two_lists(self):
        r1 = SearchResult("A", "file.md", "S1", 1, 5, 1.0, "keyword")
        r2 = SearchResult("B", "file.md", "S2", 10, 15, 0.5, "keyword")
        r3 = SearchResult("A", "file.md", "S1", 1, 5, 0.8, "semantic")
        r4 = SearchResult("C", "log.md", "S3", 20, 25, 0.3, "semantic")

        fused = _fuse_rrf([r1, r2], [r3, r4], limit=3)
        # r1/r3 should be ranked higher (appears in both lists)
        assert fused[0].source_file == "file.md"
        assert fused[0].line_start == 1
        assert fused[0].match_type == "both"

    def test_respects_limit(self):
        results = [
            SearchResult(f"R{i}", "f.md", "S", i, i + 1, 1.0, "keyword")
            for i in range(10)
        ]
        fused = _fuse_rrf(results, limit=3)
        assert len(fused) == 3


class TestFormatSearchResults:
    def test_empty_results(self):
        assert format_search_results([]) == "No results found."

    def test_formats_results(self):
        results = [
            SearchResult(
                "Test content here",
                "memory.md",
                "Key Facts",
                10,
                12,
                0.95,
                "keyword",
            ),
        ]
        output = format_search_results(results)
        assert "memory.md:10-12" in output
        assert "Key Facts" in output
        assert "KW" in output
        assert "Test content here" in output

    def test_truncates_long_content(self):
        long_content = "x" * 500
        results = [
            SearchResult(long_content, "f.md", "S", 1, 5, 0.5, "semantic"),
        ]
        output = format_search_results(results)
        assert "…" in output
