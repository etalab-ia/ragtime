# Contributing to RAG Facile

## Development Setup

### 1. Install the toolchain

Install proto (version manager):
```bash
curl -fsSL https://moonrepo.dev/install/proto.sh | bash
source ~/.bashrc  # or restart your terminal
```

Install required tools via proto:
```bash
proto install moon uv
```

The installer includes [just](https://github.com/casey/just) (task runner) automatically. No additional setup needed!

### System Dependencies

For Reflex frontend support, you need `unzip`. On Ubuntu/Debian:
```bash
sudo apt-get install unzip
```

On macOS:
```bash
brew install unzip
```

### 2. Clone and setup

```bash
git clone https://github.com/etalab-ia/rag-facile.git
cd rag-facile
just sync  # Installs dependencies and pre-commit hooks
```

> **Note:** `just sync` runs `uv sync` to install dependencies and `uv run pre-commit install` to set up automatic code quality checks on commit.

## Code Quality

### Using `just`

With [just](https://github.com/casey/just) installed:

```bash
just format       # Format code
just format-check # Check formatting
just lint         # Run linter
just lint-fix     # Run linter with auto-fix
just type-check   # Run type checker
just check        # Run all checks
```

### Using `moon run` Directly

```bash
moon run tools:format       # Format code
moon run tools:format-check # Check formatting
moon run tools:lint         # Run linter
moon run tools:lint-fix     # Run linter with auto-fix
moon run tools:type-check   # Run type checker
```

## Project Structure

```
rag-facile/
├── apps/                    # Applications
│   ├── cli/                 # rag-facile CLI tool
│   ├── chainlit-chat/       # Chainlit frontend (golden master)
│   └── reflex-chat/         # Reflex frontend (golden master)
├── packages/                # Shared packages
│   ├── rag-core/            # RAG Configuration System
│   ├── albert-client/       # Albert API SDK
│   └── retrieval/           # Unified retrieval package (basic + albert backends)
├── docs/                    # User and contributor documentation
│   ├── guides/              # Getting started, setup, pipelines
│   ├── reference/           # Components, config, ragfacile.toml
│   └── troubleshooting/     # Common issues and fixes
├── tools/                   # Development tools
│   ├── generate_templates.py # Template generator
│   └── moon.yml             # Code quality tasks
├── .moon/                   # Moon workspace config
│   ├── templates/           # Moon templates (source of truth)
│   └── toolchain.yml        # Python/uv/proto config
├── justfile                 # Developer task runner
├── CONTRIBUTING.md          # Contributing guide (you are here)
└── pyproject.toml           # Workspace config
```

## Templates

Templates live in `.moon/templates/` and are automatically bundled into the CLI package at build time via hatch's `force-include`.

## Running Tests

```bash
moon run cli:test
```

### Understanding Retrieval System

RAG Facile uses a **unified retrieval package** (`packages/retrieval/`) with two backends that are selected at runtime via `ragfacile.toml`:

- **basic** — Local PDF extraction via pypdf (lightweight, offline)
- **albert** — Full RAG via Albert API (ingestion, search, reranking)

Backend selection is automatic based on `storage.backend` config:
```toml
[storage]
backend = "albert-collections"  # Uses Albert RAG
# backend = "local-sqlite"      # Uses basic context injection
```

Both backends implement the same interface through the factory pattern:
```python
from retrieval import get_provider
provider = get_provider()  # Returns basic or albert based on config
context = provider.process_file("document.pdf")
```

The `context_loader.py` in each app dynamically loads the retrieval package, which then internally selects the right backend based on configuration.

**Key files:**
- `packages/retrieval/src/retrieval/` — Unified retrieval package
  - `__init__.py` — Factory pattern for backend selection
  - `basic.py` — Basic context injection provider
  - `albert.py` — Albert RAG retrieval
  - `parser.py` — Document parsing (Albert backend)
  - `ingestion.py` — Collection management (Albert backend)
  - `formatter.py` — Context formatting (Albert backend)
- `packages/rag-core/src/rag_core/pdf.py` — Shared PDF extraction utilities

When modifying retrieval logic:
- Test both backends (see `packages/retrieval/tests/`)
- Backend switching happens at runtime - no code changes needed
- `rag-core/pdf.py` provides shared PDF utilities used by both backends
- The `modules.yml` file determines which module is active (auto-generated from templates)

### Testing the Generate Dataset Command

The generate-dataset command supports pluggable providers. To test locally:

```bash
# Test with Letta provider
export LETTA_API_KEY="test-key"
export DATA_FOUNDRY_AGENT_ID="test-agent"
python -m pytest apps/cli/tests/test_generate_dataset.py

# Test with Albert provider
export OPENAI_API_KEY="test-key"
export OPENAI_BASE_URL="http://localhost:8000"
export OPENAI_MODEL="mistral-7b"
python -m pytest apps/cli/tests/test_generate_dataset.py
```

### Adding a New Data Foundry Provider

To add support for a new provider (e.g., another LLM service):

1. **Create provider class** in `apps/cli/src/cli/commands/eval/providers/{name}.py`:
   ```python
   from collections.abc import Iterator
   from .schema import GeneratedSample

   class MyProvider:
       def __init__(self, **kwargs):
           # Initialize with credentials
           pass

       def upload_documents(self, document_paths: list[str]) -> None:
           # Upload docs to your service
           pass

       def generate(self, num_samples: int) -> Iterator[GeneratedSample]:
           # Generate samples
           yield sample

       def cleanup(self) -> None:
           # Clean up resources
           pass
   ```

2. **Update factory** in `apps/cli/src/cli/commands/eval/providers/__init__.py`:
   ```python
   elif provider_name == "myservice":
       from .myservice import MyProvider
       return MyProvider(**kwargs)
   ```

3. **Add CLI option** in `apps/cli/src/cli/commands/generate_dataset.py`:
   - Add validation for provider-specific env vars
   - Route to factory with correct credentials

4. **Add tests** in `apps/cli/tests/test_generate_dataset.py`

All providers must:
- Implement the `DataFoundryProvider` protocol
- Output Ragas-compatible JSON (user_input, retrieved_contexts, reference, _metadata)
- Support French content
- Use `DocumentPreprocessor` for PDF extraction (prevents upload timeouts)
- Add logging via `logger = logging.getLogger(__name__)` for debugging
- Enforce strict JSONL-only output (no preamble or extraneous text)

## Testing install.sh from a branch

To test the install script in a clean Docker environment:

```bash
# Start a fresh Ubuntu container
docker run -it ubuntu:24.04

# Install curl (required to download the script)
apt-get update && apt-get install -y curl

# Run the installer from a branch
export RAG_FACILE_BRANCH=my-feature-branch
curl -fsSL https://raw.githubusercontent.com/etalab-ia/rag-facile/$RAG_FACILE_BRANCH/install.sh | bash
source ~/.bashrc

# Test workspace setup
rag-facile setup my-rag-app
```

The install script will automatically install other prerequisites (git, xz-utils) on Debian/Ubuntu.

## Commit Messages

We use [Conventional Commits](https://www.conventionalcommits.org/) for consistent versioning and changelogs. This enables automated release management via [release-please](https://github.com/googleapis/release-please).

### Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Types

Use these prefixes to indicate how commits should affect versioning:

- **`feat:`** - New feature (minor version bump)
- **`fix:`** - Bug fix (patch version bump)
- **`feat!:` or `fix!:`** - Breaking change (major version bump)
- **`docs:`** - Documentation changes (no release)
- **`chore:`** - Internal changes (no release)
- **`refactor:`** - Code reorganization (no release unless with `!`)

### Examples

**Single feature:**
```bash
git commit -m "feat: add support for PDF annotations"
```

**Bug fix:**
```bash
git commit -m "fix: resolve memory leak in pdf-context"
```

**Multiple changes in one commit:**
```bash
git commit -m "feat: add PDF viewer

This adds comprehensive PDF viewing capabilities
to reflex-chat.

fix: resolve rendering bug in pdf-context
Fixes #245"
```

**Breaking change:**
```bash
git commit -m "feat!: redesign CLI command interface

BREAKING CHANGE: the old 'rf init' command is now 'rf generate init'"
```

### Automated Releases

When commits with conventional prefixes (`feat:`, `fix:`, etc.) are merged to main, release-please automatically:

1. Creates a Release PR with:
   - Version bumps for affected packages
   - Generated changelog entries from commits
   - Updated `CHANGELOG.md` files

2. When the Release PR is merged:
   - Versions are locked in `pyproject.toml`
   - GitHub Release is created with release notes
   - Commit is tagged with version number

**No manual steps needed!** Just use conventional commits and release-please handles the rest.

## CI Checks

The CI pipeline runs:
- `ruff format --check` - Code formatting
- `ruff check` - Linting
- `ty check` - Type checking
- `moon run cli:test` - Tests

All checks must pass before merging.

## Configuration-Driven Architecture

RAG Facile uses a configuration-driven architecture. Most components (apps, packages) do not have hardcoded RAG parameters. Instead, they consume the `RAGConfig` Pydantic model from `packages/core-config`.

When adding new features that require configuration:
1. Define the schema in `packages/core-config/src/config/schema.py`.
2. Update presets in `packages/core-config/presets/` if applicable.
3. Access the configuration in your code using `rag_config.get_config()`.
