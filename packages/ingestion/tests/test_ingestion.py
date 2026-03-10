"""Tests for the ingestion package."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from rag_facile.ingestion import IngestionProvider, get_provider
from rag_facile.ingestion._base import IngestionProvider as BaseClass
from rag_facile.ingestion.local import LocalProvider


# ---------------------------------------------------------------------------
# ABC contract
# ---------------------------------------------------------------------------


def test_ingestion_provider_is_abstract():
    """IngestionProvider cannot be instantiated directly."""
    with pytest.raises(TypeError):
        IngestionProvider()


def test_local_provider_implements_interface():
    """LocalProvider satisfies the IngestionProvider interface."""
    provider = LocalProvider()
    assert isinstance(provider, BaseClass)


# ---------------------------------------------------------------------------
# LocalProvider
# ---------------------------------------------------------------------------


class TestLocalProvider:
    """Tests for LocalProvider (pypdf backend)."""

    def test_supported_extensions(self):
        provider = LocalProvider()
        assert provider.supported_extensions == [".pdf"]

    def test_accepted_mime_types(self):
        provider = LocalProvider()
        assert "application/pdf" in provider.accepted_mime_types

    def test_extract_text_file_not_found(self):
        provider = LocalProvider()
        with pytest.raises(FileNotFoundError):
            provider.extract_text("/nonexistent/file.pdf")

    def test_extract_text_not_pdf(self, tmp_path: Path):
        provider = LocalProvider()
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("hello")
        with pytest.raises(ValueError, match="Expected a PDF"):
            provider.extract_text(txt_file)

    def test_format_as_context(self):
        provider = LocalProvider()
        result = provider.format_as_context("some text", "doc.pdf")
        assert "doc.pdf" in result
        assert "some text" in result
        assert "--- Content of attached file" in result
        assert "--- End of file ---" in result

    def test_process_file_formats_output(self, tmp_path: Path, monkeypatch):
        """process_file calls extract_text and wraps with delimiters."""
        provider = LocalProvider()
        monkeypatch.setattr(provider, "extract_text", lambda _path: "extracted content")
        result = provider.process_file(tmp_path / "report.pdf")
        assert "report.pdf" in result
        assert "extracted content" in result

    def test_process_bytes_formats_output(self, monkeypatch):
        """process_bytes calls extract_text_from_bytes and wraps with delimiters."""
        provider = LocalProvider()
        monkeypatch.setattr(
            provider,
            "extract_text_from_bytes",
            lambda _data, suffix=".pdf": "bytes content",
        )
        result = provider.process_bytes(b"fake-pdf", "upload.pdf")
        assert "upload.pdf" in result
        assert "bytes content" in result


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


class TestGetProvider:
    """Tests for the get_provider factory function."""

    def test_local_provider(self):
        config = MagicMock()
        config.ingestion.provider = "local"
        provider = get_provider(config)
        assert isinstance(provider, LocalProvider)

    def test_albert_provider_removed(self):
        """AlbertProvider was removed in 0.4.1 — should raise a clear error."""
        config = MagicMock()
        config.ingestion.provider = "albert"
        with pytest.raises(ValueError, match="albert.*provider has been removed"):
            get_provider(config)

    def test_unknown_provider_raises(self):
        config = MagicMock()
        config.ingestion.provider = "unknown"
        with pytest.raises(ValueError, match="Unknown ingestion provider"):
            get_provider(config)
