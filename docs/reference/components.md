# Components Reference

RAG Facile ships with ready-to-use components: an Albert API client, two frontend applications, and pluggable modules.

## Albert Client SDK

Official Python SDK for the [Albert API](https://albert.sites.beta.gouv.fr/). OpenAI-compatible with features specific to French government administration.

**Installation:**

```bash
pip install albert-client
```

**Usage Example:**

```python
from albert_client import AlbertClient

client = AlbertClient(
    api_key="your-api-key",
    base_url="https://albert.api.etalab.gouv.fr/v1"
)

# OpenAI-compatible
response = client.chat.completions.create(
    model="openweight-small",
    messages=[{"role": "user", "content": "Hello!"}]
)

# Hybrid search with reranking
results = client.search(
    query="energy transition",
    collections=[1, 2],
    method="hybrid"
)
```

**Full Documentation:** [Albert Client SDK README](../../packages/albert-client/README.md)

## Frontend Applications

| App | Description | Default Port |
|-----|-------------|--------------|
| **Chainlit Chat** | Chat interface with file upload support | 8000 |
| **Reflex Chat** | Interactive chat with modern UI | 3000 |

Both are available during `rag-facile setup` and are pre-configured to work with the Albert API out of the box.

## Retrieval System

RAG Facile provides a **unified retrieval package** with two backends that can be switched at runtime. The backend is determined by your `ragfacile.toml` configuration.

### Architecture

The retrieval system uses a factory pattern for runtime backend selection:

```python
from retrieval import get_provider

# Backend determined by ragfacile.toml config
provider = get_provider()
context = provider.process_file("document.pdf")
```

### Backend Selection

Backend is configured in `ragfacile.toml`:

```toml
[storage]
backend = "local-sqlite"        # Uses Basic backend
# backend = "albert-collections" # Uses Albert backend
```

To switch backends:
1. Edit `ragfacile.toml`
2. Restart your application

No code changes or reinstallation needed!

### Basic Backend (`local-sqlite`)

**Best for:** Quick prototypes, offline usage, simple document processing

- **Extraction:** Local pypdf library (no network calls)
- **Supported formats:** PDF
- **Features:** Simple, lightweight, no server dependencies
- **Use case:** Getting started quickly, private/offline scenarios, small documents

### Albert Backend (`albert-collections`)

**Best for:** Production deployments, large document collections, advanced search features

- **Extraction:** Albert API server-side parsing (`/parse-beta`)
- **Supported formats:** PDF, JSON, Markdown, HTML
- **Features:** 
  - Multi-format document support
  - Server-side chunking and vectorization
  - Hybrid search (semantic + lexical)
  - Result reranking with BGE models
  - Collection-based document storage
  - Built-in fallback to local pypdf if parse API fails
- **Use case:** Advanced RAG pipelines, production applications, large document sets

### Comparison Table

| Feature | Basic | Albert |
|---------|-------|--------|
| **Extraction** | Local pypdf | Albert API + fallback |
| **Formats** | PDF only | PDF, JSON, MD, HTML |
| **Search** | None (context injection) | Semantic + Hybrid + Reranking |
| **Persistence** | None (per-session) | Collections (persistent) |
| **Network** | Offline | Requires API access |
| **Use Case** | Small docs, prototypes | Production, large collections |

> **Note:** Both backends implement the same interface, making them fully interchangeable. Apps automatically work with either backend without code changes.
