# rag-facile-lib

Python library for building RAG (Retrieval-Augmented Generation) applications, designed for the French government ecosystem.

## Installation

```bash
uv add rag-facile-lib
```

## Usage

```python
from rag_facile.core import get_config
from rag_facile.pipelines import process_file, process_query
from albert import AsyncAlbertClient
```

## Packages included

- `rag_facile.core` — Configuration, schema, presets
- `rag_facile.pipelines` — RAG pipeline orchestration
- `rag_facile.ingestion` — Document parsing (PDF, Markdown, HTML)
- `rag_facile.retrieval` — Vector search
- `rag_facile.reranking` — Cross-encoder re-scoring
- `rag_facile.context` — Context formatting for LLM prompts
- `rag_facile.storage` — Collection management

The `albert-client` package (Albert API SDK) is installed as a separate dependency.
