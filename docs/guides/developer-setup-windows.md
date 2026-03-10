# Developer Setup on Windows

This guide is for developers who want to contribute to RAG Facile itself (not just use it).

## Prerequisites

- **Windows 10/11** (64-bit)
- **Git for Windows** — [Download](https://git-scm.com/download/win)
- **GitHub account** — [Sign up](https://github.com)
- **Editor** — VS Code recommended with Python extension

## One-Time Setup

### 1. Fork & Clone the Repository

```bash
# Clone your fork
git clone https://github.com/YOUR-USERNAME/rag-facile.git
cd rag-facile

# Add upstream remote for syncing
git remote add upstream https://github.com/etalab-ia/rag-facile.git
```

### 2. Install the Development Toolchain

Using Git Bash:

```bash
curl -fsSL https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.sh | bash
```

Or Git Bash:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.sh)
```

This installs:
- **proto** — Tool version manager
- **moon** — Monorepo build system
- **uv** — Python package manager
- **just** — Task runner for development commands

### 3. Open a New Terminal

Proto updates `PATH` automatically, so restart your terminal for changes to take effect.

### 4. Install Dependencies

```bash
cd rag-facile
just sync  # Installs dependencies and pre-commit hooks
```

> **Note:** `just sync` runs `uv sync` to install dependencies and `uv run pre-commit install` to set up automatic code quality checks on commit.

## Development Workflow

### Available Commands

All development commands use `just` (defined in `justfile`):

```bash
just --list         # Show all available commands
just format         # Format code with ruff
just lint           # Run linter with ruff
just type-check     # Run type checker (ty)
just check          # Run all checks (format + lint + type-check)
```

### Making Changes

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** in your editor

3. **Run checks:**
   ```bash
   just check
   ```

4. **Commit with conventional commits:**
   ```bash
   git commit -m "feat: add new feature" 
   # or
   git commit -m "fix: resolve issue"
   ```

5. **Push and create a PR:**
   ```bash
   git push origin feature/your-feature-name
   ```

### Code Quality Standards

- **Format:** `ruff format` (automatic code formatting)
- **Lint:** `ruff check` (style and error checking)
- **Type checking:** `ty check` (static type analysis)
- **Python version:** 3.13+
- **Import organization:** Handled by ruff

All checks must pass before pushing:

```bash
# Single command to verify everything
just check
```

## Project Structure

```
rag-facile/
├── apps/                          # Applications
│   ├── cli/                       # RAG Facile CLI (Typer)
│   │   ├── src/cli/commands/      # CLI commands
│   │   ├── tests/                 # CLI tests
│   │   └── pyproject.toml
│   ├── chainlit-chat/             # Chainlit template
│   └── reflex-chat/               # Reflex template
├── packages/                      # Shared packages
│   └── pdf-context/               # PDF extraction library
├── .moon/
│   ├── templates/                 # App templates
│   ├── toolchain.yml              # Tool versions
│   └── workspace.yml              # Workspace config
├── .prototools                    # Proto version pinning
├── justfile                       # Development commands
├── install.sh                     # Unix/Linux installer
├── install.sh                     # Installer (macOS/Linux/Windows Git Bash)
└── README.md
```

## Testing Your Changes

### Running the CLI in Development

```bash
# Install CLI in editable mode
cd apps/cli
uv sync
uv run rag-facile --help
```

### Testing on Windows

When testing on Windows, use Git Bash:

```bash
just format-check
just lint
```

```bash
# Git Bash
just format-check
just lint
```

### Testing the Installer

To test the installer locally before pushing:

```bash
# Test the PowerShell installer with your changes
irm https://raw.githubusercontent.com/YOUR-USERNAME/rag-facile/YOUR-BRANCH/install.ps1 | iex

# Or the bash installer
bash <(curl -fsSL https://raw.githubusercontent.com/YOUR-USERNAME/rag-facile/YOUR-BRANCH/install.sh)
```

## Common Tasks

### Add a New CLI Command

1. Create a new file in `apps/cli/src/cli/commands/`
2. Implement the command using Typer
3. Register it in `apps/cli/src/cli/__init__.py`
4. Add tests in `apps/cli/tests/`
5. Run `just check` to verify

### Update Tool Versions

Edit `.prototools`:

```toml
python = "3.13"  # Update Python version

[tools.just]
version = "1.34.0"  # Update just version
```

Then reinstall:

```bash
proto install python just
```

### View Proto Configuration

```bash
cat $env:USERPROFILE\.proto\.prototools   # PowerShell
cat ~/.proto/.prototools                   # Git Bash
```

## Troubleshooting

### "just" command not found

Ensure proto installed successfully:

```bash
proto --version
proto install just
just --version
```

### Format/lint check fails

Run the formatters to auto-fix:

```bash
just format    # Auto-format code
just lint      # Show issues (you may need to fix manually)
```

### Python type errors

Install dependencies and run type checker:

```bash
cd apps/cli
uv sync
uv run ty check
```

### Git Bash PATH issues

If tools aren't found in Git Bash, reload your shell profile:

```bash
source ~/.bashrc
which proto
```

## Getting Help

- **Proto docs:** https://moonrepo.dev/docs/proto
- **Moon docs:** https://moonrepo.dev/
- **Uv docs:** https://docs.astral.sh/uv/
- **Ruff docs:** https://docs.astral.sh/ruff/
- **GitHub Issues:** https://github.com/etalab-ia/rag-facile/issues

## Before Submitting a PR

Checklist:

- [ ] I've created a branch (not committing to `main`)
- [ ] I've run `just check` and all checks pass
- [ ] I've tested on both PowerShell and Git Bash (if Windows-related changes)
- [ ] I've updated documentation if needed
- [ ] My commits follow conventional commit format (`feat:`, `fix:`, etc.)
- [ ] I've added tests for new functionality

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for more details.
