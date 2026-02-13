# Changelog

All notable changes to albert-client will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project uses independent versioning (matches Albert API spec, not monorepo releases).

## [0.5.0](https://github.com/etalab-ia/rag-facile/compare/v0.4.0...v0.5.0) (2026-02-13)


### Features

* Add Albert Client SDK - Complete Python SDK for Albert API ([ebf3d55](https://github.com/etalab-ia/rag-facile/commit/ebf3d55fa603cf1f9fcfed0024dae6f646080d0f))
* add albert-client SDK Phase 1 (core client + OpenAI passthrough) ([0424d2c](https://github.com/etalab-ia/rag-facile/commit/0424d2c1b8adf9f0eb6bcb9d3a2fcc35f28da5a1))
* add OPENAI_API_KEY fallback for AlbertClient initialization ([418b5f2](https://github.com/etalab-ia/rag-facile/commit/418b5f233d3432ea8d331ec0a3c9158d589fe5f9))
* **albert-client:** update to v0.4.0 API spec ([246fc11](https://github.com/etalab-ia/rag-facile/commit/246fc11ce3b171a9bcba741dce3fe94a52f15e56))
* **albert-client:** update to v0.4.0 API spec ([46b348b](https://github.com/etalab-ia/rag-facile/commit/46b348b1098fe4fe2097c0742edf9c60921fccf0))
* component-first architecture refactoring ([e289d15](https://github.com/etalab-ia/rag-facile/commit/e289d157ac2d45c2b82d47be1fdef775874c6281))
* component-first architecture refactoring with auth fixes ([23425ff](https://github.com/etalab-ia/rag-facile/commit/23425ffd7745c3cd06c03d5e508cb5bed04da618))
* implement Phase 2 (Search + Rerank) for Albert Client SDK ([675ad56](https://github.com/etalab-ia/rag-facile/commit/675ad56815574b385edd42042f379d84740ec592))
* implement Phase 3 (Collections & Documents) for Albert Client SDK ([f7d29af](https://github.com/etalab-ia/rag-facile/commit/f7d29af15ae09bc1b5be3402331d382641a0b41a))
* implement Phase 4 (Tools & Monitoring) for Albert Client SDK ([4b0abba](https://github.com/etalab-ia/rag-facile/commit/4b0abba2fe3cd0e0d6433f3915f31bd38ebe36d3))


### Bug Fixes

* add albert-client to workspace dependencies and test dependencies ([8d405f8](https://github.com/etalab-ia/rag-facile/commit/8d405f8c4ef54915350ba87a4792475567e1b710))
* add missing authentication headers to Albert API requests ([1cd1fc6](https://github.com/etalab-ia/rag-facile/commit/1cd1fc62f55e4545d516e2f33b03b6dd7811f906))
* centralize ruff config and remove unused resources directory ([552d071](https://github.com/etalab-ia/rag-facile/commit/552d07105c097ce881e83b0946f1db2ef2ebb13f))
* correct API usage in documentation examples ([122beaa](https://github.com/etalab-ia/rag-facile/commit/122beaaaee26265b58643682c6b11fdb61fc34ca))
* use correct Albert API model aliases in documentation ([a9fcd03](https://github.com/etalab-ia/rag-facile/commit/a9fcd035e851f307a3576d04802cce1a28c85dca))


### Documentation

* add Albert Client SDK documentation ([eeb5d8d](https://github.com/etalab-ia/rag-facile/commit/eeb5d8d7332910812e10bc0862f4fecbd0eb7436))
* add Albert Client SDK with audience-focused documentation ([6a3a51e](https://github.com/etalab-ia/rag-facile/commit/6a3a51e7e3c8126ca34ed08ec4054cded5ead16b))
* **albert-client:** document model aliases and api version ([c606fe4](https://github.com/etalab-ia/rag-facile/commit/c606fe4f56bba506508ba27433270ee1a3c1da9b))
* **albert-client:** improve docstrings and address PR review ([cbf5dce](https://github.com/etalab-ia/rag-facile/commit/cbf5dce13e6d861d64b859e824f39c46becd8b5d))
* improve type safety documentation in albert-client SDK ([dc7d2af](https://github.com/etalab-ia/rag-facile/commit/dc7d2afddf9de71b5fb289d5e6b453a93f6c299d))
* refactor README into focused documentation files ([c53e312](https://github.com/etalab-ia/rag-facile/commit/c53e312b011ba60d2e40cc7ad389a48f73cd70ba))

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
