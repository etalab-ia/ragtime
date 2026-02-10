"""Albert Client - Official Python SDK for France's Albert API.

A sovereign AI platform providing OpenAI-compatible endpoints plus
French government-specific features like RAG search, collections management,
and carbon footprint tracking.
"""

# Third-party imports
from openai.types.chat import ChatCompletionMessageParam

# Local imports
from albert._async_client import AsyncAlbertClient
from albert._version import __version__
from albert.client import AlbertClient
from albert.types import (
    BoundingBox,
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
    OCRPageObject,
    OCRResponse,
    OCRText,
    OCRUsage,
    ParsedDocument,
    ParsedDocumentOutputFormat,
    ParsedDocumentPage,
    RerankResponse,
    RerankResult,
    SearchMethod,
    SearchResponse,
    SearchResult,
    Usage,
    UsageList,
    UsageRecord,
)


__all__ = [
    # Clients
    "AlbertClient",
    "AsyncAlbertClient",
    # OpenAI type re-exports
    "ChatCompletionMessageParam",
    # Search & Rerank types
    "Chunk",
    "ChunkList",
    "RerankResult",
    "RerankResponse",
    "SearchMethod",
    "SearchResult",
    "SearchResponse",
    "Usage",
    # Collections & Documents types
    "Collection",
    "CollectionList",
    "CollectionVisibility",
    "Document",
    "DocumentList",
    # Tools, Parsing & Monitoring types
    "BoundingBox",
    "FileUploadResponse",
    "HealthStatus",
    "MetricsData",
    "OCRPageObject",
    "OCRResponse",
    "OCRText",
    "OCRUsage",
    "ParsedDocument",
    "ParsedDocumentOutputFormat",
    "ParsedDocumentPage",
    "UsageList",
    "UsageRecord",
    # Metadata
    "__version__",
]
