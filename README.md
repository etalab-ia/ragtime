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
- **git** and **curl** installed

## Install

One command installs the entire toolchain and the `rag-facile` CLI:

```bash
# Linux / macOS / WSL
curl -fsSL https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.sh | bash
source ~/.bashrc  # or restart your terminal
```

```powershell
# Windows (PowerShell)
irm https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.ps1 | iex
```

Verify it worked:

```bash
rag-facile --help
```

## Create Your App

```bash
rag-facile setup my-rag-app
```

The CLI will guide you through choosing a project structure, a configuration preset, and a frontend. After setup, it installs dependencies and starts the dev server — your app opens in the browser, ready to use.

## Upgrade

Re-run the installer to get the latest version:

```bash
# Linux / macOS / WSL
curl -fsSL https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.sh | bash
```

```powershell
# Windows (PowerShell)
irm https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.ps1 | iex
```

## Documentation

| Guide | Description |
|-------|-------------|
| [Getting Started](docs/guides/getting-started.md) | Detailed installation options, project structures, and running your app |
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
