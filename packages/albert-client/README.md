# Albert Client

Official Python SDK for France's [Albert API](https://albert.api.etalab.gouv.fr/) - a sovereign AI platform providing OpenAI-compatible endpoints plus French government-specific features.

## Why Use This SDK?

- **OpenAI-Compatible**: Use the same code you know from OpenAI with French sovereign models
- **Single Dependency**: The only dependency in RAG Facile that requires the OpenAI SDK - all apps and packages use albert-client
- **RAG Made Easy**: Built-in hybrid search, reranking, and collections management
- **Type-Safe**: Full autocomplete and type checking in your IDE
- **Production-Ready**: Async support, comprehensive error handling, battle-tested

## Features

- OpenAI-compatible endpoints: chat, embeddings, audio, models
- Hybrid/semantic/lexical search across document collections  
- BGE reranking for improved relevance
- Collections and document management
- OCR with bounding boxes and document parsing
- Usage tracking with carbon footprint metrics
- Both sync and async clients

## Installation

```bash
# With pip
pip install albert-client

# With uv (recommended)
uv add albert-client

# From source (development)
git clone https://github.com/etalab-ia/rag-facile.git
cd rag-facile
uv pip install -e packages/albert-client
```

## Quick Start

### Installation

```bash
pip install albert-client
```

### Basic Chat (OpenAI-Compatible)

```python
from albert_client import AlbertClient

client = AlbertClient(
    api_key="albert_...",  # Or set OPENAI_API_KEY env var
    base_url="https://albert.api.etalab.gouv.fr/v1"
)

response = client.chat.completions.create(
    model="openweight-small",  # or "openweight-medium", "openweight-large"
    messages=[
        {"role": "user", "content": "Qu'est-ce que la loi Énergie Climat ?"}
    ]
)
print(response.choices[0].message.content)
```

### Hybrid Search + Reranking

```python
# Search across your document collections
results = client.search(
    query="transition énergétique",
    collections=[1, 2],
    method="hybrid",
    k=10
)

# Rerank for better precision
reranked = client.rerank(
    query="énergies renouvelables",
    documents=[doc.chunk.content for doc in results.data],
    top_n=3
)
```

### Async Usage

```python
from albert_client import AsyncAlbertClient

async with AsyncAlbertClient(api_key="albert_...") as client:
    response = await client.chat.completions.create(
        model="openweight-small",
        messages=[{"role": "user", "content": "Hello!"}]
    )
```

## Common Use Cases

### Chat Completion (OpenAI-Compatible)

```python
response = client.chat.completions.create(
    model="openweight-small",
    messages=[{"role": "user", "content": "Question?"}]
)
```

### Embeddings (OpenAI-Compatible)

```python
embedding = client.embeddings.create(
    model="openweight-embeddings",
    input="Text to embed"
)
```

### Building a RAG System

**1. Create a collection:**
```python
collection = client.create_collection(
    name="Documentation",
    model="openweight-embeddings"
)
```

**2. Upload documents:**
```python
doc = client.upload_document(
    file_path="document.pdf",
    collection_id=collection.id
)
```

**3. Search + rerank:**
```python
results = client.search(query="...", collections=[collection.id])
reranked = client.rerank(
    query="...", 
    documents=[doc.chunk.content for doc in results.data]
)
```

**4. Generate answer with context:**
```python
# Build context from reranked results
context = "\n".join([
    results.data[r.index].chunk.content 
    for r in reranked.results
])

response = client.chat.completions.create(
    model="openweight-small",
    messages=[
        {"role": "system", "content": f"Context:\n{context}"},
        {"role": "user", "content": "Question?"}
    ]
)
```

### Document Processing

**OCR:**
```python
result = client.ocr(document="file.pdf", include_image_base64=True)
```

**Parse to markdown:**
```python
parsed = client.parse(file_path="doc.pdf", output_format="markdown")
```

### Monitoring

**Track usage and carbon footprint:**
```python
usage = client.get_usage(start_date="2024-01-01")
print(f"CO2: {usage.records[0].carbon_footprint_g}g")
```

## Full API Reference

For a complete list of methods and parameters, see the [API documentation](https://albert.api.etalab.gouv.fr/docs).

## Contributing

Interested in contributing to the SDK? We welcome improvements!

### Development Setup

```bash
# Clone the repository
git clone https://github.com/etalab-ia/rag-facile.git
cd rag-facile

# Install dependencies
uv sync

# Run tests
pytest packages/albert-client/tests/

# Run with coverage
pytest packages/albert-client/tests/ --cov=albert_client
```

### SDK Development Status

The SDK is feature-complete with 136/136 tests passing:

- ✅ **Phase 1**: Core client + OpenAI passthrough (30 tests)
- ✅ **Phase 2**: Search + Rerank (35 tests)
- ✅ **Phase 3**: Collections + Documents + Chunks (44 tests)
- ✅ **Phase 4**: Usage + OCR + Parsing + File Management + Monitoring (27 tests)

See the main [CONTRIBUTING.md](../../CONTRIBUTING.md) for project guidelines and workflow.

## License

MIT - See [LICENSE](../../LICENSE) for details.

## Links

- [Albert API Documentation](https://albert.api.etalab.gouv.fr/docs)
- [OpenAI Python SDK](https://github.com/openai/openai-python) (compatibility layer)
- [RAG Facile](https://github.com/etalab-ia/rag-facile) (parent project)
