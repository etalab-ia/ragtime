# rag-facile memory

Persistent agentic memory for the rag-facile chat assistant.

## Storage

- **Semantic Store** (`memory.md`) — curated facts, preferences, identity
- **Episodic Logs** (`logs/YYYY-MM-DD.md`) — append-only daily conversation logs
- **Session Snapshots** (`sessions/YYYY-MM-DD-HHMM-<slug>.md`) — archived transcripts

## Search

Hybrid search combining SQLite FTS5 (keyword/BM25) with optional Albert API
embeddings (cosine similarity), fused via Reciprocal Rank Fusion.
