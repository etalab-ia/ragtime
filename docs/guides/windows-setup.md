# Windows Setup Guide for RAG Facile

This guide covers installation on Windows using PowerShell or Git Bash.

## System Requirements

- **Windows 10/11** (64-bit)
- **Git for Windows** (if using Git Bash) — [Download](https://git-scm.com/download/win)
- **Internet connection** (for downloading tools and dependencies)
- **Admin privileges** (for execution policy on first PowerShell run)

## Installation Options

### Option 1: PowerShell (Recommended for Windows Users)

The fastest, most native Windows experience. Proto and uv installers are PowerShell scripts designed specifically for Windows.

```powershell
irm https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.ps1 | iex
```

This will:
1. Install **proto** (unified toolchain manager)
2. Install **moon** (monorepo build system)
3. Install **uv** (Python package manager)
4. Install **just** (task runner)
5. Install **rag-facile CLI**

**What happens next:**
- Proto modifies your system `PATH` to include the installed tools
- A new PowerShell window will have all tools available
- Ready to start: `rag-facile setup my-rag-app`

### Option 2: Git Bash (Unix-like Experience on Windows)

If you prefer a bash environment, you can use Git Bash (included with Git for Windows).

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.sh)
```

This does the same as PowerShell but using Unix bash commands.

**What happens next:**
- Tools are installed to `~/.proto/` (Unix paths)
- May need to source your shell profile: `source ~/.bashrc`
- Ready to start: `rag-facile setup my-rag-app`

## Troubleshooting

### "irm" command not found (PowerShell)

Ensure you're using PowerShell 5.0+, not Command Prompt:

```powershell
# Check PowerShell version
$PSVersionTable.PSVersion
```

If you're in Command Prompt, open PowerShell instead by typing `powershell`.

### Execution Policy Error

On first run, PowerShell may block the installer. Run as Administrator and try again, or set the policy:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned -Force
```

Then re-run the installer.

### Behind a Corporate Proxy

If you see SSL/network errors, your corporate proxy may be inspecting SSL. Both installers (`install.ps1` and `install.sh`) detect proxy environment variables and configure proto automatically.

**If that doesn't work:**

1. Export your corporate root certificate as a `.pem` file
2. Create or edit `~/.proto/.prototools`:

```toml
[settings.http]
root-cert = "C:/path/to/corporate-cert.pem"
proxies = ["http://proxy.company.com:8080"]
```

3. Try again: Re-run the installer

For more details, see [Proxy Setup Guide](../troubleshooting/proxy.md).

### Git Not Found

The installer requires `git` for cloning repositories. Ensure Git for Windows is installed:

```bash
git --version
```

If not found, download and install from [git-scm.com](https://git-scm.com/download/win).

### "rag-facile" command not found after install

**On PowerShell:** Open a **new** PowerShell window (the installer updated system PATH which requires a restart)

**On Git Bash:** Run:
```bash
source ~/.bashrc
```

Then verify:
```bash
rag-facile --version
```

## Understanding Proto on Windows

Proto is a **unified version manager** that installs all your project tools:

- **Python 3.13** — via uv
- **Moon** — monorepo build system
- **Just** — task runner (via plugin)

Installation location:
- **PowerShell path:** `%USERPROFILE%\.proto\` (or `~/.proto/`)
- **Binary location:** `~/.proto/bin/` and `~/.proto/shims/`

Tools are downloaded as pre-compiled binaries, making setup instant.

## Project-Level Tool Pinning

The `.prototools` file at the project root pins tool versions:

```toml
python = "3.13"

[plugins]
just = "source:https://raw.githubusercontent.com/Phault/proto-toml-plugins/main/just/plugin.toml"

[tools.just]
version = "1.34.0"
```

This ensures your entire team (Windows, Mac, Linux) uses the **exact same versions**.

## Using RAG Facile on Windows

### With PowerShell

All `just` tasks work with PowerShell:

```powershell
just format
just lint
just type-check
```

The `justfile` automatically uses PowerShell on Windows, bash on Unix.

### With Git Bash

Same commands work:

```bash
just format
just lint
just type-check
```

## Next Steps

1. **Initialize a workspace:**
   ```
   rag-facile setup my-rag-app
   ```

2. **Read the main README:**
   See [../README.md](../README.md) for full project documentation

3. **Explore available tasks:**
   ```
   just
   ```

## Further Help

- **Proto documentation:** https://moonrepo.dev/docs/proto
- **Moon documentation:** https://moonrepo.dev/
- **Uv documentation:** https://docs.astral.sh/uv/
- **Just documentation:** https://just.systems/

---

**Still stuck?** Open an issue: https://github.com/etalab-ia/rag-facile/issues
