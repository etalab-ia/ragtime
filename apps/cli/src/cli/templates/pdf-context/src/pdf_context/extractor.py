"""PDF text extraction module.

Provides functions to extract text content from PDF files using pypdf.
"""

from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError


def extract_text_from_pdf(path: str | Path) -> str:
    """Extract all text content from a PDF file.

    Args:
        path: Path to the PDF file (string or Path object).

    Returns:
        Extracted text content from all pages, with pages separated by newlines.

    Raises:
        FileNotFoundError: If the PDF file doesn't exist.
        PdfReadError: If the PDF is corrupted or password-protected.
        ValueError: If the path doesn't point to a PDF file.
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {path}")

    if not path.suffix.lower() == ".pdf":
        raise ValueError(f"Expected a PDF file, got: {path.suffix}")

    try:
        reader = PdfReader(path)
        text_parts: list[str] = []

        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

        return "\n".join(text_parts)
    except PdfReadError as e:
        raise PdfReadError(f"Failed to read PDF '{path}': {e}") from e


def extract_text_from_bytes(pdf_bytes: bytes) -> str:
    """Extract all text content from PDF bytes.

    Args:
        pdf_bytes: Raw PDF file content as bytes.

    Returns:
        Extracted text content from all pages, with pages separated by newlines.

    Raises:
        PdfReadError: If the PDF is corrupted or password-protected.
    """
    from io import BytesIO

    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        text_parts: list[str] = []

        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

        return "\n".join(text_parts)
    except PdfReadError as e:
        raise PdfReadError(f"Failed to read PDF from bytes: {e}") from e
