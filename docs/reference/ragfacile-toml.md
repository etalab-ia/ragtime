# `ragfacile.toml` Reference

Complete reference for the RAG Facile configuration file. Every aspect of the RAG pipeline is configurable here — from document ingestion to response formatting — without touching code.

> To understand *what* each pipeline stage does and *why*, see [Understanding the RAG Pipeline](../guides/rag-pipeline.md).

## Quick Start

Most users don't need to edit the TOML file by hand. The CLI handles it:

```bash
# Apply a preset (creates ragfacile.toml with sensible defaults)
rag-facile config preset apply balanced

# View current configuration
rag-facile config show

# Change individual settings
rag-facile config set generation.temperature 0.5

# Validate your configuration
rag-facile config validate
```

## Albert Model Aliases

Albert exposes model aliases via the OpenAI-compatible `/models` endpoint. To list the current aliases:

```bash
uv run python - <<'PY'
from albert import AlbertClient

client = AlbertClient()
for model in client.models.list().data:
    print(model.id, "| aliases:", getattr(model, "aliases", None))
PY
```

Common aliases used in RAG Facile:

- **Generation**: `openweight-small`, `openweight-medium`, `openweight-large` (also `albert-small`, `albert-large`)
- **Embeddings**: `openweight-embeddings` (alias: `embeddings-small`)
- **Reranking**: `openweight-rerank` (alias: `rerank-small`)

## Minimal Example

You only need to specify the settings you want to change. Everything else uses preset defaults:

```toml
[meta]
preset = "balanced"

[generation]
model = "openweight-large"
temperature = 0.5

[retrieval]
top_k = 15
```

## Full Annotated Example

Below is the full `ragfacile.toml` based on the `balanced` preset with every key documented:

```toml
# ==========================================================
# META
# ==========================================================
[meta]
schema_version = "1.0.0"       # Config schema version
preset = "balanced"             # Active preset name

# ==========================================================
# EVALUATION DATASET GENERATION
# ==========================================================
[eval]
provider = "albert"             # "letta" or "albert"
target_samples = 50             # Q/A pairs to generate (1–1000)
output_format = "jsonl"         # Output format (currently only "jsonl")

# ==========================================================
# DOCUMENT INGESTION
# ==========================================================
[ingestion]
file_types = [".pdf", ".md", ".txt"]  # Accepted file extensions

[ingestion.ocr]
enabled = true                  # Enable OCR for scanned PDFs
dpi = 300                       # OCR resolution (72–600)
extract_images = false          # Extract images separately
include_bounding_boxes = false  # Include text position coordinates

[ingestion.parsing]
output_format = "markdown"      # "markdown", "json", or "html"
preserve_structure = true       # Keep headings, lists, tables
include_page_numbers = true     # Add page numbers to output

# ==========================================================
# DOCUMENT CHUNKING
# ==========================================================
[chunking]
strategy = "semantic"           # "fixed-size", "semantic", "sentence", "paragraph"
chunk_size = 512                # Size in tokens/characters (64–4096)
chunk_overlap = 50              # Overlap between chunks (0–512)
preserve_metadata = true        # Keep document metadata (title, headers, pages)

# ==========================================================
# EMBEDDING GENERATION
# ==========================================================
[embedding]
model = "openweight-embeddings"  # "openweight-embeddings" (alias: "embeddings-small")
batch_size = 32                   # Chunks per batch (1–128)
normalization = "L2"              # "L2" or "none"

# ==========================================================
# VECTOR STORAGE
# ==========================================================
[storage]
provider = "albert-collections"  # "albert-collections", "local-sqlite"
collection_naming = "workspace" # "workspace", "app", or "custom"
distance_metric = "cosine"      # "cosine", "euclidean", "dot-product"

# ==========================================================
# QUERY ENHANCEMENT
# ==========================================================
[query]
rewrite_enabled = false         # Rewrite vague queries for clarity
expand_enabled = false          # Add synonyms and related terms
spell_check = false             # Fix typos in queries

# ==========================================================
# RETRIEVAL
# ==========================================================
[retrieval]
strategy = "hybrid"               # "hybrid", "semantic", "lexical"
top_k = 10                      # Number of chunks to retrieve (1–100)
score_threshold = 0.0           # Minimum relevance score (0.0–1.0)

[retrieval.hybrid]
alpha = 0.5                     # 0.0 = lexical only, 0.5 = balanced, 1.0 = semantic only

# ==========================================================
# RERANKING
# ==========================================================
[reranking]
enabled = true                  # Enable reranking (improves precision)
model = "openweight-rerank"     # "openweight-rerank" (alias: "rerank-small")
top_n = 3                       # Final chunk count after reranking (1–50)

# ==========================================================
# CONTEXT ASSEMBLY
# ==========================================================
[context]
strategy = "token-budget"       # "token-budget", "top-n", "threshold"
max_tokens = 4096               # Token budget for context (512–32768)
deduplicate = true              # Remove duplicate/similar chunks
ordering = "by-score"           # "by-score", "by-document", "by-date"

# ==========================================================
# RESPONSE GENERATION
# ==========================================================
[generation]
model = "openweight-medium"     # "openweight-small", "openweight-medium", "openweight-large" (aka albert-small/albert-large)
temperature = 0.7               # 0.0 = deterministic, 2.0 = creative
max_tokens = 1024               # Max response length (64–8192)
streaming = true                # Enable streaming responses
system_prompt = """You are a helpful assistant for the French government.
Answer questions based on the provided context.
Always cite your sources using [1], [2], etc."""

# ==========================================================
# HALLUCINATION DETECTION
# ==========================================================
[hallucination]
enabled = false                 # Enable hallucination detection
strategy = "citation-check"     # "citation-check", "fact-check", "entailment"
threshold = 0.8                 # Confidence threshold (0.0–1.0)
fallback = "warn"               # "warn", "reject", "regenerate"

# ==========================================================
# ANSWER FORMATTING
# ==========================================================
[formatting]
output_format = "markdown"      # "markdown", "html", "plain-text"
include_confidence = false      # Show confidence scores
language = "fr"                 # "fr" or "en"

[formatting.citations]
enabled = true                  # Add source citations ([1], [2], ...)
style = "inline"                # "inline" or "footnote"
include_sources = true          # Append source list to response
```

## Presets

Presets are battle-tested configurations for common use cases. Apply one as a starting point, then customize.

```bash
rag-facile config preset list           # See available presets
rag-facile config preset apply legal    # Apply a preset
```

### Comparison

> **Note**: Albert currently exposes a single embedding model alias (`openweight-embeddings`). Presets keep embeddings consistent while tuning other stages.

| Setting | balanced | fast | accurate | legal | hr |
|---------|----------|------|----------|-------|----|
| **Chunking strategy** | semantic | fixed-size | semantic | paragraph | semantic |
| **Chunk size** | 512 | 512 | 768 | 768 | 512 |
| **Embedding model** | openweight-embeddings | openweight-embeddings | openweight-embeddings | openweight-embeddings | openweight-embeddings |
| **Retrieval strategy** | hybrid | semantic | hybrid | hybrid | hybrid |
| **top_k** | 10 | 5 | 20 | 15 | 12 |
| **Reranking** | on | **off** | on | on | on |
| **Generation model** | medium | small | large | large | medium |
| **Temperature** | 0.7 | 0.3 | 0.5 | 0.3 | 0.5 |
| **Hallucination detection** | off | off | **on** | **on** | **on** |
| **Hallucination fallback** | warn | warn | warn | **reject** | warn |
| **Query enhancement** | off | off | **on** | off | **on** |

### When to Use Each Preset

| Preset | Best for |
|--------|----------|
| **balanced** | General use, getting started, demos |
| **fast** | Prototyping, development, low-latency needs |
| **accurate** | Production, research, critical accuracy |
| **legal** | Legal research, regulatory documents, policy compliance |
| **hr** | Employee handbooks, HR policies, benefits documentation |

## Environment Variable Overrides

Any setting can be overridden with environment variables using the `RAG_<SECTION>_<KEY>` format. This is useful for CI/CD or production where you don't want to modify the file.

### Naming Convention

- **Uppercase**: All characters must be uppercase
- **Underscore separator**: Use underscores between parts
- **Nested keys**: Flatten with underscores (e.g., `ingestion.ocr.enabled` → `RAG_INGESTION_OCR_ENABLED`)

### Examples

```bash
# Override the generation model
export RAG_GENERATION_MODEL=openweight-large

# Change retrieval top_k
export RAG_RETRIEVAL_TOP_K=20

# Disable reranking
export RAG_RERANKING_ENABLED=false

# Enable hallucination detection
export RAG_HALLUCINATION_ENABLED=true
```

### Precedence

1. **Environment Variables** — Highest priority, always wins
2. **`ragfacile.toml`** — Project-level configuration
3. **Preset Defaults** — Base values from the active preset

## CLI Commands

| Command | Description |
|---------|-------------|
| `rag-facile config show` | View current settings (including active overrides) |
| `rag-facile config set <key> <value>` | Update a setting in `ragfacile.toml` |
| `rag-facile config validate` | Check for errors or suboptimal settings |
| `rag-facile config preset list` | List available presets |
| `rag-facile config preset apply <name>` | Reset config to a specific preset |

## Best Practices

1. **Keep secrets out of `ragfacile.toml`** — API keys belong in `.env` files or system environment variables. The TOML file is safe to commit to version control.
2. **Start with a preset** — Begin with `balanced` or `accurate` and tune individual values from there.
3. **Validate after edits** — Run `rag-facile config validate` after manual changes to catch typos and invalid values.
4. **Use env vars in production** — Override development settings without touching the repository's config file.
5. **Keep `meta.preset` updated** — This helps teammates understand which base configuration you started from.
