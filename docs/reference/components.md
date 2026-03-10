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
| **Chainlit Chat** | Chat interface for querying ingested documents | 8000 |
| **Reflex Chat** | Interactive chat with modern UI | 3000 |

Both are available during `rag-facile setup` and are pre-configured to work with the Albert API out of the box.

## Pipeline Packages

RAG Facile organizes the RAG pipeline into dedicated packages, each handling a specific phase:

| Package | Phase | Description |
|---------|-------|-------------|
| **ingestion** | Document Ingestion | Parse documents into text (PDF, Markdown, HTML) |
| **storage** | Vector Storage | Collection management — create, populate, delete, list |
| **retrieval** | Search | Vector search across document collections (semantic, lexical, hybrid) |
| **reranking** | Reranking | Re-score search results with a cross-encoder for higher precision |
| **context** | Context Assembly | Format retrieved chunks into LLM-ready context strings with citations |
| **tracing** | Observability | Log queries, context, responses, and user feedback for pipeline improvement |
| **pipelines** | Orchestration | Coordinate all pipeline phases into a unified interface |

### Storage

Manages vector store collections via the Albert API (or local SQLite, planned).

```python
from rag_facile.storage import get_provider

provider = get_provider()  # Backend from ragfacile.toml
collection_id = provider.create_collection(client, "my-docs")
provider.ingest_documents(client, ["report.pdf"], collection_id)
```

### Retrieval → Reranking → Context

Each phase is a self-contained module under `rag_facile.*`. The `pipelines` module orchestrates them:

```python
# Individual phase modules (used by pipelines internally)
from rag_facile.retrieval import search_chunks
from rag_facile.reranking import rerank_chunks
from rag_facile.context import format_context

chunks = search_chunks(client, "energy transition", collection_ids=[1])
reranked = rerank_chunks(client, "energy transition", chunks)
context_str = format_context(reranked)
```

### Backend Selection

Backend is configured in `ragfacile.toml`:

```toml
[storage]
provider = "albert-collections"  # or "local-sqlite" (planned)
```

To switch backends:
1. Edit `ragfacile.toml`
2. Restart your application

No code changes or reinstallation needed!

### Comparison Table

| Feature | Basic (`local-sqlite`) | Albert (`albert-collections`) |
|---------|----------------------|-------------------------------|
| **Extraction** | Local pypdf | Albert API + fallback |
| **Formats** | PDF only | PDF, MD, HTML |
| **Search** | None (context injection) | Semantic + Hybrid + Reranking |
| **Persistence** | None (per-session) | Collections (persistent) |
| **Network** | Offline | Requires API access |
| **Use Case** | Small docs, prototypes | Production, large collections |

> **Note:** Both backends implement the same interface, making them fully interchangeable. Apps automatically work with either backend without code changes.
