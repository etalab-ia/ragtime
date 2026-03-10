# Agent Knowledge: RAG Facile Project

This document contains essential knowledge for coding agents working on RAG Facile.

## 0. Critical Rules

### Branch Management (Non-Negotiable)
- **CRITICAL**: You **MUST** always create a new git branch for every task before making changes
  - Command: `git checkout -b branch-name` (check `git status` first)
  - Never work directly on `main` or `master`
  - Use exact branch names provided by the user (don't create alternatives)
  
### Commit & Push Workflow
- **CRITICAL**: Always run code quality checks before pushing:
  ```bash
  uv run ruff check . && uv run ruff format .
  python -m pytest apps/cli/tests/  # Run relevant tests
  ```
- **CRITICAL**: Use conventional commits (feat:, fix:, docs:, chore:) - they trigger automated versioning
  - `feat:` → minor version bump (0.1.0 → 0.2.0)
  - `fix:` → patch version bump (0.1.0 → 0.1.1)
  - `feat!:` or `fix!:` → major version bump (0.1.0 → 1.0.0)
  - `docs:`, `chore:` → no version bump
- **CRITICAL**: Sign commits with `-S` flag (or configure `commit.gpgsign true` in git config)
- **CRITICAL**: Never force-push to main/master

### Documentation Updates
- Always check and update documentation before creating a PR
- Update README, CONTRIBUTING, docs/ as needed - don't wait for user to ask
- For CLI changes, update: README.md, apps/cli/README.md, CONTRIBUTING.md
- For generated workspaces, direct users to use `just` commands, not raw `uv`

## 1. Project Architecture

### Overview
- **Name**: RAG Facile - RAG starter kit for French government
- **Type**: Python 3.13+ monorepo
- **Build System**: Moonrepo (moon) for workspace management
- **Package Manager**: uv (fast Python package installer/manager)
- **Code Quality**: ruff (format + lint), ty (type checker), pre-commit

### Repository Structure
```
rag-facile/
├── apps/                          # Applications
│   ├── cli/                       # rag-facile CLI tool
│   ├── chainlit-chat/             # Chainlit chat UI (golden master)
│   └── reflex-chat/               # Reflex chat UI (golden master)
├── packages/                      # Shared packages
│   ├── rag-core/                  # Core config + schema (rag_facile.core)
│   ├── albert-client/             # Albert API SDK (uses `albert` namespace, not rag_facile.*)
│   ├── ingestion/                 # Document parsing (rag_facile.ingestion)
│   ├── pipelines/                 # Pipeline orchestration (rag_facile.pipelines)
│   ├── retrieval/                 # Vector search (rag_facile.retrieval)
│   ├── reranking/                 # Cross-encoder re-scoring (rag_facile.reranking)
│   ├── context/                   # Context formatting (rag_facile.context)
│   ├── storage/                   # Collection management (rag_facile.storage)
│   ├── tracing/                   # Pipeline tracing & observability (rag_facile.tracing)
│   ├── evaluation/                # RAG evaluation with Inspect AI (rag_facile.evaluation)
│   └── rag-facile-lib/            # Library bundle for external projects
├── .moon/                         # Moon workspace config
│   ├── templates/                 # App/package templates (Tera syntax)
│   ├── toolchain.yml              # Python/tool versions
│   └── workspace.yml              # Workspace definition
├── docs/                          # User documentation
│   ├── guides/                    # How-to guides (getting-started, proxy, etc.)
│   ├── reference/                 # Reference docs (ragfacile.toml, components)
│   └── troubleshooting/           # Problem-solving guides
├── pyproject.toml                 # Root workspace config
├── install.sh                     # Installation script (macOS/Linux/Windows via Git Bash)
└── README.md                      # Main project documentation
```

### Python Version
- **Current**: Python 3.13+ (`requires-python = ">=3.13, <3.14"`)
- **Why 3.13**: Modern features, stability. Previously tried 3.14 but moved back.
- **Generated workspaces**: Include `.python-version` file to pin Python version

## 2. Toolchain & Build System

### Moon (Moonrepo)
- **Purpose**: Workspace task runner and tool orchestration
- **Key Patterns**:
  - Run from repo root: `moon init`, `moon generate`, `moon run`
  - `moon init` must run FROM target directory (not with path argument)
  - `moon generate` needs `generator.templates` in workspace.yml
  - Boolean variables passed as `-- --flag` not `-- flag=true`
  - Moon runs commands directly (not through venv) - use `uv run` in task commands
  - Commands and tasks defined in `tools/moon.yml`
  
### UV (Package Manager)
- **All dependency operations** go through uv: `uv sync`, `uv add`, `uv remove`
- Never use `pip` or `poetry` in this project
- `uv sync` updates both dependencies and lockfile (`uv.lock`)
- For workspace packages, use `uv.sources` mapping:
  ```toml
  [tool.uv.sources]
  my-lib = { workspace = true }
  ```
- **CLI tools**: Installed via `uv tool install` in install.sh

### Ruff (Code Quality)
- **Format**: `uv run ruff format .`
- **Lint**: `uv run ruff check .`
- **Config**: In `pyproject.toml` under `[tool.ruff]`, `[tool.ruff.lint]`, `[tool.ruff.format]`
- **Gotcha**: Ruff scans ALL pyproject.toml files during discovery. Template files with Jinja2 syntax must be excluded
  - Use `extend-exclude = [".moon/templates"]` at root level
  - Use `exclude = [".moon/templates"]` in lint/format sections

### Ty (Type Checker)
- **Command**: `uv run ty check`
- **Config**: In `pyproject.toml` under `[tool.ty.src]` with `exclude` setting
- **Gotcha**: Pre-commit hook needs explicit entry: `uv run ty check` (default may fail)
- **Disabling Rules**: Use `[tool.ty.rules]` to ignore false positives from metaprogramming (Reflex, Chainlit)

### Just (Task Runner)
- **Purpose**: Developer-friendly shell command wrapper for moon tasks
- **Files**: `justfile` or `Justfile` (use lowercase `justfile` for consistency)
- **Key Commands** in generated workspaces:
  - `just format` → `moon run tools:format`
  - `just lint` → `moon run tools:lint`
  - `just type-check` → `moon run tools:type-check`
  - `just run [app]` → Run app(s)

## 3. CLI Development (rag-facile-cli)

### Location
- **Code**: `apps/cli/src/cli/`
- **Tests**: `apps/cli/tests/`

### Command Structure
**Current commands** (alphabetically ordered):
- `generate-dataset` - Generate synthetic Q/A evaluation datasets
- `setup <name> [--expert]` - Setup a new RAG Facile workspace (--expert shows project structure, frontend, and pipeline options)
- `version` - Show CLI version

**Key Pattern**: Alphabetical ordering is important - check help output order when adding commands

### CLI Architecture
- **Framework**: Typer (FastAPI creator's CLI framework)
- **Files**:
  - `main.py` - Root app definition
  - `commands/` - Command implementations (`setup.py`, `generate_dataset.py`, `version.py`, `config/`, `collections/`)
  - `commands/eval/providers/` - Pluggable dataset generation providers (Letta, Albert)

### Important Patterns

#### Don't Print Banners at Module Level
```python
# ❌ BAD - prints when module imported
console.print(BANNER)
app = typer.Typer()

# ✅ GOOD - only prints when CLI invoked
app = typer.Typer()

@app.callback()
def main_callback():
    console.print(BANNER)
```

#### Show Help When Subcommands Missing
```python
# ✅ GOOD - show help instead of error
app = typer.Typer(
    invoke_without_command=True,
    no_args_is_help=True,  # Show help when no subcommand
)
```

#### File Naming Matches Command Structure
- Command `setup` → File `setup.py`
- Command `generate-dataset` → File `generate_dataset.py`
- Keep naming consistent with directory structure

#### Docstring Consistency
- Update ALL references when renaming commands (docstrings, tests, help text)
- Test docstrings should match implementation

### Providers Pattern

Pluggable provider architecture for dataset generation (Letta Cloud, Albert API, etc.):

```
apps/cli/src/cli/commands/eval/providers/
├── __init__.py              # Factory for provider selection
├── letta.py                 # Letta Cloud provider
├── albert.py                # Albert API provider
└── document_preprocessor.py # Shared PDF extraction utility
```

**Key Pattern**: Provider-specific validation and instantiation logic must be grouped together
- ❌ BAD: Split validation across distant code locations (requires updates in multiple places)
- ✅ GOOD: Use dictionaries/loops for repeated patterns (DRY principle)

## 4. Release Management

### Versioning System
- **Tool**: release-please (with linked-versions plugin)
- **Mode**: Unified monorepo versioning - all packages bump versions together
- **Trigger**: Conventional commits in PR titles (not custom titles)
- **Process**:
  1. Merge PR with conventional commits
  2. release-please creates Release PR automatically
  3. Merge Release PR → Triggers GitHub Release creation

### Conventional Commits (Critical)
- **Syntax**: `type: description` where type is:
  - `feat:` - New feature (minor bump)
  - `fix:` - Bug fix (patch bump)
  - `feat!:` / `fix!:` - Breaking change (major bump)
  - `docs:`, `chore:`, `refactor:` - No bump
- **Importance**: This directly controls automated version bumping across ALL packages
- **GitHub Integration**: release-please reads commit messages, NOT PR titles for parsing
  - ❌ DON'T set PR title as regex - it breaks PR creation
  - ✅ DO follow conventional commits in merge commits

### Configuration
- **File**: `.release-please-config.json` at root
- **Manifest**: `.release-please-manifest.json` (auto-generated, tracks versions)
- **Per-package setup**: 
  1. Add pyproject.toml path to `extra-files` array
  2. Add `# x-release-please-version` comment after version line
  3. Ensure version matches root in manifest

## 5. Project Patterns & Gotchas

### Adding a New Package to the Monorepo

When adding a new package to the monorepo (`packages/mypkg/`):
1. Create `packages/mypkg/` with `pyproject.toml` and source under `packages/mypkg/src/rag_facile/mypkg/`
2. Add `# x-release-please-version` comment after version in pyproject.toml
3. Add to root `pyproject.toml`:
   ```toml
   [project]
   dependencies = ["my-package"]
   
   [tool.uv.sources]
   my-package = { workspace = true }
   ```
4. Add `pyproject.toml` path to `release-please-config.json` → `extra-files`
5. If the package is a pipeline phase, add it to `packages/rag-facile-lib/pyproject.toml` dependencies

### Template Generation

**File**: `tools/generate_templates.py` (uses Tera templating)

**Critical Pattern**: 
- Templates in `.moon/templates/` are destroyed and regenerated
- Edits to generated templates don't persist (they're overwritten)
- Use `write_text()` to embed static content that won't be Tera-rendered
- Use `copytree()` for files that SHOULD be Tera-processed
- **Escaping**: Use `{% raw %}...{% endraw %}` for blocks or `{{ "{{ var }}" }}` for inline tokens

### macOS Path Resolution

- `/tmp` on macOS resolves to `/private/tmp`
- Normalize paths in output for cleaner display
- Consider when comparing paths or displaying to users

### Git & Case Sensitivity

- **macOS case-insensitivity**: `Justfile` and `justfile` are same file but git tracks separately
- **Standard**: Use lowercase `justfile` for consistency
- Make sure both aren't added to git

## 6. Recent Work & Features (Feb 2026)

### Query Expansion System (✅ Completed Feb 18, 2026)

- **Problem**: Vocabulary mismatch — users write colloquial queries ("APL", "CNI") that don't match the formal French of indexed documents.
- **Package**: `packages/query/` → `rag_facile.query` namespace
- **Architecture**: Strategy Pattern (`QueryExpander` ABC, `get_expander(client, config)` factory)
- **Strategies**:
  - `multi_query`: generates 3–5 formal French administrative query variants via LLM (instructor + Pydantic structured output); results merged with Reciprocal Rank Fusion (RRF)
  - `hyde`: generates a hypothetical ideal administrative document to embed instead of the raw query
- **Key design**: `AlbertClient.as_instructor()` added to both sync/async clients — single choke point for structured LLM output, reusable by any package
- **Aggregation**: `fuse_results()` in `packages/retrieval/` implements RRF (k=60), de-duplicating chunks by `(chunk_id, collection_id)` and boosting chunks confirmed by multiple query angles
- **Integration**: `AlbertPipeline.process_query()` Step 0; default `strategy = "none"` → zero impact for existing deployments
- **Preset activation**: `accurate` and `hr` presets set `strategy = "multi_query"`; `legal` keeps `strategy = "none"` to preserve exact terminology
- **Config**: `[query] strategy = "multi_query"` in `ragfacile.toml`

### Library Package + rag_facile Namespace (✅ PR #121, Feb 17, 2026)
- **What changed**: All 7 pipeline packages now live under `rag_facile.*` namespace
- **Packages**: `rag_facile.core`, `rag_facile.ingestion`, `rag_facile.pipelines`, `rag_facile.retrieval`, `rag_facile.reranking`, `rag_facile.context`, `rag_facile.storage`, `rag_facile.tracing`, `rag_facile.evaluation`
- **New bundle**: `packages/rag-facile-lib/` bundles all pipeline packages for external projects
- **Generated projects** now depend on `rag-facile-lib` via git URL (no more copying pipeline source)
- **Standalone** structure: `pyproject.toml` + frontend app + `src/<name>/` for user code
- **Monorepo** setup: inlines workspace config directly (no sys-config template)
- **Import style**: `from rag_facile.pipelines import get_pipeline` (not `from pipelines import ...`)

### Issue #46: Proxy Support (✅ Completed Feb 6, 2026)
- **Problem**: Proto plugin installation fails on networks with proxies/VPNs
- **Root Cause**: Proto's reqwest doesn't auto-detect HTTP_PROXY env vars
- **Solution**: Enhanced install.sh with automatic proxy detection + .prototools generation
- **Implementation**:
  - `setup_proxy_config()` function detects and configures proxy
  - Creates `~/.proto/.prototools` with proxy settings
  - Detects corporate proxies (SSL inspection) and provides guidance
  - Improved error messages with troubleshooting steps
- **Documentation**: 
  - `docs/guides/proxy-setup.md` - User guide for corporate networks
  - `docs/troubleshooting/proxy.md` - Symptom-based troubleshooting
  - `docs/technical/` - Research and investigation details

### True RAG Pipeline (✅ PR #96, Feb 16, 2026)
- **What changed**: Replaced context-stuffing with real RAG (auto-managed Albert collections)
- **Flow**: `process_file()` → create collection → upload (Albert chunks + embeds) → `process_query()` → search → rerank → format context → inject into user message
- **Key pattern**: Context injected per-turn into user message, not accumulated as system messages

### Expert Flag + Default Flow (✅ PR #107/113, Feb 17, 2026)
- **Default setup** (no `--expert`): 2 prompts only (preset + API key), defaults to standalone + Chainlit + Albert RAG
- **Expert setup** (`--expert`): Shows all 5 prompts (structure, preset, frontend, pipeline, API key)
- **Pipeline names**: "Albert RAG" (server-side, recommended) and "Local" (offline, simple)

### Data Foundry / Eval Features
- **Command**: `rag-facile generate-dataset ./docs -o output.jsonl`
- **Purpose**: Generate synthetic Q/A evaluation datasets from documents
- **Providers**: Letta Cloud (default) or Albert API
- **Implementation**: `apps/cli/src/cli/commands/eval/providers/`

## 7. Code Quality Standards

### Pre-Commit Checks
```bash
# Always run before pushing
uv run ruff check . && uv run ruff format .
python -m pytest apps/cli/tests/
```

### Testing Standards
- Unit tests for new features/functions
- Test file location: `apps/[name]/tests/test_*.py`
- All tests must pass before commit
- Use `pytest` with `pytest-mock` for mocking

### Git Workflow
1. Create branch: `git checkout -b feature-name`
2. Make changes
3. Check formatting: `uv run ruff check . && uv run ruff format .`
4. Run tests: `python -m pytest`
5. Stage files: `git add [specific files]`
6. Commit with signature: `git commit -S -m "feat: description"`
7. Push: `git push origin branch-name`
8. Create PR, wait for review
9. Address all feedback in new commits (don't amend)
10. Merge to main when approved

## 8. Common Issues & Solutions

### "Ruff formatting issues" Error
- Run: `uv run ruff format .`
- This auto-fixes most issues

### "Type checking failed" Error
- Run: `uv run ty check`
- Check for missing type hints in new code
- May need to configure `[tool.ty.rules]` for false positives

### "Import not found" (from workspace packages or rag_facile namespace)
- All pipeline packages use the `rag_facile.*` namespace (e.g., `from rag_facile.pipelines import get_pipeline`)
- In the monorepo: ensure the package is listed in root `pyproject.toml` dependencies + `[tool.uv.sources]`
- In generated projects: ensure `rag-facile-lib` is in dependencies and `uv sync` has run
- Run `uv sync` to regenerate lockfile

### "Moon command failed"
- Check if in correct directory (moon needs workspace context)
- Check `tools/moon.yml` for task definition
- Try `moon run [task] --log trace` for debug output

### Template Generation Issues
- Clear `.moon/templates/generated/` manually if corrupted
- Verify Tera syntax in template files
- Check that `copytree()` is used for files needing rendering
- Use `write_text()` for static content

## 9. Useful Resources

- **Proto Config**: https://moonrepo.dev/docs/proto/config
- **Moon Docs**: https://moonrepo.dev/docs/moon
- **Ruff**: https://docs.astral.sh/ruff/
- **UV**: https://docs.astral.sh/uv/
- **Typer**: https://typer.tiangolo.com/
- **Project README**: https://github.com/etalab-ia/rag-facile/README.md
- **CONTRIBUTING**: CONTRIBUTING.md in repo root

## 10. Agent Memory System

The `rag-facile` chat assistant has a persistent memory system stored in the `.agent/` directory within the user's workspace. Other coding agents (Claude Code, Letta Code, Antigravity) can read and use these files.

### Directory Layout

```
<workspace>/
└── .agent/
    ├── MEMORY.md           # Semantic store — curated facts about the user
    ├── profile.md          # Session count + language preference
    ├── logs/               # Episodic daily logs (append-only, compacted after 2 days)
    │   └── YYYY-MM-DD.md   # One file per day with turns and checkpoints
    └── sessions/           # Archived session transcripts
        └── YYYYMMDD_HHMMSS.md  # One file per completed session
```

### MEMORY.md Sections

The semantic store has 6 fixed sections, each serving a specific purpose:

| Section | Purpose | Example |
|---------|---------|---------|
| User Identity | Who the user is | `Name is Luis, works at DINUM` |
| Preferences | How they like things done | `Prefers French language for UI` |
| Project State | Current project status | `Using Albert API v0.4.1` |
| Key Facts | Important learned facts | `Preset changed to accurate` |
| Routing Table | Skill/tool routing info | Agent-internal routing data |
| Recent Context | Latest session context | Current topic or task |

### How Memory Works

1. **Agent tools**: During a session, the agent can call `memory_read`, `memory_write`, and `memory_edit` to interact with MEMORY.md.
2. **Checkpoints**: Every 8 turns, a structured checkpoint is saved to the episodic log (summary, decisions, facts).
3. **Consolidation**: When a new entry is added, it checks for existing entries on the same topic and *replaces* (not duplicates) them.
4. **Fact extraction**: At session end, an LLM call extracts key facts from the conversation and routes them to the appropriate MEMORY.md section.
5. **Compaction**: Old episodic logs (>2 days) are pruned to keep only checkpoint entries. Overfull MEMORY.md sections are trimmed (oldest entries removed).
6. **Git commit**: All `.agent/` changes are committed to git at session end (best-effort, skipped if `.agent/` is gitignored).

### Package Location

- **Source**: `packages/memory/src/rag_facile/memory/`
- **Modules**: `stores.py`, `tool.py`, `context.py`, `lifecycle.py`, `consolidation.py`, `_paths.py`
- **Tests**: `packages/memory/tests/`

### For Other Agents

To discover and use the memory:
1. Check if `.agent/MEMORY.md` exists in the workspace
2. Read it — it's plain Markdown with YAML frontmatter
3. Each `## Section` contains `- [YYYY-MM-DD] fact` entries
4. The `profile.md` file has session count and language preference

## 11. Special Knowledge for This Agent

### About Luis (The User)
- Values explicit over implicit (prefers explicit paths vs globs)
- Prefers single source of truth (no duplicate files requiring manual sync)
- Wants understanding, not just fixes (explain the "why")
- Cares about code organization and clean patterns
- Detail-oriented (catches missing updates in renaming)
- Appreciates systematic, well-documented approaches
- Emphasizes comprehensive testing before pushing

### When Implementing Features
- Always ask for clarification on major vs minor classification for commits
- Propose clean solutions - Luis will push back on hacks/workarounds
- Document as you go (README, CONTRIBUTING, docs/)
- Test with the simpler provider first before propagating changes
- Update ALL related documentation and tests together (don't batch fixes)

### Git & Documentation Standards
- Luis emphasizes proper branching and never working on main
- Documentation matters: CONTRIBUTING.md, clear PR descriptions
- Configuration belongs in pyproject.toml, not separate config files
- Exclusions should be explicit and documented
- Conventional commits are critical for his release-please setup

### Development Workflow Preferences
- Create comprehensive plans before implementation (use EnterPlanMode for non-trivial tasks)
- Batch related changes together
- Run full test suite and checks before pushing
- Provide clear explanations of changes in commit messages
