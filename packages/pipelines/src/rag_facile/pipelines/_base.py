"""Base interface for RAG pipeline orchestration.

Defines the :class:`RAGPipeline` ABC that concrete pipelines must implement.
Chat applications depend on this interface rather than on individual
ingestion or retrieval packages directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class RAGPipeline(ABC):
    """Abstract RAG pipeline for chat applications.

    Provides a unified interface for both upload-time (file processing)
    and query-time (retrieval) operations.  Concrete implementations
    decide how to coordinate ingestion and retrieval.

    Subclasses must implement:
      - :meth:`process_file` — parse a file and return formatted context
      - :meth:`process_bytes` — parse bytes and return formatted context
      - :attr:`supported_extensions` — file extensions this pipeline handles
      - :attr:`accepted_mime_types` — MIME type map for file picker dialogs

    Optional override:
      - :meth:`process_query` — retrieve context for a user query
    """

    # ── Upload-time: file processing ──

    @abstractmethod
    def process_file(
        self,
        path: str | Path,
        filename: str | None = None,
    ) -> str:
        """Parse a file and return formatted context for LLM injection.

        Args:
            path: Path to the document.
            filename: Optional display name.  Defaults to the file's basename.

        Returns:
            Formatted text ready for context injection.
        """

    @abstractmethod
    def process_bytes(self, data: bytes, filename: str) -> str:
        """Parse file bytes and return formatted context.

        Args:
            data: Raw file content.
            filename: Display name (also used to infer file type).

        Returns:
            Formatted text ready for context injection.
        """

    # ── Query-time: retrieval ──

    def process_query(self, query: str, **kwargs: object) -> str:
        """Retrieve relevant context for a user query.

        The default implementation is a no-op — suitable for basic pipelines
        that rely on context stuffing (the full document is already in the
        prompt).  The Albert pipeline overrides this to perform
        search → rerank → format.

        Args:
            query: User query to retrieve context for.
            **kwargs: Pipeline-specific options (e.g., ``collection_ids``).

        Returns:
            Formatted context string.  Empty string when not applicable.
        """
        return ""

    # ── Capabilities (for UI file dialogs) ──

    @property
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """File extensions this pipeline can process (e.g., ``[".pdf"]``)."""

    @property
    @abstractmethod
    def accepted_mime_types(self) -> dict[str, list[str]]:
        """MIME types for file picker dialogs.

        Returns:
            Dict mapping MIME types to extensions, e.g.
            ``{"application/pdf": [".pdf"]}``.
        """
