"""Tests for the incremental markdown indexer."""

import pytest

from rag_facile.memory.index import MemoryIndex
from rag_facile.memory.indexer import chunk_markdown, rebuild_index
from rag_facile.memory.stores import SemanticStore


@pytest.fixture()
def index(tmp_path):
    idx = MemoryIndex(tmp_path)
    yield idx
    idx.close()


class TestChunkMarkdown:
    def test_splits_at_h2_headers(self):
        content = "# Title\n\n## Section A\nContent A\n\n## Section B\nContent B"
        chunks = chunk_markdown(content, source_file="test.md")
        assert len(chunks) == 2
        assert chunks[0].section == "Section A"
        assert chunks[1].section == "Section B"

    def test_skips_short_chunks(self):
        content = (
            "## Empty\n\n## Short\nHi\n\n## Real\nEnough content here for a chunk."
        )
        chunks = chunk_markdown(content, source_file="test.md")
        # "Empty" and "Short" have < 10 chars of content
        assert all(len(c.content) >= 10 for c in chunks)

    def test_preserves_line_numbers(self):
        content = "# Header\n\n## First\nLine 1\nLine 2\n\n## Second\nLine 3"
        chunks = chunk_markdown(content, source_file="test.md")
        assert chunks[0].line_start == 3  # 1-indexed
        assert chunks[1].line_start >= chunks[0].line_end

    def test_handles_no_headers(self):
        content = "Just plain text without any headers at all."
        chunks = chunk_markdown(content, source_file="test.md")
        assert len(chunks) == 1
        assert chunks[0].section == ""

    def test_handles_empty_content(self):
        assert chunk_markdown("", source_file="test.md") == []

    def test_source_file_preserved(self):
        content = "## Section\nSome content here."
        chunks = chunk_markdown(content, source_file="logs/2026-03-01.md")
        assert all(c.source_file == "logs/2026-03-01.md" for c in chunks)


class TestRebuildIndex:
    def test_indexes_memory_file(self, tmp_path, index):
        SemanticStore.create(tmp_path)
        count = rebuild_index(tmp_path, index)
        assert count == 1
        assert index.chunk_count() > 0

    def test_skips_unchanged_files(self, tmp_path, index):
        SemanticStore.create(tmp_path)
        rebuild_index(tmp_path, index)
        # Second run — no changes
        count = rebuild_index(tmp_path, index)
        assert count == 0

    def test_re_indexes_on_change(self, tmp_path, index):
        SemanticStore.create(tmp_path)
        rebuild_index(tmp_path, index)

        # Modify the file
        SemanticStore.add_entry(tmp_path, "Key Facts", "New fact added")
        count = rebuild_index(tmp_path, index)
        assert count == 1

    def test_returns_zero_when_no_agent_dir(self, tmp_path, index):
        assert rebuild_index(tmp_path, index) == 0

    def test_calls_embed_fn_when_provided(self, tmp_path, index):
        SemanticStore.create(tmp_path)
        calls = []

        def mock_embed(texts):
            calls.append(texts)
            return [[0.1, 0.2] for _ in texts]

        rebuild_index(tmp_path, index, embed_fn=mock_embed)
        assert len(calls) > 0
        assert index.get_all_embeddings()
