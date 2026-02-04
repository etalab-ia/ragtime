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
uv sync
```

## Code Quality

### Using Just

With [just](https://github.com/casey/just) installed:

```bash
just format       # Format code
just format-check # Check formatting
just lint         # Run linter
just lint-fix     # Run linter with auto-fix
just type-check   # Run type checker
just check        # Run all checks
```

### Using Moon directly

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
│   ├── chainlit-chat/       # Chainlit frontend
│   └── reflex-chat/         # Reflex frontend
├── packages/                # Shared packages
│   └── pdf-context/         # PDF processing
├── tools/                   # Development tools
│   └── moon.yml             # Code quality tasks
├── .moon/                   # Moon workspace config
│   └── templates/           # Moon templates (source of truth)
├── justfile                 # Developer task runner
└── pyproject.toml           # Workspace config
```

## Templates

Templates live in `.moon/templates/` and are automatically bundled into the CLI package at build time via hatch's `force-include`.

## Running Tests

```bash
moon run cli:test
```

### Testing the Eval Generate Command

The eval generate command supports pluggable providers. To test locally:

```bash
# Test with Letta provider
export LETTA_API_KEY="test-key"
export DATA_FOUNDRY_AGENT_ID="test-agent"
python -m pytest apps/cli/tests/test_eval_generate.py

# Test with Albert provider
export OPENAI_API_KEY="test-key"
export OPENAI_BASE_URL="http://localhost:8000"
export OPENAI_MODEL="mistral-7b"
python -m pytest apps/cli/tests/test_eval_generate.py
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

3. **Add CLI option** in `apps/cli/src/cli/commands/eval/generate.py`:
   - Add validation for provider-specific env vars
   - Route to factory with correct credentials

4. **Add tests** in `apps/cli/tests/test_eval_generate.py`

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

# Test workspace generation
rag-facile generate workspace my-rag-app
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
