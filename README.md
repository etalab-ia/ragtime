# RAG Facile

> [!IMPORTANT]
> This project is a starter kit for RAG applications in the French government.

## Overview

RAG Facile provides a foundation for building RAG (Retrieval-Augmented Generation) applications in the French government, specifically using the [Albert API](https://albert.sites.beta.gouv.fr/). It is designed for exploratory greenfield projects.

## Quick Start

### 1. Install Prerequisites

Ensure you have `uv` and basic build tools installed:

```bash
# macOS (most dependencies pre-installed)
brew install uv

# Ubuntu/Debian
sudo apt-get install -y git curl xz-utils
curl -LsSf https://astral.sh/uv/install.sh | sh
```

> **Note**: The CLI will automatically install `proto` and `moon` if needed. Proto requires `git` and `xz` for fetching and unpacking tools.

### 2. Install the CLI

Install the RAG Facile CLI (`rf`) globally:

```bash
uv tool install rag-facile-cli --from git+https://github.com/etalab-ia/rag-facile.git#subdirectory=apps/cli
```

Verify the installation:

```bash
rf --help
```

### 3. Generate Your Workspace

Once installed, one command gets you to a running RAG app:

```bash
rf generate workspace my-rag-app
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

To upgrade to the latest version:

```bash
uv tool install rag-facile-cli --force --from git+https://github.com/etalab-ia/rag-facile.git#subdirectory=apps/cli
```

## Generated Workspace Structure

After running `rf generate workspace`, you'll have:

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
└── pyproject.toml      # Workspace dependencies
```

## Running Your App

After generation, use moon to run your app:

```bash
cd my-rag-app
moon run chainlit-chat:dev  # or reflex-chat:dev
```

## Contributing

Want to contribute to RAG Facile itself? See [CONTRIBUTING.md](CONTRIBUTING.md) for the architecture overview and development setup.

## License

See [LICENSE](LICENSE) for details.
