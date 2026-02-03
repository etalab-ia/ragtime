#!/usr/bin/env bash
# RAG Facile CLI installer
# Usage: bash <(curl -fsSL https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.sh)

set -e

PROTO_HOME="${PROTO_HOME:-$HOME/.proto}"
PROTO_BIN="$PROTO_HOME/bin"
PROTO_SHIMS="$PROTO_HOME/shims"
LOCAL_BIN="$HOME/.local/bin"
ORIGINAL_PATH="$PATH"

echo "==> Installing RAG Facile CLI"
echo ""

# Install prerequisites on Linux if needed
if [[ "$(uname)" == "Linux" ]] && command -v apt-get &> /dev/null; then
    missing=""
    for cmd in git curl xz unzip; do
        if ! command -v "$cmd" &> /dev/null; then
            missing="$missing $cmd"
        fi
    done
    
    if [[ -n "$missing" ]]; then
        echo "Installing prerequisites:$missing"
        # Use sudo if not root
        if [[ $EUID -eq 0 ]]; then
            apt-get update && apt-get install -y git curl xz-utils unzip
        else
            sudo apt-get update && sudo apt-get install -y git curl xz-utils unzip
        fi
        echo ""
    fi
fi

# Helper to check if a command exists and get version
check_tool() {
    if command -v "$1" &> /dev/null; then
        version=$("$1" --version 2>/dev/null | head -n1)
        echo "✓ $1 ($version)"
        return 0
    fi
    return 1
}

# Detect shell profile
detect_shell_profile() {
    if [[ -n "$ZSH_VERSION" ]] || [[ "$SHELL" == */zsh ]]; then
        echo "$HOME/.zshrc"
    elif [[ -n "$BASH_VERSION" ]] || [[ "$SHELL" == */bash ]]; then
        if [[ -f "$HOME/.bash_profile" ]]; then
            echo "$HOME/.bash_profile"
        else
            echo "$HOME/.bashrc"
        fi
    else
        echo "$HOME/.profile"
    fi
}

# Add a path to shell profile if not already there
add_to_path() {
    local path_to_add="$1"
    local profile="$2"
    local export_line="export PATH=\"$path_to_add:\$PATH\""
    
    if ! grep -q "$path_to_add" "$profile" 2>/dev/null; then
        echo "" >> "$profile"
        echo "# Added by RAG Facile installer" >> "$profile"
        echo "$export_line" >> "$profile"
        echo "Added $path_to_add to $profile"
    fi
}

# Add proto paths to current session
export PATH="$PROTO_SHIMS:$PROTO_BIN:$LOCAL_BIN:$PATH"

# 1. Install proto if needed
if ! check_tool proto; then
    echo "Installing proto..."
    curl -fsSL https://moonrepo.dev/install/proto.sh | bash -s -- --yes
    export PATH="$PROTO_SHIMS:$PROTO_BIN:$PATH"
    
    if ! check_tool proto; then
        echo "ERROR: proto installed but not working"
        exit 1
    fi
fi

# 2. Install moon via proto if needed
if ! check_tool moon; then
    echo "Installing moon via proto..."
    proto install moon
    
    if ! check_tool moon; then
        echo "ERROR: moon installed but not working"
        exit 1
    fi
fi

# 3. Install uv via proto if needed
if ! check_tool uv; then
    echo "Installing uv via proto..."
    proto install uv
    
    if ! check_tool uv; then
        echo "ERROR: uv installed but not working"
        exit 1
    fi
fi

# 4. Install just if needed
if ! check_tool just; then
    echo "Installing just..."
    curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to "$LOCAL_BIN"
    
    if ! check_tool just; then
        echo "ERROR: just installed but not working"
        exit 1
    fi
fi

# 5. Install rag-facile CLI via uv
echo ""
echo "Installing RAG Facile CLI..."
BRANCH="${RAG_FACILE_BRANCH:-main}"
uv tool install rag-facile-cli --force --from "git+https://github.com/etalab-ia/rag-facile.git@${BRANCH}#subdirectory=apps/cli"

# 6. Verify and handle PATH
echo ""
if [[ ! -f "$LOCAL_BIN/rag-facile" ]]; then
    echo "ERROR: rag-facile installation failed"
    exit 1
fi

# Check if ~/.local/bin was already in the user's original PATH
if [[ ":$ORIGINAL_PATH:" == *":$LOCAL_BIN:"* ]]; then
    echo "✓ RAG Facile CLI installed successfully!"
    echo ""
    echo "Get started with:"
    echo "  rag-facile generate workspace my-rag-app"
else
    echo "rag-facile was installed to $LOCAL_BIN which is not in your PATH."
    echo ""
    read -p "Would you like to add $LOCAL_BIN to your PATH? [Y/n] " -n 1 -r < /dev/tty
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
        profile=$(detect_shell_profile)
        add_to_path "$PROTO_SHIMS" "$profile"
        add_to_path "$PROTO_BIN" "$profile"
        add_to_path "$LOCAL_BIN" "$profile"
        
        echo ""
        echo "✓ RAG Facile CLI installed successfully!"
        echo ""
        echo "Run this to use rag-facile in your current terminal:"
        echo "  source $profile"
        echo ""
        echo "Or open a new terminal, then:"
        echo "  rag-facile generate workspace my-rag-app"
    else
        echo ""
        echo "To use rag-facile, add this to your shell profile:"
        echo "  export PATH=\"$PROTO_SHIMS:$PROTO_BIN:$LOCAL_BIN:\$PATH\""
    fi
fi
