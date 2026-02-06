# Troubleshooting Proxy & Network Issues

When installing RAG Facile on corporate networks, restricted networks, or behind VPNs, you may encounter network-related errors. This guide helps you diagnose and fix them.

## Before You Start

1. **Have you set proxy environment variables?**
   ```bash
   echo $HTTP_PROXY
   echo $HTTPS_PROXY
   ```
   If empty, see [Proxy Setup Guide](../guides/proxy-setup.md#quick-start)

2. **What error message did you get?** Find it below to get specific solutions.

---

## Symptom: Connection Timeout

### Error Message

```
Error: Failed to download plugin
caused by: connection timed out
```

### Root Causes

- Proxy server not configured
- Proxy blocks GitHub/GHCR URLs
- Firewall rules block outbound connections
- Network temporarily unavailable

### Step-by-Step Solutions

#### Solution 1: Verify Proxy Settings

Check if proxy environment variables are set:

```bash
echo "HTTP_PROXY: $HTTP_PROXY"
echo "HTTPS_PROXY: $HTTPS_PROXY"
echo "http_proxy: $http_proxy"
echo "https_proxy: $https_proxy"
```

If all are empty, set them and try again:

```bash
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080
bash <(curl -fsSL https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.sh)
```

#### Solution 2: Test Connectivity Through Proxy

Test if you can reach GitHub through your proxy:

```bash
# Test basic connectivity
curl -x $HTTPS_PROXY -I https://github.com
curl -x $HTTPS_PROXY -I https://ghcr.io

# You should see "HTTP/1.1 200 OK" or similar
# If you get timeout or "Connection refused", proxy is not working
```

**If connectivity test fails**:
- Verify proxy URL is correct
- Check if proxy requires authentication (see below)
- Contact IT team to verify proxy is working

#### Solution 3: Handle Proxy Authentication

If your proxy requires username/password:

```bash
# Format: http://username:password@proxy.company.com:8080
export HTTP_PROXY=http://user:password@proxy.company.com:8080
export HTTPS_PROXY=http://user:password@proxy.company.com:8080
bash <(curl -fsSL https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.sh)
```

#### Solution 4: Whitelist Domains with IT Team

If your organization uses a firewall allowlist, these domains need to be whitelisted:

```
github.com
ghcr.io
raw.githubusercontent.com
moonrepo.dev
just.systems
curl.se (for script downloads)
```

Contact your IT team and provide this list.

#### Solution 5: Manually Configure Proto

If auto-detection didn't work, manually create the configuration:

```bash
mkdir -p ~/.proto
cat > ~/.proto/.prototools << 'EOF'
[settings.http]
proxies = ["https://proxy.company.com:8080"]

[settings.offline]
timeout = 5000
EOF
```

Then try the installer again:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.sh)
```

---

## Symptom: SSL Certificate Error

### Error Message

```
Error: certificate verify failed
caused by: Self signed certificate
```

Or variations like:
- `x509: certificate signed by unknown authority`
- `CERTIFICATE_VERIFY_FAILED`
- `SSL_CERTIFICATE_VERIFY_FAILED`

### Root Cause

Corporate proxy performing **SSL inspection (MITM)**:
1. Proxy intercepts your HTTPS connection
2. Creates a self-signed certificate for the connection
3. Proto tries to verify the certificate
4. Verification fails because cert isn't signed by a trusted CA

This is common in enterprise environments for security/compliance reasons.

### Step-by-Step Solutions

#### Solution 1: Export Corporate Root Certificate

Your organization's proxy should have a root certificate that signed the self-signed certs.

**macOS** (Keychain):
```bash
# 1. Open Keychain Access
open -a "Keychain Access"

# 2. Find your corporate proxy/CA certificate (usually in System Keychain)
# 3. Right-click on it
# 4. Select "Export..."
# 5. Save as "corporate-ca.pem" to your home directory
# 6. When prompted for password, leave empty (no password)

# Verify the export worked:
ls -la ~/corporate-ca.pem
```

**Linux (Ubuntu/Debian)**:
```bash
# If your company's cert is already installed:
sudo cp /etc/ssl/certs/company-ca.crt ~/corporate-ca.pem

# Or get from your IT department and copy:
cp /path/to/company-ca.pem ~/corporate-ca.pem

# Verify:
ls -la ~/corporate-ca.pem
```

**Windows (WSL)**:
```bash
# Export from Windows certificate store:
powershell -Command "Get-ChildItem -Path Cert:\LocalMachine\Root | Where-Object {$_.Issuer -like '*company*'} | Export-Certificate -FilePath 'C:\Users\YourUsername\corporate-ca.crt'"

# Copy to WSL home:
cp /mnt/c/Users/YourUsername/corporate-ca.crt ~/corporate-ca.pem
```

**If you don't have the certificate**:
- Ask your IT department to provide the corporate root CA certificate
- Or have them provide the proxy URL and SSL inspection settings

#### Solution 2: Configure Proto to Use the Certificate

Once you have the certificate as a `.pem` file:

```bash
cat > ~/.proto/.prototools << 'EOF'
[settings.http]
proxies = ["https://proxy.company.com:8080"]
root-cert = "/home/username/corporate-ca.pem"

[settings.offline]
timeout = 5000
EOF
```

Replace:
- `https://proxy.company.com:8080` with your actual proxy URL
- `/home/username/corporate-ca.pem` with the actual path to your certificate

#### Solution 3: Test the Configuration

Verify the certificate works:

```bash
proto install moon --log trace
```

If it works, continue with the installer:
```bash
bash <(curl -fsSL https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.sh)
```

#### Solution 4: Emergency Fallback (Not Recommended)

If you can't get the certificate working, this is a last resort:

```bash
cat > ~/.proto/.prototools << 'EOF'
[settings.http]
proxies = ["https://proxy.company.com:8080"]
allow-invalid-certs = true

[settings.offline]
timeout = 5000
EOF
```

⚠️ **WARNING**: This disables SSL certificate verification. Only use this temporarily while troubleshooting. This makes you vulnerable to man-in-the-middle attacks.

---

## Symptom: Offline Mode Detection Fails

### Error Message

```
proto: offline mode detected
Error: Cannot install tools while offline
```

### Root Causes

- Proto checks internet connectivity by pinging hosts
- Corporate proxy blocks these ping hosts
- Network connectivity check times out
- Proto incorrectly thinks you're offline when you actually have internet

### Step-by-Step Solutions

#### Solution 1: Increase Timeout for Network Checks

Proto pings several hosts to check connectivity. Increase the timeout:

```bash
cat > ~/.proto/.prototools << 'EOF'
[settings.http]
proxies = ["https://proxy.company.com:8080"]

[settings.offline]
timeout = 10000
EOF
```

This increases timeout from 750ms to 10 seconds (10000ms).

#### Solution 2: Override Default Connectivity Hosts

Proto pings: Google DNS, Cloudflare DNS, Google, Mozilla. If proxy blocks these:

```bash
cat > ~/.proto/.prototools << 'EOF'
[settings.http]
proxies = ["https://proxy.company.com:8080"]

[settings.offline]
override-default-hosts = true
custom-hosts = ["8.8.8.8:53", "proxy.company.com:80"]
timeout = 10000
EOF
```

Replace `proxy.company.com:80` with your proxy's hostname and port.

#### Solution 3: Bypass Version Checks

If the tool is already installed, you can skip network checks:

```bash
export PROTO_BYPASS_VERSION_CHECK=1
proto install moon
```

---

## Symptom: Authentication Required

### Error Message

```
Error: 407 Proxy Authentication Required
```

### Root Cause

Your proxy requires username and password authentication.

### Solution

Include credentials in the proxy URL:

```bash
export HTTP_PROXY=http://username:password@proxy.company.com:8080
export HTTPS_PROXY=http://username:password@proxy.company.com:8080
bash <(curl -fsSL https://raw.githubusercontent.com/etalab-ia/rag-facile/main/install.sh)
```

**Or in configuration file**:

```bash
cat > ~/.proto/.prototools << 'EOF'
[settings.http]
proxies = ["https://username:password@proxy.company.com:8080"]

[settings.offline]
timeout = 5000
EOF
```

⚠️ **Security Note**: Storing passwords in plain text is not recommended. Prefer using environment variables or asking IT to configure authentication differently.

---

## Symptom: Can't Resolve Domain

### Error Message

```
Error: Failed to resolve domain
caused by: Name resolution failed
```

Or:
- `DNS lookup failed`
- `Temporary failure in name resolution`
- `nodename nor servname provided`

### Root Cause

Corporate proxy blocks DNS resolution, or DNS settings need updating.

### Solutions

#### Solution 1: Check DNS Resolution

Test if you can resolve domains:

```bash
nslookup github.com
nslookup ghcr.io

# Should return IP addresses
# If it hangs or returns error, DNS is blocked
```

#### Solution 2: Use Custom DNS

Configure proto to use a custom DNS host:

```bash
cat > ~/.proto/.prototools << 'EOF'
[settings.offline]
custom-hosts = ["8.8.8.8:53", "1.1.1.1:53"]
timeout = 5000
EOF
```

#### Solution 3: Contact IT Team

If DNS resolution is blocked at the network level, IT team needs to:
1. Whitelist DNS resolution for the required domains
2. Or configure DNS forwarding through the proxy

---

## Symptom: Multiple Errors / Nothing Works

If you've tried the above and still have issues:

### Diagnostic Steps

1. **Collect information**:
   ```bash
   # Show network configuration
   echo "HTTP_PROXY: $HTTP_PROXY"
   echo "HTTPS_PROXY: $HTTPS_PROXY"
   
   # Show proto configuration
   cat ~/.proto/.prototools 2>/dev/null || echo "No config file"
   
   # Test connectivity
   curl -I https://github.com 2>&1
   curl -I https://ghcr.io 2>&1
   
   # Show proto logs
   tail -20 ~/.proto/logs/*.log 2>/dev/null || echo "No logs"
   ```

2. **Run installer with debug output**:
   ```bash
   proto install moon --log trace 2>&1 | head -50
   ```

3. **Check proto documentation**:
   - [Proto Configuration Docs](https://moonrepo.dev/docs/proto/config)
   - [Proto FAQ](https://moonrepo.dev/docs/proto/faq)

### Report an Issue

If you can't find the solution:

1. **RAG Facile Issues**: [github.com/etalab-ia/rag-facile/issues](https://github.com/etalab-ia/rag-facile/issues)
   - Include: error message, proxy setup, OS, network info

2. **Proto Issues**: [github.com/moonrepo/proto/issues](https://github.com/moonrepo/proto/issues)
   - Include: full error, proto version (`proto --version`), OS

3. **Contact Your IT Team**:
   - Ask for proxy documentation
   - Request root CA certificate path
   - Confirm required domains are whitelisted
   - Verify SSL inspection settings

---

## Quick Reference: Common Issues & Fixes

| Issue | Quick Fix |
|-------|-----------|
| Connection timeout | Set `HTTP_PROXY`/`HTTPS_PROXY` env vars |
| SSL certificate error | Export corporate root cert, add to `.prototools` |
| Offline mode detected | Increase timeout: `timeout = 10000` |
| Authentication required | Add credentials to proxy URL |
| DNS resolution failed | Add custom DNS: `custom-hosts = ["8.8.8.8:53"]` |

---

## Getting Help

**Fast path to solution**:
1. Identify your error message above
2. Follow the step-by-step solutions
3. If still stuck, contact IT team with collected diagnostics
4. Report issue on GitHub if it's a bug

See the [Proxy Setup Guide](../guides/proxy-setup.md) for more information and advanced configurations.
