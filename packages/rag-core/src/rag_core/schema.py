"""Pydantic models for RAG Facile configuration.

This module defines the complete configuration schema for the RAG pipeline,
covering all phases from document ingestion to response formatting.
"""

from typing import Literal

from pydantic import BaseModel, Field


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
    """Configuration for synthetic Q/A dataset generation."""

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
        default=512,
        ge=64,
        le=4096,
        description="Chunk size in tokens (semantic) or characters (fixed-size)",
    )
    chunk_overlap: int = Field(
        default=50,
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
        default="albert-embedding-small",
        description="Embedding model (albert-embedding-small, albert-embedding-large)",
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

    backend: Literal["albert-collections", "local-sqlite"] = Field(
        default="albert-collections",
        description="Vector store backend",
    )
    collection_naming: Literal["workspace", "app", "custom"] = Field(
        default="workspace",
        description="Collection naming strategy",
    )
    distance_metric: Literal["cosine", "euclidean", "dot-product"] = Field(
        default="cosine",
        description="Distance metric for similarity search",
    )


# ==============================================================================
# QUERY ENHANCEMENT
# ==============================================================================


class QueryConfig(BaseModel):
    """Configuration for query enhancement."""

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

    method: Literal["hybrid", "semantic", "lexical"] = Field(
        default="hybrid",
        description="Retrieval method",
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

    enabled: bool = Field(
        default=True,
        description="Enable reranking (improves precision at cost of latency)",
    )
    model: str = Field(
        default="bge-reranker-large",
        description="Reranking model (bge-reranker-large, bge-reranker-base)",
    )
    top_n: int = Field(
        default=3,
        ge=1,
        le=50,
        description="Final number of results after reranking",
    )


# ==============================================================================
# CONTEXT SELECTION
# ==============================================================================


class ContextFormattingConfig(BaseModel):
    """Context formatting settings."""

    include_citations: bool = Field(
        default=True,
        description="Include source citations in context",
    )
    citation_style: Literal["inline", "footnote"] = Field(
        default="inline",
        description="Citation style",
    )


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
    formatting: ContextFormattingConfig = Field(
        default_factory=ContextFormattingConfig,
        description="Context formatting settings",
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
        default=0.7,
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
    method: Literal["entailment", "fact-check", "citation-check"] = Field(
        default="citation-check",
        description="Detection method",
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


class FormattingConfig(BaseModel):
    """Configuration for answer formatting."""

    output_format: Literal["markdown", "html", "plain-text"] = Field(
        default="markdown",
        description="Output format",
    )
    include_sources: bool = Field(
        default=True,
        description="Include retrieved sources in response",
    )
    include_confidence: bool = Field(
        default=False,
        description="Include confidence scores",
    )
    language: Literal["fr", "en"] = Field(
        default="fr",
        description="Response language",
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
    query: QueryConfig = Field(
        default_factory=QueryConfig,
        description="Query enhancement",
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
                        "method": "hybrid",
                        "top_k": 10,
                        "hybrid": {"alpha": 0.5},
                    },
                }
            ]
        }
    }
