"""Base interface for vector storage providers.

Defines the :class:`StorageProvider` ABC that all backends must implement.
Provides the contract for collection management operations: create, ingest,
delete, and list collections.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from albert import AlbertClient
    from albert.types.collections import CollectionList


class StorageProvider(ABC):
    """Abstract base class for vector storage providers.

    Subclasses must implement collection lifecycle operations:

      - :meth:`create_collection` — create a new collection
      - :meth:`ingest_documents` — upload documents to a collection
      - :meth:`delete_collection` — delete a collection
      - :meth:`list_collections` — list accessible collections
    """

    @abstractmethod
    def create_collection(
        self,
        client: AlbertClient,
        name: str,
        description: str = "",
    ) -> int:
        """Create a collection.

        Args:
            client: Authenticated API client.
            name: Name for the new collection.
            description: Optional description.

        Returns:
            The collection ID.
        """

    @abstractmethod
    def ingest_documents(
        self,
        client: AlbertClient,
        paths: list[str | Path],
        collection_id: int,
        *,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> list[int]:
        """Upload documents to a collection.

        Args:
            client: Authenticated API client.
            paths: List of file paths to upload.
            collection_id: Target collection ID.
            chunk_size: Override chunk size (defaults to config).
            chunk_overlap: Override overlap (defaults to config).

        Returns:
            List of created document IDs.
        """

    @abstractmethod
    def delete_collection(self, client: AlbertClient, collection_id: int) -> None:
        """Delete a collection and all its documents.

        Args:
            client: Authenticated API client.
            collection_id: Collection to delete.
        """

    @abstractmethod
    def list_collections(
        self,
        client: AlbertClient,
        *,
        limit: int = 10,
        offset: int = 0,
    ) -> CollectionList:
        """List accessible collections.

        Args:
            client: Authenticated API client.
            limit: Maximum results to return.
            offset: Pagination offset.

        Returns:
            Collection list from the backend.
        """
