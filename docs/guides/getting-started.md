# Getting Started

This guide walks you through installing Ragtime and running your first RAG application.

> Looking for the 5-minute quickstart? See the [main README](../../README.md).

## Prerequisites

- An **Albert API key** — [request one here](https://albert.sites.beta.gouv.fr/)
- **curl** (pre-installed on macOS/Linux/WSL/Git Bash)

The installer handles everything else: it installs [uv](https://docs.astral.sh/uv/) (Python package manager), [just](https://just.systems/) (command runner), and the `ragtime` CLI as a global tool.

## Install

### Linux / macOS / WSL / Windows (Git Bash)

```bash
curl -fsSL https://raw.githubusercontent.com/etalab-ia/ragtime/main/install.sh | bash
```

Then **restart your terminal** (or run the `source` command shown by the installer).

## What the installer does

1. Installs **uv** (Python package manager) — if not already present
2. Installs **just** (command runner) — if not already present
3. Fetches the latest release tag from GitHub
4. Installs **ragtime** as a global tool via `uv tool install`

Total toolchain: **curl + uv + just + ragtime**. No proto, no moon.

## Your first app

After installation, create and configure your project:

```bash
# Create your RAG project (prompts for API key and preferences)
ragtime setup mon-projet

# Start the Chainlit app
cd mon-projet && just run
```

Your app opens at **http://localhost:8000** — ask questions about your ingested documents.

## Available commands

Run `just` inside `my-rag-app/` to see all available commands:

| Command | Description |
|---------|-------------|
| `just run` | Start the Chainlit web application |
| `just sync` | Install / update dependencies |

## Using the Ragtime CLI

`ragtime` is installed globally — run it from anywhere:

```bash
ragtime --help
```

Common commands:

```bash
# Create a new RAG project
ragtime setup mon-projet


# View your current RAG configuration
ragtime config show

# Change a configuration value
ragtime config set retrieval.top_k 15

# List available Albert public collections
ragtime collections list

# Generate a synthetic Q/A evaluation dataset
ragtime generate-dataset ./docs -o dataset.jsonl
```

Or use the shortcut recipes in your project's `justfile`:

```bash
just learn   # same as: ragtime learn
```

## Advanced: setup options

`ragtime setup` accepts flags for non-default configurations:

```bash
# Expert mode — choose preset, frontend, and pipeline interactively
ragtime setup mon-projet --expert

# Available presets: fast, balanced, accurate, legal, hr
ragtime setup mon-projet --preset legal
```

## Upgrading

To get the latest version, re-run the installer:

```bash
curl -fsSL https://raw.githubusercontent.com/etalab-ia/ragtime/main/install.sh | bash
```

This reinstalls the `ragtime` CLI pinned to the latest release. Your existing project workspaces are not affected.

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
curl -fsSL https://raw.githubusercontent.com/etalab-ia/ragtime/main/install.sh | bash
```

The installer uses `curl` and `uv` which both respect these environment variables automatically.
