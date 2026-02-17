# Getting Started

This guide walks through every installation option and helps you choose the right project structure for your needs.

> Looking for the 5-minute quickstart? See the [main README](../../README.md).

## Prerequisites

- An **Albert API key** — [request one here](https://albert.sites.beta.gouv.fr/)
- **git** and **curl** installed (the installer handles the rest)
- On Windows: PowerShell 5.1+ or Git Bash

## Installation

The installer sets up the full toolchain automatically: [proto](https://moonrepo.dev/docs/proto) (toolchain manager) → [moon](https://moonrepo.dev/) (task runner) → [uv](https://docs.astral.sh/uv/) (Python package manager) → `rag-facile` CLI.

### Linux / macOS / WSL

```bash
curl -fsSL https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.sh | bash
```

Then **restart your terminal** (or run the `source` command shown by the installer).

> **Note**: On Ubuntu/Debian, the installer will automatically install prerequisites (git, curl, xz-utils, unzip) if needed.

### Windows (PowerShell) — Recommended

```powershell
irm https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.ps1 | iex
```

Open a new PowerShell window and you're ready to go.

> For a complete walkthrough, see the [Windows Setup Guide](windows-setup.md).

### Windows (Git Bash / MSYS2)

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.sh)
source ~/.bashrc
```

### Behind a Corporate Proxy or VPN?

The installer automatically detects and configures proxy support. If you run into issues, see:

- [Proxy & Network Setup](proxy-setup.md)
- [Proxy Troubleshooting](../troubleshooting/proxy.md)

### Verify

```bash
rag-facile --help
```

### Upgrading

To upgrade to the latest version, re-run the installer:

```bash
# Linux / macOS / WSL
curl -fsSL https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.sh | bash
```

```powershell
# Windows (PowerShell)
irm https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.ps1 | iex
```

### Uninstalling

To remove RAG Facile and its entire toolchain:

```bash
rag-facile uninstall
```

See the [Uninstalling Guide](uninstalling.md) for manual steps and details.

## Setting Up Your Workspace

One command gets you to a running RAG app:

```bash
rag-facile setup my-rag-app
```

The CLI will interactively guide you through:

1. **Configuration preset** — Balanced, Fast, Accurate, Legal, or HR
2. **Environment** — Your Albert API key (presets handle the rest)

By default, the CLI creates a simple standalone Chainlit project using the Albert RAG pipeline. For advanced options (project structure, frontend, pipeline selection), use `--expert`:

```bash
rag-facile setup my-rag-app --expert
```

After configuration, the CLI automatically:

- Creates your project with all pipeline components
- Writes `ragfacile.toml` based on your chosen preset
- Creates your `.env` file with your credentials
- Installs all dependencies with `uv sync`
- Starts the development server

Your app will open in the browser, ready to use.

## Project Structure

```
my-rag-app/
├── pyproject.toml          # All dependencies in one place
├── .env                    # Your API credentials
├── ragfacile.toml          # RAG pipeline configuration
├── app.py                  # Your application code
├── chainlit.md             # Chat welcome message (Chainlit only)
├── albert/                 # Albert API client
├── rag_core/               # Configuration system
├── pipelines/              # Pipeline orchestration
├── ingestion/              # Document parsing
├── retrieval/              # Vector search
├── reranking/              # Cross-encoder re-scoring
├── context/                # Context assembly
└── storage/                # Collection management
```

## Running Your App

```bash
cd my-rag-app
just run
```

## Advanced: Project Structures (`--expert`)

With `--expert`, you can choose between a simple standalone project or a monorepo:

### Simple (Default)

Best for: **Quick prototypes, single-app deployments, learning RAG Facile**

- Familiar single-project structure
- No build tools to learn
- Easy to understand and modify

### Monorepo

Best for: **Team projects, multiple apps sharing code, production deployments**

```
my-rag-app/
├── .moon/              # Moon workspace configuration
├── apps/
│   └── chainlit-chat/  # Your selected frontend app
├── packages/
│   ├── rag-core/       # Configuration system
│   ├── albert-client/  # Albert API SDK
│   ├── retrieval/      # Vector search
│   ├── reranking/      # Cross-encoder re-scoring
│   ├── context/        # Context assembly
│   ├── storage/        # Collection management
│   ├── ingestion/      # Document parsing
│   └── pipelines/      # Pipeline orchestration
├── ragfacile.toml      # RAG pipeline configuration
├── justfile            # Common commands
└── pyproject.toml      # Workspace root
```

**Advantages:**
- Multiple apps can share packages
- Consistent tooling across apps
- Easy to add new apps with `just add <template>`
- Built-in task runner with [Moon](https://moonrepo.dev/)

### Which Should I Choose?

| Scenario | Recommendation |
|----------|----------------|
| First time using RAG Facile | **Simple** (default) |
| Building a quick prototype | **Simple** (default) |
| Single application deployment | **Simple** (default) |
| Multiple related apps | **Monorepo** (`--expert`) |
| Team with shared components | **Monorepo** (`--expert`) |
| Need to add apps later | **Monorepo** (`--expert`) |

### Running a Monorepo

```bash
cd my-rag-app
just run chainlit-chat      # Run a specific app
just run                    # Run all apps
```

### Available `just` Commands

| Command | Description |
|---------|-------------|
| `just run` | Run all apps |
| `just run <name>` | Run a specific app (e.g., `just run chainlit-chat`) |
| `just format` | Format code with ruff |
| `just lint` | Run linter |
| `just check` | Run all checks (format, lint, type-check) |
| `just sync` | Sync dependencies with uv |
| `just add <template>` | Add a new app from template |
