"""Base interface for reranking providers.

Defines the :class:`RerankingProvider` ABC that all cross-encoder reranking
backends must implement.  Configuration-driven parameters (model, top_n) are
injected at construction time by the factory so the :meth:`rerank` signature
stays stable across provider implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from rag_facile.core import RetrievedChunk


class RerankingProvider(ABC):
    """Abstract base class for reranking providers.

    Subclasses must implement:
      - :meth:`rerank` — re-score retrieved chunks against a query

    Configuration parameters (``model``, ``top_n``) are passed at construction
    time by :func:`rag_facile.reranking.get_provider` so that call-sites only
    need to supply the runtime inputs: query and chunk list.
    """

    @abstractmethod
    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
    ) -> list[RetrievedChunk]:
        """Re-score chunks by relevance to *query*.

        Args:
            query: The original user query to rank chunks against.
            chunks: Candidate chunks from the retrieval phase.

        Returns:
            Reranked list of chunks (highest relevance first), trimmed to the
            configured ``top_n``.
        """
