# Getting Started

This guide walks you through installing RAG Facile and running your first RAG application.

> Looking for the 5-minute quickstart? See the [main README](../../README.md).

## Prerequisites

- An **Albert API key** — [request one here](https://albert.sites.beta.gouv.fr/)
- **curl** (pre-installed on macOS/Linux/WSL)

The installer handles everything else: it installs [uv](https://docs.astral.sh/uv/) (Python package manager) and [just](https://just.systems/) (command runner), then downloads and sets up a ready-to-run workspace.

## Install

### Linux / macOS / WSL

```bash
curl -fsSL https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.sh | bash
```

Then **restart your terminal** (or run the `source` command shown by the installer).

### Windows (PowerShell)

```powershell
irm https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.ps1 | iex
```

Open a new PowerShell window after installation completes.

## What the installer does

1. Installs **uv** (Python package manager) — if not already present
2. Installs **just** (command runner) — if not already present
3. Downloads the latest **RAG Facile workspace** zip from GitHub Releases
4. Extracts it to `./my-rag-app/`
5. Runs `uv sync` to install Python dependencies

Total toolchain: just **curl + uv + just**. No proto, no moon, no global CLI tools.

## Your first app

After installation:

```bash
# 1. Add your Albert API key
cd my-rag-app
cp .env.template .env
# Edit .env and set OPENAI_API_KEY=<your-key>

# 2. Start the Chainlit app
just run
```

Your app opens at **http://localhost:8000** — upload documents and ask questions.

## Available commands

Run `just` inside `my-rag-app/` to see all available commands:

| Command | Description |
|---------|-------------|
| `just run` | Start the Chainlit web application |
| `just learn` | Open the interactive RAG learning assistant |
| `just sync` | Install / update dependencies |

## Using the RAG Facile CLI

The CLI (`rag-facile`) is included as a development dependency in your workspace. Run it with:

```bash
cd my-rag-app
uv run rag-facile --help
```

Common commands:

```bash
# Open the interactive RAG learning assistant
uv run rag-facile learn

# View your current RAG configuration
uv run rag-facile config show

# Change a configuration value
uv run rag-facile config set retrieval.top_k 15

# List available Albert public collections
uv run rag-facile collections list

# Generate a synthetic Q/A evaluation dataset
uv run rag-facile generate-dataset ./docs -o dataset.jsonl
```

Or use the shortcut recipes in `justfile`:

```bash
just learn   # same as: uv run rag-facile learn
```

## Advanced: scaffold a custom workspace

Power users who want to choose a different preset, frontend (Reflex), or RAG pipeline can scaffold a workspace from scratch:

```bash
# Default (balanced preset, Chainlit, Albert RAG)
uv run rag-facile setup my-custom-app

# Expert mode — choose preset, frontend, and pipeline interactively
uv run rag-facile setup my-custom-app --expert

# Available presets: fast, balanced, accurate, legal, hr
uv run rag-facile setup my-custom-app --preset legal
```

## Upgrading

To get the latest version, re-run the installer — it downloads a fresh workspace zip:

```bash
# Linux / macOS / WSL
curl -fsSL https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.sh | bash
```

```powershell
# Windows (PowerShell)
irm https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.ps1 | iex
```

> **Note**: Re-running the installer creates a new `my-rag-app/` directory. Your existing workspace is not modified.

## Troubleshooting

### `just: command not found`

Restart your terminal, or add `~/.local/bin` to your PATH:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Add this line to your shell profile (`~/.zshrc` or `~/.bashrc`) to make it permanent.

### `uv: command not found`

Same as above — restart your terminal after installation.

### Albert API errors (401 / 403)

Your `OPENAI_API_KEY` in `.env` is missing or incorrect.
[Request an API key here](https://albert.sites.beta.gouv.fr/).

### Behind a corporate proxy or VPN?

Set standard proxy environment variables before running the installer:

```bash
export HTTP_PROXY=http://proxy.example.com:3128
export HTTPS_PROXY=http://proxy.example.com:3128
curl -fsSL https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.sh | bash
```

The installer uses `curl` and `uv` which both respect these environment variables automatically.
