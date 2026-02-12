"""Document preprocessor for converting PDFs to text for upload.

Converts large PDF files to smaller text/markdown files to avoid
upload timeouts and improve compatibility with providers that handle
text better than binary files.
"""

import tempfile
from pathlib import Path
from typing import Optional


try:
    from retrieval_basic import extract_text_from_pdf
except ImportError:
    try:
        # Fallback for development/editable install
        from cli.retrieval_basic_src import extract_text_from_pdf
    except ImportError as e:
        raise ImportError(
            "retrieval_basic module is required for PDF extraction. "
            "Ensure the retrieval-basic package is installed."
        ) from e


class DocumentPreprocessor:
    """Preprocessor that converts PDFs to markdown for efficient upload."""

    def __init__(self, temp_dir: Optional[str] = None):
        """Initialize the document preprocessor.

        Args:
            temp_dir: Optional temporary directory for extracted files.
                      If None, uses system temp directory.
        """
        self.temp_dir = temp_dir
        self.processed_files: list[Path] = []

    def process_documents(self, document_paths: list[str]) -> list[str]:
        """Process documents, converting PDFs to markdown text.

        Args:
            document_paths: List of paths to documents (PDF, MD, TXT)

        Returns:
            List of paths to processed documents (originals or extracted text files)
        """
        processed: list[str] = []

        for doc_path in document_paths:
            path = Path(doc_path)

            if path.suffix.lower() == ".pdf":
                # Extract PDF to markdown
                extracted_path = self._extract_pdf(path)
                processed.append(str(extracted_path))
            else:
                # Keep non-PDF files as-is
                processed.append(str(path))

        return processed

    def _extract_pdf(self, pdf_path: Path) -> Path:
        """Extract text from PDF and save as markdown.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Path to the extracted markdown file

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            RuntimeError: If PDF extraction fails
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        try:
            # Extract text from PDF
            text = extract_text_from_pdf(pdf_path)

            # Create temp file for extracted text
            temp_dir = Path(self.temp_dir) if self.temp_dir else None
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".md",
                dir=temp_dir,
                delete=False,
                encoding="utf-8",
            ) as tmp:
                # Write extracted text with metadata header
                tmp.write(f"# {pdf_path.stem}\n\n")
                tmp.write(f"*Extracted from: {pdf_path.name}*\n\n")
                tmp.write(text)
                tmp_path = Path(tmp.name)

            self.processed_files.append(tmp_path)
            return tmp_path

        except Exception as e:
            raise RuntimeError(
                f"Failed to extract text from PDF '{pdf_path}': {e}"
            ) from e

    def cleanup(self) -> None:
        """Clean up temporary files created during processing."""
        for tmp_file in self.processed_files:
            try:
                if tmp_file.exists():
                    tmp_file.unlink()
            except Exception:
                pass  # Non-critical, ignore cleanup errors
