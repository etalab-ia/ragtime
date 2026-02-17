"""Albert API document ingestion provider.

Uses Albert's server-side parse API for high-quality document parsing
with OCR support. Supports PDF, Markdown, and HTML files.
Falls back to local pypdf for PDF files when the API returns a server error.
"""

from __future__ import annotations

import logging
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING

from rag_facile.ingestion._base import IngestionProvider


if TYPE_CHECKING:
    from albert import AlbertClient


logger = logging.getLogger(__name__)


class AlbertProvider(IngestionProvider):
    """Albert API document parsing.

    Parses documents via Albert's ``/parse-beta`` endpoint, which provides
    high-quality OCR and markdown conversion for multiple file formats.

    Falls back to local pypdf for PDF files when the API is unavailable.

    Args:
        client: Optional pre-configured Albert client.
            If None, creates one from environment variables.
    """

    def __init__(self, client: AlbertClient | None = None) -> None:
        self._client = client

    @property
    def supported_extensions(self) -> list[str]:
        return [".pdf", ".md", ".html"]

    @property
    def accepted_mime_types(self) -> dict[str, list[str]]:
        return {
            "application/pdf": [".pdf"],
            "text/markdown": [".md"],
            "text/html": [".html", ".htm"],
        }

    @property
    def client(self) -> AlbertClient:
        """Lazily create the Albert client on first use."""
        if self._client is None:
            from albert import AlbertClient

            self._client = AlbertClient()
        return self._client

    def _parse_and_combine(self, file_path: Path, *, force_ocr: bool = False) -> str:
        """Parse a file via Albert API and combine page contents."""
        parsed = self.client.parse(file_path=file_path, force_ocr=force_ocr)

        return "\n".join(page.content for page in parsed.data if page.content)

    def extract_text(self, path: str | Path) -> str:
        """Extract text from a document using Albert's parse API.

        For PDF files, falls back to local pypdf if the API returns
        a server error (5xx).

        Args:
            path: Path to the document file.

        Returns:
            Extracted text content as markdown.

        Raises:
            FileNotFoundError: If the file doesn't exist.
        """
        import httpx

        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        try:
            return self._parse_and_combine(path)
        except httpx.HTTPStatusError as e:
            if e.response.status_code >= 500 and path.suffix.lower() == ".pdf":
                logger.warning(
                    "Albert parse API returned %s for '%s', "
                    "falling back to local pypdf",
                    e.response.status_code,
                    path.name,
                )
                from rag_facile.core.pdf import extract_text_from_pdf

                return extract_text_from_pdf(path)
            raise

    def extract_text_from_bytes(
        self,
        data: bytes,
        *,
        suffix: str = ".pdf",
    ) -> str:
        """Extract text from file bytes using Albert's parse API.

        For PDF bytes, falls back to local pypdf if the API returns
        a server error (5xx).

        Args:
            data: Raw file content.
            suffix: File extension hint (e.g., ``".pdf"``).

        Returns:
            Extracted text content as markdown.
        """
        import httpx

        # Albert parse API requires a file path, so write to a temp file.
        # delete=False for Windows compatibility (prevents read-while-open).
        with NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = Path(tmp.name)
            tmp.write(data)

        try:
            return self._parse_and_combine(tmp_path)
        except httpx.HTTPStatusError as e:
            if e.response.status_code >= 500 and suffix.lower() == ".pdf":
                logger.warning(
                    "Albert parse API returned %s, falling back to local pypdf",
                    e.response.status_code,
                )
                from rag_facile.core.pdf import extract_text_from_bytes as _local

                return _local(data)
            raise
        finally:
            tmp_path.unlink(missing_ok=True)
