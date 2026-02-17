"""Basic RAG pipeline — context stuffing with local parsing.

Parses documents locally (via the ingestion package) and injects the
full text into the LLM prompt.  No retrieval search is performed.

Selected when ``storage.provider = "local-sqlite"`` in ragfacile.toml.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ._base import RAGPipeline


class BasicPipeline(RAGPipeline):
    """Context-stuffing pipeline using local document parsing.

    Delegates all file processing to the ingestion package's
    :class:`~ingestion.LocalProvider`.  Query-time retrieval is a no-op
    because the full document text is already included in the prompt.
    """

    def __init__(self, config: Any | None = None) -> None:
        from rag_facile.ingestion import get_provider

        self._ingestion = get_provider(config)

    def process_file(
        self,
        path: str | Path,
        filename: str | None = None,
    ) -> str:
        """Parse a file locally and return formatted context."""
        return self._ingestion.process_file(path, filename)

    def process_bytes(self, data: bytes, filename: str) -> str:
        """Parse file bytes locally and return formatted context."""
        return self._ingestion.process_bytes(data, filename)

    @property
    def supported_extensions(self) -> list[str]:
        """File extensions supported by the local ingestion provider."""
        return self._ingestion.supported_extensions

    @property
    def accepted_mime_types(self) -> dict[str, list[str]]:
        """MIME types accepted by the local ingestion provider."""
        return self._ingestion.accepted_mime_types
