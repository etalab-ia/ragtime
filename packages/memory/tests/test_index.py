"""Tests for the SQLite FTS5 index."""

import pytest

from rag_facile.memory.index import MemoryChunk, MemoryIndex, _cosine_similarity


@pytest.fixture()
def index(tmp_path):
    """Create a MemoryIndex backed by a temp workspace."""
    idx = MemoryIndex(tmp_path)
    yield idx
    idx.close()


@pytest.fixture()
def sample_chunks():
    return [
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
            section="21:30 — User",
            line_start=5,
            line_end=7,
        ),
    ]


class TestMemoryIndexUpsert:
    def test_insert_chunks(self, index, sample_chunks):
        index.upsert_chunks(sample_chunks, updated_at="2026-03-01")
        assert index.chunk_count() == 3

    def test_upsert_replaces_existing(self, index, sample_chunks):
        index.upsert_chunks(sample_chunks, updated_at="2026-03-01")
        index.upsert_chunks(sample_chunks[:1], updated_at="2026-03-02")
        assert index.chunk_count() == 3  # replaced, not duplicated


class TestMemoryIndexRemoveFile:
    def test_removes_chunks_for_file(self, index, sample_chunks):
        index.upsert_chunks(sample_chunks, updated_at="2026-03-01")
        index.remove_file("memory.md")
        assert index.chunk_count() == 1  # only the log chunk remains

    def test_no_op_on_unknown_file(self, index):
        index.remove_file("nonexistent.md")  # should not raise


class TestMemoryIndexFileState:
    def test_update_and_get(self, index):
        index.update_file_state("memory.md", 1234.0, "abc123")
        result = index.get_file_state("memory.md")
        assert result == (1234.0, "abc123")

    def test_returns_none_for_unknown(self, index):
        assert index.get_file_state("unknown.md") is None

    def test_update_replaces(self, index):
        index.update_file_state("memory.md", 1234.0, "abc123")
        index.update_file_state("memory.md", 5678.0, "def456")
        result = index.get_file_state("memory.md")
        assert result == (5678.0, "def456")


class TestKeywordSearch:
    def test_finds_matching_content(self, index, sample_chunks):
        index.upsert_chunks(sample_chunks, updated_at="2026-03-01")
        results = index.search_keyword("chunking")
        assert len(results) > 0
        assert any("chunking" in r.content.lower() for r in results)

    def test_returns_empty_for_no_match(self, index, sample_chunks):
        index.upsert_chunks(sample_chunks, updated_at="2026-03-01")
        results = index.search_keyword("xyznonexistent")
        assert results == []

    def test_results_have_metadata(self, index, sample_chunks):
        index.upsert_chunks(sample_chunks, updated_at="2026-03-01")
        results = index.search_keyword("embedding")
        assert len(results) > 0
        r = results[0]
        assert r.source_file == "memory.md"
        assert r.match_type == "keyword"
        assert r.line_start > 0

    def test_respects_limit(self, index, sample_chunks):
        index.upsert_chunks(sample_chunks, updated_at="2026-03-01")
        results = index.search_keyword("le", limit=1)
        assert len(results) <= 1


class TestEmbeddings:
    def test_store_and_retrieve(self, index):
        embedding = [0.1, 0.2, 0.3, 0.4]
        index.store_embedding("hash123", embedding)
        result = index.get_all_embeddings()
        assert len(result) == 1
        assert result[0][0] == "hash123"
        # Float comparison with tolerance
        assert all(abs(a - b) < 1e-6 for a, b in zip(result[0][1], embedding))

    def test_semantic_search(self, index, sample_chunks):
        index.upsert_chunks(sample_chunks, updated_at="2026-03-01")
        # Store embeddings for all chunks
        for chunk in sample_chunks:
            # Simple dummy embeddings that differ by chunk
            emb = [float(i) for i in range(4)]
            index.store_embedding(chunk.hash, emb)

        # Query with same embedding → should return all
        results = index.search_semantic([0.0, 1.0, 2.0, 3.0], limit=3)
        assert len(results) == 3
        assert all(r.match_type == "semantic" for r in results)


class TestCosineSimilarity:
    def test_identical_vectors(self):
        assert abs(_cosine_similarity([1, 0, 0], [1, 0, 0]) - 1.0) < 1e-6

    def test_orthogonal_vectors(self):
        assert abs(_cosine_similarity([1, 0], [0, 1])) < 1e-6

    def test_zero_vector(self):
        assert _cosine_similarity([0, 0], [1, 1]) == 0.0

    def test_different_lengths(self):
        assert _cosine_similarity([1, 2], [1, 2, 3]) == 0.0
