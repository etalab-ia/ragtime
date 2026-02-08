# Albert Client

Official Python SDK for France's [Albert API](https://albert.api.etalab.gouv.fr/) - a sovereign AI platform.

## Features

✅ **OpenAI-Compatible**: Drop-in replacement for OpenAI SDK with French government models  
✅ **Type-Safe**: Full Pydantic models for all responses with `.to_dict()` and `.to_json()` helpers  
✅ **Async Support**: Both sync (`AlbertClient`) and async (`AsyncAlbertClient`) clients  
✅ **Albert-Specific**: Hybrid RAG search, BGE reranking, collections, documents, OCR, parsing, carbon footprint tracking  
✅ **100% Test Coverage**: 136 passing tests with comprehensive API mocking

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

### Basic Usage

```python
from albert_client import AlbertClient

# Initialize client
client = AlbertClient(
    api_key="albert_...",  # Or set ALBERT_API_KEY env var
    base_url="https://albert.api.etalab.gouv.fr"
)

# Chat completion (OpenAI-compatible)
response = client.chat.completions.create(
    model="AgentPublic/llama3-instruct-8b",
    messages=[
        {"role": "user", "content": "Qu'est-ce que la loi Énergie Climat ?"}
    ]
)
print(response.choices[0].message.content)

# Embeddings (OpenAI-compatible)
embedding = client.embeddings.create(
    model="BAAI/bge-m3",
    input="Transition énergétique en France"
)
print(embedding.data[0].embedding)

# Hybrid RAG search (Albert-specific)
results = client.search(
    query="transition énergétique",
    collections=[1, 2],
    method="hybrid",  # or "semantic", "lexical"
    k=5
)
for result in results.results:
    print(f"Score: {result.score:.3f} - {result.chunk.content[:100]}...")

# Rerank for better relevance (Albert-specific)
reranked = client.rerank(
    query="énergies renouvelables",
    documents=[doc.chunk for doc in results.results],
    model="BAAI/bge-reranker-v2-m3",
    top_n=3
)
for result in reranked.results:
    print(f"Relevance: {result.relevance_score:.3f}")
```

### Async Usage

```python
from albert_client import AsyncAlbertClient

async with AsyncAlbertClient(api_key="albert_...") as client:
    # All methods have async variants
    response = await client.chat.completions.create(
        model="AgentPublic/llama3-instruct-8b",
        messages=[{"role": "user", "content": "Hello!"}]
    )
    print(response.choices[0].message.content)
    
    # Async search
    results = await client.search(
        query="énergies renouvelables",
        collections=[1],
        method="hybrid"
    )
```

### Complete RAG Pipeline Example

```python
from albert_client import AlbertClient
from pathlib import Path

client = AlbertClient(api_key="albert_...")

# 1. Create a knowledge base
collection = client.create_collection(
    name="Documentation Énergie",
    description="Documents sur la transition énergétique",
    model="BAAI/bge-m3"
)

# 2. Upload documents
doc = client.upload_document(
    file_path=Path("./rapport_energie.pdf"),
    collection_id=collection.id,
    metadata={"source": "ministère", "year": 2024}
)

# 3. Search for relevant context
results = client.search(
    query="Quelles sont les aides pour les panneaux solaires ?",
    collections=[collection.id],
    method="hybrid",
    k=10
)

# 4. Rerank for precision
reranked = client.rerank(
    query="aides panneaux solaires",
    documents=[r.chunk.content for r in results.results],
    top_n=3
)

# 5. Build context and generate answer
context = "\n\n".join([
    results.results[r.index].chunk.content 
    for r in reranked.results
])

response = client.chat.completions.create(
    model="AgentPublic/llama3-instruct-8b",
    messages=[
        {"role": "system", "content": f"Contexte:\n{context}"},
        {"role": "user", "content": "Quelles sont les aides disponibles ?"}
    ]
)

print(response.choices[0].message.content)

# 6. Track usage and carbon footprint
usage = client.get_usage(start_date="2024-01-01", end_date="2024-12-31")
print(f"CO2: {usage.records[0].carbon_footprint_g}g")
```

## API Reference

The SDK wraps the OpenAI Python client for OpenAI-compatible endpoints while providing custom implementations for Albert-specific features:

### OpenAI-Compatible Endpoints

Passthrough to internal OpenAI client:

- `client.chat.completions.create()` - Chat completions
- `client.embeddings.create()` - Text embeddings
- `client.audio.transcriptions.create()` - Audio transcriptions
- `client.audio.speech.create()` - Text-to-speech
- `client.models.list()` - Available models

### Albert-Specific Features

#### Search & Reranking

- `client.search()` - Hybrid/semantic/lexical search across collections
- `client.rerank()` - BGE reranking for improved relevance

#### Collections Management

- `client.create_collection()` - Create knowledge base
- `client.list_collections()` - List all collections
- `client.get_collection()` - Get collection details
- `client.update_collection()` - Update collection metadata
- `client.delete_collection()` - Delete collection

#### Documents & Chunks

- `client.upload_document()` - Upload documents to collections
- `client.list_documents()` - List documents in collection
- `client.get_document()` - Get document details
- `client.delete_document()` - Delete document
- `client.list_chunks()` - List document chunks
- `client.get_chunk()` - Get specific chunk

#### Advanced Tools

- `client.get_usage()` - Usage tracking with carbon footprint
- `client.ocr()` - OCR with bounding boxes
- `client.ocr_beta()` - Advanced OCR with image extraction
- `client.parse()` - Parse documents to markdown/json/html
- `client.upload_file()` - Generic file uploads
- `client.health_check()` - API health status
- `client.get_metrics()` - API metrics

## Development Status

**✅ SDK Complete** - All 4 development phases finished:

- ✅ **Phase 1**: Core client + OpenAI passthrough (30 tests)
- ✅ **Phase 2**: Search + Rerank (35 tests)
- ✅ **Phase 3**: Collections + Documents + Chunks (44 tests)
- ✅ **Phase 4**: Usage + OCR + Parsing + File Management + Monitoring (27 tests)

**Total: 136/136 tests passing** with 100% coverage of all practical Albert API endpoints.

## Running Tests

```bash
# Run all tests
pytest packages/albert-client/tests/

# Run with coverage
pytest packages/albert-client/tests/ --cov=albert_client

# Run specific test file
pytest packages/albert-client/tests/test_client.py
```

## Contributing

See the main [CONTRIBUTING.md](../../CONTRIBUTING.md) for development setup and guidelines.

## License

MIT - See [LICENSE](../../LICENSE) for details.

## Links

- [Albert API Documentation](https://albert.api.etalab.gouv.fr/docs)
- [OpenAI Python SDK](https://github.com/openai/openai-python) (compatibility layer)
- [RAG Facile](https://github.com/etalab-ia/rag-facile) (parent project)
