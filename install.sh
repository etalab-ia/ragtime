#!/usr/bin/env bash
# Installateur RAG Facile pour Unix / macOS / WSL / Git Bash
# Prérequis : curl
# Installe : uv, just, puis la commande rag-facile en tant qu'outil global.
#
# Utilisation :
#   curl -fsSL https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.sh | bash
#
# Variables d'environnement :
#   RAG_FACILE_VERSION  Version spécifique à installer (par défaut : dernière version)

set -e

LOCAL_BIN="$HOME/.local/bin"

echo ""
echo "==> Installateur RAG Facile"
echo ""

# ── Fonctions utilitaires ──────────────────────────────────────────────────────

outil_disponible() {
    command -v "$1" &>/dev/null
}

ajouter_au_path() {
    # Rendre ~/.local/bin disponible dans cette session
    if [[ ":$PATH:" != *":$LOCAL_BIN:"* ]]; then
        export PATH="$LOCAL_BIN:$PATH"
    fi
}

spinner_start() {
    # Lance un spinner (points toutes les 2 secondes) en arrière-plan.
    # Utilisation : spinner_start ; ... ; spinner_stop
    while true; do
        printf '.'
        sleep 2
    done &
    SPINNER_PID=$!
}

spinner_stop() {
    kill "$SPINNER_PID" 2>/dev/null
    wait "$SPINNER_PID" 2>/dev/null || true
    printf '\n'
}

# ── 1. Installation de uv ─────────────────────────────────────────────────────

ajouter_au_path

if outil_disponible uv; then
    echo "✓ uv déjà installé"
else
    echo "==> Installation de uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ajouter_au_path
    if ! outil_disponible uv; then
        echo "ERREUR : l'installation de uv a échoué"
        exit 1
    fi
    echo "✓ uv installé"
fi

# ── 2. Installation de just ───────────────────────────────────────────────────

if outil_disponible just; then
    echo "✓ just déjà installé"
else
    UV_LOG=$(mktemp)
    printf "==> Installation de just "
    spinner_start

    uv tool install rust-just >"$UV_LOG" 2>&1 \
        || { UV_FAILED=true; }

    spinner_stop

    if [[ "${UV_FAILED:-}" == "true" ]]; then
        cat "$UV_LOG"
        rm -f "$UV_LOG"
        echo "ERREUR : l'installation de just a échoué"
        exit 1
    fi
    rm -f "$UV_LOG"
    ajouter_au_path
    if ! outil_disponible just; then
        echo "ERREUR : la commande just n'est pas disponible après installation"
        exit 1
    fi
    echo "✓ just installé"
fi

# ── 3. Récupération de la version ─────────────────────────────────────────────

if [[ -n "${RAG_FACILE_VERSION:-}" ]]; then
    LATEST_TAG="$RAG_FACILE_VERSION"
    echo "==> Utilisation de la version : $LATEST_TAG"
else
    echo "==> Récupération de la dernière version..."
    LATEST_TAG=$(curl -fsSL "https://api.github.com/repos/etalab-ia/rag-facile/releases/latest" \
        2>/dev/null | sed -n -E 's/.*"tag_name": *"([^"]+)".*/\1/p')

    if [[ -z "$LATEST_TAG" ]]; then
        echo "ERREUR : impossible de récupérer la dernière version depuis l'API GitHub."
        echo "         Vérifiez votre connexion ou définissez RAG_FACILE_VERSION manuellement."
        exit 1
    fi

    echo "   Dernière version : $LATEST_TAG"
fi

# ── 4. Installation de rag-facile ─────────────────────────────────────────────

UV_LOG=$(mktemp)
printf "==> Installation de rag-facile %s " "$LATEST_TAG"
spinner_start

uv tool install \
    "rag-facile-cli @ git+https://github.com/etalab-ia/rag-facile.git@${LATEST_TAG}#subdirectory=apps/cli" \
    --force >"$UV_LOG" 2>&1 \
    || { UV_FAILED=true; }

spinner_stop

if [[ "${UV_FAILED:-}" == "true" ]]; then
    cat "$UV_LOG"
    rm -f "$UV_LOG"
    echo "ERREUR : l'installation de rag-facile a échoué"
    exit 1
fi

# Afficher uniquement la ligne de résumé (ex. "Installed 1 executable: rag-facile")
SUMMARY=$(grep -E "^Installed [0-9]+ executable" "$UV_LOG" | tail -1)
[[ -n "$SUMMARY" ]] && echo "   $SUMMARY"
rm -f "$UV_LOG"

ajouter_au_path

if ! outil_disponible rag-facile; then
    echo "ERREUR : la commande rag-facile n'est pas disponible après installation"
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

# Mise à jour du profil shell si ~/.local/bin n'est pas encore dans le PATH permanent
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
    echo "     pour que 'just', 'uv' et 'rag-facile' soient disponibles."
    echo ""
fi

# Export vers l'environnement GitHub Actions si applicable
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
