# Retrieval

Unified retrieval package for RAG Facile with runtime provider selection.

## Overview

This package provides document retrieval capabilities with two backends that can be switched at runtime via configuration:

- **basic**: In-memory context injection - stuffs entire PDF into prompt (suitable for small documents)
- **albert**: Full RAG via Albert API - ingestion, semantic search, reranking (suitable for large document collections)

## Configuration

Provider selection is automatic based on `ragfacile.toml`:

```toml
[storage]
backend = "albert-collections"  # Uses Albert RAG
# backend = "local-sqlite"      # Uses basic context injection
```

## Usage

### Factory Pattern (Recommended)

```python
from retrieval import get_provider

# Get provider based on config
provider = get_provider()

# Use provider (same interface for both backends)
context = provider.process_file("document.pdf")
```

### Direct Imports (Backward Compatible)

```python
# Basic provider functions are re-exported for convenience
from retrieval import extract_text_from_pdf, process_pdf_file, format_as_context

text = extract_text_from_pdf("document.pdf")
context = process_pdf_file("document.pdf")
```

## Providers

### Basic Provider

Simple context injection approach - extracts text from PDFs and injects the entire content into the LLM context.

**When to use:**
- Small documents (< 10 pages)
- Documents that fit in model context window
- Simple use cases without persistence

**Functions:**
- `extract_text_from_pdf(path)` - Extract raw text
- `extract_text_from_bytes(data)` - Extract from bytes (for uploads)
- `format_as_context(text, filename)` - Format with delimiters
- `process_pdf_file(path, filename=None)` - Extract + format
- `process_file(path, filename=None)` - Generic file processor
- `process_multiple_files(paths)` - Batch processing

### Albert Provider

Full RAG pipeline via Albert's sovereign AI platform - document ingestion, semantic/hybrid search, and reranking.

**When to use:**
- Large document collections
- Need persistence across sessions
- Advanced retrieval (semantic search, reranking)
- Production deployments

**Parser Functions (backward compatible with basic):**
- `extract_text`, `extract_text_from_pdf`, `extract_text_from_bytes`
- `format_as_context`, `process_file`, `process_pdf_file`, `process_multiple_files`

**Ingestion Functions:**
- `create_collection(client, name, description)` - Create collection
- `ingest_documents(client, paths, collection_id)` - Upload and chunk documents
- `delete_collection(client, collection_id)` - Delete collection
- `list_collections(client)` - List accessible collections

**Retrieval Functions:**
- `retrieve(client, query, collection_ids)` - Full pipeline: search + rerank
- `search_chunks(client, query, collection_ids)` - Search only
- `rerank_chunks(client, query, chunks)` - Rerank existing chunks

**Formatting Functions:**
- `format_context(chunks)` - Format chunks as context string
- `process_query(query, collection_ids)` - Convenience: retrieve + format

## Switching Backends

To switch backends:

1. Edit `ragfacile.toml`:
   ```toml
   [storage]
   backend = "albert-collections"  # or "local-sqlite"
   ```

2. Restart your application

No code changes or reinstallation required!

## Integration with Context Loader

The chat applications use `context_loader.py` which dynamically loads this package. The `modules.yml` file should reference:

```yaml
context_providers:
  retrieval: retrieval
```

The `context_loader` will call `process_file()` from the appropriate backend based on your configuration.

## Development

### Running Tests

```bash
uv run pytest packages/retrieval/tests/
```

### Type Checking

```bash
uv run ty check packages/retrieval/
```

### Linting

```bash
uv run ruff check packages/retrieval/
uv run ruff format packages/retrieval/
```

## Migration from Old Packages

If you have code that directly imports from `retrieval_basic` or `retrieval_albert`:

```python
# OLD
from retrieval_basic import process_pdf_file
from retrieval_albert import retrieve

# NEW
from retrieval import get_provider

provider = get_provider()
context = provider.process_pdf_file("doc.pdf")
chunks = provider.retrieve(client, query, [collection_id])
```

Or use backward-compatible imports for basic functions:

```python
# Still works
from retrieval import process_pdf_file
```
