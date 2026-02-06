# Issue #46: Proto Plugin Loading Behind Proxy

## Problem Summary

French government developers on restricted networks (VPN, corporate proxy) report that `proto install moon` fails with plugin loading errors. Standard HTTP proxy environment variables (`HTTP_PROXY`, `HTTPS_PROXY`) don't resolve the issue.

## Root Cause Analysis

### How Proto Plugin Installation Works

1. **Proto Installation**: `curl -fsSL https://moonrepo.dev/install/proto.sh | bash`
   - Downloads proto binary directly
   - Does NOT require plugin configuration

2. **Moon Plugin Installation**: `proto install moon`
   - **This is where failures occur**
   - Proto downloads the moon WASM plugin from: `https://github.com/moonrepo/plugins/releases/download/...`
   - Plugin is cached in `~/.proto/plugins/`
   - Network issues at this step block tool installation

### Why Standard Environment Variables May Not Work

1. **Plugin Download Location**: Moon plugin is hosted on GitHub (githubusercontent.com)
   - Corporate proxies may not intercept GitHub URLs
   - Or may require special proxy configuration for GitHub specifically

2. **SSL/TLS Inspection**: Corporate proxies often perform SSL inspection
   - Creates self-signed certificates for MITM
   - Standard root certificates don't validate these certs
   - Proto fails with SSL validation error

3. **DNS/Host Resolution**: Proxy may block certain hosts
   - Proto performs connectivity checks by pinging hosts
   - If these pings fail, proto may think it's offline
   - Causes version check to be skipped or behavior to change

4. **Curl vs Proto**: The install.sh uses `curl` for proto but then uses `proto` for plugins
   - `curl` is called with explicit flags: `-fsSL` (follow redirects, silent, show errors, TLS)
   - `proto` uses its own HTTP client (Rust-based reqwest) with different behavior
   - Environment variable handling differs between the two

## Proto Configuration Options

Proto provides multiple configuration mechanisms (in `.prototools`):

### 1. HTTP Proxy Configuration
```toml
[settings.http]
# List of proxy servers (tested in order)
proxies = ["https://proxy.corp.com:8080"]

# Mark insecure HTTP proxies as secure anyway
secure-proxies = ["http://internal-proxy:8080"]

# Allow invalid/self-signed certificates (DANGEROUS - last resort)
allow-invalid-certs = true

# Use custom root certificate for SSL verification
root-cert = "/path/to/corporate-cert.pem"
```

### 2. Offline Mode Configuration
```toml
[settings.offline]
# Custom hosts to ping for connectivity checks
custom-hosts = ["proxy.corp.com:80"]

# Disable default hosts if they're blocked
override-default-hosts = true

# Timeout for connectivity checks (ms)
timeout = 5000
```

### 3. URL Rewrite Rules
```toml
[settings.url-rewrites]
# Redirect GitHub to internal mirror
"github.com/(\\w+)/(\\w+)" = "github-mirror.corp.com/$1/$2"
```

### 4. Bypass Checks
```bash
# Skip version validation (requires tool to already be installed)
export PROTO_BYPASS_VERSION_CHECK=1
```

## Simulating the Issue

### Scenario 1: Network Connectivity Blocked

**Setup**: Block outbound access to GitHub
```bash
# Using macOS pfctl (requires sudo)
sudo pfctl -f /etc/pf.conf

# Or using Linux iptables (requires sudo)
sudo iptables -A OUTPUT -d github.com -j DROP
sudo iptables -A OUTPUT -d githubusercontent.com -j DROP
sudo iptables -A OUTPUT -d ghcr.io -j DROP
```

**Expected Error**:
```
Error: Failed to download plugin 'moon' from registry
caused by: connection timed out
```

### Scenario 2: SSL Certificate Validation Failure

**Setup**: Intercept HTTPS with self-signed certificate (like corporate proxy)
```bash
# Using mitmproxy or similar tool
mitmproxy --mode regular -p 8080

# Configure environment
export HTTP_PROXY=http://127.0.0.1:8080
export HTTPS_PROXY=http://127.0.0.1:8080
```

**Expected Error**:
```
Error: certificate verify failed
caused by: Self signed certificate
```

### Scenario 3: DNS Resolution Issues

**Setup**: Block DNS resolution
```bash
# Using /etc/hosts to simulate DNS failure
sudo bash -c 'echo "127.0.0.1  github.com" >> /etc/hosts'
```

**Expected Error**:
```
Error: Failed to resolve domain
caused by: Name resolution failed
```

## Recommended Solutions

### Solution 1: Update install.sh to Support Proxy Configuration (RECOMMENDED)

**Approach**: 
1. Detect if HTTP_PROXY/HTTPS_PROXY environment variables are set
2. Create a `.prototools` configuration file with proxy settings
3. Pass this config to proto commands

**Advantages**:
- Non-invasive - only creates config if proxy is detected
- Allows users to test with different proxy settings
- Supports all proto proxy configuration options
- No code changes needed for different proxy types

### Solution 2: Add Corporate Network Detection

**Approach**:
1. Check for environment variables indicating corporate network:
   - `CORP_PROXY`, `COMPANY_PROXY`
   - `http_proxy`, `https_proxy` (lowercase variants)
   - `NO_PROXY`, `no_proxy`

2. If detected, offer to create .prototools with sensible defaults

### Solution 3: DNS Override Configuration

**Approach**:
1. Create .prototools with offline mode configured
2. Override default connectivity checks with custom hosts
3. Helps if proxy blocks standard DNS endpoints

### Solution 4: SSL Certificate Support

**Approach**:
1. Detect if corporate proxy is likely (based on proxy URL)
2. Ask user to export their corporate root certificate
3. Configure proto to use custom root certificate

## Implementation in install.sh

The install script should:

1. **Check for proxy environment variables**:
   ```bash
   if [[ -n "$HTTP_PROXY" ]] || [[ -n "$HTTPS_PROXY" ]] || [[ -n "$http_proxy" ]] || [[ -n "$https_proxy" ]]; then
       # User has proxy configured
   fi
   ```

2. **Create .prototools configuration**:
   ```bash
   cat > ~/.proto/.prototools << 'EOF'
   [settings.http]
   # Proxy configuration for corporate/restricted networks
   proxies = ["${HTTPS_PROXY}"]
   
   [settings.offline]
   timeout = 5000
   EOF
   ```

3. **Add helper function for SSL certificates**:
   - Check if `.pem` file exists in common locations
   - Offer user ability to specify custom certificate path
   - Configure `root-cert` in .prototools if provided

4. **Document workarounds**:
   - Link to proto configuration documentation
   - Provide examples for common proxy scenarios
   - Explain each configuration option

## Testing Recommendations

1. **Local proxy simulation**:
   ```bash
   # Start mitmproxy on localhost
   mitmproxy --mode regular -p 8080
   
   # Run install script with proxy
   HTTP_PROXY=http://127.0.0.1:8080 \
   HTTPS_PROXY=http://127.0.0.1:8080 \
   bash install.sh
   ```

2. **VPN testing** (if available):
   - Test with actual corporate VPN
   - Verify connectivity to GitHub and ghcr.io

3. **Different proxy types**:
   - HTTP proxy (cleartext)
   - HTTPS proxy (encrypted)
   - SOCKS proxy (if supported)

## Additional Resources

- [Proto Configuration Documentation](https://moonrepo.dev/docs/proto/config)
- [Proto FAQ - Troubleshooting](https://moonrepo.dev/docs/proto/faq)
- [Proto GitHub Issues](https://github.com/moonrepo/proto/issues)
- [mitmproxy Documentation](https://mitmproxy.org/) - For testing proxy scenarios
