"""Pydantic models for RAG Facile configuration.

This module defines the complete configuration schema for the RAG pipeline,
covering all phases from document ingestion to response formatting.

It also provides pipeline metadata (`PIPELINE_STAGES`) that defines the logical
ordering and descriptions of each pipeline step, used by `config show` to present
configuration in a way that teaches users about the RAG pipeline.
"""

from dataclasses import dataclass
from typing import Any, Literal, TypedDict

from pydantic import BaseModel, Field


# ==============================================================================
# SHARED TYPES
# ==============================================================================


class RetrievedChunk(TypedDict):
    """A retrieved chunk with score and source metadata.

    This type is shared across pipeline phase packages (retrieval,
    reranking, context) and lives here to avoid inter-phase dependencies.
    """

    content: str
    score: float
    source_file: str | None
    page: int | None
    collection_id: int
    document_id: int
    chunk_id: int


# ==============================================================================
# META
# ==============================================================================


class MetaConfig(BaseModel):
    """Metadata about the configuration file."""

    schema_version: str = Field(
        default="1.0.0",
        description="Configuration schema version for migrations",
    )
    preset: str = Field(
        default="balanced",
        description="Active preset (fast, balanced, accurate, legal, hr)",
    )


# ==============================================================================
# EVALUATION DATASET GENERATION
# ==============================================================================


class EvalConfig(BaseModel):
    """Configuration for evaluation: dataset generation and scoring."""

    provider: Literal["letta", "albert"] = Field(
        default="albert",
        description="Data Foundry provider (letta or albert)",
    )
    target_samples: int = Field(
        default=50,
        ge=1,
        le=1000,
        description="Target number of Q/A pairs to generate",
    )
    output_format: Literal["jsonl"] = Field(
        default="jsonl",
        description="Output format (currently only JSONL supported)",
    )
    data_dir: str = Field(
        default="data",
        description="Root directory for evaluation assets (datasets, traces, logs)",
    )
    inspect_log_dir: str = Field(
        default="data/evals/logs",
        description="Directory for Inspect AI evaluation logs",
    )
    generation_model: str = Field(
        default="openweight-large",
        description="Model for dataset generation (uses openweight-large for best Q/A quality)",
    )


# ==============================================================================
# DOCUMENT INGESTION
# ==============================================================================


class OCRConfig(BaseModel):
    """OCR settings for scanned documents."""

    enabled: bool = Field(
        default=True,
        description="Enable OCR for scanned PDFs",
    )
    dpi: int = Field(
        default=300,
        ge=72,
        le=600,
        description="DPI for OCR processing",
    )
    extract_images: bool = Field(
        default=False,
        description="Extract and process images separately",
    )
    include_bounding_boxes: bool = Field(
        default=False,
        description="Include bounding box coordinates in output",
    )


class ParsingConfig(BaseModel):
    """Document parsing settings."""

    output_format: Literal["markdown", "json", "html"] = Field(
        default="markdown",
        description="Output format for parsed documents",
    )
    preserve_structure: bool = Field(
        default=True,
        description="Preserve document structure (headings, lists, tables)",
    )
    include_page_numbers: bool = Field(
        default=True,
        description="Include page numbers in output",
    )


class IngestionConfig(BaseModel):
    """Configuration for document ingestion and pre-processing."""

    provider: Literal["local"] = Field(
        default="local",
        description="Document parsing provider (local pypdf). "
        "Note: 'albert' provider was removed in albert-client 0.4.1 — "
        "use AlbertPipeline for server-side document ingestion instead.",
    )
    file_types: list[str] = Field(
        default=[".pdf", ".md", ".txt"],
        description="Supported file extensions",
    )
    ocr: OCRConfig = Field(
        default_factory=OCRConfig,
        description="OCR settings",
    )
    parsing: ParsingConfig = Field(
        default_factory=ParsingConfig,
        description="Parsing settings",
    )


# ==============================================================================
# DOCUMENT CHUNKING
# ==============================================================================


class ChunkingConfig(BaseModel):
    """Configuration for document chunking."""

    strategy: Literal["fixed-size", "semantic", "sentence", "paragraph"] = Field(
        default="semantic",
        description="Chunking strategy",
    )
    chunk_size: int = Field(
        default=1024,
        ge=64,
        le=4096,
        description="Chunk size in tokens (semantic) or characters (fixed-size)",
    )
    chunk_overlap: int = Field(
        default=100,
        ge=0,
        le=512,
        description="Overlap between chunks in tokens/characters",
    )
    preserve_metadata: bool = Field(
        default=True,
        description="Preserve document metadata (title, headers, page numbers)",
    )


# ==============================================================================
# EMBEDDING GENERATION
# ==============================================================================


class EmbeddingConfig(BaseModel):
    """Configuration for embedding generation."""

    model: str = Field(
        default="openweight-embeddings",
        description="Embedding model alias",
    )
    batch_size: int = Field(
        default=32,
        ge=1,
        le=128,
        description="Batch size for embedding generation",
    )
    normalization: Literal["L2", "none"] = Field(
        default="L2",
        description="Vector normalization method",
    )


# ==============================================================================
# VECTOR STORAGE / INDEX
# ==============================================================================


class StorageConfig(BaseModel):
    """Configuration for vector storage."""

    provider: Literal["albert-collections", "local-sqlite"] = Field(
        default="albert-collections",
        description="Vector store provider",
    )
    collection_naming: Literal["workspace", "app", "custom"] = Field(
        default="workspace",
        description="Collection naming strategy",
    )
    distance_metric: Literal["cosine", "euclidean", "dot-product"] = Field(
        default="cosine",
        description="Distance metric for similarity search",
    )
    collections: list[int] = Field(
        default=[],
        description="Albert collection IDs to search (e.g., public MediaTech collections)",
    )


# ==============================================================================
# QUERY EXPANSION
# ==============================================================================


class QueryExpansionConfig(BaseModel):
    """Configuration for query expansion before retrieval.

    Query expansion bridges the vocabulary gap between colloquial user queries
    (acronyms, slang) and the formal language of indexed official documents.

    The default strategy is ``"none"`` — expansion is opt-in.

    Enable in ``ragfacile.toml``::

        [query]
        strategy = "multi_query"
        num_variations = 3
        include_original = true
        model = "openweight-medium"
    """

    # ── Legacy flags (kept for backward compatibility) ──
    rewrite_enabled: bool = Field(
        default=False,
        description="Enable query rewriting for poorly phrased queries",
    )
    expand_enabled: bool = Field(
        default=False,
        description="Enable query expansion (synonyms, related terms)",
    )
    spell_check: bool = Field(
        default=False,
        description="Enable spell checking and correction",
    )

    # ── Strategy-based expansion ──
    strategy: Literal["multi_query", "hyde", "none"] = Field(
        default="none",
        description=(
            'Expansion strategy: "multi_query" generates N formal French variations, '
            '"hyde" generates a hypothetical administrative document for embedding, '
            '"none" disables expansion (default).'
        ),
    )
    num_variations: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Number of query variations to generate (multi_query only)",
    )
    model: str = Field(
        default="openweight-medium",
        description="LLM model alias used for query expansion",
    )
    include_original: bool = Field(
        default=True,
        description=(
            "Always include the original query alongside generated expansions. "
            "Recommended: keeps single-query recall as a safety net."
        ),
    )


# Backward-compatible alias
QueryConfig = QueryExpansionConfig


# ==============================================================================
# RETRIEVAL
# ==============================================================================


class HybridRetrievalConfig(BaseModel):
    """Hybrid search specific settings."""

    alpha: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Hybrid balance: 0.0=lexical only, 0.5=balanced, 1.0=semantic only",
    )


class RetrievalConfig(BaseModel):
    """Configuration for retrieval."""

    provider: Literal["albert", "none"] = Field(
        default="albert",
        description='Retrieval provider ("albert" or "none" to skip retrieval)',
    )
    strategy: Literal["hybrid", "semantic", "lexical"] = Field(
        default="hybrid",
        description="Retrieval strategy",
    )
    top_k: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of results to retrieve",
    )
    score_threshold: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum relevance score (0.0-1.0)",
    )
    hybrid: HybridRetrievalConfig = Field(
        default_factory=HybridRetrievalConfig,
        description="Hybrid search settings",
    )


# ==============================================================================
# RERANKING
# ==============================================================================


class RerankingConfig(BaseModel):
    """Configuration for result reranking."""

    provider: Literal["albert"] = Field(
        default="albert",
        description="Reranking provider (currently only 'albert' supported)",
    )
    enabled: bool = Field(
        default=True,
        description="Enable reranking (improves precision at cost of latency)",
    )
    model: str = Field(
        default="openweight-rerank",
        description="Reranking model alias",
    )
    top_n: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Final number of results after reranking",
    )


# ==============================================================================
# CONTEXT SELECTION
# ==============================================================================


class ContextConfig(BaseModel):
    """Configuration for context selection."""

    strategy: Literal["top-n", "threshold", "token-budget"] = Field(
        default="token-budget",
        description="Context selection strategy",
    )
    max_tokens: int = Field(
        default=4096,
        ge=512,
        le=32768,
        description="Maximum tokens for context window",
    )
    deduplicate: bool = Field(
        default=True,
        description="Remove duplicate or highly similar chunks",
    )
    ordering: Literal["by-score", "by-document", "by-date"] = Field(
        default="by-score",
        description="Ordering of context chunks",
    )


# ==============================================================================
# RESPONSE GENERATION
# ==============================================================================


class GenerationConfig(BaseModel):
    """Configuration for LLM response generation."""

    model: str = Field(
        default="openweight-medium",
        description="LLM model (openweight-small, openweight-medium, openweight-large)",
    )
    temperature: float = Field(
        default=0.2,
        ge=0.0,
        le=2.0,
        description="Temperature (0.0=deterministic, 1.0=balanced, 2.0=creative)",
    )
    max_tokens: int = Field(
        default=1024,
        ge=64,
        le=8192,
        description="Maximum tokens in response",
    )
    streaming: bool = Field(
        default=True,
        description="Enable streaming responses",
    )
    system_prompt: str = Field(
        default=(
            "You are a helpful assistant for the French government. "
            "Answer questions based on the provided context. "
            "Always cite your sources using [1], [2], etc."
        ),
        description="System prompt template",
    )


# ==============================================================================
# HALLUCINATION DETECTION
# ==============================================================================


class HallucinationConfig(BaseModel):
    """Configuration for hallucination detection."""

    enabled: bool = Field(
        default=False,
        description="Enable hallucination detection",
    )
    strategy: Literal["entailment", "fact-check", "citation-check"] = Field(
        default="citation-check",
        description="Detection strategy",
    )
    threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Confidence threshold (0.0-1.0)",
    )
    fallback: Literal["warn", "reject", "regenerate"] = Field(
        default="warn",
        description="Fallback behavior when hallucination detected",
    )


# ==============================================================================
# ANSWER FORMATTING
# ==============================================================================


class CitationsConfig(BaseModel):
    """Citation settings for context markers and source attribution."""

    enabled: bool = Field(
        default=True,
        description="Include source citations ([1], [2], ...) in context",
    )
    style: Literal["inline", "footnote"] = Field(
        default="inline",
        description="Citation style (inline or footnote)",
    )
    include_sources: bool = Field(
        default=True,
        description="Append source list (URLs, document names) to the response",
    )


class FormattingConfig(BaseModel):
    """Configuration for answer formatting."""

    output_format: Literal["markdown", "html", "plain-text"] = Field(
        default="markdown",
        description="Output format",
    )
    include_confidence: bool = Field(
        default=False,
        description="Include confidence scores",
    )
    language: Literal["fr", "en"] = Field(
        default="fr",
        description="Response language",
    )
    citations: CitationsConfig = Field(
        default_factory=CitationsConfig,
        description="Citation and source attribution settings",
    )


# ==============================================================================
# TRACING & OBSERVABILITY
# ==============================================================================


class TracingConfig(BaseModel):
    """Configuration for pipeline tracing and observability.

    Traces capture queries, retrieved chunks, LLM responses, and user
    feedback for debugging, tuning, and evaluation.
    """

    enabled: bool = Field(
        default=True,
        description="Enable trace logging for RAG queries",
    )
    provider: Literal["sqlite", "postgres", "none"] = Field(
        default="sqlite",
        description='Trace storage backend ("sqlite" built-in, "postgres" for Supabase/PostgreSQL, "none" disabled)',
    )
    database: str = Field(
        default=".rag-facile/traces.db",
        description="SQLite database path (relative to workspace root)",
    )
    connection_string: str = Field(
        default="",
        description="PostgreSQL connection string (used when provider is 'postgres'). "
        "Typically set via DATABASE_URL environment variable.",
    )


# ==============================================================================
# PERSISTENCE (Conversation & Data Layer)
# ==============================================================================


class PersistenceConfig(BaseModel):
    """Configuration for conversation persistence and data layer.

    Persistence stores conversation history, user sessions, and feedback
    in a PostgreSQL database (e.g., Supabase). This enables multi-user
    support, conversation resumption, and audit trails.

    The connection string should be set via the DATABASE_URL environment
    variable for security (keeps credentials out of config files).
    """

    provider: Literal["none", "postgres"] = Field(
        default="none",
        description='Persistence provider ("none" disabled, "postgres" for Supabase/PostgreSQL)',
    )
    connection_string: str = Field(
        default="",
        description="PostgreSQL connection string (used when provider is 'postgres'). "
        "Typically set via DATABASE_URL environment variable.",
    )


# ==============================================================================
# ROOT CONFIG
# ==============================================================================


class RAGConfig(BaseModel):
    """Complete RAG pipeline configuration.

    This model represents the entire ragfacile.toml configuration file,
    covering all phases of the RAG pipeline from document ingestion to
    response formatting.

    Example:
        >>> import tomllib
        >>> with open("ragfacile.toml", "rb") as f:
        ...     config_dict = tomllib.load(f)
        >>> config = RAGConfig(**config_dict)
        >>> print(config.generation.model)
        'openweight-medium'
    """

    meta: MetaConfig = Field(
        default_factory=MetaConfig,
        description="Metadata and versioning",
    )
    eval: EvalConfig = Field(
        default_factory=EvalConfig,
        description="Evaluation dataset generation",
    )
    ingestion: IngestionConfig = Field(
        default_factory=IngestionConfig,
        description="Document ingestion and pre-processing",
    )
    chunking: ChunkingConfig = Field(
        default_factory=ChunkingConfig,
        description="Document chunking",
    )
    embedding: EmbeddingConfig = Field(
        default_factory=EmbeddingConfig,
        description="Embedding generation",
    )
    storage: StorageConfig = Field(
        default_factory=StorageConfig,
        description="Vector storage",
    )
    query: QueryExpansionConfig = Field(
        default_factory=QueryExpansionConfig,
        description="Query expansion",
    )
    retrieval: RetrievalConfig = Field(
        default_factory=RetrievalConfig,
        description="Retrieval",
    )
    reranking: RerankingConfig = Field(
        default_factory=RerankingConfig,
        description="Reranking",
    )
    context: ContextConfig = Field(
        default_factory=ContextConfig,
        description="Context selection",
    )
    generation: GenerationConfig = Field(
        default_factory=GenerationConfig,
        description="Response generation",
    )
    hallucination: HallucinationConfig = Field(
        default_factory=HallucinationConfig,
        description="Hallucination detection",
    )
    formatting: FormattingConfig = Field(
        default_factory=FormattingConfig,
        description="Answer formatting",
    )
    tracing: TracingConfig = Field(
        default_factory=TracingConfig,
        description="Pipeline tracing and observability",
    )
    persistence: PersistenceConfig = Field(
        default_factory=PersistenceConfig,
        description="Conversation persistence and data layer",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "meta": {"schema_version": "1.0.0", "preset": "balanced"},
                    "generation": {
                        "model": "openweight-medium",
                        "temperature": 0.7,
                        "max_tokens": 1024,
                    },
                    "retrieval": {
                        "strategy": "hybrid",
                        "top_k": 10,
                        "hybrid": {"alpha": 0.5},
                    },
                }
            ]
        }
    }


# ==============================================================================
# PIPELINE METADATA
# ==============================================================================


@dataclass(frozen=True)
class PipelineStage:
    """Metadata for a RAG pipeline stage, used by ``config show``.

    Each stage maps to a section in ``ragfacile.toml`` and carries display
    metadata so the CLI can present configuration in pipeline order with
    educational descriptions.
    """

    key: str
    """Config section key (e.g., ``"ingestion"``)."""

    title: str
    """Human-readable title (e.g., ``"Document Ingestion"``)."""

    description: str
    """One-line explanation of what this pipeline step does."""

    emoji: str
    """Visual indicator displayed next to the step number."""

    model: type[BaseModel]
    """Pydantic model class for this section (enables field introspection)."""


PIPELINE_STAGES: list[PipelineStage] = [
    PipelineStage(
        key="ingestion",
        title="Document Ingestion",
        description="Load and pre-process documents (PDF, Markdown, text) with optional OCR.",
        emoji="\U0001f4c4",
        model=IngestionConfig,
    ),
    PipelineStage(
        key="chunking",
        title="Document Chunking",
        description="Split documents into smaller, semantically meaningful chunks for indexing.",
        emoji="\u2702\ufe0f",
        model=ChunkingConfig,
    ),
    PipelineStage(
        key="embedding",
        title="Embedding Generation",
        description="Convert text chunks into vector representations for similarity search.",
        emoji="\U0001f522",
        model=EmbeddingConfig,
    ),
    PipelineStage(
        key="storage",
        title="Vector Storage",
        description="Store and index embedding vectors for efficient retrieval.",
        emoji="\U0001f4be",
        model=StorageConfig,
    ),
    PipelineStage(
        key="query",
        title="Query Expansion",
        description=(
            "Expand user queries into formal French administrative vocabulary "
            "before retrieval (multi-query or HyDE strategies)."
        ),
        emoji="\U0001f50d",
        model=QueryExpansionConfig,
    ),
    PipelineStage(
        key="retrieval",
        title="Retrieval",
        description="Search the vector store to find the most relevant document chunks.",
        emoji="\U0001f4e5",
        model=RetrievalConfig,
    ),
    PipelineStage(
        key="reranking",
        title="Reranking",
        description="Re-score retrieved chunks with a cross-encoder for higher precision.",
        emoji="\U0001f3c6",
        model=RerankingConfig,
    ),
    PipelineStage(
        key="context",
        title="Context Assembly",
        description="Select, deduplicate, and format retrieved chunks into a context window.",
        emoji="\U0001f4cb",
        model=ContextConfig,
    ),
    PipelineStage(
        key="generation",
        title="Response Generation",
        description="Generate an answer from the assembled context using an LLM.",
        emoji="\U0001f4ac",
        model=GenerationConfig,
    ),
    PipelineStage(
        key="tracing",
        title="Tracing & Observability",
        description="Log queries, retrieved context, responses, and user feedback for pipeline improvement.",
        emoji="\U0001f50d",
        model=TracingConfig,
    ),
    PipelineStage(
        key="persistence",
        title="Persistence & Data Layer",
        description="Store conversation history, user sessions, and feedback in PostgreSQL for multi-user support.",
        emoji="\U0001f4be",
        model=PersistenceConfig,
    ),
    PipelineStage(
        key="hallucination",
        title="Hallucination Detection",
        description="Verify the generated response is grounded in the provided context.",
        emoji="\U0001f6e1\ufe0f",
        model=HallucinationConfig,
    ),
    PipelineStage(
        key="formatting",
        title="Answer Formatting",
        description="Format the final response (Markdown, HTML, citations, language).",
        emoji="\u2728",
        model=FormattingConfig,
    ),
    PipelineStage(
        key="eval",
        title="Evaluation",
        description="Generate synthetic Q/A datasets to measure RAG pipeline quality.",
        emoji="\U0001f4ca",
        model=EvalConfig,
    ),
]


def flatten_model_fields(
    model_instance: BaseModel,
    prefix: str = "",
) -> list[tuple[str, Any, str]]:
    """Flatten a Pydantic model into ``(key, value, description)`` tuples.

    Nested :class:`BaseModel` fields are recursed with dot-separated keys.

    Args:
        model_instance: An instantiated Pydantic model.
        prefix: Dot prefix for nested fields (used internally during recursion).

    Returns:
        List of ``(dotted_key, value, description)`` tuples.

    Example:
        >>> from rag_facile.core.schema import IngestionConfig, flatten_model_fields
        >>> rows = flatten_model_fields(IngestionConfig())
        >>> rows[0]
        ('file_types', ['.pdf', '.md', '.txt'], 'Supported file extensions')
    """
    rows: list[tuple[str, Any, str]] = []

    for field_name, field_info in model_instance.model_fields.items():
        value = getattr(model_instance, field_name)
        dotted_key = f"{prefix}.{field_name}" if prefix else field_name
        description = field_info.description or ""

        if isinstance(value, BaseModel):
            # Recurse into nested models
            rows.extend(flatten_model_fields(value, prefix=dotted_key))
        else:
            rows.append((dotted_key, value, description))

    return rows
