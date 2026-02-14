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
source ~/.bashrc  # or restart your terminal
```

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

## Setting Up Your Workspace

One command gets you to a running RAG app:

```bash
rag-facile setup my-rag-app
```

The CLI will interactively guide you through:

1. **Project structure** — Simple or Monorepo (see below)
2. **Configuration preset** — Balanced, Fast, Accurate, Legal, or HR
3. **Frontend** — Chainlit or Reflex
4. **Retrieval module** — PDF (local extraction) or Albert RAG (server-side parsing + search)
5. **Environment** — Your Albert API key (presets handle the rest)

After configuration, the CLI automatically:

- Creates your workspace with the selected components
- Writes `ragfacile.toml` based on your chosen preset
- Creates your `.env` file with your credentials
- Installs all dependencies with `uv sync`
- Starts the development server

Your app will open in the browser, ready to use.

## Project Structure Options

### Simple (Recommended for Getting Started)

Best for: **Quick prototypes, single-app deployments, learning RAG Facile**

```
my-rag-app/
├── pyproject.toml          # All dependencies in one place
├── .env                    # Your API credentials
├── app.py                  # Your application code
├── context_loader.py       # Module loading logic
├── modules.yml             # Retrieval module configuration
├── ragfacile.toml          # RAG pipeline configuration
├── chainlit.md             # Chat welcome message (Chainlit only)
└── retrieval_basic/ OR retrieval_albert/   # Selected retrieval module
```

**Advantages:**
- Familiar single-project structure
- No build tools to learn
- Easy to understand and modify
- Simple deployment

### Monorepo (For Multi-App Projects)

Best for: **Team projects, multiple apps sharing code, production deployments**

```
my-rag-app/
├── .moon/              # Moon workspace configuration
│   ├── templates/      # Templates for adding new apps
│   ├── toolchain.yml   # Python/uv configuration
│   └── workspace.yml   # Workspace settings
├── apps/
│   └── chainlit-chat/  # Your selected frontend app
│       ├── app.py
│       ├── .env        # Your API credentials
│       └── ...
├── packages/
│   ├── rag-core/       # Configuration system
│   ├── albert-client/  # Albert API SDK
│   └── retrieval/      # Unified retrieval package (basic + albert backends)
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
| First time using RAG Facile | **Simple** |
| Building a quick prototype | **Simple** |
| Single application deployment | **Simple** |
| Multiple related apps | **Monorepo** |
| Team with shared components | **Monorepo** |
| Need to add apps later | **Monorepo** |

## Running Your App

### Simple Structure

```bash
cd my-rag-app
just run
```

### Monorepo Structure

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
