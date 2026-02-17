"""Main Albert Client implementation."""

from __future__ import annotations

import json
import logging
import os
import shlex
from typing import TYPE_CHECKING, Any

import httpx
from openai import OpenAI

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pathlib import Path

    from albert.types import (
        Chunk,
        ChunkList,
        Collection,
        CollectionList,
        CollectionVisibility,
        Document,
        DocumentList,
        DocumentResponse,
        FileResponse,
        OCRResponse,
        ParsedDocument,
        RerankResponse,
        SearchResponse,
        UsageList,
    )


_MAX_BODY_LOG = 2000  # Truncate request/response bodies in logs
_OPENGATELLM_REPO = "etalab-ia/OpenGateLLM"


def _log_api_error(
    method: str,
    path: str,
    kwargs: dict[str, Any],
    response: httpx.Response,
) -> None:
    """Log a detailed diagnostic when the Albert API returns an error.

    Captures the HTTP method, endpoint, request payload, and response body
    so that errors can be reported to the API team without needing to reproduce.
    No credentials are included in the log output.

    For 5xx errors, also prints a ready-to-use ``gh issue create`` command
    targeting the OpenGateLLM repository.
    """
    level = logging.ERROR if response.status_code >= 500 else logging.WARNING

    # Extract the request payload (json body or form data), skip file uploads
    request_body: str | None = None
    if "json" in kwargs:
        try:
            request_body = json.dumps(kwargs["json"], ensure_ascii=False)
            if len(request_body) > _MAX_BODY_LOG:
                request_body = request_body[:_MAX_BODY_LOG] + "…(truncated)"
        except (TypeError, ValueError):
            request_body = repr(kwargs["json"])[:_MAX_BODY_LOG]

    # Extract the response body
    response_text = response.text[:_MAX_BODY_LOG] if response.text else "(empty)"
    if len(response.text) > _MAX_BODY_LOG:
        response_text += "…(truncated)"

    lines = [
        f"Albert API error on {method.upper()} {path} (HTTP {response.status_code})",
    ]
    if request_body:
        lines.append(f"  Request: {request_body}")
    lines.append(f"  Response: {response_text}")

    logger.log(level, "\n".join(lines))

    # For server errors, print a gh command to file an issue on OpenGateLLM
    if response.status_code >= 500:
        _print_gh_issue_command(method, path, response, request_body, response_text)


def _print_gh_issue_command(
    method: str,
    path: str,
    response: httpx.Response,
    request_body: str | None,
    response_text: str,
) -> None:
    """Print a ready-to-use ``gh issue create`` command for the OpenGateLLM repo."""
    title = f"[Bug] {method.upper()} {path} returns {response.status_code}"

    body_parts = [
        "## Bug Report",
        "",
        f"**Endpoint:** `{method.upper()} {path}`",
        f"**HTTP Status:** {response.status_code}",
        "",
    ]

    if request_body:
        body_parts += [
            "### Request payload",
            "",
            "```json",
            request_body,
            "```",
            "",
        ]

    body_parts += [
        "### Response body",
        "",
        "```json",
        response_text,
        "```",
        "",
        "### Reproduction",
        "",
        "```bash",
        f"curl -s -X {method.upper()} \\",
        '  -H "Authorization: Bearer $ALBERT_API_KEY" \\',
    ]

    if request_body:
        body_parts.append('  -H "Content-Type: application/json" \\')
        body_parts.append(f"  -d '{request_body}' \\")

    base_url = str(response.request.url).rsplit(path, 1)[0]
    body_parts += [
        f"  {base_url}{path}",
        "```",
    ]

    body = "\n".join(body_parts)

    gh_cmd = (
        f"gh issue create"
        f" --repo {_OPENGATELLM_REPO}"
        f" --title {shlex.quote(title)}"
        f" --body {shlex.quote(body)}"
    )

    logger.error(
        "To report this issue to the Albert API team, run:\n\n%s\n",
        gh_cmd,
    )


class AlbertClient:
    """Official Python SDK for France's Albert API.

    Provides OpenAI-compatible endpoints (chat, embeddings, audio, models) and
    Albert-specific endpoints (search, rerank, collections, documents, tools, management).

    Example:
        ```python
        from albert import AlbertClient

        # Initialize client
        client = AlbertClient(
            api_key="albert_...",  # Or set ALBERT_API_KEY env var
            base_url="https://albert.api.etalab.gouv.fr/v1"
        )

        # OpenAI-compatible endpoints
        response = client.chat.completions.create(
            model="AgentPublic/llama3-instruct-8b",
            messages=[{"role": "user", "content": "Hello!"}]
        )

        # Albert-specific endpoints
        # results = client.search(prompt="...", collections=["..."])
        ```

    Architecture:
        - Wraps internal OpenAI client for OpenAI-compatible endpoints
        - Provides custom implementations for Albert-specific features
        - All responses use Pydantic models for type safety
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = "https://albert.api.etalab.gouv.fr/v1",
        **kwargs,
    ):
        """Initialize Albert client.

        Args:
            api_key: Albert API key. If not provided, reads from ALBERT_API_KEY or OPENAI_API_KEY env var.
            base_url: Base URL for Albert API (includes /v1 suffix).
            **kwargs: Additional arguments passed to OpenAI client (timeout, max_retries, etc.).
        """
        # Get API key from env if not provided (check both ALBERT_API_KEY and OPENAI_API_KEY)
        if api_key is None:
            api_key = os.environ.get("ALBERT_API_KEY") or os.environ.get(
                "OPENAI_API_KEY"
            )

        if not api_key:
            raise ValueError(
                "Albert API key is required. Provide via api_key parameter or "
                "ALBERT_API_KEY/OPENAI_API_KEY environment variable."
            )

        # Initialize wrapped OpenAI client
        self._client = OpenAI(api_key=api_key, base_url=base_url, **kwargs)

        # OpenAI-Compatible Passthrough (direct proxy to internal client)
        self.chat = self._client.chat
        self.embeddings = self._client.embeddings
        self.audio = self._client.audio
        self.models = self._client.models

    def close(self) -> None:
        """Close the underlying client."""
        self._client.close()

    def __enter__(self) -> "AlbertClient":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    @property
    def api_key(self) -> str:
        """Get the API key."""
        return self._client.api_key

    @property
    def base_url(self) -> str:
        """Get the base URL."""
        return str(self._client.base_url)

    def _make_request(self, method: str, path: str, **kwargs) -> "httpx.Response":
        """Make an authenticated HTTP request using the internal httpx client.

        Adds the Authorization header with the API key and delegates to the
        wrapped OpenAI client's internal httpx client.

        Args:
            method: HTTP method (get, post, patch, delete, etc.)
            path: API endpoint path (e.g., "/collections")
            **kwargs: Additional arguments to pass to the httpx method

        Returns:
            httpx.Response object
        """
        # Add authorization header if not already present (case-insensitive check)
        headers = kwargs.get("headers", {})
        # Check for Authorization header case-insensitively (HTTP header names are case-insensitive)
        has_auth = any(key.lower() == "authorization" for key in headers.keys())
        if not has_auth:
            headers["Authorization"] = f"Bearer {self.api_key}"
        kwargs["headers"] = headers

        # Get the HTTP method from the internal httpx client
        http_method = getattr(self._client._client, method)
        response = http_method(path, **kwargs)

        if response.status_code >= 400:
            _log_api_error(method, path, kwargs, response)

        return response

    # Search and Rerank methods

    def search(
        self,
        prompt: str,
        collections: list[str | int] | None = None,
        limit: int = 10,
        offset: int = 0,
        method: str = "semantic",
        score_threshold: float | None = None,
        rff_k: int = 20,
    ) -> SearchResponse:
        """Hybrid RAG search across collections.

        Searches for relevant chunks in the specified collections using the given prompt.
        Supports semantic, lexical, or hybrid search methods.

        Args:
            prompt: Search query to find relevant chunks.
            collections: List of collection IDs to search in. Defaults to all collections.
            limit: Maximum number of results to return (1-200). Defaults to 10.
            offset: Pagination offset. Defaults to 0.
            method: Search method - "semantic", "lexical", or "hybrid". Defaults to "semantic".
            score_threshold: Minimum cosine similarity score (0.0-1.0). Only for semantic search.
            rff_k: RFF algorithm constant. Defaults to 20.

        Returns:
            SearchResponse with results, usage info, and metadata.

        Raises:
            httpx.HTTPStatusError: If the API request fails.

        Example:
            ```python
            results = client.search(
                prompt="Code civil",
                collections=["legal_docs"],
                limit=5,
                method="hybrid"
            )
            for chunk in results.data:
                print(chunk.score, chunk.chunk.content)
            ```
        """
        from albert.types import SearchResponse

        # Build request body
        body = {
            "prompt": prompt,
            "collections": collections or [],
            "limit": limit,
            "offset": offset,
            "method": method,
            "rff_k": rff_k,
        }
        if score_threshold is not None:
            body["score_threshold"] = score_threshold

        # Make authenticated request
        response = self._make_request("post", "/search", json=body)
        response.raise_for_status()

        # Parse and return Pydantic model
        return SearchResponse(**response.json())

    def rerank(
        self,
        query: str,
        documents: list[str],
        model: str,
        top_n: int | None = None,
    ) -> RerankResponse:
        """Rerank documents by relevance to a query using BGE reranker.

        Takes a list of documents and reorders them by relevance to the query.

        Args:
            query: The search query to rank documents against.
            documents: List of document texts to rerank.
            model: Reranker model to use (e.g., "BAAI/bge-reranker-v2-m3").
            top_n: Return only top N results. If None, returns all documents.

        Returns:
            RerankResponse with reranked results and scores.

        Raises:
            httpx.HTTPStatusError: If the API request fails.
        """
        from albert.types import RerankResponse

        # Build request body
        body = {
            "query": query,
            "documents": documents,
            "model": model,
        }
        if top_n is not None:
            body["top_n"] = top_n

        # Make authenticated request
        response = self._make_request("post", "/rerank", json=body)
        response.raise_for_status()

        # Parse and return Pydantic model
        return RerankResponse(**response.json())

    # Collections methods

    def create_collection(
        self,
        name: str,
        description: str | None = None,
        visibility: CollectionVisibility = "private",
    ) -> Collection:
        """Create a new RAG collection.

        Args:
            name: Name of the collection (required).
            description: Optional description of the collection.
            visibility: "private" (owner only) or "public" (all users). Defaults to "private".

        Returns:
            Collection object with ID and metadata.

        Raises:
            httpx.HTTPStatusError: If the API request fails.
        """
        from albert.types import Collection

        # Build request body
        body = {"name": name, "visibility": visibility}
        if description is not None:
            body["description"] = description

        # Make authenticated request
        response = self._make_request("post", "/collections", json=body)
        response.raise_for_status()

        return Collection(**response.json())

    def list_collections(
        self,
        name: str | None = None,
        visibility: CollectionVisibility | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> CollectionList:
        """List all accessible collections.

        Args:
            name: Filter by collection name (optional).
            visibility: Filter by collection visibility (optional).
            limit: Maximum number of collections to return. Defaults to 10.
            offset: Pagination offset. Defaults to 0.

        Returns:
            CollectionList containing all accessible collections.

        Raises:
            httpx.HTTPStatusError: If the API request fails.
        """
        from albert.types import CollectionList

        params = {"limit": limit, "offset": offset}
        if name is not None:
            params["name"] = name
        if visibility is not None:
            params["visibility"] = visibility

        response = self._make_request("get", "/collections", params=params)
        response.raise_for_status()

        return CollectionList(**response.json())

    def get_collection(self, collection_id: int) -> Collection:
        """Get a specific collection by ID.

        Args:
            collection_id: The collection ID.

        Returns:
            Collection object with full metadata.

        Raises:
            httpx.HTTPStatusError: If the collection doesn't exist or isn't accessible.
        """
        from albert.types import Collection

        response = self._make_request("get", f"/collections/{collection_id}")
        response.raise_for_status()

        return Collection(**response.json())

    def update_collection(
        self,
        collection_id: int,
        name: str | None = None,
        description: str | None = None,
        visibility: CollectionVisibility | None = None,
    ) -> None:
        """Update a collection's metadata.

        Only the collection owner can update it. At least one field must be provided.

        Args:
            collection_id: The collection ID to update.
            name: New name for the collection (optional).
            description: New description (optional).
            visibility: New visibility setting (optional).

        Raises:
            httpx.HTTPStatusError: If the update fails (e.g. 404, 403).
        """
        # Build request body with only provided fields
        body = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if visibility is not None:
            body["visibility"] = visibility

        response = self._make_request(
            "patch", f"/collections/{collection_id}", json=body
        )
        response.raise_for_status()

    def delete_collection(self, collection_id: int) -> None:
        """Delete a collection and all its documents.

        Only the collection owner can delete it. This action is irreversible.

        Args:
            collection_id: The collection ID to delete.

        Raises:
            httpx.HTTPStatusError: If the deletion fails or user lacks permission.
        """
        response = self._make_request("delete", f"/collections/{collection_id}")
        response.raise_for_status()

    # Documents methods

    def upload_document(
        self,
        file_path: str | Path,
        collection_id: int,
        chunk_size: int = 2048,
        chunk_overlap: int = 0,
        chunker: str = "RecursiveCharacterTextSplitter",
        chunk_min_size: int = 0,
        separators: list[str] | None = None,
        preset_separators: str | None = None,
        is_separator_regex: bool = False,
        metadata: str | None = None,
    ) -> DocumentResponse:
        """Upload a document to a collection.

        The document will be parsed, chunked, and embedded according to the collection's
        settings.

        Args:
            file_path: Path to the file to upload.
            collection_id: The collection ID to add the document to.
            chunk_size: Size of text chunks for embedding (default: 2048).
            chunk_overlap: Overlap between chunks (default: 0).
            chunker: Chunker strategy (default: "RecursiveCharacterTextSplitter").
            chunk_min_size: Minimum chunk size (default: 0).
            separators: List of custom separators.
            preset_separators: Preset generic separators (e.g. "markdown").
            is_separator_regex: Treat separators as regex? (default: False).
            metadata: Stringified JSON object matching the Metadata schema.

        Returns:
            DocumentResponse with document ID.

        Raises:
            httpx.HTTPStatusError: If the upload fails.

        Example:
            ```python
            doc = client.upload_document(
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

        # Convert to Path object
        file_path = Path(file_path)

        # Build form data
        form_data = {
            "collection": collection_id,
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
            "chunker": chunker,
            "chunk_min_size": chunk_min_size,
            "is_separator_regex": is_separator_regex,
        }
        if separators is not None:
            # For list items in multipart form data, we might need multiple keys
            # or JSON serialization depending on API expectation.
            # Assuming standard "separators" list field here.
            form_data["separators"] = separators
        if preset_separators is not None:
            form_data["preset_separators"] = preset_separators
        if metadata is not None:
            form_data["metadata"] = metadata

        # Open and upload file
        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f, "application/octet-stream")}
            response = self._make_request(
                "post", "/documents", data=form_data, files=files
            )
            response.raise_for_status()

        return DocumentResponse(**response.json())

    def list_documents(
        self,
        collection_id: int | None = None,
        name: str | None = None,
        limit: int | None = 10,
        offset: int | str = 0,
    ) -> DocumentList:
        """List documents in a collection or all accessible documents.

        Args:
            collection_id: Filter to specific collection.
            name: Filter by document name.
            limit: Max results (default: 10).
            offset: Pagination offset (default: 0).

        Returns:
            DocumentList containing matching documents.

        Raises:
            httpx.HTTPStatusError: If the request fails.
        """
        from albert.types import DocumentList

        params = {}
        if collection_id is not None:
            params["collection"] = collection_id
        if name is not None:
            params["name"] = name
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = self._make_request("get", "/documents", params=params)
        response.raise_for_status()

        return DocumentList(**response.json())

    def get_document(self, document_id: int) -> Document:
        """Get a specific document by ID.

        Args:
            document_id: The document ID.

        Returns:
            Document object with metadata.

        Raises:
            httpx.HTTPStatusError: If the document doesn't exist or isn't accessible.
        """
        from albert.types import Document

        response = self._make_request("get", f"/documents/{document_id}")
        response.raise_for_status()

        return Document(**response.json())

    def delete_document(self, document_id: int) -> None:
        """Delete a document and all its chunks.

        This action is irreversible.

        Args:
            document_id: The document ID to delete.

        Raises:
            httpx.HTTPStatusError: If the deletion fails.
        """
        response = self._make_request("delete", f"/documents/{document_id}")
        response.raise_for_status()

    # Chunks methods

    def list_chunks(
        self,
        document_id: int,
        limit: int = 10,
        offset: int | str = 0,
    ) -> ChunkList:
        """List chunks for a specific document.

        Args:
            document_id: The document ID.
            limit: Max results (default: 10).
            offset: Pagination offset (default: 0).

        Returns:
            ChunkList containing chunks.

        Raises:
            httpx.HTTPStatusError: If the request fails.
        """
        from albert.types import ChunkList

        params = {"limit": limit, "offset": offset}
        response = self._make_request("get", f"/chunks/{document_id}", params=params)
        response.raise_for_status()

        return ChunkList(**response.json())

    def get_chunk(self, document_id: int, chunk_id: int) -> Chunk:
        """Get a specific chunk by document and chunk ID.

        Args:
            document_id: The document ID.
            chunk_id: The chunk ID.

        Returns:
            Chunk object with content and metadata.

        Raises:
            httpx.HTTPStatusError: If the chunk doesn't exist.
        """
        from albert.types import Chunk

        response = self._make_request("get", f"/chunks/{document_id}/{chunk_id}")
        response.raise_for_status()

        return Chunk(**response.json())

    # Usage tracking

    def get_usage(
        self,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int = 10,
        offset: int = 0,
        endpoint: str | None = None,
    ) -> UsageList:
        """Get API usage statistics.

        Returns usage data aggregated by request.

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
            # Get usage for the last 24 hours
            import time
            now = int(time.time())
            usage = client.get_usage(
                start_time=now - 86400,
                end_time=now
            )
            for record in usage.data:
                print(f"{record.model}: {record.usage.total_tokens} tokens")
            ```
        """
        from albert.types import UsageList

        params = {"limit": limit, "offset": offset}
        if start_time is not None:
            params["start_time"] = start_time
        if end_time is not None:
            params["end_time"] = end_time
        if endpoint is not None:
            params["endpoint"] = endpoint

        response = self._make_request("get", "/me/usage", params=params)
        response.raise_for_status()

        return UsageList(**response.json())

    # OCR & Parsing methods

    def ocr(
        self,
        document: dict[str, str] | str,
        model: str | None = None,
        pages: list[int] | None = None,
        include_image_base64: bool = False,
        image_limit: int | None = None,
        image_min_size: int | None = None,
        **kwargs,
    ) -> OCRResponse:
        """Perform OCR on a document with advanced options.

        Args:
            document: Document to OCR. Can be:
                - Dict with 'url', 'image_url', or 'document_url' key
                - Direct URL string
            model: Model to use for OCR (optional).
            pages: Specific pages to process (0-indexed).
            include_image_base64: Include base64-encoded images in response.
            image_limit: Max images to extract.
            image_min_size: Min size of images to extract.
            **kwargs: Additional OCR options.

        Returns:
            OCRResponse with pages, text, and optional bounding boxes.

        Raises:
            httpx.HTTPStatusError: If the OCR request fails.
        """
        from albert.types import OCRResponse

        # Build request body
        body = {}

        # Handle document parameter
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

        # Add any additional kwargs
        body.update(kwargs)

        response = self._make_request("post", "/ocr", json=body)
        response.raise_for_status()

        return OCRResponse(**response.json())

    def ocr_beta(
        self,
        file_path: str | Path,
        model: str,
        dpi: int = 150,
        prompt: str | None = None,
    ) -> ParsedDocument:
        """Perform simple file-based OCR (beta).

        Args:
            file_path: Path to the file to OCR.
            model: Model to use for OCR (required).
            dpi: DPI for rendering pages (100-600, default: 150).
            prompt: Custom prompt for OCR extraction.

        Returns:
            ParsedDocument with OCR results per page.

        Raises:
            httpx.HTTPStatusError: If the OCR request fails.
        """
        from pathlib import Path

        from albert.types import ParsedDocument

        file_path = Path(file_path)

        # Build form data
        form_data = {"model": model, "dpi": dpi}
        if prompt is not None:
            form_data["prompt"] = prompt

        # Open and upload file
        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f, "application/octet-stream")}
            response = self._make_request(
                "post", "/ocr-beta", data=form_data, files=files
            )
            response.raise_for_status()

        return ParsedDocument(**response.json())

    def parse(
        self,
        file_path: str | Path,
        force_ocr: bool = False,
        page_range: str = "",
    ) -> ParsedDocument:
        """Parse a document to markdown.

        Args:
            file_path: Path to the file to parse.
            force_ocr: Force OCR on all pages (default: False).
            page_range: Page range (e.g., "0,5-10,20"). Empty = all pages.

        Returns:
            ParsedDocument with parsed pages.

        Raises:
            httpx.HTTPStatusError: If the parsing fails.
        """
        from pathlib import Path

        from albert.types import ParsedDocument

        file_path = Path(file_path)

        # Build form data
        form_data = {
            "force_ocr": force_ocr,
            "page_range": page_range,
        }

        # Open and upload file
        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f, "application/octet-stream")}
            response = self._make_request(
                "post", "/parse-beta", data=form_data, files=files
            )
            response.raise_for_status()

        return ParsedDocument(**response.json())

    # File management (Deprecated)

    def upload_file(
        self, file_path: str | Path, purpose: str | None = None
    ) -> FileResponse:
        """[DEPRECATED] Upload a file to Albert API.

        This endpoint is deprecated. Use `upload_document` for RAG or `ocr_beta` for OCR.

        Args:
            file_path: Path to the file to upload.
            purpose: Purpose of the file upload (optional).

        Returns:
            FileResponse with file ID.

        Raises:
            httpx.HTTPStatusError: If the upload fails.
        """
        from pathlib import Path

        from albert.types import FileResponse

        file_path = Path(file_path)

        # Build form data
        form_data = {}
        # 'purpose' is not in the deprecated /v1/files spec body anymore,
        # but kept here if API still accepts it or for backward compat structure.
        # The spec shows 'request' JSON + 'file'.
        # For simplicity, sending multipart/form-data as before, but checking spec...
        # Spec says multipart/form-data with 'file' and 'request' ($ref FilesRequest).
        # We'll mimic the old behavior but warn it's deprecated.

        # Open and upload file
        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f, "application/octet-stream")}
            # If server creates 'request' param automatically or accepts loose form fields:
            if purpose:
                form_data["purpose"] = purpose

            response = self._make_request("post", "/files", data=form_data, files=files)
            response.raise_for_status()

        return FileResponse(**response.json())

    # Health & Monitoring

    def health_check(self) -> dict[str, Any]:
        """Check API health status.

        Returns:
            Dict with health info (schema undefined in spec).
        """
        response = self._make_request("get", "/health")
        response.raise_for_status()
        return response.json()

    def get_metrics(self) -> dict[str, Any]:
        """Get API metrics.

        Returns:
            Dict with metrics info (schema undefined in spec).
        """
        response = self._make_request("get", "/metrics")
        response.raise_for_status()
        return response.json()
