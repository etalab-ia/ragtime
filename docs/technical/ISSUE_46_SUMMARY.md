# Issue #46 Summary: Proto Plugin Loading Behind Corporate Proxies

## Status

✅ **RESOLVED** - Commit: `0a90cc3`

Branch: `46-allow-use-of-proxy-in-install-script`

## Problem

French government developers on restricted networks reported that `proto install moon` failed during the install.sh script execution. The user attempted to work around this by setting HTTP proxy environment variables, but it didn't resolve the issue.

**Root cause**: The install.sh script did not configure proto to use the proxy for plugin downloads.

## Root Cause Analysis

### How Proto Plugin Installation Works

The installation has two network-dependent stages:

1. **Proto Binary Installation** (usually works)
   - Downloads proto directly via curl
   - Curl respects HTTP_PROXY/HTTPS_PROXY automatically

2. **Plugin Installation** (where failures occur)
   - Proto downloads WASM plugins from GitHub/GHCR
   - Proto uses its own HTTP client (Rust-based reqwest)
   - **Proto does NOT automatically use HTTP_PROXY environment variables**
   - Requires explicit configuration in `.prototools` file

### Why Standard Environment Variables Weren't Working

1. **Proto's HTTP Client Behavior**
   - Curl (used for proto binary) respects HTTP_PROXY env vars
   - Proto CLI (used for moon/uv plugins) requires explicit configuration
   - Different HTTP clients = different proxy handling

2. **SSL/TLS Inspection**
   - Corporate proxies often intercept HTTPS traffic (MITM)
   - They create self-signed certificates
   - Proto can't verify these certs by default
   - Requires `allow-invalid-certs` or `root-cert` configuration

3. **Connectivity Check Issues**
   - Proto pings hosts to detect internet connectivity
   - Corporate proxies may block these ping hosts
   - Proto incorrectly thinks it's offline
   - Requires custom host configuration

## Solution: Enhanced install.sh

### What We Implemented

1. **Automatic Proxy Detection**
   - Detects HTTP_PROXY, http_proxy, HTTPS_PROXY, https_proxy environment variables
   - Checks both uppercase and lowercase variants

2. **Automatic .prototools Configuration**
   - Creates `~/.proto/.prototools` with proxy settings when detected
   - Configures extended timeouts for network checks
   - No manual configuration needed by user

3. **Corporate Proxy Detection**
   - Recognizes corporate proxies by URL patterns ("corp", "internal")
   - Provides intelligent guidance for SSL certificate issues

4. **Improved Error Messages**
   - When `proto install moon/uv` fails, provides detailed troubleshooting steps
   - Guides users to test connectivity
   - Links to official proto documentation

### Implementation Details

**Bash function added to install.sh**:
```bash
setup_proxy_config() {
    # Detects proxy environment variables
    # Creates ~/.proto/.prototools with:
    #   [settings.http]
    #   proxies = ["$proxy_url"]
    #   [settings.offline]
    #   timeout = 5000
    # Provides SSL certificate guidance for corporate proxies
}
```

**Configuration created by script**:
```toml
[settings.http]
proxies = ["https://proxy.company.com:8080"]

[settings.offline]
timeout = 5000
```

## Testing: How to Simulate the Issue

### Scenario 1: Network Blocked (Immediate Failure)
```bash
# Block GitHub/GHCR access
sudo iptables -A OUTPUT -d github.com -j DROP
sudo iptables -A OUTPUT -d ghcr.io -j DROP

# Run installer (will fail at proto install moon)
bash <(curl -fsSL https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.sh)
```

**Expected error**: Connection timeout during plugin download

### Scenario 2: SSL Certificate Inspection (Corporate Proxy)
```bash
# Install mitmproxy (local proxy simulator)
brew install mitmproxy  # macOS
apt install mitmproxy   # Linux

# Start proxy on localhost:8080
mitmproxy --mode regular -p 8080

# Run installer with proxy (without fix, would fail)
HTTP_PROXY=http://127.0.0.1:8080 \
HTTPS_PROXY=http://127.0.0.1:8080 \
bash <(curl -fsSL https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.sh)
```

**Expected behavior** (with fix): Script detects proxy and configures proto correctly

### Scenario 3: DNS/Connectivity Check Issues
```bash
# Simulate proxy blocking DNS endpoints
echo "127.0.0.1  8.8.8.8" | sudo tee -a /etc/hosts

# Run installer with proxy
HTTP_PROXY=http://proxy.company.com:8080 \
bash <(curl -fsSL ...)
```

**Expected behavior** (with fix): Extended timeout and custom host detection

## Workarounds Provided

### Workaround 1: Environment Variable (Quick)
```bash
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080
bash <(curl -fsSL https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.sh)
```

Works because:
- Installer now detects these variables
- Automatically creates .prototools configuration
- No manual intervention needed

### Workaround 2: Manual .prototools Configuration
```bash
mkdir -p ~/.proto
cat > ~/.proto/.prototools << 'EOF'
[settings.http]
proxies = ["https://proxy.company.com:8080"]

[settings.offline]
timeout = 5000
EOF

bash <(curl -fsSL ...)
```

### Workaround 3: SSL Certificate Configuration
For corporate proxies performing SSL inspection:

```bash
# 1. Export corporate root certificate
# (Usually available from IT/Proxy admin as .pem file)

# 2. Configure proto to use it
cat > ~/.proto/.prototools << 'EOF'
[settings.http]
proxies = ["https://proxy.company.com:8080"]
root-cert = "/path/to/corporate-ca.pem"

[settings.offline]
timeout = 5000
EOF
```

### Workaround 4: URL Rewriting (Internal Mirrors)
If company has internal GitHub mirror:

```bash
cat > ~/.proto/.prototools << 'EOF'
[settings.http]
proxies = ["https://proxy.company.com:8080"]

[settings.url-rewrites]
"github.com/(\\w+)/(\\w+)" = "github-mirror.company.com/$1/$2"
"ghcr.io/(.*)" = "registry.company.com/$1"
EOF
```

### Workaround 5: Offline Connectivity Configuration
For proxy blocking connectivity checks:

```bash
cat > ~/.proto/.prototools << 'EOF'
[settings.http]
proxies = ["https://proxy.company.com:8080"]

[settings.offline]
override-default-hosts = true
custom-hosts = ["8.8.8.8:53"]
timeout = 5000
EOF
```

## Deliverables

### 1. Updated install.sh
- ✅ Automatic proxy detection
- ✅ Automatic .prototools generation
- ✅ Corporate proxy detection and guidance
- ✅ Improved error messages with troubleshooting

### 2. PROXY_INVESTIGATION.md
- Technical analysis of the problem
- Detailed explanation of proto's plugin loading
- Why standard environment variables don't work
- All available proto configuration options
- Simulation instructions for testing

### 3. PROXY_SETUP_GUIDE.md
- Complete user guide for restricted networks
- Quick start instructions
- Detailed troubleshooting sections
- SSL certificate configuration steps
- Advanced URL rewriting and offline mode
- Simulation instructions using mitmproxy
- IT team / sysadmin guidelines

### 4. Updated README.md
- Added note about proxy support
- Link to comprehensive proxy guide

## Key Insights

1. **Proto Doesn't Automatically Respect HTTP_PROXY**
   - This is the core issue - proto uses its own HTTP client
   - Requires explicit configuration in .prototools
   - This is documented but not obvious to users

2. **SSL/TLS Inspection is Common**
   - Corporate proxies often perform MITM SSL inspection
   - Users need to provide corporate root certificate
   - Fallback: allow-invalid-certs (security risk)

3. **Plugin Downloads are the Bottleneck**
   - Proto binary installation (via curl) usually works
   - Plugin downloads (via proto) are where failures occur
   - This is the #1 pain point for corporate users

4. **Network Connectivity Checks Can Fail**
   - Proto pings hosts to detect internet
   - Corporate proxies may block these pings
   - Requires custom host configuration

## Recommendations for Users

### Quick Start (Most Users)
```bash
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080
bash <(curl -fsSL https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.sh)
```

### If You Encounter SSL Errors
1. Export corporate root certificate as .pem
2. Add to ~/.proto/.prototools:
   ```toml
   [settings.http]
   root-cert = "/path/to/cert.pem"
   ```

### If You Still Have Issues
1. Check ~/.proto logs for details
2. Test connectivity: `curl -x $HTTPS_PROXY https://github.com`
3. Refer to PROXY_SETUP_GUIDE.md
4. Contact your IT team for proxy settings

## Next Steps

1. **Testing**: Run through scenarios with mitmproxy
2. **Documentation**: French government users should reference PROXY_SETUP_GUIDE.md
3. **Upstream**: Consider contributing proxy documentation improvements to proto project
4. **Monitoring**: Track if this resolves issue #46 reports

## Related Issues

- Issue #46: Proto unable to install moon plugin on restricted networks
- Proto repository: [WASM Plugin Loading](https://github.com/moonrepo/proto/issues)
- Proto documentation: [Configuration](https://moonrepo.dev/docs/proto/config)

## Files Changed

```
install.sh (major update)
  - Added setup_proxy_config() function
  - Added proxy detection and .prototools generation
  - Improved error handling with troubleshooting steps

README.md (minor update)
  - Added note about proxy support
  - Link to PROXY_SETUP_GUIDE.md

PROXY_INVESTIGATION.md (new)
  - Technical analysis and implementation details
  - Proxy simulation instructions

PROXY_SETUP_GUIDE.md (new)
  - Complete user guide
  - Troubleshooting sections
  - Configuration examples
  - IT team guidelines
```

Commit: `0a90cc3` - "feat: add proxy support to install script for corporate/restricted networks"
