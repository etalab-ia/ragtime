"""Shared types for retrieval-albert."""

from typing import TypedDict


class RetrievedChunk(TypedDict):
    """A retrieved chunk with score and source metadata."""

    content: str
    score: float
    source_file: str | None
    page: int | None
    collection_id: int
    document_id: int
    chunk_id: int
