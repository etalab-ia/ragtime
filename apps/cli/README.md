# RAG Facile CLI

The `rag-facile` CLI helps you generate RAG workspaces for the French government.

## Installation

### Option 1: Install Script (Recommended)

One command installs the entire toolchain (proto, moon, uv) and the CLI:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.sh)
source ~/.bashrc  # or restart your terminal
```

### Option 2: Manual Installation

If you already have `uv` installed:

```bash
uv tool install rag-facile --from git+https://github.com/etalab-ia/rag-facile.git#subdirectory=apps/cli
```

To upgrade:

```bash
uv tool install rag-facile --force --from git+https://github.com/etalab-ia/rag-facile.git#subdirectory=apps/cli
```

### Option 3: One-time Usage

Run directly without installing:

```bash
uvx --from git+https://github.com/etalab-ia/rag-facile.git#subdirectory=apps/cli rag-facile [command]
```

## Usage

```bash
# Show all available commands
rag-facile --help

# Generate a new workspace
rag-facile generate workspace my-rag-app

# Check version
rag-facile version
```

## Commands

### `generate workspace`

Generates a new RAG workspace with your choice of structure, frontend, and modules.

```bash
rag-facile generate workspace <name>
```

The CLI will guide you through:
1. **Project structure** - Choose between:
   - **Simple** - Flat structure, single app, easy to understand (recommended for getting started)
   - **Monorepo** - Multi-app workspace with shared packages (for larger projects)
2. **Frontend selection** - Choose Chainlit or Reflex
3. **Module selection** - Add PDF processing, vector stores, etc.
4. **Environment configuration** - Set your Albert API key and preferences

See the main [README](../../README.md) for detailed comparison of project structures.

### `eval generate`

Generate synthetic Q/A evaluation datasets from your documents using Letta Cloud.

```bash
rag-facile eval generate ./docs -o golden_dataset.jsonl -n 50
```

**Options:**
- `-o, --output` - Output JSONL file path (default: `golden_dataset.jsonl`)
- `-n, --samples` - Target number of Q/A pairs (default: 50)
- `--agent-id` - Data Foundry agent ID (or set `DATA_FOUNDRY_AGENT_ID` env var)

**Environment variables:**
- `LETTA_API_KEY` - Your Letta Cloud API key ([get one here](https://app.letta.com/api-keys))
- `DATA_FOUNDRY_AGENT_ID` - Pre-configured Data Foundry agent ID

## Development

The CLI is built with [Typer](https://typer.tiangolo.com/) and [Rich](https://rich.readthedocs.io/).

For development setup and contribution guidelines, see the main [CONTRIBUTING.md](../../CONTRIBUTING.md) file.

**Source code structure:**
- `src/cli/` - Main CLI package
- `src/cli/commands/` - Command definitions
