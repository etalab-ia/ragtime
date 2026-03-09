# RAG Facile installer for Windows PowerShell
# Prerequisites: PowerShell 5.1+ (no other prerequisites)
# Installs: uv, just, then the rag-facile CLI as a global tool.
#
# Usage:
#   irm https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.ps1 | iex
#
# Environment variables:
#   RAG_FACILE_VERSION  Specific version tag to install (default: latest release)

$ErrorActionPreference = "Stop"
$PYTHONUTF8 = "1"  # Force UTF-8 for Python output

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

# -- 3. Fetch release tag ------------------------------------------------------

if ($env:RAG_FACILE_VERSION) {
    $LatestTag = $env:RAG_FACILE_VERSION
    Write-Host "==> Using version: $LatestTag" -ForegroundColor Yellow
} else {
    Write-Host "==> Fetching latest release..." -ForegroundColor Yellow
    try {
        $LatestTag = (Invoke-RestMethod -Uri "https://api.github.com/repos/etalab-ia/rag-facile/releases/latest" -ErrorAction Stop).tag_name
    } catch {
        Write-Error "ERROR: Could not fetch latest release tag from GitHub API. Check your network connection."
        exit 1
    }
    Write-Host "   Latest release: $LatestTag" -ForegroundColor Cyan
}

# -- 4. Install rag-facile CLI -------------------------------------------------

Write-Host "==> Installing rag-facile $LatestTag..." -ForegroundColor Yellow
uv tool install `
    "rag-facile-cli @ git+https://github.com/etalab-ia/rag-facile.git@${LatestTag}#subdirectory=apps/cli" `
    --force

$env:PATH = "$LocalBin;$env:PATH"

if (-not (Test-Command "rag-facile")) {
    Write-Error "ERROR: rag-facile installation failed"
    exit 1
}

Write-Host "OK rag-facile installe" -ForegroundColor Green

# -- 5. Done -------------------------------------------------------------------

Write-Host ""
Write-Host "Done: RAG Facile est pret!" -ForegroundColor Green
Write-Host ""
Write-Host "Prochaines etapes :" -ForegroundColor Cyan
Write-Host ""
Write-Host "  1. Creez votre projet RAG :"
Write-Host "       rag-facile setup mon-projet"
Write-Host ""
Write-Host "  2. Lancez votre application :"
Write-Host "       cd mon-projet; just run"
Write-Host ""
Write-Host "  3. Apprenez, explorez et configurez avec votre assistant IA :"
Write-Host "       cd mon-projet; just learn"
Write-Host ""

# Add LocalBin to permanent User PATH if not already there
$UserPath = [System.Environment]::GetEnvironmentVariable("PATH", "User")
if ($UserPath -notlike "*$LocalBin*") {
    [System.Environment]::SetEnvironmentVariable(
        "PATH",
        "$LocalBin;$UserPath",
        "User"
    )
    Write-Host "  WARNING: Open a new PowerShell window so PATH changes take effect."
    Write-Host ""
}
