# Orchestration

RAG pipeline orchestration for chat applications. Coordinates document ingestion and retrieval behind a unified `RAGPipeline` interface.

## Usage

```python
from orchestration import get_pipeline

pipeline = get_pipeline()

# Upload time: parse a file and format as LLM context
context = pipeline.process_file("document.pdf", filename="My Doc")

# Upload time: parse from bytes (e.g., Reflex file upload)
context = pipeline.process_bytes(data, "document.pdf")

# Query time: retrieve relevant context (Albert RAG only)
context = pipeline.process_query(query, collection_ids=[1, 2])

# UI: get supported file types for file picker dialogs
mime_types = pipeline.accepted_mime_types
```

## Pipelines

- **BasicPipeline** (`storage.provider = "local-sqlite"`): Context stuffing — parses files locally and injects full text into the LLM prompt.
- **AlbertPipeline** (`storage.provider = "albert-collections"`): Full RAG — parses files via Albert API, supports query-time retrieval with search + reranking.

Pipeline selection is driven by `ragfacile.toml` configuration.
