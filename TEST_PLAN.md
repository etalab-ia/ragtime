# Ragtime Test Plan

## 📋 Prerequisites

- **Operating System**: macOS, Linux (Ubuntu/Debian recommended), or Windows (Git Bash).
- **Tools**: `curl` (pre-installed on macOS/Linux/WSL/Git Bash).
- **Environment**: A clean directory for testing (e.g., `~/tmp/rf-testing`).
- **Albert API key** — [request one here](https://albert.sites.beta.gouv.fr/).

---

## 🏗️ Scenario A: New Installation (Default)

*Focus: Testing the one-line installer with the pre-built workspace zip.*

### Step 1: Run the Installer

**macOS/Linux/WSL/Windows (Git Bash):**
```bash
curl -fsSL https://raw.githubusercontent.com/etalab-ia/ragtime/main/install.sh | bash
```

**Expected installer output:**
- [ ] `✓ uv déjà installé` (or installs uv)
- [ ] `✓ just déjà installé` (or installs just)
- [ ] `==> Récupération de la dernière version...` → `Dernière version : vX.Y.Z`
- [ ] `==> Installation de ragtime vX.Y.Z .......`
- [ ] `   Installed 1 executable: ragtime`
- [ ] `✓ ragtime installé`
- [ ] `✅ Ragtime est prêt !`

### Step 2: Verify the Workspace

```bash
cd my-rag-app
just
```

Expected commands listed: `run`, `learn`, `sync`.

```bash
# Check key files
ls -la
```

- [ ] `pyproject.toml` exists with `ragtime-lib` dependency
- [ ] `app.py` exists (Chainlit entry point)
- [ ] `.env.template` exists
- [ ] `ragtime.toml` exists
- [ ] `justfile` exists
- [ ] `.gitignore` exists (contains `.env`)
- [ ] `src/my_rag_app/__init__.py` exists

### Step 3: Configure API Key

```bash
cp .env.template .env
# Edit .env → set OPENAI_API_KEY=<your-key>
```

### Step 4: Start the App

```bash
just run
```

- [ ] Chainlit starts without errors
- [ ] App accessible at http://localhost:8000
- [ ] No upload button visible in the input bar
- [ ] Can ask questions and receive answers

### Step 5: RAG Learning Assistant

```bash
just learn
```

- [ ] Welcome message (French) is shown
- [ ] Can ask RAG-related questions
- [ ] Type `q` or `quit` to exit cleanly

---

## 🏗️ Scenario B: ragtime setup (Advanced / Expert)

*Focus: Testing the `setup` command scaffold for developers who want customization.*

### Prerequisites

The `ragtime` CLI must be installed. From inside a workspace:
```bash
uv run ragtime --version
```

### Default Setup (non-expert)

```bash
cd ~/tmp/rf-testing
uv run ragtime setup custom-app
```

**Interactive Prompts:**
- **API Key**: Provide your Albert API key
- **Confirm**: Yes

**Verify:**
- [ ] `custom-app/pyproject.toml` has `ragtime-lib` + `chainlit` + `ragtime-cli` (dev)
- [ ] `custom-app/app.py` exists
- [ ] `custom-app/justfile` has `run`, `learn`, `sync` recipes
- [ ] `custom-app/ragtime.toml` has `provider = "albert-collections"`
- [ ] `custom-app/.env` has `OPENAI_API_KEY`
- [ ] `custom-app/.gitignore` has `.env`
- [ ] Summary shows `Structure: Standalone`

### Expert Setup

```bash
uv run ragtime setup expert-app --expert
```

**Interactive Prompts:**
- **Preset**: `legal`
- **API Key**: Provide your Albert API key
- **Frontend**: `Chainlit`
- **Pipeline**: `Albert RAG`
- **Confirm**: Yes

**Verify:**
- [ ] `ragtime.toml` has `preset = "legal"` in `[meta]`
- [ ] All files created as above
- [ ] `--no-serve` flag skips starting the dev server:
  ```bash
  uv run ragtime setup no-serve-app --no-serve
  ```
  - [ ] Completes without starting a server
  - [ ] Shows "Next steps" instructions

---

## 🏗️ Scenario C: CLI Commands

*Focus: Testing core CLI commands once a workspace exists.*

Navigate to an existing workspace and run:

### Config commands

```bash
uv run ragtime config show
```
- [ ] Shows RAG pipeline configuration in tabular form
- [ ] Groups by pipeline stage (ingestion, retrieval, etc.)

```bash
uv run ragtime config set retrieval.top_k 15
```
- [ ] Updates `ragtime.toml`
- [ ] `uv run ragtime config show` reflects the new value

### Collections

```bash
uv run ragtime collections list
```
- [ ] Lists available Albert public collections with IDs and names

### Generate dataset

```bash
mkdir test-docs && echo "# Test document" > test-docs/test.md
uv run ragtime generate-dataset ./test-docs -o test-dataset.jsonl --provider albert
```
- [ ] Generates Q/A pairs from the document
- [ ] Output file is valid JSONL

---

## 🏗️ Scenario D: CI Verification

The `check-install.yml` workflow automatically validates installation on Linux, macOS, and Windows with every push.

To verify CI locally:

### Build the release asset

From the monorepo root:
```bash
uv run --project tools python tools/build_release_asset.py
```
- [ ] Creates `dist/ragtime-workspace-vX.Y.Z.zip`
- [ ] Zip contains `my-rag-app/` with all expected files

### Test install with local asset

```bash
RAG_FACILE_LOCAL_ASSET="$(ls dist/ragtime-workspace-*.zip | head -1)" bash install.sh
```
- [ ] Skips GitHub API call
- [ ] Extracts and installs correctly

---

## 🔧 Troubleshooting

| Issue | Solution |
|-------|----------|
| `just: command not found` | Restart terminal or `export PATH="$HOME/.local/bin:$PATH"` |
| `uv: command not found` | Same as above |
| `401 Unauthorized` from Albert | Check `OPENAI_API_KEY` in `.env` |
| Port 8000 already in use | Kill existing process: `lsof -ti:8000 \| xargs kill` |
| `uv sync` fails | Check Python version ≥ 3.13: `python3 --version` |
