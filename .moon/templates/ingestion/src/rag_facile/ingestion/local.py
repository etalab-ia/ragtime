"""Local document ingestion provider using pypdf.

Extracts text from PDF files locally without any external API calls.
Suitable for offline use or when server-side parsing is unavailable.
"""

from __future__ import annotations

from pathlib import Path

from rag_facile.core.pdf import extract_text_from_bytes as _pdf_from_bytes
from rag_facile.core.pdf import extract_text_from_pdf as _pdf_from_path

from rag_facile.ingestion._base import IngestionProvider


class LocalProvider(IngestionProvider):
    """Local PDF parsing using pypdf.

    Only supports PDF files. For multi-format parsing (HTML, Markdown, JSON),
    use the Albert provider instead.
    """

    @property
    def supported_extensions(self) -> list[str]:
        return [".pdf"]

    @property
    def accepted_mime_types(self) -> dict[str, list[str]]:
        return {"application/pdf": [".pdf"]}

    def extract_text(self, path: str | Path) -> str:
        """Extract text from a PDF file using pypdf.

        Args:
            path: Path to the PDF file.

        Returns:
            Extracted text content.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            ValueError: If the file is not a PDF.
            pypdf.errors.PdfReadError: If the PDF is corrupted.
        """
        return _pdf_from_path(path)

    def extract_text_from_bytes(
        self,
        data: bytes,
        *,
        suffix: str = ".pdf",
    ) -> str:
        """Extract text from PDF bytes using pypdf.

        Args:
            data: Raw PDF file content.
            suffix: File extension hint (only ``".pdf"`` supported).

        Returns:
            Extracted text content.

        Raises:
            pypdf.errors.PdfReadError: If the PDF is corrupted.
        """
        return _pdf_from_bytes(data)
