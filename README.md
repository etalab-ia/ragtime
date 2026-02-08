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

#### Linux / macOS / WSL

```bash
curl -fsSL https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.sh | bash
source ~/.bashrc  # or restart your terminal
```

> **Note**: On Ubuntu/Debian, the installer will automatically install prerequisites (git, curl, xz-utils, unzip) if needed.

#### Windows (PowerShell) — Recommended

```powershell
irm https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.ps1 | iex
```

Open a new PowerShell window and you're ready to go!

#### Windows (Git Bash / MSYS2)

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.sh)
source ~/.bashrc
```

> **Behind a corporate proxy or VPN?** The installer automatically detects and configures proxy support. See [Installation Documentation](docs/) for troubleshooting guides.

Verify the installation:

```bash
rag-facile --help
```

### 2. Setup Your Workspace

One command gets you to a running RAG app:

```bash
rag-facile setup my-rag-app
```

The CLI will guide you through:
1. **Project structure** - Choose Simple or Monorepo (see below)
2. **Frontend selection** - Choose Chainlit or Reflex
3. **Module selection** - Add PDF processing, vector stores, etc.
4. **Environment configuration** - Set your Albert API key and preferences

After configuration, the CLI automatically:
- Sets up your workspace with the selected components
- Creates your `.env` file with your credentials
- Installs all dependencies with `uv sync`
- Starts the development server

Your app will open in the browser, ready to use!

## Documentation

For detailed guides and troubleshooting, see the [Documentation Hub](docs/):

### Installation & Setup

- **[Windows Setup Guide](docs/guides/windows-setup.md)** - Complete guide for Windows (PowerShell and Git Bash)
- **[Proxy & Network Setup](docs/guides/proxy-setup.md)** - Install RAG Facile on corporate networks or behind VPNs
- **[Proxy Troubleshooting](docs/troubleshooting/proxy.md)** - Solve network-related issues

### Reference

- **[Full Documentation Index](docs/)** - All guides and resources

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
- ✅ No build tools to learn
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

### Albert Client SDK

A comprehensive Python SDK for the Albert API, providing both synchronous and asynchronous clients with full type safety.

**Installation:**
```bash
pip install albert-client
# or with uv
uv add albert-client
```

**Features:**
- ✅ **OpenAI-Compatible**: Drop-in replacement for chat, embeddings, audio, and models endpoints
- ✅ **Albert-Specific Features**: Hybrid RAG search, BGE reranking, collections management
- ✅ **Advanced Tools**: OCR with bounding boxes, document parsing, usage tracking with carbon footprint
- ✅ **Full Type Safety**: Comprehensive Pydantic models with `.to_dict()` and `.to_json()` helpers
- ✅ **Async Support**: All methods available in both sync and async variants
- ✅ **100% Test Coverage**: 136 passing tests with respx HTTP mocking

**Quick Example:**
```python
from albert_client import AlbertClient

# Initialize client
client = AlbertClient(
    api_key="your-albert-api-key",
    base_url="https://albert.api.etalab.gouv.fr"
)

# OpenAI-compatible chat
response = client.chat.completions.create(
    model="AgentPublic/llama3-instruct-8b",
    messages=[{"role": "user", "content": "Bonjour!"}]
)

# Albert-specific: Hybrid RAG search
results = client.search(
    query="transition énergétique",
    collections=[1, 2],
    method="hybrid",
    k=5
)

# Rerank documents for better relevance
reranked = client.rerank(
    query="énergies renouvelables",
    documents=[doc.chunk for doc in results.results],
    model="BAAI/bge-reranker-v2-m3",
    top_n=3
)
```

**Learn More:** See the [Albert Client Documentation](packages/albert-client/README.md) for complete API reference and examples.

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

Use the `just` commands:

```bash
cd my-rag-app
just run chainlit-chat      # Run a specific app
just run                    # Run all apps
```

#### Available `just` Commands

| Command | Description |
|---------|-------------|
| `just run` | Run all apps |
| `just run <name>` | Run a specific app (e.g., `just run chainlit-chat`) |
| `just format` | Format code with ruff |
| `just lint` | Run linter |
| `just check` | Run all checks (format, lint, type-check) |
| `just sync` | Sync dependencies with uv |
| `just add <template>` | Add a new app from template |

## Evaluating Your RAG Application

Before deploying, you need to know if your RAG application works well. Evaluation helps answer: Is my chatbot giving correct answers? Does it find the right documents? Is it hallucinating?

### Generate Synthetic Evaluation Datasets

Don't have evaluation data? Generate it automatically from your documents using the **Data Foundry** feature. Choose between Letta Cloud or self-hosted Albert API:

#### Option 1: Letta Cloud (Easiest)

```bash
# Set up Letta Cloud credentials
export LETTA_API_KEY="your-letta-api-key"           # Get at https://app.letta.com/api-keys
export DATA_FOUNDRY_AGENT_ID="agent-xxx"            # Pre-configured agent ID

# Generate Q/A pairs from your documents
rag-facile generate-dataset ./my-docs -o golden_dataset.jsonl -n 50 --provider letta
```

#### Option 2: Albert API (Self-Hosted)

```bash
# Set up Albert API credentials
export OPENAI_API_KEY="your-api-key"                # Albert API key
export OPENAI_BASE_URL="http://localhost:8000"      # Albert API endpoint
export OPENAI_MODEL="mistral-7b"                    # Model to use

# Generate Q/A pairs using your Albert instance
rag-facile generate-dataset ./my-docs -o golden_dataset.jsonl -n 50 --provider albert
```

#### Output Format

Both providers create Ragas-compatible JSONL files with French Q/A pairs:

```json
{
  "user_input": "Quel est le délai de recours administratif?",
  "retrieved_contexts": ["Le délai de recours est de deux mois..."],
  "reference": "Le délai de recours administratif est de deux mois.",
  "_metadata": {"source_file": "code.pdf", "quality_score": 0.95}
}
```

### Basic Evaluation Workflow

```python
from datasets import load_dataset

# Load a dataset from HuggingFace
dataset = load_dataset("AgentPublic/service-public")

# Run your RAG pipeline on each question
results = []
for example in dataset["train"]:
    answer = your_rag_pipeline(example["question"])
    results.append({
        "question": example["question"],
        "expected": example["ground_truth"],
        "actual": answer,
    })

# Measure accuracy
accuracy = sum(1 for r in results if r["expected"] == r["actual"]) / len(results) if results else 0.0
```

### What to Measure

| Metric | What it Measures |
|--------|------------------|
| **Accuracy** | Correct answers / Total questions |
| **Retrieval Recall** | Did we find the right documents? |
| **Faithfulness** | Does the answer match the sources? |
| **Latency** | Response time |

For sovereign AI, also consider: sovereignty (only *.gouv.fr sources), energy score, and French language quality.

### Learn More

- [Letta Evals](https://github.com/letta-ai/letta-evals) - Framework for testing AI agents
- [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard) - Embedding model benchmarks
- [BEIR Benchmark](https://github.com/beir-cellar/beir) - Information retrieval benchmarks

## Contributing

Want to contribute to RAG Facile itself? See [CONTRIBUTING.md](CONTRIBUTING.md) for the architecture overview and development setup.

## License

See [LICENSE](LICENSE) for details.
