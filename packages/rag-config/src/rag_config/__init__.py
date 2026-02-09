"""RAG Config - Configuration management for RAG Facile.

This package provides TOML-based configuration management with:
- Complete RAG pipeline coverage (12 phases)
- Type-safe validation with Pydantic
- Environment variable overrides
- Preset system for common use cases
- JSON Schema export for tooling

Quick Start:
    >>> from rag_config import get_config
    >>> config = get_config()
    >>> print(config.generation.model)
    'openweight-medium'

Environment Overrides:
    >>> import os
    >>> os.environ["RAG_GENERATION_MODEL"] = "openweight-large"
    >>> config = get_config()
    >>> print(config.generation.model)
    'openweight-large'

Presets:
    >>> from rag_config import list_presets, load_preset
    >>> print(list_presets())
    ['fast', 'balanced', 'accurate', 'legal', 'hr']
    >>> config = load_preset("legal")
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
    ChunkingConfig,
    ContextConfig,
    EmbeddingConfig,
    EvalConfig,
    FormattingConfig,
    GenerationConfig,
    HallucinationConfig,
    IngestionConfig,
    MetaConfig,
    QueryConfig,
    RAGConfig,
    RerankingConfig,
    RetrievalConfig,
    StorageConfig,
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
