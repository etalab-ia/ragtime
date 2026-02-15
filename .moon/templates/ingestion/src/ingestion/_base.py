"""Base interface for document ingestion providers.

Defines the :class:`IngestionProvider` ABC that all backends must implement.
Shared logic (context formatting, file/bytes processing) lives here so
concrete providers only need to implement text extraction.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class IngestionProvider(ABC):
    """Abstract base class for document ingestion providers.

    Subclasses must implement:
      - :attr:`supported_extensions` — file extensions this provider handles
      - :attr:`accepted_mime_types` — MIME type map for file picker dialogs
      - :meth:`extract_text` — extract text from a file path
      - :meth:`extract_text_from_bytes` — extract text from raw bytes

    Shared methods provided by this base class:
      - :meth:`format_as_context` — wrap text with source delimiters
      - :meth:`process_file` — extract + format in one call
      - :meth:`process_bytes` — extract from bytes + format in one call
    """

    @property
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """File extensions this provider can parse (e.g., ``[".pdf"]``)."""

    @property
    @abstractmethod
    def accepted_mime_types(self) -> dict[str, list[str]]:
        """MIME types for file picker dialogs.

        Returns:
            Dict mapping MIME types to extensions, e.g.
            ``{"application/pdf": [".pdf"]}``.
        """

    @abstractmethod
    def extract_text(self, path: str | Path) -> str:
        """Extract text content from a document file.

        Args:
            path: Path to the document.

        Returns:
            Extracted text content.

        Raises:
            FileNotFoundError: If the file doesn't exist.
        """

    @abstractmethod
    def extract_text_from_bytes(
        self,
        data: bytes,
        *,
        suffix: str = ".pdf",
    ) -> str:
        """Extract text content from raw file bytes.

        Args:
            data: Raw file content.
            suffix: File extension hint (e.g., ``".pdf"``).

        Returns:
            Extracted text content.
        """

    def format_as_context(self, text: str, filename: str) -> str:
        """Format extracted text with source delimiters for context injection.

        Args:
            text: The extracted text content.
            filename: Display name of the source file.

        Returns:
            Text wrapped with file delimiters.
        """
        return (
            f"\n\n--- Content of attached file '{filename}' ---\n"
            f"{text}\n"
            f"--- End of file ---\n"
        )

    def process_file(
        self,
        path: str | Path,
        filename: str | None = None,
    ) -> str:
        """Extract text from a file and format it for context injection.

        Convenience method combining :meth:`extract_text` and
        :meth:`format_as_context`.

        Args:
            path: Path to the document.
            filename: Optional display name. Defaults to the file's basename.

        Returns:
            Formatted text ready for context injection.
        """
        path = Path(path)
        display_name = filename or path.name
        text = self.extract_text(path)
        return self.format_as_context(text, display_name)

    def process_bytes(self, data: bytes, filename: str) -> str:
        """Extract text from bytes and format it for context injection.

        Convenience method combining :meth:`extract_text_from_bytes` and
        :meth:`format_as_context`.

        Args:
            data: Raw file content.
            filename: Display name (also used to infer file type).

        Returns:
            Formatted text ready for context injection.
        """
        suffix = Path(filename).suffix or ".pdf"
        text = self.extract_text_from_bytes(data, suffix=suffix)
        return self.format_as_context(text, filename)
