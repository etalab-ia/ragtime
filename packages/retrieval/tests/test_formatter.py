"""Tests for formatter functions."""

from retrieval.formatter import format_context
from retrieval._types import RetrievedChunk


def _make_chunk(
    content: str,
    score: float = 0.9,
    source_file: str | None = "doc.pdf",
    page: int | None = 1,
) -> RetrievedChunk:
    """Helper to create a RetrievedChunk for testing."""
    return RetrievedChunk(
        content=content,
        score=score,
        source_file=source_file,
        page=page,
        collection_id=1,
        document_id=1,
        chunk_id=1,
    )


class TestFormatContext:
    """Tests for format_context function."""

    def test_formats_with_inline_citations(self, mock_config):
        """Should format chunks with numbered inline citations."""
        chunks = [
            _make_chunk("Premier passage.", source_file="rapport.pdf", page=5),
            _make_chunk("Deuxieme passage.", source_file="guide.pdf", page=12),
        ]

        result = format_context(chunks)

        assert "[1] Premier passage. (source: rapport.pdf, p.5)" in result
        assert "[2] Deuxieme passage. (source: guide.pdf, p.12)" in result
        assert "--- Retrieved context ---" in result
        assert "--- End of context ---" in result

    def test_formats_with_footnote_citations(self, mock_config):
        """Should format chunks with footnote-style citations."""
        chunks = [
            _make_chunk("Un passage."),
        ]

        result = format_context(chunks, citation_style="footnote")

        assert "Un passage. [1]" in result

    def test_formats_without_citations(self, mock_config):
        """Should format chunks without citations when disabled."""
        chunks = [
            _make_chunk("Contenu brut."),
        ]

        result = format_context(chunks, include_citations=False)

        assert "Contenu brut." in result
        assert "[1]" not in result

    def test_empty_chunks(self, mock_config):
        """Should return empty string for empty input."""
        result = format_context([])

        assert result == ""

    def test_handles_missing_source_file(self, mock_config):
        """Should handle chunks without source_file."""
        chunks = [
            _make_chunk("Passage sans source.", source_file=None, page=None),
        ]

        result = format_context(chunks)

        assert "[1] Passage sans source." in result
        # Should not include empty parentheses
        assert "()" not in result

    def test_handles_source_without_page(self, mock_config):
        """Should handle chunks with source but no page number."""
        chunks = [
            _make_chunk("Un passage.", source_file="doc.pdf", page=None),
        ]

        result = format_context(chunks)

        assert "(source: doc.pdf)" in result
        assert "p." not in result

    def test_strips_whitespace_from_content(self, mock_config):
        """Should strip leading/trailing whitespace from chunk content."""
        chunks = [
            _make_chunk("  Passage avec espaces.  "),
        ]

        result = format_context(chunks)

        assert "[1] Passage avec espaces." in result

    def test_multiple_chunks_have_separators(self, mock_config):
        """Should separate multiple chunks with blank lines."""
        chunks = [
            _make_chunk("Premier."),
            _make_chunk("Deuxieme."),
            _make_chunk("Troisieme."),
        ]

        result = format_context(chunks)

        # All three should be present
        assert "[1]" in result
        assert "[2]" in result
        assert "[3]" in result
