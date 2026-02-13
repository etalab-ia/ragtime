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

## Modules

| Module | Description | Status |
|--------|-------------|--------|
| **PDF Context** | Extract and process PDF documents for RAG context | Available |
| **Albert RAG** | Full RAG pipeline: ingestion, search, reranking via Albert API | Available |

Modules are selected during `rag-facile setup` and automatically included in your project.
