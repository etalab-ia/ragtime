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

## CI Checks

The CI pipeline runs:
- `ruff format --check` - Code formatting
- `ruff check` - Linting
- `ty check` - Type checking
- `moon run cli:test` - Tests

All checks must pass before merging.
