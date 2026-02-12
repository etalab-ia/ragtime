#!/usr/bin/env bash
# RAG Facile CLI installer for Unix/Linux/macOS/WSL/Git Bash
# Usage: bash <(curl -fsSL https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.sh)

set -e

# Detect OS
OS_TYPE=$(uname -s)
if [[ "$OS_TYPE" == MINGW* ]] || [[ "$OS_TYPE" == MSYS* ]]; then
    OS_IS_WINDOWS=1
else
    OS_IS_WINDOWS=0
fi

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
    fi
    
    return 0
}

# Setup proxy configuration if detected
setup_proxy_config

# Install prerequisites on Linux if needed (skip on Windows)
if [[ $OS_IS_WINDOWS -eq 0 ]] && [[ "$(uname)" == "Linux" ]] && command -v apt-get &> /dev/null; then
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

# 1. Install direnv for automatic .env file loading
if ! check_tool direnv; then
    echo "Installing direnv..."
    if [[ $OS_IS_WINDOWS -eq 0 ]] && command -v apt-get &> /dev/null; then
        # Linux
        if [[ $EUID -eq 0 ]]; then
            apt-get update && apt-get install -y direnv
        else
            sudo apt-get update && sudo apt-get install -y direnv
        fi
    elif [[ $OS_IS_WINDOWS -eq 0 ]] && command -v brew &> /dev/null; then
        # macOS
        brew install direnv
    fi
    
    # Add direnv hook to shell profile
    if check_tool direnv; then
        profile=$(detect_shell_profile)
        if ! grep -q "direnv hook" "$profile" 2>/dev/null; then
            echo "" >> "$profile"
            echo "# Added by RAG Facile installer" >> "$profile"
            if [[ "$SHELL" == */zsh ]]; then
                echo 'eval "$(direnv hook zsh)"' >> "$profile"
            else
                echo 'eval "$(direnv hook bash)"' >> "$profile"
            fi
            echo "Added direnv hook to $profile"
        fi
    fi
fi

# 2. Install proto if needed
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

# 3. Install moon via proto if needed
if ! check_tool moon; then
    echo "Installing moon via proto..."
    if ! proto install moon; then
        echo "ERROR: Failed to install moon via proto"
        echo ""
        echo "This often happens behind corporate proxies or VPNs."
        echo "Troubleshooting steps:"
        echo ""
        echo "1. Check proto logs for details"
        echo "2. Verify proxy configuration:"
        echo "   cat $PROTOTOOLS_FILE"
        echo ""
        echo "3. Test connectivity to GitHub:"
        echo "   curl -I https://github.com"
        echo ""
        echo "4. If you're behind a corporate proxy with SSL inspection:"
        echo "   a) Export your root certificate as a .pem file"
        echo "   b) Add this to $PROTOTOOLS_FILE:"
        echo "      [settings.http]"
        echo "      root-cert = \"/path/to/your/cert.pem\""
        echo ""
        echo "For more help, see: https://moonrepo.dev/docs/proto/config"
        exit 1
    fi
    
    if ! check_tool moon; then
        echo "ERROR: moon installed but not working"
        exit 1
    fi
fi

# 4. Install uv via proto if needed
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

# 5. Install just via proto
if ! check_tool just; then
    echo "Installing just via proto..."
    # Register the just plugin (idempotent - safe to run even if already registered)
    proto plugin add just "https://raw.githubusercontent.com/Phault/proto-toml-plugins/main/just/plugin.toml" 2>/dev/null || true
    
    if ! proto install just; then
        echo "ERROR: Failed to install just via proto"
        echo ""
        echo "This often happens behind corporate proxies or VPNs."
        echo "See troubleshooting steps from 'moon' installation above."
        exit 1
    fi
    
    if ! check_tool just; then
        echo "ERROR: just installed but not working"
        exit 1
    fi
fi

# 6. Install rag-facile CLI via uv
echo ""
echo "Installing RAG Facile CLI..."
BRANCH="${RAG_FACILE_BRANCH:-main}"

if ! uv tool install rag-facile-cli --force --from "git+https://github.com/etalab-ia/rag-facile.git@${BRANCH}#subdirectory=apps/cli"; then
    echo "ERROR: rag-facile installation failed"
    exit 1
fi

# 7. Verify installation
echo ""
if ! check_tool rag-facile; then
    echo "ERROR: rag-facile installation failed"
    exit 1
fi

echo "✓ RAG Facile CLI installed successfully!"
echo ""

# Provide OS-specific guidance
if [[ $OS_IS_WINDOWS -eq 1 ]]; then
    echo "🪟 Windows detected (Git Bash / MSYS2)"
    echo ""
    echo "Proto has configured your tools. You may need to:"
    echo "  1. Open a new Git Bash / terminal window"
    echo "  2. Or run: source ~/.bashrc"
    echo ""
    echo "💡 For a native Windows PowerShell experience, use install.ps1 instead:"
    echo "  irm https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.ps1 | iex"
else
    echo "✓ Proto has configured your tools."
    echo ""
    # Check if ~/.local/bin was already in the original PATH
    if [[ ":$ORIGINAL_PATH:" == *":$LOCAL_BIN:"* ]]; then
        echo "Tools are ready to use!"
    else
        echo "Proto and tool paths may need to be added to your shell profile."
        profile=$(detect_shell_profile)
        if [[ ! -f "$profile" ]]; then
            echo "Creating shell profile: $profile"
            touch "$profile"
        fi
        add_to_path "$PROTO_SHIMS" "$profile"
        add_to_path "$PROTO_BIN" "$profile"
        add_to_path "$LOCAL_BIN" "$profile"
        echo ""
        echo "Run this to use tools in your current terminal:"
        echo "  source $profile"
    fi
fi

# Export PATH to GitHub Actions environment if running in CI
if [[ -n "$GITHUB_PATH" ]]; then
    echo "Adding tool paths to GITHUB_PATH for CI..."
    echo "$PROTO_SHIMS" >> "$GITHUB_PATH"
    echo "$PROTO_BIN" >> "$GITHUB_PATH"
    echo "$LOCAL_BIN" >> "$GITHUB_PATH"
fi

echo ""
echo "Get started with:"
echo "  rag-facile setup my-rag-app"
