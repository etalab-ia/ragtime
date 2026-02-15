# RAG Config

Configuration management for RAG Facile - customize your RAG pipeline without touching code.

## Why Use This?

**Stop hardcoding RAG parameters.** Whether you need fast responses or maximum accuracy, different temperature settings for production vs development, or domain-specific optimizations - configure it all in one place.

**Key Benefits:**
- **Start Fast** - Apply a preset (`balanced`, `legal`, `hr`) and go
- **Iterate Easily** - Tune model, temperature, retrieval settings via TOML file
- **Deploy Confidently** - Override configs per environment with env vars
- **Stay Type-Safe** - Pydantic validation catches errors before runtime

## Features

- **Complete RAG Pipeline Coverage** - 12 phases from ingestion to response formatting
- **Preset System** - Start with battle-tested configs (fast, balanced, accurate, legal, hr)
- **Environment Override** - Override any config value with env vars (no code changes)
- **Type-Safe** - Pydantic models with full validation
- **Schema Versioning** - Forward-compatible config migrations
- **JSON Schema Export** - Documentation and IDE autocomplete support

## Installation

```bash
# With pip
pip install rag-config

# With uv (recommended)
uv add rag-config

# From source (development)
git clone https://github.com/etalab-ia/rag-facile.git
cd rag-facile
uv pip install -e packages/rag-config
```

## Quick Start

### Load Configuration

```python
from rag_config import load_config

# Load from ragfacile.toml (default)
config = load_config()

# Load from custom path
config = load_config("path/to/config.toml")

# Access config values
print(config.generation.model)  # "openweight-medium"
print(config.retrieval.top_k)   # 10
```

### Use in Application

```python
from rag_config import get_config

# Get cached config (singleton pattern)
config = get_config()

# Use in your RAG pipeline
search_results = client.search(
    query=user_query,
    method=config.retrieval.strategy,
    top_k=config.retrieval.top_k,
)

if config.reranking.enabled:
    reranked = client.rerank(
        query=user_query,
        documents=search_results,
        top_n=config.reranking.top_n,
    )
```

### Environment Variable Override

```bash
# Override any config value
export RAG_GENERATION_MODEL="openweight-large"
export RAG_RETRIEVAL_TOP_K="20"
export RAG_RERANKING_ENABLED="false"

# Run your app - env vars take precedence
python app.py
```

### Load Preset

```python
from rag_config import load_preset, list_presets

# List available presets
print(list_presets())  # ['fast', 'balanced', 'accurate', 'legal', 'hr']

# Load a preset
config = load_preset("legal")
print(config.hallucination.enabled)  # True (legal requires strict accuracy)
```

## Common Use Cases

### Build a Legal Document Q&A System

```python
from rag_config import load_preset

# Legal preset: strict citations, low temperature, hallucination detection
config = load_preset("legal")

# Your RAG pipeline automatically uses:
# - temperature 0.3 (consistent answers)
# - mandatory source citations [1], [2]
# - hallucination detection enabled
# - higher retrieval threshold for accuracy
```

### Different Configs Per Environment

```bash
# Development - fast iteration
export RAG_GENERATION_MODEL=openweight-small
export RAG_RERANKING_ENABLED=false

# Production - maximize quality
export RAG_GENERATION_MODEL=openweight-large
export RAG_RERANKING_ENABLED=true
export RAG_HALLUCINATION_ENABLED=true
```

### Optimize for Speed vs Quality

```python
from rag_config import load_preset

# Fast prototype - skip expensive operations
config = load_preset("fast")
# Uses: smaller model, no reranking, fixed-size chunks

# Production - maximize accuracy
config = load_preset("accurate")
# Uses: larger model, reranking enabled, semantic chunks, hallucination detection
```

### A/B Test RAG Parameters

```python
from rag_config import load_config

# Load base config
config = load_config("ragfacile.toml")

# Test different temperatures
for temp in [0.3, 0.5, 0.7]:
    config.generation.temperature = temp
    # Run your evaluation suite
```

## Configuration Sections

RAG Config covers the complete RAG pipeline:

1. **eval** - Synthetic dataset generation settings
2. **ingestion** - Document loading and OCR
3. **chunking** - Text splitting strategies
4. **embedding** - Vector generation
5. **storage** - Vector store configuration
6. **query** - Query enhancement and rewriting
7. **retrieval** - Search methods and parameters
8. **reranking** - Result refinement
9. **context** - Context window management
10. **generation** - LLM response settings
11. **hallucination** - Accuracy validation
12. **formatting** - Output presentation

See [Configuration Guide](../../docs/guides/config-guide.md) for complete reference.

## Presets

### Performance-Focused

- **fast** - Speed-optimized (smaller models, skip reranking)
- **balanced** - Recommended default (quality/speed tradeoff)
- **accurate** - Quality-optimized (larger models, hallucination detection)

### Domain-Focused

- **legal** - Legal documents (strict citations, accuracy validation, lower temperature)
- **hr** - HR policies (privacy-aware, clear attribution, semantic search)

## Schema Version

RAG Config uses semantic versioning for the config schema:

```toml
[meta]
schema_version = "1.0.0"
```

Future versions may add new fields (minor version bump) or change field meanings (major version bump). The loader handles migrations automatically.

## Advanced Usage

### Generate JSON Schema

```python
from rag_config import export_json_schema

# Export schema for documentation or IDE support
schema = export_json_schema()
with open("ragfacile-schema.json", "w") as f:
    f.write(schema)
```

### Validate Configuration

```python
from rag_config import validate_config
from pydantic import ValidationError

try:
    config = validate_config("ragfacile.toml")
    print("✓ Configuration is valid")
except ValidationError as e:
    print(f"✗ Configuration errors:")
    for error in e.errors():
        print(f"  {error['loc']}: {error['msg']}")
```

### Programmatic Updates

```python
from rag_config import load_config, save_config

# Load, modify, save
config = load_config()
config.generation.temperature = 0.5
config.retrieval.top_k = 20
save_config(config, "ragfacile.toml")
```

## Configuration vs Secrets

**Important:** Keep secrets in `.env` files, not `ragfacile.toml`:

### ragfacile.toml (safe to commit)
```toml
[generation]
model = "openweight-medium"
temperature = 0.7
```

### .env (never commit)
```bash
OPENAI_API_KEY=albert_xxxxx
OPENAI_BASE_URL=https://albert.api.etalab.gouv.fr/v1
```

## Contributing

See [Contributing Guide](../../CONTRIBUTING.md) for development setup and guidelines.

## License

MIT License - see [LICENSE](../../LICENSE) for details.
