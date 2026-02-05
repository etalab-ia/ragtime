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

# Setup a new workspace
rag-facile setup my-rag-app

# Check version
rag-facile version
```

## Commands

### `setup`

Setup a new RAG workspace with your choice of structure, frontend, and modules.

```bash
rag-facile setup <name>
```

The CLI will guide you through:
1. **Project structure** - Choose between:
   - **Simple** - Flat structure, single app, easy to understand (recommended for getting started)
   - **Monorepo** - Multi-app workspace with shared packages (for larger projects)
2. **Frontend selection** - Choose Chainlit or Reflex
3. **Module selection** - Add PDF processing, vector stores, etc.
4. **Environment configuration** - Set your Albert API key and preferences

See the main [README](../../README.md) for detailed comparison of project structures.

### `generate-dataset`

Generate synthetic Q/A evaluation datasets from your documents. Supports multiple providers: Letta Cloud or self-hosted Albert API.

```bash
rag-facile generate-dataset ./docs -o golden_dataset.jsonl -n 50 --provider letta
```

**Options:**
- `-p, --provider` - Provider to use (`letta` or `albert`) - **required**
- `-o, --output` - Output JSONL file path (default: `golden_dataset.jsonl`)
- `-n, --samples` - Target number of Q/A pairs (default: 50)
- `--agent-id` - Data Foundry agent ID for Letta (or set `DATA_FOUNDRY_AGENT_ID` env var)
- `--debug` - Enable debug logging (verbose output to console + file)

**For Letta Cloud Provider:**

```bash
export LETTA_API_KEY="your-api-key"           # Get at https://app.letta.com/api-keys
export DATA_FOUNDRY_AGENT_ID="agent-xxx"      # Pre-configured agent ID

rag-facile generate-dataset ./docs -o golden_dataset.jsonl --provider letta
```

**For Albert API Provider (Self-Hosted):**

```bash
export OPENAI_API_KEY="your-api-key"          # Albert API key
export OPENAI_BASE_URL="http://localhost:8000"  # Albert API endpoint
export OPENAI_MODEL="mistral-7b"              # Model to use

rag-facile generate-dataset ./docs -o golden_dataset.jsonl --provider albert
```

**Output:**

Creates two files:

1. **JSONL dataset** (`golden_dataset.jsonl`) - Ragas-compatible format with French Q/A pairs:
   ```json
   {
     "user_input": "Quel est le délai de recours administratif?",
     "retrieved_contexts": ["Le délai de recours est de deux mois..."],
     "reference": "Le délai de recours administratif est de deux mois.",
     "_metadata": {"source_file": "code.pdf", "quality_score": 0.95}
   }
   ```

2. **Debug log** (`golden_dataset.jsonl.log`) - Trace of all interactions:
   - INFO level: Document uploads, provider IDs, session progress
   - DEBUG level (with `--debug` flag): Full prompts and responses

**Debug Mode:**

```bash
# Standard mode - clean output, INFO logs only to file
rag-facile generate-dataset ./docs -o output.jsonl --provider albert

# Debug mode - verbose console + file logging
rag-facile generate-dataset ./docs -o output.jsonl --provider albert --debug
```

**Debug Features:**
- See exact prompts sent to LLM
- View complete LLM responses
- Track provider IDs (Letta Folder ID, Albert Collection ID, Conversation ID)
- Monitor document uploads
- Full error traces for troubleshooting

## Development

The CLI is built with [Typer](https://typer.tiangolo.com/) and [Rich](https://rich.readthedocs.io/).

For development setup and contribution guidelines, see the main [CONTRIBUTING.md](../../CONTRIBUTING.md) file.

**Source code structure:**
- `src/cli/` - Main CLI package
- `src/cli/commands/` - Command definitions
