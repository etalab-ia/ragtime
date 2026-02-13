# Retrieval Albert

Albert API RAG retrieval for RAG Facile applications.

This package provides true RAG retrieval via Albert's sovereign AI platform:
document ingestion (upload + chunking + embedding), semantic/hybrid search,
and reranking. It replaces the simple "stuff the whole PDF in the prompt"
approach of `retrieval-basic` with a proper vector-search pipeline.

## Quick Start

```python
from albert import AlbertClient
from retrieval_albert import process_query, retrieve

# One-shot: retrieve + format
client = AlbertClient()
context = process_query("Qu'est-ce que le Code civil?", collection_ids=[123])

# Granular control
chunks = retrieve(client, "Code civil", collection_ids=[123])
```

## Features

- **Ingestion**: Upload documents to Albert collections with configurable chunking
- **Search**: Semantic, lexical, or hybrid search across collections
- **Reranking**: Optional reranking with BGE reranker for better precision
- **Formatting**: Context formatting with inline or footnote citations
- **Config-driven**: All defaults read from `ragfacile.toml` via `rag-core`

## API

All functions follow a functional style -- no classes, explicit `AlbertClient` injection.

### Ingestion

- `create_collection(client, name, description)` -- Create a collection
- `ingest_documents(client, paths, collection_id)` -- Upload and chunk documents
- `delete_collection(client, collection_id)` -- Delete a collection
- `list_collections(client)` -- List accessible collections

### Retrieval

- `retrieve(client, query, collection_ids)` -- Full pipeline: search + rerank
- `search_chunks(client, query, collection_ids)` -- Search only (no rerank)
- `rerank_chunks(client, query, chunks)` -- Rerank existing chunks

### Formatting

- `format_context(chunks)` -- Format chunks as context string
- `process_query(query, collection_ids)` -- Convenience: retrieve + format
