# query-expansion

Query expansion for the RAG Facile pipeline — bridges the vocabulary gap between
colloquial user queries and formal French administrative language.

## Strategies

### Multi-Query Expansion (default)

Generates 3–5 variations of the user's query using an LLM, targeting formal
administrative French:

- Expands acronyms: "APL" → "Aide Personnalisée au Logement"
- Rewrites colloquial phrasing into formal administrative language
- Generates synonyms from the official French administrative vocabulary

All variations are searched in parallel; results are fused via Reciprocal Rank Fusion
(RRF) before reranking.

### HyDE (Hypothetical Document Embeddings)

Generates a hypothetical administrative document that would ideally answer the query.
The document's text is embedded and searched instead of the raw query, matching the
formal vocabulary of indexed documents.

## Usage

Enable in `ragfacile.toml`:

```toml
[query]
strategy = "multi_query"   # or "hyde"
num_variations = 3         # multi_query only (1-5)
include_original = true    # always include the original query
model = "openweight-medium"
```

## Architecture

Requires `instructor` (via `albert-client`) for structured LLM output.
Results from multiple queries are aggregated with `fuse_results()` from the
`retrieval` package before passing to the reranker.
