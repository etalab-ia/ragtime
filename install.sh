#!/usr/bin/env bash
# RAG Facile CLI installer
# Usage: bash <(curl -fsSL https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.sh)

set -e

PROTO_HOME="${PROTO_HOME:-$HOME/.proto}"
PROTO_BIN="$PROTO_HOME/bin"
PROTO_SHIMS="$PROTO_HOME/shims"
LOCAL_BIN="$HOME/.local/bin"
ORIGINAL_PATH="$PATH"
PROTOTOOLS_FILE="$PROTO_HOME/.prototools"

echo "==> Installing RAG Facile CLI"
echo ""

# Check for proxy configuration
setup_proxy_config() {
    local has_proxy=0
    local proxy_url=""
    
    # Check for common proxy environment variables
    if [[ -n "${HTTP_PROXY:-}" ]]; then
        proxy_url="$HTTP_PROXY"
        has_proxy=1
    elif [[ -n "${http_proxy:-}" ]]; then
        proxy_url="$http_proxy"
        has_proxy=1
    elif [[ -n "${HTTPS_PROXY:-}" ]]; then
        proxy_url="$HTTPS_PROXY"
        has_proxy=1
    elif [[ -n "${https_proxy:-}" ]]; then
        proxy_url="$https_proxy"
        has_proxy=1
    fi
    
    if [[ $has_proxy -eq 1 ]]; then
        echo "==> Detected proxy configuration: $proxy_url"
        echo "Creating proto configuration for proxy support..."
        echo ""
        
        # Create .proto directory if it doesn't exist
        mkdir -p "$PROTO_HOME"
        
        # Only create .prototools if it doesn't already exist (preserve user config)
        if [[ ! -f "$PROTOTOOLS_FILE" ]]; then
            cat > "$PROTOTOOLS_FILE" << EOF
# Proto configuration created by RAG Facile installer
# For corporate/restricted networks and VPN environments

[settings.http]
# Proxy configuration
proxies = ["$proxy_url"]

[settings.offline]
# Increase timeout for network checks when behind proxy
timeout = 5000
EOF
            echo "✓ Created proto configuration at $PROTOTOOLS_FILE"
        else
            echo "✓ Proto configuration already exists at $PROTOTOOLS_FILE (preserving existing config)"
        fi
        echo ""
        
        # Check for corporate proxy (likely to use SSL inspection)
        if [[ "$proxy_url" =~ "corp" ]] || [[ "$proxy_url" =~ "internal" ]]; then
            echo "⚠️  Corporate proxy detected (based on URL)"
            echo ""
            echo "If you encounter SSL certificate errors, you have two options:"
            echo ""
            echo "Option 1: Export your corporate root certificate"
            echo "  1. Export the root certificate from your proxy/firewall as a .pem file"
            echo "  2. Add to $PROTOTOOLS_FILE:"
            echo "     [settings.http]"
            echo "     root-cert = \"/path/to/corporate-cert.pem\""
            echo ""
            echo "Option 2: Allow invalid certificates (not recommended)"
            echo "  Add to $PROTOTOOLS_FILE:"
            echo "  [settings.http]"
            echo "  allow-invalid-certs = true"
            echo ""
        fi
        
        return 0
    fi
    
    return 1
}

# Setup proxy configuration if detected
setup_proxy_config

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
    
    proto_installer="/tmp/proto-install-$$.sh"
    
    # Try downloading with SSL verification first (secure)
    if ! curl -fsSL https://moonrepo.dev/install/proto.sh -o "$proto_installer" 2>/tmp/curl-error-$$.txt; then
        # If SSL certificate error, try again with -k (skip SSL verification)
        if grep -q "SSL certificate" /tmp/curl-error-$$.txt 2>/dev/null; then
            echo "⚠️  SSL certificate verification failed. Trying with certificate verification disabled..."
            if curl -fsSLk https://moonrepo.dev/install/proto.sh -o "$proto_installer" 2>/dev/null; then
                echo "✓ Downloaded successfully (note: SSL verification was disabled)"
            else
                # curl -k still failed
                echo "ERROR: Failed to download proto installer"
                echo ""
                echo "This can happen if:"
                echo "  1. Network connection is unavailable"
                echo "  2. You're behind a corporate proxy with SSL inspection"
                echo ""
                echo "Error details:"
                cat /tmp/curl-error-$$.txt 2>/dev/null || echo "  (check your network connection)"
                echo ""
                echo "Solutions for SSL inspection by corporate proxy:"
                echo "  1. Ask your IT team to whitelist: github.com, ghcr.io, api.github.com, moonrepo.dev"
                echo "  2. Or export your corporate root certificate and configure proto:"
                echo "     mkdir -p ~/.proto"
                echo "     cat > ~/.proto/.prototools << 'EOF'"
                echo "     [settings.http]"
                echo "     root-cert = \"/path/to/corporate-ca.pem\""
                echo "     EOF"
                echo ""
                echo "For more help, see: https://github.com/etalab-ia/rag-facile/blob/main/docs/"
                rm -f "$proto_installer" /tmp/curl-error-$$.txt
                exit 1
            fi
        else
            # Not an SSL error
            echo "ERROR: Failed to download proto installer"
            echo ""
            echo "Error details:"
            cat /tmp/curl-error-$$.txt 2>/dev/null || echo "  (check your network connection)"
            echo ""
            echo "For more help, see: https://github.com/etalab-ia/rag-facile/blob/main/docs/"
            rm -f "$proto_installer" /tmp/curl-error-$$.txt
            exit 1
        fi
    fi
    
    # Run the installer (preserve proxy env vars so proto can use them)
    if ! HTTP_PROXY="$HTTP_PROXY" HTTPS_PROXY="$HTTPS_PROXY" bash "$proto_installer" --yes; then
        echo "ERROR: proto installation failed"
        echo ""
        echo "For help, see: https://github.com/etalab-ia/rag-facile/blob/main/docs/"
        rm -f "$proto_installer" /tmp/curl-error-$$.txt
        exit 1
    fi
    
    rm -f "$proto_installer" /tmp/curl-error-$$.txt
    export PATH="$PROTO_SHIMS:$PROTO_BIN:$PATH"
    
    if ! check_tool proto; then
        echo "ERROR: proto installed but not working"
        exit 1
    fi
fi

# 2. Install moon via proto if needed
if ! check_tool moon; then
    echo "Installing moon via proto..."
    if ! proto install moon; then
        echo "ERROR: Failed to install moon via proto"
        echo ""
        echo "This often happens behind corporate proxies or VPNs."
        echo "Troubleshooting steps:"
        echo ""
        echo "1. Check proto logs for details:"
        echo "   Check ~/.proto logs for more information"
        echo ""
        echo "2. Verify proxy configuration:"
        echo "   cat $PROTOTOOLS_FILE"
        echo ""
        echo "3. Test connectivity to GitHub:"
        echo "   curl -I https://github.com"
        echo "   curl -I https://ghcr.io"
        echo ""
        echo "4. If you're behind a corporate proxy with SSL inspection:"
        echo "   a) Export your root certificate as a .pem file"
        echo "   b) Add this to $PROTOTOOLS_FILE:"
        echo "      [settings.http]"
        echo "      root-cert = \"/path/to/your/cert.pem\""
        echo ""
        echo "5. For more help, see: https://moonrepo.dev/docs/proto/config"
        exit 1
    fi
    
    if ! check_tool moon; then
        echo "ERROR: moon installed but not working"
        exit 1
    fi
fi

# 3. Install uv via proto if needed
if ! check_tool uv; then
    echo "Installing uv via proto..."
    if ! proto install uv; then
        echo "ERROR: Failed to install uv via proto"
        echo ""
        echo "This often happens behind corporate proxies or VPNs."
        echo "See troubleshooting steps from 'moon' installation above."
        exit 1
    fi
    
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
    echo "  rag-facile setup my-rag-app"
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
        echo "  rag-facile setup my-rag-app"
    else
        echo ""
        echo "To use rag-facile, add this to your shell profile:"
        echo "  export PATH=\"$PROTO_SHIMS:$PROTO_BIN:$LOCAL_BIN:\$PATH\""
    fi
fi
