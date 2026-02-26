# RAG Facile installer for Windows PowerShell
# Prerequisites: PowerShell 5.1+ (no other prerequisites)
# Installs: uv, just, then downloads and sets up the latest RAG Facile workspace.
#
# Usage:
#   irm https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.ps1 | iex
#
# Environment variables:
#   RAG_FACILE_LOCAL_ASSET  Path to a local zip asset (for CI - skips GitHub download)
#   RAG_FACILE_DIR          Target directory name (default: my-rag-app)

param(
    [string]$WorkspaceDir = ""
)

$ErrorActionPreference = "Stop"
$PYTHONUTF8 = "1"  # Force UTF-8 for Python output

if ([string]::IsNullOrEmpty($WorkspaceDir)) {
    $WorkspaceDir = if ($env:RAG_FACILE_DIR) { $env:RAG_FACILE_DIR } else { "my-rag-app" }
}

$LocalBin = "$env:USERPROFILE\.local\bin"

Write-Host ""
Write-Host "==> RAG Facile Installer" -ForegroundColor Green
Write-Host ""

# Ensure LocalBin is on PATH for this session
if ($env:PATH -notlike "*$LocalBin*") {
    $env:PATH = "$LocalBin;$env:PATH"
}

# -- Helpers -------------------------------------------------------------------

function Test-Command($name) {
    return [bool](Get-Command $name -ErrorAction SilentlyContinue)
}

# -- 1. Install uv -------------------------------------------------------------

if (Test-Command "uv") {
    Write-Host "OK uv already installed" -ForegroundColor Green
} else {
    Write-Host "==> Installing uv..." -ForegroundColor Yellow
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    # Refresh PATH
    $env:PATH = "$LocalBin;$env:PATH"
    if (-not (Test-Command "uv")) {
        Write-Error "ERROR: uv installation failed"
        exit 1
    }
    Write-Host "OK uv installed" -ForegroundColor Green
}

# -- 2. Install just -----------------------------------------------------------

if (Test-Command "just") {
    Write-Host "OK just already installed" -ForegroundColor Green
} else {
    Write-Host "==> Installing just..." -ForegroundColor Yellow
    # just has no official install.ps1 - download binary zip from GitHub Releases
    try {
        $justTag = (Invoke-RestMethod -Uri "https://api.github.com/repos/casey/just/releases/latest" -ErrorAction Stop).tag_name
    } catch {
        Write-Error "ERROR: Could not fetch just release info from GitHub API."
        exit 1
    }
    $arch = if ([System.Environment]::Is64BitOperatingSystem) { "x86_64" } else { "i686" }
    $justUrl = "https://github.com/casey/just/releases/download/$justTag/just-$justTag-$arch-pc-windows-msvc.zip"
    $justZip = [System.IO.Path]::GetTempFileName() -replace "\.tmp$", ".zip"

    try {
        Invoke-WebRequest -Uri $justUrl -OutFile $justZip -ErrorAction Stop
    } catch {
        Write-Error "ERROR: Could not download just from $justUrl"
        exit 1
    }

    New-Item -ItemType Directory -Force -Path $LocalBin | Out-Null
    Expand-Archive -Path $justZip -DestinationPath $LocalBin -Force
    Remove-Item $justZip -Force -ErrorAction SilentlyContinue

    $env:PATH = "$LocalBin;$env:PATH"
    if (-not (Test-Command "just")) {
        Write-Error "ERROR: just installation failed"
        exit 1
    }
    Write-Host "OK just installed" -ForegroundColor Green
}

# -- 3. Download the release workspace zip -------------------------------------

$AssetPath = ""

if ($env:RAG_FACILE_LOCAL_ASSET) {
    Write-Host "==> Using local asset: $($env:RAG_FACILE_LOCAL_ASSET)" -ForegroundColor Yellow
    $AssetPath = $env:RAG_FACILE_LOCAL_ASSET
} else {
    Write-Host "==> Fetching latest release..." -ForegroundColor Yellow
    try {
        $releaseInfo = Invoke-RestMethod -Uri "https://api.github.com/repos/etalab-ia/rag-facile/releases/latest" -ErrorAction Stop
        $LatestTag = $releaseInfo.tag_name
    } catch {
        Write-Error "ERROR: Could not fetch latest release tag from GitHub API. Check your network connection."
        exit 1
    }

    Write-Host "   Latest release: $LatestTag" -ForegroundColor Cyan
    $AssetUrl = "https://github.com/etalab-ia/rag-facile/releases/download/$LatestTag/rag-facile-workspace-$LatestTag.zip"
    $AssetPath = [System.IO.Path]::GetTempFileName() -replace "\.tmp$", ".zip"

    Write-Host "==> Downloading workspace..." -ForegroundColor Yellow
    try {
        Invoke-WebRequest -Uri $AssetUrl -OutFile $AssetPath -ErrorAction Stop
    } catch {
        Write-Error "ERROR: Could not download $AssetUrl"
        exit 1
    }
}

# -- 4. Extract ----------------------------------------------------------------

if (Test-Path $WorkspaceDir) {
    Write-Error "ERROR: Directory '$WorkspaceDir' already exists. Set RAG_FACILE_DIR to a different name."
    if (-not $env:RAG_FACILE_LOCAL_ASSET) { Remove-Item $AssetPath -Force -ErrorAction SilentlyContinue }
    exit 1
}

Write-Host "==> Extracting to .\$WorkspaceDir\ ..." -ForegroundColor Yellow
$ExtractTmp = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), "rag-facile-extract-$PID")
Expand-Archive -Path $AssetPath -DestinationPath $ExtractTmp -Force

# Move the extracted inner directory to the chosen workspace name
$ExtractedDir = Get-ChildItem $ExtractTmp | Select-Object -First 1
Move-Item -Path $ExtractedDir.FullName -Destination $WorkspaceDir

Remove-Item $ExtractTmp -Recurse -Force -ErrorAction SilentlyContinue
if (-not $env:RAG_FACILE_LOCAL_ASSET) { Remove-Item $AssetPath -Force -ErrorAction SilentlyContinue }

Write-Host "OK Extracted to .\$WorkspaceDir\" -ForegroundColor Green

# -- 5. Install dependencies ---------------------------------------------------

Write-Host "==> Installing dependencies (this may take a minute on first run)..." -ForegroundColor Yellow
Push-Location $WorkspaceDir
try {
    uv sync
} finally {
    Pop-Location
}

# -- 6. Done -------------------------------------------------------------------

Write-Host ""
Write-Host "Done: RAG Facile is ready!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host ""
Write-Host "  1. Add your Albert API key:"
Write-Host "       cd $WorkspaceDir"
Write-Host "       copy .env.template .env"
Write-Host "       # Edit .env and set OPENAI_API_KEY=<your-key>"
Write-Host "       # Get a key at: https://albert.sites.beta.gouv.fr/"
Write-Host ""
Write-Host "  2. Start your app:"
Write-Host "       cd $WorkspaceDir; just run"
Write-Host ""
Write-Host "  3. Chat with the RAG assistant:"
Write-Host "       cd $WorkspaceDir; just learn"
Write-Host ""

# Add LocalBin to permanent User PATH if not already there
$UserPath = [System.Environment]::GetEnvironmentVariable("PATH", "User")
if ($UserPath -notlike "*$LocalBin*") {
    [System.Environment]::SetEnvironmentVariable(
        "PATH",
        "$LocalBin;$UserPath",
        "User"
    )
    Write-Host "  WARNING:  Open a new PowerShell window so PATH changes take effect."
    Write-Host ""
}
