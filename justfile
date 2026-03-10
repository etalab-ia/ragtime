# RAG Facile development tasks

# Use PowerShell on Windows, sh on Unix
set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

# Workaround for moon not supporting bare repo worktrees (moonrepo/moon#2162).
# Fixed in moon v2 — remove this once upgraded.
export GIT_WORK_TREE := justfile_directory()

# Display available commands
default:
    @just --list

# Sync dependencies and install pre-commit hooks
sync:
    uv sync
    uv run pre-commit install

# TODO: restore uv-upx --interactive once Alirex/uv_upgrade#6 is fixed (workspace members flood the prompt)
# Upgrade all third-party deps: refreshes uv.lock without touching pyproject.toml (workspace-safe)
upgrade:
    uv lock --upgrade

# Upgrade a single third-party package to latest (e.g.: just upgrade-pkg httpx)
upgrade-pkg pkg:
    uv lock --upgrade-package {{pkg}}

# Format code (write changes)
format:
    moon run tools:format
    
# Check formatting without writing
format-check:
    moon run tools:format-check

# Run linter
lint:
    moon run tools:lint

# Run linter with auto-fix
lint-fix:
    moon run tools:lint-fix

# Run type checker
type-check:
    moon run tools:type-check

# Run all checks (format-check, lint, type-check)
check: format-check lint type-check

# Run the chat UI: just run (chainlit) or just run reflex
run ui="chainlit":
    cd "apps/{{ui}}-chat" && just run

# Add a new app from a template (e.g., just add chainlit-chat)
add template:
    moon generate {{template}}
