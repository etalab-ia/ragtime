# Windows Setup Guide for RAG Facile

This guide covers installation on Windows using Git Bash.

## Prerequisites

- **Windows 10/11** (64-bit)
- **Git for Windows** (includes Git Bash) — [Download](https://git-scm.com/download/win)
- **Internet connection** (for downloading tools and dependencies)

## Installation

Open **Git Bash** and run:

```bash
curl -fsSL https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.sh | bash
```

This installs uv, just, and the `rag-facile` CLI as a global tool.

Then **restart Git Bash** (or run the `source` command shown by the installer) so the new tools are available on your PATH.

## Create your project

```bash
rag-facile setup mon-projet
cd mon-projet && just run
```

## Troubleshooting

### `curl` not found

Make sure you are using **Git Bash**, not Command Prompt or PowerShell. Git Bash includes `curl` by default.

### `rag-facile` command not found after install

Restart Git Bash so the updated PATH takes effect, then verify:

```bash
rag-facile --version
```

If still not found, add `~/.local/bin` to your PATH manually:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Add this line to `~/.bashrc` to make it permanent.

### Git Not Found

Ensure Git for Windows is installed and available:

```bash
git --version
```

If not found, download and install from [git-scm.com](https://git-scm.com/download/win).

### Behind a Corporate Proxy

Set proxy environment variables before running the installer:

```bash
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080
curl -fsSL https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.sh | bash
```

For more details, see [Proxy Setup Guide](../troubleshooting/proxy.md).

## Next Steps

1. **Read the main README:** [../../README.md](../../README.md)
2. **Explore available tasks:**
   ```bash
   cd mon-projet && just
   ```

---

**Still stuck?** Open an issue: https://github.com/etalab-ia/rag-facile/issues
