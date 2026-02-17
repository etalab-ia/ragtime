"""Local PDF text extraction using pypdf.

Shared utility for all retrieval modules. Provides a reliable local fallback
when server-side parsing (e.g. Albert parse API) is unavailable.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError


def _extract_text(reader: PdfReader) -> str:
    """Extract text from all pages of a PdfReader.

    Args:
        reader: An initialised PdfReader instance.

    Returns:
        Extracted text content from all pages, separated by newlines.
    """
    text_parts: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text_parts.append(page_text)
    return "\n".join(text_parts)


def extract_text_from_pdf(path: str | Path) -> str:
    """Extract all text content from a PDF file.

    Args:
        path: Path to the PDF file.

    Returns:
        Extracted text content from all pages, separated by newlines.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        ValueError: If the file is not a PDF.
        pypdf.errors.PdfReadError: If the PDF is corrupted or password-protected.
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a PDF file, got: {path.suffix}")

    try:
        return _extract_text(PdfReader(path))
    except PdfReadError as e:
        raise PdfReadError(f"Failed to read PDF '{path}': {e}") from e


def extract_text_from_bytes(data: bytes) -> str:
    """Extract all text content from PDF bytes.

    Args:
        data: Raw PDF file content as bytes.

    Returns:
        Extracted text content from all pages, separated by newlines.

    Raises:
        pypdf.errors.PdfReadError: If the PDF is corrupted or password-protected.
    """
    try:
        return _extract_text(PdfReader(BytesIO(data)))
    except PdfReadError as e:
        raise PdfReadError(f"Failed to read PDF from bytes: {e}") from e
