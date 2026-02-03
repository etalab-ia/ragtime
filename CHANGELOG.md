# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-02-03

### Added

- **CLI Enhancements** (#18, #17)
  - Rename CLI to `rag-facile` for consistency
  - Add ASCII banner on CLI startup for better UX
  - Add Justfile for generated projects to simplify common tasks
  - Make CLI installable via `uv tool install` for easy distribution

- **Bootstrap Installer** (#16)
  - Create comprehensive bootstrap installer (`install.sh`)
  - Bundle templates into CLI at build time for zero-dependency deployment
  - Support for system prerequisites auto-installation on Debian/Ubuntu

- **Template System Overhaul** (#14, #7)
  - Refactor from simple string templates to Moon codegen for production-grade template handling
  - Implement hybrid LibCST + ast-grep pipeline for intelligent code transformation
  - Support code-aware template generation for Python and other languages

- **Application Templates** (#5, #6)
  - Add `chainlit-chat` template with Grit-based code generation
  - Add support for `reflex-chat` in template generation CLI
  - Enable template generation CLI to scaffold multiple app types

- **Core Applications** (#4, #3)
  - Implement `chainlit-chat` application with Albert API integration
  - Add `reflex-chat` application with Albert API support
  - Integrate PDF context support in reflex-chat for document-aware RAG

- **PDF Context Package** (#12, #13)
  - Extract PDF context handling into reusable `pdf-context` package
  - Add PDF context support to reflex-chat application
  - Implement refined UI for PDF interaction

- **Workspace Generation** (#15)
  - Create `rf generate` command for one-command workspace scaffolding
  - Enable rapid project initialization with all necessary boilerplate

- **Development Tools & Documentation** (#8, #9, #10, #11, #2)
  - Add direnv configuration for automatic environment setup
  - Separate user-facing and contributor documentation
  - Add AGENTS.md with comprehensive project knowledge
  - Clarify available vs planned application templates in README

### Initial Release

- Project setup with monorepo structure using moonrepo and uv
- Foundation for multi-app RAG framework targeting French government use cases
- Python 3.13+ codebase with ruff (linting/formatting) and ty (type checking)
- Extensible template system for scaffolding new applications

---

## How to Read This Changelog

- **Added**: New features and capabilities
- **Changed**: Modifications to existing features
- **Fixed**: Bug fixes
- **Deprecated**: Features marked for future removal
- **Removed**: Features that have been removed
- **Security**: Security-related fixes

## Release History

| Version | Date | Notes |
|---------|------|-------|
| 0.1.0 | 2026-02-03 | Initial release with core RAG framework and applications |
