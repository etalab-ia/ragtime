# CI/CD Windows Testing Guide

This guide explains how to test RAG Facile installation on Windows in CI/CD pipelines using GitHub Actions.

**See also:** [Linux Testing Guide](ci-cd-linux.md) | [macOS Testing Guide](ci-cd-macos.md) | [Complete Workflow Example](../../.github/workflows/test-install.yml)

## Why Test on Windows?

- **Cross-platform consistency**: Ensure the installer works on all three major platforms
- **Path handling**: Windows uses backslashes and different environment variable syntax
- **Proto compatibility**: Verify proto's binary downloads work on Windows (MSVC builds)
- **PowerShell quirks**: Shell differences between PowerShell and bash can cause subtle bugs

## GitHub Actions Setup

### PowerShell Installer Testing

Add this job to your `.github/workflows/ci.yml`:

```yaml
windows-powershell-install:
  runs-on: windows-latest
  name: "Test install.ps1 (Windows PowerShell)"
  
  steps:
    - uses: actions/checkout@v4
    
    - name: Run PowerShell installer
      shell: powershell
      run: |
        # Execute installer script
        powershell -ExecutionPolicy Bypass -Command "& { irm ${{ github.server_url }}/${{ github.repository }}/raw/${{ github.ref_name }}/install.ps1 | iex }"
    
    - name: Verify installation
      shell: powershell
      run: |
        rag-facile --version
        proto --version
        moon --version
        uv --version
        just --version
```

### Git Bash Installer Testing

Add this job for Git Bash (MSYS2) testing:

```yaml
windows-git-bash-install:
  runs-on: windows-latest
  name: "Test install.sh (Windows Git Bash)"
  
  steps:
    - uses: actions/checkout@v4
    
    - name: Run bash installer
      shell: bash
      run: |
        bash <(curl -fsSL ${{ github.server_url }}/${{ github.repository }}/raw/${{ github.ref_name }}/install.sh)
    
    - name: Verify installation
      shell: bash
      run: |
        rag-facile --version
        proto --version
        moon --version
        uv --version
        just --version
```

### Proxy Testing (Simulated)

To test proxy compatibility without a real proxy, you can simulate proxy environment variables:

```yaml
windows-proxy-simulation:
  runs-on: windows-latest
  name: "Test proxy configuration (simulated)"
  
  env:
    HTTP_PROXY: "http://proxy.example.com:8080"
    HTTPS_PROXY: "http://proxy.example.com:8080"
  
  steps:
    - uses: actions/checkout@v4
    
    - name: Run installer with proxy env vars
      shell: powershell
      run: |
        # The installer should detect these and configure .prototools
        powershell -ExecutionPolicy Bypass -Command "& { irm ${{ github.server_url }}/${{ github.repository }}/raw/${{ github.ref_name }}/install.ps1 | iex }"
    
    - name: Verify .prototools was created with proxy config
      shell: powershell
      run: |
        $PrototoolsPath = "$env:USERPROFILE\.proto\.prototools"
        if (Test-Path $PrototoolsPath) {
          Write-Host "✓ .prototools created successfully"
          Get-Content $PrototoolsPath
        } else {
          Write-Host "✗ .prototools not found"
          exit 1
        }
```

## Testing Proto Plugin Registration

Ensure the `just` plugin is correctly registered:

```yaml
proto-plugin-registration:
  runs-on: windows-latest
  
  steps:
    - uses: actions/checkout@v4
    
    - name: Install proto
      shell: powershell
      run: |
        irm https://moonrepo.dev/install/proto.ps1 | iex
    
    - name: Verify proto can find just plugin
      shell: powershell
      run: |
        proto plugin add just "https://raw.githubusercontent.com/Phault/proto-toml-plugins/main/just/plugin.toml"
        proto install just
        just --version
```

## Justfile Cross-Platform Testing

Test that `just` commands work on both PowerShell and bash:

```yaml
justfile-testing:
  strategy:
    matrix:
      shell: [powershell, bash]
  
  runs-on: windows-latest
  name: "Test just recipes (${{ matrix.shell }})"
  
  steps:
    - uses: actions/checkout@v4
    
    - name: Install tools
      shell: ${{ matrix.shell }}
      run: |
        if [ "${{ matrix.shell }}" = "bash" ]; then
          bash <(curl -fsSL ${{ github.server_url }}/${{ github.repository }}/raw/${{ github.ref_name }}/install.sh)
        else
          powershell -ExecutionPolicy Bypass -Command "& { irm ${{ github.server_url }}/${{ github.repository }}/raw/${{ github.ref_name }}/install.ps1 | iex }"
        fi
    
    - name: Test just commands
      shell: ${{ matrix.shell }}
      run: |
        just --list
        just format-check
        just lint
```

## Local Windows Testing

If you need to test locally on Windows before pushing:

### Using GitHub CLI

```bash
# Download and run latest installer from your branch
gh run view <run-id> -w
```

### Manual Testing on Windows VM

1. **Spin up a Windows VM** (Azure, AWS, or local VirtualBox)
2. **Test PowerShell path:**
   ```powershell
   irm https://raw.githubusercontent.com/etalab-ia/rag-facile/YOUR-BRANCH/install.ps1 | iex
   ```
3. **Test Git Bash path:**
   ```bash
   bash <(curl -fsSL https://raw.githubusercontent.com/etalab-ia/rag-facile/YOUR-BRANCH/install.sh)
   ```

## Troubleshooting CI/CD Failures

### PowerShell Execution Policy

If the installer fails with "execution of scripts is disabled", the system policy may be too strict:

```powershell
# In CI, GitHub Actions should allow this, but if not:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process -Force
```

### Network Timeouts

Windows runners can sometimes have slower network access to GitHub. Increase curl timeout:

```powershell
# In your GitHub Actions step
$ProgressPreference = 'SilentlyContinue'
irm https://moonrepo.dev/install/proto.ps1 | iex
```

### Path Not Updated Between Steps

After installing proto, tools may not be immediately available. Force path refresh:

```powershell
# Refresh environment in PowerShell
$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH","User")
```

### Git Bash PATH Issues

On Windows, `/c/Users/...` paths can cause issues. Use `cygpath` for conversion:

```bash
# Convert Windows path to Unix path
UNIX_PATH=$(cygpath -u "C:\Users\runner\work")
echo $UNIX_PATH
```

## Best Practices

✅ **Test both shells** — PowerShell and Git Bash behave differently  
✅ **Test proxy scenarios** — Use environment variables to simulate corporate networks  
✅ **Run on real Windows runners** — GitHub Actions `windows-latest` is more reliable than Docker  
✅ **Pin tool versions** — Use `.prototools` to ensure consistency  
✅ **Document failures** — Add verbose logging to help debug Windows-specific issues  

## References

- [GitHub Actions: Windows Runners](https://docs.github.com/en/actions/using-github-hosted-runners/about-github-hosted-runners)
- [GitHub Actions: Shell Behavior](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#jobsjob_idstepsshell)
- [Proto: Installation](https://moonrepo.dev/docs/proto/install)
- [Uv: Windows Installation](https://docs.astral.sh/uv/getting-started/installation/)
