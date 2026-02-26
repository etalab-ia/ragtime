# RAG Facile

[![Release](https://img.shields.io/github/v/release/etalab-ia/rag-facile?sort=date&style=flat-square)](https://github.com/etalab-ia/rag-facile/releases)
[![License](https://img.shields.io/github/license/etalab-ia/rag-facile?style=flat-square)](LICENSE)

```
 ██████╗  █████╗  ██████╗     ███████╗ █████╗  ██████╗██╗██╗     ███████╗
 ██╔══██╗██╔══██╗██╔════╝     ██╔════╝██╔══██╗██╔════╝██║██║     ██╔════╝
 ██████╔╝███████║██║  ███╗    █████╗  ███████║██║     ██║██║     █████╗
 ██╔══██╗██╔══██║██║   ██║    ██╔══╝  ██╔══██║██║     ██║██║     ██╔══╝
 ██║  ██║██║  ██║╚██████╔╝    ██║     ██║  ██║╚██████╗██║███████╗███████╗
 ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝     ╚═╝     ╚═╝  ╚═╝ ╚═════╝╚═╝╚══════╝╚══════╝
```

Build a RAG application for the French government in under 5 minutes, powered by the [Albert API](https://albert.sites.beta.gouv.fr/).

## Prerequisites

- An **Albert API key** — [request one here](https://albert.sites.beta.gouv.fr/)
- **curl** (pre-installed on macOS / Linux / WSL)

## Install

Linux / macOS / WSL:

```bash
curl -fsSL https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.sh | bash
```

Windows (PowerShell):

```powershell
irm https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.ps1 | iex
```

This creates a ready-to-run Chainlit workspace at `./my-rag-app/`.

## Quick Start

```bash
# Add your Albert API key
cd my-rag-app
cp .env.template .env
# Edit .env and set OPENAI_API_KEY=<your-key>

# Start your app
just run
```

Your app opens at **http://localhost:8000** — upload documents and ask questions.

```bash
# Chat with the interactive RAG learning assistant
just learn
```

## Upgrade

Re-run the installer to get the latest version:

Linux / macOS / WSL:

```bash
curl -fsSL https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.sh | bash
```

Windows (PowerShell):

```powershell
irm https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.ps1 | iex
```

## Documentation

| Guide | Description |
|-------|-------------|
| [Getting Started](docs/guides/getting-started.md) | Detailed installation, available commands, advanced setup |
| [Understanding the RAG Pipeline](docs/guides/rag-pipeline.md) | What each stage of the pipeline does and why it matters |
| [`ragfacile.toml` Reference](docs/reference/ragfacile-toml.md) | Every configuration option, presets comparison, environment overrides |
| [Evaluation Guide](docs/guides/evaluation.md) | Generate synthetic datasets and measure RAG quality |
| [Components Reference](docs/reference/components.md) | Albert Client SDK, frontend apps, and modules |
| [Windows Setup](docs/guides/windows-setup.md) | Complete guide for Windows (PowerShell and Git Bash) |
| [Proxy & Network Setup](docs/guides/proxy-setup.md) | Install behind corporate proxies and VPNs |

## Contributing

Want to contribute to RAG Facile itself? See [CONTRIBUTING.md](CONTRIBUTING.md) for the architecture overview and development setup.

## License

See [LICENSE](LICENSE) for details.
