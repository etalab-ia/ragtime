"""RAG Core - Core functionality for RAG Facile.

This package provides:
- TOML-based configuration management (previously in core-config)
- Type-safe validation with Pydantic
- Preset system for common use cases

Quick Start:
    >>> from rag_core import get_config
    >>> config = get_config()
    >>> print(config.generation.model)
    'openweight-medium'
"""

from .loader import (
    export_json_schema,
    get_env_override_docs,
    load_config,
    load_config_or_default,
    parse_value,
    save_config,
    validate_config,
)
from .presets import (
    apply_preset,
    compare_presets,
    get_preset_description,
    list_presets,
    load_preset,
)
from .runtime import get_config, has_config_file, reload_config
from .schema import (
    PIPELINE_STAGES,
    ChunkingConfig,
    CitationsConfig,
    ContextConfig,
    EmbeddingConfig,
    EvalConfig,
    FormattingConfig,
    GenerationConfig,
    HallucinationConfig,
    IngestionConfig,
    MetaConfig,
    PipelineStage,
    QueryConfig,
    RAGConfig,
    RerankingConfig,
    RetrievalConfig,
    StorageConfig,
    flatten_model_fields,
)


__version__ = "0.8.0"

__all__ = [
    # Main config class
    "RAGConfig",
    # Config sections
    "MetaConfig",
    "EvalConfig",
    "IngestionConfig",
    "ChunkingConfig",
    "EmbeddingConfig",
    "StorageConfig",
    "QueryConfig",
    "RetrievalConfig",
    "RerankingConfig",
    "ContextConfig",
    "GenerationConfig",
    "HallucinationConfig",
    "FormattingConfig",
    "CitationsConfig",
    # Pipeline metadata
    "PIPELINE_STAGES",
    "PipelineStage",
    "flatten_model_fields",
    # Loader functions
    "load_config",
    "load_config_or_default",
    "save_config",
    "validate_config",
    "export_json_schema",
    "get_env_override_docs",
    "parse_value",
    # Runtime functions
    "get_config",
    "reload_config",
    "has_config_file",
    # Preset functions
    "list_presets",
    "load_preset",
    "apply_preset",
    "get_preset_description",
    "compare_presets",
]
