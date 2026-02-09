# Changelog

All notable changes to albert-client will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project uses independent versioning (matches Albert API spec, not monorepo releases).

## [0.3.7] - 2026-02-07

### Added

- Initial SDK implementation with OpenAI-compatible passthrough
- `AlbertClient` class for sync operations
- `AsyncAlbertClient` class for async/await operations  
- Full type safety with Pydantic models (`.to_dict()`, `.to_json()` helpers)
- OpenAI-compatible endpoints: `chat`, `embeddings`, `audio`, `models`
- Environment variable support (`ALBERT_API_KEY`)
- Comprehensive test suite with respx mocking

### Architecture

- Composition pattern: wraps `openai.OpenAI` client internally
- Clean separation between OpenAI-compatible and Albert-specific features
- Pydantic `BaseModel` for all response types (following OpenAI SDK pattern)

[0.3.7]: https://github.com/etalab-ia/rag-facile/tree/v0.3.7/packages/albert-client
