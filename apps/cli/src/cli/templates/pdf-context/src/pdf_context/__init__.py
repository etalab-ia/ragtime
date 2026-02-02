"""PDF Context - PDF text extraction and context formatting for LLM applications.

This package provides utilities for extracting text from PDF files and
formatting it for injection into LLM prompts (context-injection approach).

Example usage:
    from pdf_context import extract_text_from_pdf, format_as_context, process_pdf_file

    # Extract raw text
    text = extract_text_from_pdf("document.pdf")

    # Format for context injection
    context = format_as_context(text, "document.pdf")

    # Or use the convenience function
    context = process_pdf_file("document.pdf")
"""

from .extractor import extract_text_from_bytes, extract_text_from_pdf
from .formatter import format_as_context, process_multiple_files, process_pdf_file

__all__ = [
    "extract_text_from_pdf",
    "extract_text_from_bytes",
    "format_as_context",
    "process_pdf_file",
    "process_multiple_files",
]

__version__ = "0.1.0"
