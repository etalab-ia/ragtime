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
    CarbonFootprintUsage,
    CarbonFootprintUsageKgCO2eq,
    CarbonFootprintUsageKWh,
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
    MetadataFilterType,
    MetricsUsage,
    OCRImageObject,
    OCRPageDimensions,
    OCRPageObject,
    OCRResponse,
    OCRUsage,
    Rerank,
    RerankResponse,
    RerankResult,
    SearchMethod,
    SearchResponse,
    SearchResult,
    Usage,
    UsageDetail,
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
    "CarbonFootprintUsage",
    "CarbonFootprintUsageKgCO2eq",
    "CarbonFootprintUsageKWh",
    "Chunk",
    "ChunkInput",
    "ChunkList",
    "CompoundMetadataFilter",
    "MetadataFilter",
    "MetadataFilterType",
    "Rerank",
    "RerankResponse",
    "RerankResult",
    "SearchMethod",
    "SearchResponse",
    "SearchResult",
    "Usage",
    # Collections & Documents types
    "Collection",
    "CollectionList",
    "CollectionVisibility",
    "Document",
    "DocumentList",
    "DocumentResponse",
    # OCR & Monitoring types
    "MetricsUsage",
    "OCRImageObject",
    "OCRPageDimensions",
    "OCRPageObject",
    "OCRResponse",
    "OCRUsage",
    "UsageDetail",
    "UsageList",
    "UsageRecord",
    # Metadata
    "__version__",
]
