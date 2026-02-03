# RAG Facile

[![Release](https://img.shields.io/github/v/release/etalab-ia/rag-facile?style=flat-square)](https://github.com/etalab-ia/rag-facile/releases)
[![License](https://img.shields.io/github/license/etalab-ia/rag-facile?style=flat-square)](LICENSE)

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
1. **Project structure** - Choose Simple or Monorepo (see below)
2. **Frontend selection** - Choose Chainlit or Reflex
3. **Module selection** - Add PDF processing, vector stores, etc.
4. **Environment configuration** - Set your Albert API key and preferences

After configuration, the CLI automatically:
- Generates your workspace with the selected components
- Creates your `.env` file with your credentials
- Installs all dependencies with `uv sync`
- Starts the development server

Your app will open in the browser, ready to use!

## Project Structure Options

When generating a workspace, you'll choose between two project structures:

### Simple (Recommended for Getting Started)

Best for: **Quick prototypes, single-app deployments, learning RAG Facile**

```
my-rag-app/
├── pyproject.toml      # All dependencies in one place
├── .env                # Your API credentials
├── app.py              # Your application code
├── context_loader.py   # Module loading logic
├── modules.yml         # Enabled modules configuration
├── chainlit.md         # Chat welcome message (Chainlit only)
└── pdf_context/        # PDF module (if selected)
```

**Advantages:**
- ✅ Familiar single-project structure
- ✅ No build tools to learn (just `uv`)
- ✅ Easy to understand and modify
- ✅ Simple deployment

**Run your app:**
```bash
cd my-rag-app
uv run chainlit run app.py -w    # For Chainlit
uv run reflex run                 # For Reflex
```

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
│   └── pdf-context/    # Shared modules
├── justfile            # Common commands
└── pyproject.toml      # Workspace root
```

**Advantages:**
- ✅ Multiple apps can share packages
- ✅ Consistent tooling across apps
- ✅ Easy to add new apps with `just add <template>`
- ✅ Built-in task runner with Moon

**Run your app:**
```bash
cd my-rag-app
just run chainlit-chat    # Run specific app
just run                  # Run all apps
```

### Which Should I Choose?

| Scenario | Recommendation |
|----------|----------------|
| First time using RAG Facile | **Simple** |
| Building a quick prototype | **Simple** |
| Single application deployment | **Simple** |
| Multiple related apps | **Monorepo** |
| Team with shared components | **Monorepo** |
| Need to add apps later | **Monorepo** |

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

## Running Your App

### Simple Structure

```bash
cd my-rag-app
uv run chainlit run app.py -w    # Chainlit with hot-reload
uv run reflex run                 # Reflex
```

### Monorepo Structure

Use the justfile commands:

```bash
cd my-rag-app
just run chainlit-chat      # Run a specific app
just run                    # Run all apps
```

#### Available Monorepo Commands

| Command | Description |
|---------|-------------|
| `just run` | Run all apps |
| `just run <name>` | Run a specific app (e.g., `just run chainlit-chat`) |
| `just format` | Format code with ruff |
| `just lint` | Run linter |
| `just check` | Run all checks (format, lint, type-check) |
| `just sync` | Sync dependencies with uv |
| `just add <template>` | Add a new app from template |

## Documentation

| Guide | Description |
|-------|-------------|
| [Evaluation Guide](docs/evaluation.md) | How to evaluate your RAG application |
| [Contributing Guide](CONTRIBUTING.md) | Architecture overview and development setup |

## Contributing

Want to contribute to RAG Facile itself? See [CONTRIBUTING.md](CONTRIBUTING.md) for the architecture overview and development setup.

## License

See [LICENSE](LICENSE) for details.
