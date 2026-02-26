#!/usr/bin/env bash
# RAG Facile installer for Unix / macOS / WSL / Git Bash
# Prerequisites: curl, unzip (auto-installed on apt/dnf/yum systems if missing)
# Installs: uv, just, then downloads and sets up the latest RAG Facile workspace.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.sh | bash
#
# Environment variables:
#   RAG_FACILE_LOCAL_ASSET  Path to a local zip asset (for CI — skips GitHub download)
#   RAG_FACILE_DIR          Target directory name (default: my-rag-app)

set -e

WORKSPACE_DIR="${RAG_FACILE_DIR:-my-rag-app}"
LOCAL_BIN="$HOME/.local/bin"

echo ""
echo "==> RAG Facile Installer"
echo ""

# ── Helpers ───────────────────────────────────────────────────────────────────

check_tool() {
    command -v "$1" &>/dev/null
}

ensure_bin_on_path() {
    # Make ~/.local/bin available in this session (uv and just land there)
    if [[ ":$PATH:" != *":$LOCAL_BIN:"* ]]; then
        export PATH="$LOCAL_BIN:$PATH"
    fi
}

# ── 0. Ensure prerequisites ───────────────────────────────────────────────────

if ! check_tool unzip; then
    echo "==> Installing prerequisite: unzip"
    if [[ "$(uname)" == "Linux" ]]; then
        if command -v apt-get &>/dev/null; then
            if [[ $EUID -eq 0 ]]; then
                apt-get update -qq && apt-get install -y -qq unzip
            else
                sudo apt-get update -qq && sudo apt-get install -y -qq unzip
            fi
        elif command -v dnf &>/dev/null; then
            sudo dnf install -y unzip 2>/dev/null || dnf install -y unzip
        elif command -v yum &>/dev/null; then
            sudo yum install -y unzip 2>/dev/null || yum install -y unzip
        else
            echo "ERROR: 'unzip' is required but could not be installed automatically."
            echo "       Please install it manually, then re-run this script."
            exit 1
        fi
    fi
    if ! check_tool unzip; then
        echo "ERROR: 'unzip' is required but is not available."
        exit 1
    fi
    echo "✓ unzip installed"
fi

# ── 1. Install uv ─────────────────────────────────────────────────────────────

ensure_bin_on_path

if check_tool uv; then
    echo "✓ uv already installed"
else
    echo "==> Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ensure_bin_on_path
    if ! check_tool uv; then
        echo "ERROR: uv installation failed"
        exit 1
    fi
    echo "✓ uv installed"
fi

# ── 2. Install just ───────────────────────────────────────────────────────────

if check_tool just; then
    echo "✓ just already installed"
else
    echo "==> Installing just..."
    # Official just installer — downloads a single static binary to ~/.local/bin
    curl -LsSf https://just.systems/install.sh | bash -s -- --to "$LOCAL_BIN"
    ensure_bin_on_path
    if ! check_tool just; then
        echo "ERROR: just installation failed"
        exit 1
    fi
    echo "✓ just installed"
fi

# ── 3. Download the release workspace zip ─────────────────────────────────────

if [[ -n "${RAG_FACILE_LOCAL_ASSET:-}" ]]; then
    # CI mode: use a pre-built local asset (no GitHub API call needed)
    echo "==> Using local asset: $RAG_FACILE_LOCAL_ASSET"
    ASSET_PATH="$RAG_FACILE_LOCAL_ASSET"
else
    echo "==> Fetching latest release..."
    LATEST_TAG=$(curl -fsSL "https://api.github.com/repos/etalab-ia/rag-facile/releases/latest" \
        2>/dev/null | sed -n -E 's/.*"tag_name": *"([^"]+)".*/\1/p')

    if [[ -z "$LATEST_TAG" ]]; then
        echo "ERROR: Could not fetch latest release tag from GitHub API."
        echo "       Check your network connection or set RAG_FACILE_LOCAL_ASSET for offline use."
        exit 1
    fi

    echo "   Latest release: $LATEST_TAG"
    ASSET_URL="https://github.com/etalab-ia/rag-facile/releases/download/${LATEST_TAG}/rag-facile-workspace-${LATEST_TAG}.zip"
    ASSET_PATH="/tmp/rag-facile-workspace-$$.zip"

    echo "==> Downloading workspace..."
    if ! curl -fsSL "$ASSET_URL" -o "$ASSET_PATH"; then
        echo "ERROR: Could not download $ASSET_URL"
        echo "       Make sure the release has the workspace zip attached."
        rm -f "$ASSET_PATH"
        exit 1
    fi
fi

# ── 4. Extract ────────────────────────────────────────────────────────────────

if [[ -d "$WORKSPACE_DIR" ]]; then
    echo "ERROR: Directory '$WORKSPACE_DIR' already exists."
    echo "       Move it aside or set RAG_FACILE_DIR to a different name:"
    echo "         RAG_FACILE_DIR=my-app bash install.sh"
    # Clean up temp asset if we downloaded it
    [[ -z "${RAG_FACILE_LOCAL_ASSET:-}" ]] && rm -f "$ASSET_PATH"
    exit 1
fi

echo "==> Extracting to ./$WORKSPACE_DIR/ ..."
# The zip contains a single top-level dir (my-rag-app/).
# We extract to a temp dir then rename to the chosen WORKSPACE_DIR.
EXTRACT_TMP="/tmp/rag-facile-extract-$$"
mkdir -p "$EXTRACT_TMP"
unzip -q "$ASSET_PATH" -d "$EXTRACT_TMP"

# Find the extracted directory (should be exactly one)
EXTRACTED_DIR=$(ls -1 "$EXTRACT_TMP" | head -n1)
mv "$EXTRACT_TMP/$EXTRACTED_DIR" "$WORKSPACE_DIR"
rm -rf "$EXTRACT_TMP"

# Clean up temp asset if we downloaded it
[[ -z "${RAG_FACILE_LOCAL_ASSET:-}" ]] && rm -f "$ASSET_PATH"

echo "✓ Extracted to ./$WORKSPACE_DIR/"

# ── 5. Install dependencies ───────────────────────────────────────────────────

echo "==> Installing dependencies (this may take a minute on first run)..."
cd "$WORKSPACE_DIR"
uv sync
cd - >/dev/null

# ── 6. Done ───────────────────────────────────────────────────────────────────

echo ""
echo "✅ RAG Facile is ready!"
echo ""
echo "Next steps:"
echo ""
echo "  1. Add your Albert API key:"
echo "       cd $WORKSPACE_DIR"
echo "       cp .env.template .env"
echo "       # Edit .env and set OPENAI_API_KEY=<your-key>"
echo "       # Get a key at: https://albert.sites.beta.gouv.fr/"
echo ""
echo "  2. Start your app:"
echo "       cd $WORKSPACE_DIR && just run"
echo ""
echo "  3. Chat with the RAG assistant:"
echo "       cd $WORKSPACE_DIR && just learn"
echo ""

# Guidance for shell profiles (so just/uv are found after terminal restart)
if [[ ":$PATH:" != *":$LOCAL_BIN:"* ]]; then
    # Detect shell profile
    if [[ -n "$ZSH_VERSION" ]] || [[ "$SHELL" == */zsh ]]; then
        PROFILE="$HOME/.zshrc"
    elif [[ -f "$HOME/.bash_profile" ]]; then
        PROFILE="$HOME/.bash_profile"
    else
        PROFILE="$HOME/.bashrc"
    fi

    # Add to profile if not already there
    if ! grep -q "$LOCAL_BIN" "$PROFILE" 2>/dev/null; then
        echo "" >> "$PROFILE"
        echo "# Added by RAG Facile installer" >> "$PROFILE"
        echo "export PATH=\"$LOCAL_BIN:\$PATH\"" >> "$PROFILE"
    fi

    echo "  ⚠️  Restart your terminal (or run: source $PROFILE)"
    echo "     so that 'just' and 'uv' are found in future sessions."
    echo ""
fi

# Export to GitHub Actions CI environment if applicable
if [[ -n "${GITHUB_PATH:-}" ]]; then
    echo "$LOCAL_BIN" >> "$GITHUB_PATH"
fi
