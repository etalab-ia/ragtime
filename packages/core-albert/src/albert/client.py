"""Main Albert Client implementation."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from openai import OpenAI


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
        FileUploadResponse,
        HealthStatus,
        MetricsData,
        OCRResponse,
        ParsedDocument,
        ParsedDocumentOutputFormat,
        RerankResponse,
        SearchResponse,
        UsageList,
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

        # Albert-specific endpoints (coming in Phase 2+)
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

        # Albert-Specific Resources (will be implemented in Phase 2+)
        # self.collections = Collections(self._client)
        # self.documents = Documents(self._client)
        # self.tools = Tools(self._client)
        # self.management = Management(self._client)

    @property
    def api_key(self) -> str:
        """Get the API key."""
        return self._client.api_key

    @property
    def base_url(self) -> str:
        """Get the base URL."""
        return str(self._client.base_url)

    # Phase 2: Search and Rerank methods

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
                prompt="Loi Énergie Climat",
                collections=["col_123"],
                limit=5,
                method="hybrid"
            )
            for result in results.data:
                print(f"Score: {result.score:.3f}")
                print(f"Content: {result.chunk.content[:100]}...")
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

        # Make request using internal httpx client
        response = self._client._client.post("/search", json=body)
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
        Useful for improving RAG retrieval quality.

        Args:
            query: The search query to rank documents against.
            documents: List of document texts to rerank.
            model: Reranker model to use (e.g., "BAAI/bge-reranker-v2-m3").
            top_n: Return only top N results. If None, returns all documents.

        Returns:
            RerankResponse with reranked results and scores.

        Raises:
            httpx.HTTPStatusError: If the API request fails.

        Example:
            ```python
            results = client.rerank(
                query="transition énergétique",
                documents=[
                    "La loi Énergie Climat vise à...",
                    "Le changement climatique est...",
                    "Les énergies renouvelables..."
                ],
                model="BAAI/bge-reranker-v2-m3",
                top_n=2
            )
            for result in results.results:
                print(f"Rank {result.index}: Score {result.relevance_score:.3f}")
            ```
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

        # Make request using internal httpx client
        response = self._client._client.post("/rerank", json=body)
        response.raise_for_status()

        # Parse and return Pydantic model
        return RerankResponse(**response.json())

    # Phase 3: Collections methods

    def create_collection(
        self,
        name: str,
        description: str | None = None,
        visibility: CollectionVisibility = "private",
    ) -> Collection:
        """Create a new RAG collection.

        Collections organize documents for semantic search. Each collection has its
        own embedding model and access permissions.

        Args:
            name: Name of the collection (required).
            description: Optional description of the collection.
            visibility: "private" (owner only) or "public" (all users). Defaults to "private".

        Returns:
            Collection object with ID and metadata.

        Raises:
            httpx.HTTPStatusError: If the API request fails.

        Example:
            ```python
            collection = client.create_collection(
                name="French Legal Documents",
                description="Collection of French government legal texts",
                visibility="private"
            )
            print(f"Created collection {collection.id}")
            ```
        """
        from albert.types import Collection

        # Build request body
        body = {"name": name, "visibility": visibility}
        if description is not None:
            body["description"] = description

        # Make request
        response = self._client._client.post("/collections", json=body)
        response.raise_for_status()

        return Collection(**response.json())

    def list_collections(self) -> CollectionList:
        """List all accessible collections.

        Returns collections owned by the user plus any public collections.

        Returns:
            CollectionList containing all accessible collections.

        Raises:
            httpx.HTTPStatusError: If the API request fails.

        Example:
            ```python
            collections = client.list_collections()
            for collection in collections.data:
                print(f"{collection.name}: {collection.documents} documents")
            ```
        """
        from albert.types import CollectionList

        response = self._client._client.get("/collections")
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

        Example:
            ```python
            collection = client.get_collection(123)
            print(f"Collection: {collection.name}")
            print(f"Documents: {collection.documents}")
            ```
        """
        from albert.types import Collection

        response = self._client._client.get(f"/collections/{collection_id}")
        response.raise_for_status()

        return Collection(**response.json())

    def update_collection(
        self,
        collection_id: int,
        name: str | None = None,
        description: str | None = None,
        visibility: CollectionVisibility | None = None,
    ) -> Collection:
        """Update a collection's metadata.

        Only the collection owner can update it. At least one field must be provided.

        Args:
            collection_id: The collection ID to update.
            name: New name for the collection (optional).
            description: New description (optional).
            visibility: New visibility setting (optional).

        Returns:
            Updated Collection object.

        Raises:
            httpx.HTTPStatusError: If the update fails or user lacks permission.

        Example:
            ```python
            updated = client.update_collection(
                123,
                name="Updated Collection Name",
                visibility="public"
            )
            ```
        """
        from albert.types import Collection

        # Build request body with only provided fields
        body = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if visibility is not None:
            body["visibility"] = visibility

        response = self._client._client.patch(
            f"/collections/{collection_id}", json=body
        )
        response.raise_for_status()

        return Collection(**response.json())

    def delete_collection(self, collection_id: int) -> None:
        """Delete a collection and all its documents.

        Only the collection owner can delete it. This action is irreversible.

        Args:
            collection_id: The collection ID to delete.

        Raises:
            httpx.HTTPStatusError: If the deletion fails or user lacks permission.

        Example:
            ```python
            client.delete_collection(123)
            print("Collection deleted")
            ```
        """
        response = self._client._client.delete(f"/collections/{collection_id}")
        response.raise_for_status()

    # Phase 3: Documents methods

    def upload_document(
        self,
        file_path: str | Path,
        collection_id: int,
        chunk_size: int = 2048,
        chunk_overlap: int = 0,
        **kwargs,
    ) -> Document:
        """Upload a document to a collection.

        The document will be parsed, chunked, and embedded according to the collection's
        settings. Supports PDF, DOCX, TXT, and other common formats.

        Args:
            file_path: Path to the file to upload.
            collection_id: The collection ID to add the document to.
            chunk_size: Size of text chunks for embedding (default: 2048).
            chunk_overlap: Overlap between chunks (default: 0).
            **kwargs: Additional upload parameters (page_range, force_ocr, etc.).

        Returns:
            Document object with ID and metadata.

        Raises:
            httpx.HTTPStatusError: If the upload fails.

        Example:
            ```python
            doc = client.upload_document(
                file_path="./legal_doc.pdf",
                collection_id=123,
                chunk_size=1024
            )
            print(f"Uploaded document {doc.id} with {doc.chunks} chunks")
            ```
        """
        from pathlib import Path

        from albert.types import Document

        # Convert to Path object
        file_path = Path(file_path)

        # Build form data
        form_data = {
            "collection": collection_id,
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
        }
        # Add any additional parameters
        form_data.update(kwargs)

        # Open and upload file
        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f, "application/octet-stream")}
            response = self._client._client.post(
                "/documents", data=form_data, files=files
            )
            response.raise_for_status()

        return Document(**response.json())

    def list_documents(self, collection_id: int | None = None) -> DocumentList:
        """List documents in a collection or all accessible documents.

        Args:
            collection_id: Filter to specific collection. If None, returns all accessible documents.

        Returns:
            DocumentList containing matching documents.

        Raises:
            httpx.HTTPStatusError: If the request fails.

        Example:
            ```python
            # List all documents in a collection
            docs = client.list_documents(collection_id=123)
            for doc in docs.data:
                print(f"{doc.name}: {doc.chunks} chunks")

            # List all accessible documents
            all_docs = client.list_documents()
            ```
        """
        from albert.types import DocumentList

        params = {}
        if collection_id is not None:
            params["collection"] = collection_id

        response = self._client._client.get("/documents", params=params)
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

        Example:
            ```python
            doc = client.get_document(456)
            print(f"Document: {doc.name}")
            print(f"Chunks: {doc.chunks}")
            ```
        """
        from albert.types import Document

        response = self._client._client.get(f"/documents/{document_id}")
        response.raise_for_status()

        return Document(**response.json())

    def delete_document(self, document_id: int) -> None:
        """Delete a document and all its chunks.

        This action is irreversible. The document's embeddings will also be removed.

        Args:
            document_id: The document ID to delete.

        Raises:
            httpx.HTTPStatusError: If the deletion fails.

        Example:
            ```python
            client.delete_document(456)
            print("Document deleted")
            ```
        """
        response = self._client._client.delete(f"/documents/{document_id}")
        response.raise_for_status()

    # Phase 3: Chunks methods

    def list_chunks(self, document_id: int) -> ChunkList:
        """List all chunks for a specific document.

        Returns the text chunks that were created when the document was uploaded.

        Args:
            document_id: The document ID.

        Returns:
            ChunkList containing all chunks for the document.

        Raises:
            httpx.HTTPStatusError: If the request fails.

        Example:
            ```python
            chunks = client.list_chunks(document_id=456)
            for chunk in chunks.data:
                print(f"Chunk {chunk.id}: {chunk.content[:100]}...")
            ```
        """
        from albert.types import ChunkList

        response = self._client._client.get(f"/chunks/{document_id}")
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

        Example:
            ```python
            chunk = client.get_chunk(document_id=456, chunk_id=123)
            print(chunk.content)
            print(chunk.metadata)
            ```
        """
        from albert.types import Chunk

        response = self._client._client.get(f"/chunks/{document_id}/{chunk_id}")
        response.raise_for_status()

        return Chunk(**response.json())

    # Phase 4: Usage tracking

    def get_usage(
        self, start_date: str | None = None, end_date: str | None = None
    ) -> UsageList:
        """Get API usage statistics.

        Returns usage data (tokens, cost, carbon) aggregated by date.

        Args:
            start_date: Filter from this date (ISO format YYYY-MM-DD). Optional.
            end_date: Filter until this date (ISO format YYYY-MM-DD). Optional.

        Returns:
            UsageList with usage records per date.

        Raises:
            httpx.HTTPStatusError: If the request fails.

        Example:
            ```python
            # Get all usage
            usage = client.get_usage()
            for record in usage.data:
                print(f"{record.date}: {record.total_tokens} tokens, ${record.cost}")

            # Get usage for date range
            usage = client.get_usage(start_date="2024-01-01", end_date="2024-01-31")
            ```
        """
        from albert.types import UsageList

        params = {}
        if start_date is not None:
            params["start_date"] = start_date
        if end_date is not None:
            params["end_date"] = end_date

        response = self._client._client.get("/me/usage", params=params)
        response.raise_for_status()

        return UsageList(**response.json())

    # Phase 4: OCR & Parsing methods

    def ocr(
        self,
        document: dict[str, str] | str,
        model: str | None = None,
        pages: list[int] | None = None,
        include_image_base64: bool = False,
        **kwargs,
    ) -> OCRResponse:
        """Perform OCR on a document with advanced options.

        Advanced OCR with support for JSON mode, bounding boxes, and image extraction.

        Args:
            document: Document to OCR. Can be:
                - Dict with 'url' key for document URL
                - Dict with 'image_url' key for image URL
                - Direct URL string
            model: Model to use for OCR (optional).
            pages: Specific pages to process (0-indexed). If None, processes all pages.
            include_image_base64: Include base64-encoded images in response.
            **kwargs: Additional OCR options (bbox_annotation_format,
                document_annotation_format, etc.).

        Returns:
            OCRResponse with pages, text, and optional bounding boxes.

        Raises:
            httpx.HTTPStatusError: If the OCR request fails.

        Example:
            ```python
            # OCR from URL
            result = client.ocr(
                document="https://example.com/doc.pdf",
                pages=[0, 1, 2],
                include_image_base64=True
            )
            for page in result.pages:
                print(f"Page {page.page}: {page.text}")
            ```
        """
        from albert.types import OCRResponse

        # Build request body
        body = {}

        # Handle document parameter
        if isinstance(document, str):
            body["document"] = {"url": document}
        else:
            body["document"] = document

        if model is not None:
            body["model"] = model
        if pages is not None:
            body["pages"] = pages
        if include_image_base64:
            body["include_image_base64"] = include_image_base64

        # Add any additional kwargs
        body.update(kwargs)

        response = self._client._client.post("/ocr", json=body)
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

        Simpler OCR method that takes a file and returns parsed text.

        Args:
            file_path: Path to the file to OCR.
            model: Model to use for OCR (required).
            dpi: DPI for rendering pages as images (100-600, default: 150).
            prompt: Custom prompt for OCR extraction (optional).

        Returns:
            ParsedDocument with OCR results per page.

        Raises:
            httpx.HTTPStatusError: If the OCR request fails.

        Example:
            ```python
            result = client.ocr_beta(
                file_path="./scanned_doc.pdf",
                model="gpt-4o-mini",
                dpi=300
            )
            for page in result.data:
                print(f"Page {page.page}: {page.content}")
            ```
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
            response = self._client._client.post(
                "/ocr-beta", data=form_data, files=files
            )
            response.raise_for_status()

        return ParsedDocument(**response.json())

    def parse(
        self,
        file_path: str | Path,
        output_format: ParsedDocumentOutputFormat = "markdown",
        force_ocr: bool = False,
        page_range: str = "",
        paginate_output: bool = False,
    ) -> ParsedDocument:
        """Parse a document to markdown, JSON, or HTML.

        Extract and convert document content to structured format.

        Args:
            file_path: Path to the file to parse.
            output_format: Output format - "markdown", "json", or "html" (default: "markdown").
            force_ocr: Force OCR on all pages (default: False).
            page_range: Page range to convert (e.g., "0,5-10,20"). Empty = all pages.
            paginate_output: Separate pages with horizontal rules containing page numbers.

        Returns:
            ParsedDocument with parsed pages.

        Raises:
            httpx.HTTPStatusError: If the parsing fails.

        Example:
            ```python
            # Parse to markdown
            result = client.parse(
                file_path="./document.pdf",
                output_format="markdown",
                page_range="0-5"
            )
            for page in result.data:
                print(f"Page {page.page}:")
                print(page.content)
            ```
        """
        from pathlib import Path

        from albert.types import ParsedDocument

        file_path = Path(file_path)

        # Build form data
        form_data = {
            "output_format": output_format,
            "force_ocr": force_ocr,
            "page_range": page_range,
            "paginate_output": paginate_output,
        }

        # Open and upload file
        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f, "application/octet-stream")}
            response = self._client._client.post(
                "/parse-beta", data=form_data, files=files
            )
            response.raise_for_status()

        return ParsedDocument(**response.json())

    # Phase 4: File management

    def upload_file(
        self, file_path: str | Path, purpose: str | None = None
    ) -> FileUploadResponse:
        """Upload a file to Albert API.

        Generic file upload (different from uploading documents to collections).

        Args:
            file_path: Path to the file to upload.
            purpose: Purpose of the file upload (optional).

        Returns:
            FileUploadResponse with file ID and metadata.

        Raises:
            httpx.HTTPStatusError: If the upload fails.

        Example:
            ```python
            result = client.upload_file(
                file_path="./data.json",
                purpose="analysis"
            )
            print(f"Uploaded file ID: {result.id}")
            ```
        """
        from pathlib import Path

        from albert.types import FileUploadResponse

        file_path = Path(file_path)

        # Build form data
        form_data = {}
        if purpose is not None:
            form_data["purpose"] = purpose

        # Open and upload file
        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f, "application/octet-stream")}
            response = self._client._client.post("/files", data=form_data, files=files)
            response.raise_for_status()

        return FileUploadResponse(**response.json())

    # Phase 4: Health & Monitoring

    def health_check(self) -> HealthStatus:
        """Check API health status.

        Returns:
            HealthStatus with current API status.

        Raises:
            httpx.HTTPStatusError: If the health check fails.

        Example:
            ```python
            health = client.health_check()
            print(f"API Status: {health.status}")
            ```
        """
        from albert.types import HealthStatus

        response = self._client._client.get("/health")
        response.raise_for_status()

        return HealthStatus(**response.json())

    def get_metrics(self) -> MetricsData:
        """Get API metrics.

        Returns performance and usage metrics for the API.

        Returns:
            MetricsData with API metrics.

        Raises:
            httpx.HTTPStatusError: If the metrics request fails.

        Example:
            ```python
            metrics = client.get_metrics()
            print(f"Requests/sec: {metrics.requests_per_second}")
            print(f"Avg latency: {metrics.average_latency_ms}ms")
            ```
        """
        from albert.types import MetricsData

        response = self._client._client.get("/metrics")
        response.raise_for_status()

        return MetricsData(**response.json())
