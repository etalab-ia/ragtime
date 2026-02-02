"""Context formatting module.

Provides functions to format extracted text for LLM context injection.
"""

from pathlib import Path

from .extractor import extract_text_from_pdf


def format_as_context(text: str, filename: str) -> str:
    """Format extracted text with delimiters for context injection.

    Wraps the text with clear delimiters indicating the source file,
    making it easy for LLMs to understand the context boundaries.

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


def process_pdf_file(path: str | Path, filename: str | None = None) -> str:
    """Extract text from a PDF and format it for context injection.

    Convenience function that combines extraction and formatting.

    Args:
        path: Path to the PDF file.
        filename: Optional display name for the file.
                  If not provided, uses the file's basename.

    Returns:
        Formatted text ready for context injection.

    Raises:
        FileNotFoundError: If the PDF file doesn't exist.
        PdfReadError: If the PDF is corrupted or password-protected.
    """
    path = Path(path)
    display_name = filename if filename else path.name

    text = extract_text_from_pdf(path)
    return format_as_context(text, display_name)


def process_multiple_files(paths: list[str | Path]) -> str:
    """Process multiple PDF files and combine their context.

    Args:
        paths: List of paths to PDF files.

    Returns:
        Combined formatted text from all files.

    Raises:
        FileNotFoundError: If any PDF file doesn't exist.
        PdfReadError: If any PDF is corrupted or password-protected.
    """
    results: list[str] = []

    for path in paths:
        try:
            formatted = process_pdf_file(path)
            results.append(formatted)
        except Exception as e:
            # Include error message in context so LLM knows about the failure
            path_obj = Path(path)
            results.append(f"\n\nError reading PDF '{path_obj.name}': {e!s}\n")

    return "".join(results)
