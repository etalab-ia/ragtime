"""Base interface for retrieval providers.

Defines the :class:`RetrievalProvider` ABC that all vector-search backends
must implement.  Configuration-driven parameters (method, top_k,
score_threshold) are injected at construction time by the factory so the
:meth:`search` signature stays stable across provider implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from rag_facile.core import RetrievedChunk


class RetrievalProvider(ABC):
    """Abstract base class for vector-search retrieval providers.

    Subclasses must implement:
      - :meth:`search` — search collections and return ranked chunks

    Configuration parameters (``top_k``, search ``method``, etc.) are passed
    at construction time by :func:`rag_facile.retrieval.get_provider` so that
    call-sites only need to supply the runtime inputs: query and collection IDs.
    """

    @abstractmethod
    def search(
        self,
        query: str,
        collection_ids: list[int | str],
    ) -> list[RetrievedChunk]:
        """Search for relevant chunks across collections.

        Args:
            query: Search query text.
            collection_ids: Collections to search in.

        Returns:
            List of retrieved chunks sorted by relevance score (descending).
        """
