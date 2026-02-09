"""Search and rerank types for Albert API.

Models for hybrid RAG search and BGE reranking endpoints.
"""

from typing import Any, Literal

from albert_client._models import BaseModel


# Search types


class Chunk(BaseModel):
    """A chunk of text from a document in a collection."""

    object: Literal["chunk"] = "chunk"
    id: int
    metadata: dict[str, Any]
    content: str


class ChunkList(BaseModel):
    """Response from listing chunks."""

    object: Literal["list"] = "list"
    data: list[Chunk]


SearchMethod = Literal["hybrid", "semantic", "lexical"]
"""Search method: hybrid (semantic + lexical), semantic only, or lexical only."""


class SearchResult(BaseModel):
    """A single search result from Albert API."""

    method: SearchMethod
    score: float
    chunk: Chunk


class Usage(BaseModel):
    """Usage information for a request."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    carbon: dict[str, Any] | None = None  # Carbon footprint details
    requests: int = 0


class SearchResponse(BaseModel):
    """Response from /v1/search endpoint."""

    object: Literal["list"] = "list"
    data: list[SearchResult]
    usage: Usage | None = None


# Rerank types


class RerankResult(BaseModel):
    """A single reranked document result."""

    relevance_score: float
    index: int  # Original position in input list


class RerankResponse(BaseModel):
    """Response from /v1/rerank endpoint."""

    object: Literal["list"] = "list"
    id: str
    results: list[RerankResult]
    model: str
    usage: Usage | None = None
