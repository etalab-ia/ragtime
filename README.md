# RAG Facile

```
 ██████╗  █████╗  ██████╗     ███████╗ █████╗  ██████╗██╗██╗     ███████╗
 ██╔══██╗██╔══██╗██╔════╝     ██╔════╝██╔══██╗██╔════╝██║██║     ██╔════╝
 ██████╔╝███████║██║  ███╗    █████╗  ███████║██║     ██║██║     █████╗
 ██╔══██╗██╔══██║██║   ██║    ██╔══╝  ██╔══██║██║     ██║██║     ██╔══╝
 ██║  ██║██║  ██║╚██████╔╝    ██║     ██║  ██║╚██████╗██║███████╗███████╗
 ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝     ╚═╝     ╚═╝  ╚═╝ ╚═════╝╚═╝╚══════╝╚══════╝
```

> [!IMPORTANT]
> This project is a starter kit for RAG applications in the French government.

## Overview

RAG Facile provides a foundation for building RAG (Retrieval-Augmented Generation) applications in the French government, specifically using the [Albert API](https://albert.sites.beta.gouv.fr/). It is designed for exploratory greenfield projects.

## Quick Start

### 1. Install the CLI

One command installs the entire toolchain (proto, moon, uv) and the CLI:

```bash
curl -fsSL https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.sh | bash
source ~/.bashrc  # or restart your terminal
```

> **Note**: On Ubuntu/Debian, the installer will automatically install prerequisites (git, curl, xz-utils, unzip) if needed.

Verify the installation:

```bash
rag-facile --help
```

### 2. Generate Your Workspace

One command gets you to a running RAG app:

```bash
rag-facile generate workspace my-rag-app
```

The CLI will guide you through:
1. **Frontend selection** - Choose Chainlit or Reflex
2. **Module selection** - Add PDF processing, vector stores, etc.
3. **Environment configuration** - Set your Albert API key and preferences

After configuration, the CLI automatically:
- Generates your workspace with the selected components
- Creates your `.env` file with your credentials
- Installs all dependencies with `uv sync`
- Starts the development server

Your app will open in the browser, ready to use!

## Available Components

### Frontend Apps

| App | Description | Port |
|-----|-------------|------|
| **Chainlit Chat** | Chat interface with file upload support | 8000 |
| **Reflex Chat** | Interactive chat with modern UI | 3000 |

### Modules

| Module | Description | Status |
|--------|-------------|--------|
| **PDF Context** | Extract and process PDF documents | ✅ Available |
| **Chroma Context** | Vector store for semantic search | 🚧 Coming Soon |

## Upgrading the CLI

To upgrade to the latest version, re-run the installer:

```bash
curl -fsSL https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.sh | bash
```

## Generated Workspace Structure

After running `rag-facile generate workspace`, you'll have:

```
my-rag-app/
├── .moon/              # Moon configuration
│   ├── templates/      # Available templates for future expansion
│   ├── toolchain.yml   # Python/uv configuration
│   └── workspace.yml   # Workspace settings
├── apps/
│   └── chainlit-chat/  # Your selected frontend app
│       ├── app.py
│       ├── .env        # Your API credentials
│       └── ...
├── packages/
│   └── pdf-context/    # Selected modules
├── .python-version     # Pinned to Python 3.13
├── justfile            # Common commands (just dev, just check, etc.)
└── pyproject.toml      # Workspace dependencies
```

## Running Your App

After generation, use the justfile commands:

```bash
cd my-rag-app
just run                    # Run all apps
just run chainlit-chat      # Run a specific app
```

### Available Commands

| Command | Description |
|---------|-------------|
| `just run` | Run all apps |
| `just run <name>` | Run a specific app (e.g., `just run chainlit-chat`) |
| `just format` | Format code with ruff |
| `just lint` | Run linter |
| `just check` | Run all checks (format, lint, type-check) |
| `just sync` | Sync dependencies with uv |
| `just add <template>` | Add a new app from template |

## Contributing

Want to contribute to RAG Facile itself? See [CONTRIBUTING.md](CONTRIBUTING.md) for the architecture overview and development setup.

## License

See [LICENSE](LICENSE) for details.
