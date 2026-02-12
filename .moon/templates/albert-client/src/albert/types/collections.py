"""Collections and documents types for Albert API.

Models for managing RAG collections and document uploads.
"""

from typing import Literal

from albert._models import BaseModel


# Collection types

CollectionVisibility = Literal["private", "public"]
"""Collection visibility: private (owner only) or public (all users)."""


class Collection(BaseModel):
    """A RAG collection for organizing documents."""

    object: Literal["collection"] = "collection"
    id: int
    name: str
    owner: str
    description: str | None = None
    visibility: CollectionVisibility | None = None
    created: int  # Unix timestamp
    updated: int  # Unix timestamp
    documents: int = 0  # Number of documents in collection


class CollectionList(BaseModel):
    """Response from listing collections."""

    object: Literal["list"] = "list"
    data: list[Collection]


# Document types


class Document(BaseModel):
    """A document uploaded to a collection."""

    object: Literal["document"] = "document"
    id: int
    name: str
    collection_id: int
    created: int  # Unix timestamp
    chunks: int | None = None  # Number of chunks (may be None during upload)


class DocumentList(BaseModel):
    """Response from listing documents."""

    object: Literal["list"] = "list"
    data: list[Document]
