"""Albert API vector storage provider.

Implements collection management via the Albert API: create, populate,
delete, and list collections.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from rag_facile.core import get_config

from ._base import StorageProvider


if TYPE_CHECKING:
    from albert import AlbertClient
    from albert.types.collections import Collection, CollectionList


logger = logging.getLogger(__name__)


class AlbertProvider(StorageProvider):
    """Vector storage provider using Albert API collections.

    Wraps the Albert client SDK for collection lifecycle operations.
    Chunking parameters default to ragfacile.toml values via rag_core.
    """

    def create_collection(
        self,
        client: AlbertClient,
        name: str,
        description: str = "",
    ) -> int:
        """Create an Albert collection.

        Args:
            client: Authenticated Albert client.
            name: Name for the new collection.
            description: Optional description.

        Returns:
            The collection ID.
        """
        collection: Collection = client.create_collection(
            name=name,
            description=description,
        )
        logger.info("Created collection %s (id=%s)", name, collection.id)
        return collection.id

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

        Chunking parameters default to values from ragfacile.toml.

        Args:
            client: Authenticated Albert client.
            paths: List of file paths to upload.
            collection_id: Target collection ID.
            chunk_size: Override chunk size (defaults to config.chunking.chunk_size).
            chunk_overlap: Override overlap (defaults to config.chunking.chunk_overlap).

        Returns:
            List of created document IDs.
        """
        config = get_config()
        chunk_size = (
            chunk_size if chunk_size is not None else config.chunking.chunk_size
        )
        chunk_overlap = (
            chunk_overlap
            if chunk_overlap is not None
            else config.chunking.chunk_overlap
        )

        document_ids: list[int] = []
        for i, file_path in enumerate(paths, 1):
            file_path = Path(file_path)
            logger.info("Uploading document %d/%d: %s", i, len(paths), file_path.name)

            response = client.upload_document(
                file_path=file_path,
                collection_id=collection_id,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
            document_ids.append(response.id)
            logger.debug("  Uploaded document id=%s", response.id)

        logger.info(
            "Ingested %d documents into collection %s",
            len(document_ids),
            collection_id,
        )
        return document_ids

    def delete_collection(self, client: AlbertClient, collection_id: int) -> None:
        """Delete a collection and all its documents.

        Args:
            client: Authenticated Albert client.
            collection_id: Collection to delete.
        """
        client.delete_collection(collection_id)
        logger.info("Deleted collection %s", collection_id)

    def list_collections(
        self,
        client: AlbertClient,
        *,
        limit: int = 10,
        offset: int = 0,
    ) -> CollectionList:
        """List accessible collections.

        Args:
            client: Authenticated Albert client.
            limit: Maximum results to return.
            offset: Pagination offset.

        Returns:
            CollectionList with matching collections.
        """
        return client.list_collections(limit=limit, offset=offset)
