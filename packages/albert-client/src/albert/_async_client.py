"""Async Albert Client implementation."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import httpx
from openai import AsyncOpenAI

from albert.client import _log_api_error

if TYPE_CHECKING:
    from pathlib import Path

    from albert.types import (
        Chunk,
        ChunkInput,
        ChunkList,
        Collection,
        CollectionList,
        CollectionVisibility,
        CompoundMetadataFilter,
        Document,
        DocumentList,
        DocumentResponse,
        MetadataFilter,
        OCRResponse,
        RerankResponse,
        SearchResponse,
        UsageList,
    )


class AsyncAlbertClient:
    """Official Async Python SDK for France's Albert API.

    Provides OpenAI-compatible endpoints (chat, embeddings, audio, models) and
    Albert-specific endpoints (search, rerank, collections, documents, tools, management).

    Example:
        ```python
        from albert import AsyncAlbertClient

        # Initialize client
        client = AsyncAlbertClient(
            api_key="albert_...",
            base_url="https://albert.api.etalab.gouv.fr/v1"
        )

        # OpenAI-compatible endpoints
        response = await client.chat.completions.create(
            model="openweight-large",
            messages=[{"role": "user", "content": "Hello!"}]
        )

        # Albert-specific endpoints
        results = await client.search(query="Code civil", collection_ids=[785])
        ```
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = "https://albert.api.etalab.gouv.fr/v1",
        **kwargs,
    ):
        """Initialize Async Albert client.

        Args:
            api_key: Albert API key. If not provided, reads from ALBERT_API_KEY or OPENAI_API_KEY env var.
            base_url: Base URL for Albert API (includes /v1 suffix).
            **kwargs: Additional arguments passed to OpenAI client.
        """
        if api_key is None:
            api_key = os.environ.get("ALBERT_API_KEY") or os.environ.get(
                "OPENAI_API_KEY"
            )

        if not api_key:
            raise ValueError(
                "Albert API key is required. Provide via api_key parameter or "
                "ALBERT_API_KEY/OPENAI_API_KEY environment variable."
            )

        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url, **kwargs)

        # OpenAI-Compatible Passthrough
        self.chat = self._client.chat
        self.embeddings = self._client.embeddings
        self.audio = self._client.audio
        self.models = self._client.models

    def as_instructor(self):
        """Return an instructor-patched version of the internal AsyncOpenAI client.

        Enables structured Pydantic output via the ``instructor`` library, using
        the same API key, base URL, and connection pool as the rest of the client.

        Example::

            from my_package._models import ExpandedQueries

            ic = client.as_instructor()
            result = await ic.chat.completions.create(
                model="openweight-medium",
                response_model=ExpandedQueries,
                messages=[{"role": "user", "content": "..."}],
            )

        Returns:
            Instructor-patched :class:`openai.AsyncOpenAI` client.
        """
        import instructor

        return instructor.from_openai(self._client)

    async def close(self) -> None:
        """Close the underlying client."""
        await self._client.close()

    async def __aenter__(self) -> "AsyncAlbertClient":
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        await self.close()

    @property
    def api_key(self) -> str:
        """Get the API key."""
        return self._client.api_key

    @property
    def base_url(self) -> str:
        """Get the base URL."""
        return str(self._client.base_url)

    async def _make_request(self, method: str, path: str, **kwargs) -> "httpx.Response":
        """Make an authenticated HTTP request using the internal httpx client.

        Args:
            method: HTTP method (get, post, patch, delete, etc.)
            path: API endpoint path
            **kwargs: Additional arguments to pass to the httpx method

        Returns:
            httpx.Response object
        """
        headers = kwargs.get("headers", {})
        has_auth = any(key.lower() == "authorization" for key in headers.keys())
        if not has_auth:
            headers["Authorization"] = f"Bearer {self.api_key}"
        kwargs["headers"] = headers

        http_method = getattr(self._client._client, method)
        response = await http_method(path, **kwargs)

        if response.status_code >= 400:
            _log_api_error(method, path, kwargs, response)

        return response

    # Search and Rerank methods

    async def search(
        self,
        query: str,
        collection_ids: list[int] | None = None,
        document_ids: list[int] | None = None,
        limit: int = 10,
        offset: int = 0,
        method: str = "semantic",
        score_threshold: float | None = None,
        rff_k: int = 20,
        metadata_filters: "MetadataFilter | CompoundMetadataFilter | None" = None,
    ) -> "SearchResponse":
        """Search for relevant chunks across collections.

        Supports semantic, lexical, or hybrid search methods with optional
        metadata filtering and document-level scoping.

        Args:
            query: Search query text.
            collection_ids: Collection IDs to search in. Pass empty list to search
                all collections. Defaults to all collections.
            document_ids: Document IDs to scope the search. Defaults to all documents.
            limit: Maximum number of results to return (1-200). Defaults to 10.
            offset: Pagination offset. Defaults to 0.
            method: Search method - ``"semantic"``, ``"lexical"``, or ``"hybrid"``.
                Defaults to ``"semantic"``.
            score_threshold: Minimum cosine similarity score (0.0-1.0).
                Only valid for ``method="semantic"``.
            rff_k: RFF algorithm constant for hybrid search. Defaults to 20.
            metadata_filters: Optional metadata filter or compound filter.

        Returns:
            SearchResponse with results, usage info, and metadata.

        Raises:
            httpx.HTTPStatusError: If the API request fails.

        Example:
            ```python
            results = await client.search(
                query="Code civil",
                collection_ids=[785],
                limit=5,
                method="hybrid"
            )
            for result in results.data:
                print(result.score, result.chunk.content)
            ```
        """
        from albert.types import SearchResponse

        body: dict[str, Any] = {
            "query": query,
            "collection_ids": collection_ids if collection_ids is not None else [],
            "limit": limit,
            "offset": offset,
            "method": method,
            "rff_k": rff_k,
        }
        if document_ids is not None:
            body["document_ids"] = document_ids
        if score_threshold is not None:
            body["score_threshold"] = score_threshold
        if metadata_filters is not None:
            body["metadata_filters"] = metadata_filters.model_dump()

        response = await self._make_request("post", "/search", json=body)
        response.raise_for_status()

        return SearchResponse(**response.json())

    async def rerank(
        self,
        query: str,
        documents: list[str],
        model: str,
        top_n: int | None = None,
    ) -> "RerankResponse":
        """Rerank documents by relevance to a query."""
        from albert.types import RerankResponse

        body: dict[str, Any] = {
            "query": query,
            "documents": documents,
            "model": model,
        }
        if top_n is not None:
            body["top_n"] = top_n

        response = await self._make_request("post", "/rerank", json=body)
        response.raise_for_status()

        return RerankResponse(**response.json())

    # Collections methods

    async def create_collection(
        self,
        name: str,
        description: str | None = None,
        visibility: "CollectionVisibility" = "private",
    ) -> "Collection":
        """Create a new RAG collection."""
        from albert.types import Collection

        body: dict[str, Any] = {"name": name, "visibility": visibility}
        if description is not None:
            body["description"] = description

        response = await self._make_request("post", "/collections", json=body)
        response.raise_for_status()

        return Collection(**response.json())

    async def list_collections(
        self,
        name: str | None = None,
        visibility: "CollectionVisibility | None" = None,
        limit: int = 10,
        offset: int = 0,
        order_by: str | None = None,
        order_direction: str | None = None,
    ) -> "CollectionList":
        """List all accessible collections."""
        from albert.types import CollectionList

        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if name is not None:
            params["name"] = name
        if visibility is not None:
            params["visibility"] = visibility
        if order_by is not None:
            params["order_by"] = order_by
        if order_direction is not None:
            params["order_direction"] = order_direction

        response = await self._make_request("get", "/collections", params=params)
        response.raise_for_status()

        return CollectionList(**response.json())

    async def get_collection(self, collection_id: int) -> "Collection":
        """Get a specific collection by ID."""
        from albert.types import Collection

        response = await self._make_request("get", f"/collections/{collection_id}")
        response.raise_for_status()

        return Collection(**response.json())

    async def update_collection(
        self,
        collection_id: int,
        name: str | None = None,
        description: str | None = None,
        visibility: "CollectionVisibility | None" = None,
    ) -> None:
        """Update a collection's metadata."""
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if visibility is not None:
            body["visibility"] = visibility

        response = await self._make_request(
            "patch", f"/collections/{collection_id}", json=body
        )
        response.raise_for_status()

    async def delete_collection(self, collection_id: int) -> None:
        """Delete a collection and all its documents."""
        response = await self._make_request("delete", f"/collections/{collection_id}")
        response.raise_for_status()

    # Documents methods

    async def upload_document(
        self,
        file_path: "str | Path",
        collection_id: int,
        name: str | None = None,
        chunk_size: int = 2048,
        chunk_overlap: int = 0,
        chunk_min_size: int = 0,
        separators: list[str] | None = None,
        preset_separators: str | None = None,
        is_separator_regex: bool = False,
        disable_chunking: bool = False,
        metadata: str | None = None,
    ) -> "DocumentResponse":
        """Upload a document to a collection.

        The document will be parsed, chunked, and embedded by Albert server-side.

        Args:
            file_path: Path to the file to upload.
            collection_id: The collection ID to add the document to.
            name: Optional display name for the document.
            chunk_size: Size of text chunks for embedding (default: 2048).
            chunk_overlap: Overlap between chunks (default: 0).
            chunk_min_size: Minimum chunk size to keep (default: 0).
            separators: List of custom separators for splitting.
            preset_separators: Preset separator profile (e.g. ``"markdown"``).
            is_separator_regex: Treat separators as regex patterns (default: False).
            disable_chunking: Store without chunking; use :meth:`add_chunks` to supply
                chunks manually (default: False).
            metadata: Stringified JSON object with custom document metadata.

        Returns:
            DocumentResponse with the new document ID.

        Raises:
            httpx.HTTPStatusError: If the upload fails.

        Example:
            ```python
            doc = await client.upload_document(
                file_path="report.pdf",
                collection_id=123,
                chunk_size=1000,
                metadata='{"category": "finance"}'
            )
            print(f"Uploaded document ID: {doc.id}")
            ```
        """
        from pathlib import Path

        from albert.types import DocumentResponse

        file_path = Path(file_path)

        form_data: dict[str, Any] = {
            "collection_id": collection_id,
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
            "chunk_min_size": chunk_min_size,
            "is_separator_regex": is_separator_regex,
            "disable_chunking": disable_chunking,
        }
        if name is not None:
            form_data["name"] = name
        if separators is not None:
            form_data["separators"] = separators
        if preset_separators is not None:
            form_data["preset_separators"] = preset_separators
        if metadata is not None:
            form_data["metadata"] = metadata

        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f, "application/octet-stream")}
            response = await self._make_request(
                "post", "/documents", data=form_data, files=files
            )
            response.raise_for_status()

        return DocumentResponse(**response.json())

    async def list_documents(
        self,
        collection_id: int | None = None,
        name: str | None = None,
        limit: int | None = 10,
        offset: int | str = 0,
        order_by: str | None = None,
        order_direction: str | None = None,
    ) -> "DocumentList":
        """List documents in a collection or all accessible documents."""
        from albert.types import DocumentList

        params: dict[str, Any] = {}
        if collection_id is not None:
            params["collection_id"] = collection_id
        if name is not None:
            params["name"] = name
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if order_by is not None:
            params["order_by"] = order_by
        if order_direction is not None:
            params["order_direction"] = order_direction

        response = await self._make_request("get", "/documents", params=params)
        response.raise_for_status()

        return DocumentList(**response.json())

    async def get_document(self, document_id: int) -> "Document":
        """Get a specific document by ID."""
        from albert.types import Document

        response = await self._make_request("get", f"/documents/{document_id}")
        response.raise_for_status()

        return Document(**response.json())

    async def delete_document(self, document_id: int) -> None:
        """Delete a document and all its chunks."""
        response = await self._make_request("delete", f"/documents/{document_id}")
        response.raise_for_status()

    # Chunks methods

    async def list_chunks(
        self,
        document_id: int,
        limit: int = 10,
        offset: int | str = 0,
    ) -> "ChunkList":
        """List chunks for a specific document."""
        from albert.types import ChunkList

        params: dict[str, Any] = {"limit": limit, "offset": offset}
        response = await self._make_request(
            "get", f"/documents/{document_id}/chunks", params=params
        )
        response.raise_for_status()

        return ChunkList(**response.json())

    async def get_chunk(self, document_id: int, chunk_id: int) -> "Chunk":
        """Get a specific chunk by document and chunk ID."""
        from albert.types import Chunk

        response = await self._make_request(
            "get", f"/documents/{document_id}/chunks/{chunk_id}"
        )
        response.raise_for_status()

        return Chunk(**response.json())

    async def add_chunks(
        self,
        document_id: int,
        chunks: "list[ChunkInput]",
    ) -> None:
        """Add chunks directly to a document.

        Use this when you want full control over chunking — upload the document
        with ``disable_chunking=True``, then call this method to supply your
        own chunks with optional per-chunk metadata.

        Args:
            document_id: The document ID to add chunks to.
            chunks: List of :class:`~albert.types.ChunkInput` objects.

        Raises:
            httpx.HTTPStatusError: If the request fails.

        Example:
            ```python
            from albert.types import ChunkInput

            doc = await client.upload_document(
                file_path="doc.pdf",
                collection_id=123,
                disable_chunking=True,
            )
            await client.add_chunks(doc.id, [
                ChunkInput(content="First chunk.", metadata={"page": 1}),
                ChunkInput(content="Second chunk.", metadata={"page": 2}),
            ])
            ```
        """
        body = [chunk.model_dump(exclude_none=True) for chunk in chunks]
        response = await self._make_request(
            "post", f"/documents/{document_id}/chunks", json=body
        )
        response.raise_for_status()

    async def delete_chunk(self, document_id: int, chunk_id: int) -> None:
        """Delete a specific chunk from a document.

        Args:
            document_id: The document ID.
            chunk_id: The chunk ID to delete.

        Raises:
            httpx.HTTPStatusError: If the chunk doesn't exist or deletion fails.

        Example:
            ```python
            await client.delete_chunk(document_id=456, chunk_id=789)
            print("Chunk 789 from document 456 deleted.")
            ```
        """
        response = await self._make_request(
            "delete", f"/documents/{document_id}/chunks/{chunk_id}"
        )
        response.raise_for_status()

    # Usage tracking

    async def get_usage(
        self,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int = 10,
        offset: int = 0,
        endpoint: str | None = None,
    ) -> "UsageList":
        """Get API usage statistics.

        Args:
            start_time: Filter from this timestamp (Unix seconds). Optional.
            end_time: Filter until this timestamp (Unix seconds). Optional.
            limit: Max results. Default 10.
            offset: Pagination offset. Default 0.
            endpoint: Filter by endpoint API path.

        Returns:
            UsageList with usage records.

        Raises:
            httpx.HTTPStatusError: If the request fails.

        Example:
            ```python
            import time
            now = int(time.time())
            usage = await client.get_usage(
                start_time=now - 86400,
                end_time=now
            )
            for record in usage.data:
                print(f"{record.model}: {record.usage.total_tokens} tokens")
            ```
        """
        from albert.types import UsageList

        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if start_time is not None:
            params["start_time"] = start_time
        if end_time is not None:
            params["end_time"] = end_time
        if endpoint is not None:
            params["endpoint"] = endpoint

        response = await self._make_request("get", "/me/usage", params=params)
        response.raise_for_status()

        return UsageList(**response.json())

    # OCR methods

    async def ocr(
        self,
        document: dict[str, str] | str,
        model: str | None = None,
        pages: list[int] | None = None,
        include_image_base64: bool = False,
        image_limit: int | None = None,
        image_min_size: int | None = None,
        **kwargs,
    ) -> "OCRResponse":
        """Perform OCR on a document with advanced options."""
        from albert.types import OCRResponse

        body: dict[str, Any] = {}
        if isinstance(document, str):
            body["document"] = {"document_url": document}
        else:
            body["document"] = document

        if model is not None:
            body["model"] = model
        if pages is not None:
            body["pages"] = pages
        if include_image_base64:
            body["include_image_base64"] = include_image_base64
        if image_limit is not None:
            body["image_limit"] = image_limit
        if image_min_size is not None:
            body["image_min_size"] = image_min_size

        body.update(kwargs)

        response = await self._make_request("post", "/ocr", json=body)
        response.raise_for_status()

        return OCRResponse(**response.json())

    # Health & Monitoring

    async def health_check(self) -> dict[str, Any]:
        """Check API health status."""
        response = await self._make_request("get", "/health")
        response.raise_for_status()
        return response.json()

    async def get_metrics(self) -> dict[str, Any]:
        """Get API metrics."""
        response = await self._make_request("get", "/metrics")
        response.raise_for_status()
        return response.json()
