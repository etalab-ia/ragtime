"""Document parsing via Albert's parse API.

Provides the same interface as retrieval-basic (process_pdf_file,
format_as_context, extract_text_from_bytes) so the two packages
are interchangeable in context_loader.py / modules.yml.

The key difference: retrieval-basic uses local pypdf extraction,
while this module uses Albert's server-side parse API which provides
better quality OCR and markdown conversion.
"""

from __future__ import annotations

import logging
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from albert import AlbertClient


logger = logging.getLogger(__name__)


def _get_client() -> AlbertClient:
    """Create an AlbertClient from environment variables."""
    from albert import AlbertClient

    return AlbertClient()


def extract_text_from_pdf(
    path: str | Path,
    *,
    client: AlbertClient | None = None,
    force_ocr: bool = False,
) -> str:
    """Extract text from a PDF file using Albert's parse API.

    Args:
        path: Path to the PDF file.
        client: Optional pre-configured Albert client.
        force_ocr: Force OCR on all pages (default: False).

    Returns:
        Extracted text content as markdown from all pages.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        ValueError: If the file is not a PDF.
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a PDF file, got: {path.suffix}")

    client = client or _get_client()
    parsed = client.parse(file_path=path, force_ocr=force_ocr)

    # Combine all page contents
    text_parts: list[str] = []
    for page in parsed.data:
        if page.content:
            text_parts.append(page.content)

    return "\n".join(text_parts)


def extract_text_from_bytes(
    pdf_bytes: bytes,
    *,
    client: AlbertClient | None = None,
    force_ocr: bool = False,
) -> str:
    """Extract text from PDF bytes using Albert's parse API.

    Args:
        pdf_bytes: Raw PDF file content as bytes.
        client: Optional pre-configured Albert client.
        force_ocr: Force OCR on all pages.

    Returns:
        Extracted text content as markdown.
    """
    client = client or _get_client()

    # Write bytes to a temp file (Albert parse API requires a file path)
    with NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
        tmp.write(pdf_bytes)
        tmp.flush()
        parsed = client.parse(file_path=tmp.name, force_ocr=force_ocr)

    text_parts: list[str] = []
    for page in parsed.data:
        if page.content:
            text_parts.append(page.content)

    return "\n".join(text_parts)


def format_as_context(text: str, filename: str) -> str:
    """Format extracted text with delimiters for context injection.

    Same format as retrieval-basic for interchangeability.

    Args:
        text: The extracted text content.
        filename: The name of the source file (for labeling).

    Returns:
        Formatted text with file delimiters.
    """
    return (
        f"\n\n--- Content of attached file '{filename}' ---\n"
        f"{text}\n"
        f"--- End of file ---\n"
    )


def process_pdf_file(
    path: str | Path,
    filename: str | None = None,
    *,
    client: AlbertClient | None = None,
) -> str:
    """Extract text from a PDF and format it for context injection.

    Drop-in replacement for retrieval_basic.process_pdf_file().

    Args:
        path: Path to the PDF file.
        filename: Optional display name for the file.
        client: Optional pre-configured Albert client.

    Returns:
        Formatted text ready for context injection.
    """
    path = Path(path)
    display_name = filename if filename else path.name

    text = extract_text_from_pdf(path, client=client)
    return format_as_context(text, display_name)


def process_multiple_files(
    paths: list[str | Path],
    *,
    client: AlbertClient | None = None,
) -> str:
    """Process multiple PDF files and combine their context.

    Args:
        paths: List of paths to PDF files.
        client: Optional pre-configured Albert client.

    Returns:
        Combined formatted text from all files.
    """
    client = client or _get_client()
    results: list[str] = []

    for path in paths:
        try:
            formatted = process_pdf_file(path, client=client)
            results.append(formatted)
        except Exception as e:
            path_obj = Path(path)
            results.append(f"\n\nError reading PDF '{path_obj.name}': {e!s}\n")

    return "".join(results)
