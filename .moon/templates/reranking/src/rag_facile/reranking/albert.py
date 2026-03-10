"""Albert-powered reranking provider.

Implements :class:`RerankingProvider` using the Albert API cross-encoder.
Configuration parameters (model, top_n) are injected at construction time by
:func:`rag_facile.reranking.get_provider`.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from rag_facile.core import RetrievedChunk

from ._base import RerankingProvider


if TYPE_CHECKING:
    from albert import AlbertClient  # Only needed for type annotations


logger = logging.getLogger(__name__)


class AlbertRerankingProvider(RerankingProvider):
    """Reranking provider backed by the Albert API cross-encoder.

    Re-scores retrieved chunks using a cross-encoder model for higher
    precision.  All scoring parameters are fixed at construction time
    (loaded from ``ragfacile.toml`` by the factory).

    Args:
        model: Cross-encoder model alias (e.g. ``"openweight-rerank"``).
        top_n: Number of top-ranked chunks to return.
    """

    def __init__(
        self,
        *,
        model: str = "openweight-rerank",
        top_n: int = 5,
        client: AlbertClient | None = None,
    ) -> None:
        self._model = model
        self._top_n = top_n
        self._client: AlbertClient | None = client

    @property
    def _albert_client(self) -> AlbertClient:
        """Lazily create the Albert client on first use."""
        if self._client is None:
            from albert import AlbertClient as _AlbertClient

            self._client = _AlbertClient()
        return self._client

    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
    ) -> list[RetrievedChunk]:
        """Re-score chunks using the Albert cross-encoder.

        Args:
            query: The original user query to rank chunks against.
            chunks: Candidate chunks from the retrieval phase.

        Returns:
            Reranked list of chunks (highest relevance first), trimmed to
            ``top_n``.  Returns *chunks* unchanged if the list is empty.
        """
        if not chunks:
            return []

        documents = [c["content"] for c in chunks]
        response = self._albert_client.rerank(
            query=query,
            documents=documents,
            model=self._model,
            top_n=self._top_n,
        )

        reranked: list[RetrievedChunk] = []
        for result in response.results:
            original = chunks[result.index]
            reranked_chunk = original.copy()
            reranked_chunk["score"] = result.relevance_score
            reranked.append(reranked_chunk)

        logger.info("Reranked %d chunks → %d results", len(chunks), len(reranked))
        return reranked
