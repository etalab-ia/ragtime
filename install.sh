#!/usr/bin/env bash
# RAG Facile installer for Unix / macOS / WSL / Git Bash
# Prerequisites: curl
# Installs: uv, just, then the rag-facile CLI as a global tool.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.sh | bash
#
# Environment variables:
#   RAG_FACILE_VERSION  Specific version tag to install (default: latest release)

set -e

LOCAL_BIN="$HOME/.local/bin"

echo ""
echo "==> RAG Facile Installer"
echo ""

# ── Helpers ───────────────────────────────────────────────────────────────────

check_tool() {
    command -v "$1" &>/dev/null
}

ensure_bin_on_path() {
    # Make ~/.local/bin available in this session (uv, just, and rag-facile land there)
    if [[ ":$PATH:" != *":$LOCAL_BIN:"* ]]; then
        export PATH="$LOCAL_BIN:$PATH"
    fi
}

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
    curl -LsSf https://just.systems/install.sh | bash -s -- --to "$LOCAL_BIN"
    ensure_bin_on_path
    if ! check_tool just; then
        echo "ERROR: just installation failed"
        exit 1
    fi
    echo "✓ just installed"
fi

# ── 3. Fetch release tag ───────────────────────────────────────────────────────

if [[ -n "${RAG_FACILE_VERSION:-}" ]]; then
    LATEST_TAG="$RAG_FACILE_VERSION"
    echo "==> Using version: $LATEST_TAG"
else
    echo "==> Fetching latest release..."
    LATEST_TAG=$(curl -fsSL "https://api.github.com/repos/etalab-ia/rag-facile/releases/latest" \
        2>/dev/null | sed -n -E 's/.*"tag_name": *"([^"]+)".*/\1/p')

    if [[ -z "$LATEST_TAG" ]]; then
        echo "ERROR: Could not fetch latest release tag from GitHub API."
        echo "       Check your network connection or set RAG_FACILE_VERSION manually."
        exit 1
    fi

    echo "   Latest release: $LATEST_TAG"
fi

# ── 4. Install rag-facile CLI ─────────────────────────────────────────────────

echo "==> Installing rag-facile $LATEST_TAG..."
uv tool install \
    "rag-facile-cli @ git+https://github.com/etalab-ia/rag-facile.git@${LATEST_TAG}#subdirectory=apps/cli" \
    --force

ensure_bin_on_path

if ! check_tool rag-facile; then
    echo "ERROR: rag-facile installation failed"
    exit 1
fi

echo "✓ rag-facile installé"

# ── 5. Terminé ────────────────────────────────────────────────────────────────

echo ""
echo "✅ RAG Facile est prêt !"
echo ""
cat <<EOF
Prochaines étapes :

  1. Créez votre projet RAG :
       rag-facile setup mon-projet

  2. Lancez votre application :
       cd mon-projet && just run

  3. Apprenez, explorez et configurez avec votre assistant IA :
       cd mon-projet && just learn

     Votre assistant peut vous aider à :
       • Comprendre le projet que vous venez d'installer
       • Apprendre les concepts RAG
       • Configurer votre application

  4. Vous découvrez les assistants conversationnels basés sur le RAG ?
     Le guide officiel de la DINUM vous accompagne pas à pas,
     de l'investigation jusqu'à la mise en production — conçu pour
     les porteurs de projet, chefs de projet et équipes non-expertes.

     👉  https://docs.numerique.gouv.fr/docs/6bd3ca79-9cb9-4603-866a-6fa1788d2c8e/

EOF

# Guidance for shell profiles (so just/uv/rag-facile are found after terminal restart)
if [[ ":$PATH:" != *":$LOCAL_BIN:"* ]]; then
    if [[ -n "$ZSH_VERSION" ]] || [[ "$SHELL" == */zsh ]]; then
        PROFILE="$HOME/.zshrc"
    elif [[ -f "$HOME/.bash_profile" ]]; then
        PROFILE="$HOME/.bash_profile"
    else
        PROFILE="$HOME/.bashrc"
    fi

    if ! grep -q "$LOCAL_BIN" "$PROFILE" 2>/dev/null; then
        echo "" >> "$PROFILE"
        echo "# Ajouté par l'installateur RAG Facile" >> "$PROFILE"
        echo "export PATH=\"$LOCAL_BIN:\$PATH\"" >> "$PROFILE"
    fi

    echo "  ⚠️  Redémarrez votre terminal (ou lancez : source $PROFILE)"
    echo "     pour que 'just', 'uv' et 'rag-facile' soient disponibles dans les prochaines sessions."
    echo ""
fi

# Export to GitHub Actions CI environment if applicable
if [[ -n "${GITHUB_PATH:-}" ]]; then
    echo "$LOCAL_BIN" >> "$GITHUB_PATH"
fi

# ── 6. Rejoindre la communauté ALLiaNCE ───────────────────────────────────────

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  🤝  Rejoignez la communauté ALLiaNCE !"
echo ""
echo "  L'incubateur IA de la DINUM — pour les agents publics de l'État"
echo "  qui souhaitent faire adopter l'IA au service de la vie des gens et des agents."
echo ""
echo "  👉  https://alliance.numerique.gouv.fr/les-membres-de-lincubateur/"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
