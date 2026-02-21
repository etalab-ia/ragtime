---
name: explore-codebase
description: Navigate the rag-facile source code — find where things are implemented.
triggers: ["source", "code", "where is", "où est", "how is implemented", "comment est implémenté", "package", "module", "fichier", "file"]
---

# Skill: Explore Codebase

You are helping the user understand the rag-facile source structure. Use the available
tools to give accurate, specific answers rather than guessing.

## Navigation strategy

1. Call `get_agents_md()` first — AGENTS.md has the package tree and key file locations
2. Call `get_recent_git_activity()` for "what changed recently?" questions
3. Call `run_rag_facile("config show --format json")` to cross-reference config with implementation

## Package map (rag_facile namespace)

| Package | Import | Responsibility |
|---------|--------|---------------|
| `rag-core` | `rag_facile.core` | Config schema, shared types, presets |
| `ingestion` | `rag_facile.ingestion` | PDF/MD/HTML parsing → Albert upload |
| `storage` | `rag_facile.storage` | Albert collection management |
| `retrieval` | `rag_facile.retrieval` | Vector search → RetrievedChunk list |
| `reranking` | `rag_facile.reranking` | Cross-encoder re-scoring |
| `context` | `rag_facile.context` | Format chunks → LLM prompt string |
| `pipelines` | `rag_facile.pipelines` | Orchestrates all phases end-to-end |
| `query` | `rag_facile.query` | Multi-query / HyDE expansion |
| `albert-client` | `albert` | Albert API SDK (versioned independently) |

## Apps

| App | Entry point | Purpose |
|-----|------------|---------|
| `apps/cli` | `rag-facile` | Main CLI + chat harness |
| `apps/chainlit-chat` | `just run` | Chainlit web UI |
| `apps/reflex-chat` | `just run reflex` | Reflex web UI |

## When asked "where is X configured?"
Always cite the exact ragfacile.toml section and the Pydantic model that validates it
(found in `packages/rag-core/src/rag_facile/core/schema.py`).
