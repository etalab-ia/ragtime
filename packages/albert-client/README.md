# Albert Client

Official Python SDK for France's [Albert API](https://albert.api.etalab.gouv.fr/) - a sovereign AI platform.

## Features

✅ **OpenAI-Compatible**: Drop-in replacement for OpenAI SDK with French government models
✅ **Type-Safe**: Full Pydantic models for all responses with `.to_dict()` and `.to_json()` helpers
✅ **Async Support**: Both sync (`AlbertClient`) and async (`AsyncAlbertClient`) clients
🚧 **Albert-Specific**: RAG search, collections, documents, OCR, carbon footprint tracking (coming soon)

## Installation

```bash
# From monorepo (development)
uv pip install -e packages/albert-client

# From PyPI (once published)
pip install albert-client
```

## Quick Start

### Basic Usage

```python
from albert_client import AlbertClient

# Initialize client
client = AlbertClient(
    api_key="albert_...",  # Or set ALBERT_API_KEY env var
    base_url="https://albert.api.etalab.gouv.fr/v1"
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
```

### Async Usage

```python
from albert_client import AsyncAlbertClient

async with AsyncAlbertClient(api_key="albert_...") as client:
    response = await client.chat.completions.create(
        model="AgentPublic/llama3-instruct-8b",
        messages=[{"role": "user", "content": "Hello!"}]
    )
    print(response.choices[0].message.content)
```

## Architecture

The SDK wraps the OpenAI Python client for OpenAI-compatible endpoints while providing custom implementations for Albert-specific features:

- **OpenAI-Compatible** (passthrough to internal OpenAI client):
  - `client.chat.completions.create()`
  - `client.embeddings.create()`
  - `client.audio.transcriptions.create()`
  - `client.models.list()`

- **Albert-Specific** (custom implementations, coming in Phase 2+):
  - `client.search()` - Hybrid RAG search
  - `client.rerank()` - BGE reranking
  - `client.collections.create()` - Knowledge base management
  - `client.documents.create()` - Document uploads
  - `client.tools.ocr()` - OCR endpoint
  - `client.management.get_usage()` - Usage stats with carbon footprint

## Development Status

This SDK is under active development. Current status:

- ✅ **Phase 1**: Core client + OpenAI passthrough (COMPLETE)
- 🚧 **Phase 2**: Search + Rerank (IN PROGRESS)
- 🔜 **Phase 3**: Collections + Documents
- 🔜 **Phase 4**: Tools + Management
- 🔜 **Phase 5**: Documentation + Monitoring

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
