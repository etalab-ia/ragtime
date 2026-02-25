#!/usr/bin/env pwsh
# RAG Facile CLI installer for Windows PowerShell
# Usage: irm https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.ps1 | iex
# Or:    powershell -ExecutionPolicy Bypass -Command "& { irm https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.ps1 | iex }"

param(
    [string]$Branch = ""
)

$ErrorActionPreference = "Stop"

# Determine which ref to install from:
# - If -Branch parameter is set, use it
# - If RAG_FACILE_BRANCH env var is set, use it (for testing pre-release branches)
# - Otherwise, fetch the latest release tag from GitHub API (stable release)
if ([string]::IsNullOrEmpty($Branch)) {
    if ($env:RAG_FACILE_BRANCH) {
        $Branch = $env:RAG_FACILE_BRANCH
        $BranchSource = "RAG_FACILE_BRANCH env var"
    } else {
        try {
            Write-Host "Fetching latest release tag..." -ForegroundColor Yellow
            $releaseInfo = Invoke-RestMethod -Uri "https://api.github.com/repos/etalab-ia/rag-facile/releases/latest" -ErrorAction Stop
            $Branch = $releaseInfo.tag_name
            $BranchSource = "latest stable release"
        } catch {
            Write-Host "WARNING: Could not fetch latest release tag, falling back to 'main'" -ForegroundColor Yellow
            $Branch = "main"
            $BranchSource = "fallback"
        }
    }
} else {
    $BranchSource = "-Branch parameter"
}

Write-Host "==> Installing RAG Facile CLI (Windows PowerShell)" -ForegroundColor Green
Write-Host ""

# Ensure execution policy allows script execution
try {
    $policy = Get-ExecutionPolicy -Scope CurrentUser
    if ($policy -eq "Restricted") {
        Write-Host "Setting execution policy to RemoteSigned..." -ForegroundColor Yellow
        Set-ExecutionPolicy -Scope CurrentUser RemoteSigned -Force | Out-Null
    }
} catch {
    Write-Host "⚠️  Could not set execution policy automatically." -ForegroundColor Yellow
    Write-Host "You may need to run in an Administrator PowerShell:" -ForegroundColor Yellow
    Write-Host "  Set-ExecutionPolicy -Scope CurrentUser RemoteSigned" -ForegroundColor Yellow
    Write-Host ""
}

# Check for proxy configuration
function Setup-ProxyConfig {
    $ProxyUrl = $null
    
    if ($env:HTTP_PROXY) {
        $ProxyUrl = $env:HTTP_PROXY
    } elseif ($env:HTTPS_PROXY) {
        $ProxyUrl = $env:HTTPS_PROXY
    }
    
    if ($ProxyUrl) {
        Write-Host "==> Detected proxy configuration: $($ProxyUrl)" -ForegroundColor Yellow
        Write-Host "Creating proto configuration for proxy support..." -ForegroundColor Yellow
        Write-Host ""
        
        $ProtoHome = if ($env:PROTO_HOME) { $env:PROTO_HOME } else { "$env:USERPROFILE\.proto" }
        $PrototoolsFile = "$ProtoHome\.prototools"
        
        # Create .proto directory if it doesn't exist
        if (-not (Test-Path $ProtoHome)) {
            New-Item -ItemType Directory -Path $ProtoHome -Force | Out-Null
        }
        
        # Only create .prototools if it doesn't already exist (preserve user config)
        if (-not (Test-Path $PrototoolsFile)) {
            $ProtoConfig = @"
# Proto configuration created by RAG Facile installer
# For corporate/restricted networks and VPN environments

[settings.http]
# Proxy configuration
proxies = ["$ProxyUrl"]

[settings.offline]
# Increase timeout for network checks when behind proxy
timeout = 5000
"@
            Set-Content -Path $PrototoolsFile -Value $ProtoConfig -Force
            Write-Host "✓ Created proto configuration at $($PrototoolsFile)" -ForegroundColor Green
        } else {
            Write-Host "✓ Proto configuration already exists at $($PrototoolsFile) (preserving existing config)" -ForegroundColor Green
        }
        Write-Host ""
        
        # Check for corporate proxy
        if ($ProxyUrl -match "corp|internal") {
            Write-Host "⚠️  Corporate proxy detected (based on URL)" -ForegroundColor Yellow
            Write-Host ""
            Write-Host "If you encounter SSL certificate errors, you have two options:" -ForegroundColor Yellow
            Write-Host ""
            Write-Host "Option 1: Export your corporate root certificate" -ForegroundColor Cyan
            Write-Host "  1. Export the root certificate from your proxy/firewall as a .pem file" -ForegroundColor Cyan
            Write-Host "  2. Add to ~/.proto/.prototools:" -ForegroundColor Cyan
            Write-Host "     [settings.http]" -ForegroundColor Cyan
            Write-Host "     root-cert = `"/path/to/corporate-cert.pem`"" -ForegroundColor Cyan
            Write-Host ""
            Write-Host "Option 2: Allow invalid certificates (not recommended)" -ForegroundColor Cyan
            Write-Host "  Add to ~/.proto/.prototools:" -ForegroundColor Cyan
            Write-Host "  [settings.http]" -ForegroundColor Cyan
            Write-Host "  allow-invalid-certs = true" -ForegroundColor Cyan
            Write-Host ""
        }
    }
}

# Helper to check if a command exists
function Test-Command {
    param([string]$Name)
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if ($cmd) {
        $version = & $Name --version 2>$null | Select-Object -First 1
        Write-Host "✓ $($Name) ($($version))" -ForegroundColor Green
        return $true
    }
    return $false
}

Setup-ProxyConfig

# 1. Install proto if needed
if (-not (Test-Command proto)) {
    Write-Host "Installing proto..." -ForegroundColor Yellow
    try {
        irm https://moonrepo.dev/install/proto.ps1 | iex
    } catch {
        Write-Host "ERROR: Failed to install proto" -ForegroundColor Red
        Write-Host ""
        Write-Host "This can happen if:" -ForegroundColor Red
        Write-Host "  1. Network connection is unavailable" -ForegroundColor Red
        Write-Host "  2. You're behind a corporate proxy with SSL inspection" -ForegroundColor Red
        Write-Host ""
        Write-Host "Solutions:" -ForegroundColor Red
        Write-Host "  1. Check your internet connection" -ForegroundColor Red
        Write-Host "  2. If behind corporate proxy, see proxy setup instructions above" -ForegroundColor Red
        exit 1
    }
    Write-Host ""
}

# Set proto paths for current session
$ProtoHome = if ($env:PROTO_HOME) { $env:PROTO_HOME } else { "$env:USERPROFILE\.proto" }
$ProtoBin = "$ProtoHome\bin"
$ProtoShims = "$ProtoHome\shims"
$env:PATH = "$ProtoBin;$ProtoShims;$env:PATH"

# In GitHub Actions, add proto paths to GITHUB_PATH for subsequent steps
if ($env:GITHUB_PATH) {
    Write-Host "Adding proto paths to GITHUB_PATH for CI..." -ForegroundColor Yellow
    Add-Content -Path $env:GITHUB_PATH -Value $ProtoShims
    Add-Content -Path $env:GITHUB_PATH -Value $ProtoBin
}

if (-not (Test-Command proto)) {
    Write-Host "ERROR: proto installed but not working" -ForegroundColor Red
    exit 1
}

# 2. Install moon via proto
if (-not (Test-Command moon)) {
    Write-Host "Installing moon via proto..." -ForegroundColor Yellow
    try {
        proto install moon
    } catch {
        Write-Host "ERROR: Failed to install moon via proto" -ForegroundColor Red
        Write-Host ""
        Write-Host "This often happens behind corporate proxies or VPNs." -ForegroundColor Red
        Write-Host "Troubleshooting steps:" -ForegroundColor Red
        Write-Host ""
        Write-Host "1. Check proto logs for details" -ForegroundColor Red
        Write-Host "2. Verify proxy configuration:" -ForegroundColor Red
        Write-Host "   cat ~/.proto/.prototools" -ForegroundColor Red
        Write-Host ""
        Write-Host "For more help, see: https://moonrepo.dev/docs/proto/config" -ForegroundColor Red
        exit 1
    }
    Write-Host ""
}

if (-not (Test-Command moon)) {
    Write-Host "ERROR: moon installed but not working" -ForegroundColor Red
    exit 1
}

# 3. Install uv via proto
if (-not (Test-Command uv)) {
    Write-Host "Installing uv via proto..." -ForegroundColor Yellow
    try {
        proto install uv
    } catch {
        Write-Host "ERROR: Failed to install uv via proto" -ForegroundColor Red
        Write-Host "See troubleshooting steps from moon installation above." -ForegroundColor Red
        exit 1
    }
    Write-Host ""
}

if (-not (Test-Command uv)) {
    Write-Host "ERROR: uv installed but not working" -ForegroundColor Red
    exit 1
}

# 4. Register and install just plugin
Write-Host "Installing just via proto..." -ForegroundColor Yellow
try {
    # Register the just plugin (idempotent)
    proto plugin add just "https://raw.githubusercontent.com/Phault/proto-toml-plugins/main/just/plugin.toml" 2>$null
    proto install just
} catch {
    Write-Host "ERROR: Failed to install just via proto" -ForegroundColor Red
    Write-Host "See troubleshooting steps from moon installation above." -ForegroundColor Red
    exit 1
}

if (-not (Test-Command just)) {
    Write-Host "ERROR: just installed but not working" -ForegroundColor Red
    exit 1
}

Write-Host ""

# 5. Install rag-facile CLI via uv
Write-Host "Installing RAG Facile CLI..." -ForegroundColor Yellow
Write-Host "Using ref: $Branch ($BranchSource)" -ForegroundColor Cyan
try {
    $gitUrl = "git+https://github.com/etalab-ia/rag-facile.git@${Branch}#subdirectory=apps/cli"
    uv tool install rag-facile-cli --force --from $gitUrl
} catch {
    Write-Host "ERROR: rag-facile installation failed" -ForegroundColor Red
    exit 1
}

# Add uv tools directory to PATH for current session
$UvToolsPath = "$env:USERPROFILE\.local\bin"
$env:PATH = "$UvToolsPath;$env:PATH"

# In GitHub Actions, add to GITHUB_PATH for subsequent steps
if ($env:GITHUB_PATH) {
    Write-Host "Adding uv tools path to GITHUB_PATH for CI..." -ForegroundColor Yellow
    Add-Content -Path $env:GITHUB_PATH -Value $UvToolsPath
}

# For local installations, add to User PATH in registry for future sessions
if (-not $env:GITHUB_PATH) {
    $UserPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
    if ($UserPath -notlike "*$UvToolsPath*") {
        [System.Environment]::SetEnvironmentVariable("Path", "$UvToolsPath;$UserPath", "User")
        Write-Host "Added uv tools directory to system PATH" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "✓ RAG Facile CLI installed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Proto has updated your system PATH. Open a new PowerShell window and try:" -ForegroundColor Cyan
Write-Host "  rag-facile setup my-rag-app" -ForegroundColor Cyan
Write-Host ""
