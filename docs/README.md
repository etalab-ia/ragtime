# RAG Facile Documentation

Welcome to the RAG Facile documentation. This directory contains guides, troubleshooting resources, and technical documentation for the RAG Facile starter kit.

## Quick Navigation

### For End Users

**Getting Started**
- [Installation](../README.md#quick-start) - Basic installation instructions
- [Proxy & Network Setup Guide](guides/proxy-setup.md) - Complete setup guide for corporate networks and VPNs

**Troubleshooting**
- [Proxy Issues](troubleshooting/proxy.md) - Solve proxy and network-related problems
- [Installation Help](../README.md#quick-start) - General installation troubleshooting

### For Developers & IT Teams

**Technical Deep-Dives**
- [Issue #46 Investigation](technical/issue-46-investigation.md) - Technical analysis and research findings
- [Issue #46 Summary](technical/issue-46-summary.md) - Complete implementation summary

## Documentation by Topic

### Installation & Setup

If you're installing RAG Facile:
1. Start with the [main README](../README.md#quick-start)
2. If behind a proxy → [Proxy Setup Guide](guides/proxy-setup.md)
3. Experiencing issues? → [Troubleshooting: Proxy](troubleshooting/proxy.md)

### Proxy & Corporate Networks

RAG Facile supports installation on corporate networks, restricted networks, and behind VPNs.

**Quick reference:**
- **Standard HTTP proxy**: See [Quick Start section](guides/proxy-setup.md#quick-start) of Proxy Setup Guide
- **Corporate proxy with SSL inspection**: See [SSL Certificate Configuration](guides/proxy-setup.md#troubleshooting-ssl-certificate-error)
- **Network blocked**: See [Troubleshooting: Connection Timeout](troubleshooting/proxy.md#symptom-connection-timeout)
- **Advanced configuration**: See [Advanced Configuration](guides/proxy-setup.md#advanced-url-rewriting-for-internal-mirrors)

### For IT Teams & System Administrators

See [Proxy Setup Guide: For IT Teams](guides/proxy-setup.md#for-it-teams--system-administrators) for guidance on:
- Whitelisting requirements
- Proxy configuration recommendations
- Root CA certificate distribution
- Setup for your organization

## How This Documentation is Organized

### `/guides/` - Actionable User Guides

Step-by-step guides for common tasks and setup scenarios.

- **proxy-setup.md**: Complete guide to installing RAG Facile on networks with proxies, VPNs, or corporate firewalls

### `/troubleshooting/` - Problem Solving

When something goes wrong, start here.

- **proxy.md**: Diagnose and fix proxy-related installation issues
  - Organized by symptom (Connection Timeout, SSL Certificate Error, etc.)
  - Includes tests and solutions for each issue

### `/technical/` - Technical Documentation

Research, investigation, and implementation details (primarily of historical interest).

- **issue-46-investigation.md**: Technical analysis, research findings, and proto configuration reference
- **issue-46-summary.md**: Complete implementation summary with testing instructions

---

## Common Issues & Quick Fixes

### Installation fails at "Installing moon via proto..."

→ You're likely behind a proxy. See [Proxy Setup Guide](guides/proxy-setup.md#quick-start)

### SSL certificate verification failed

→ Corporate proxy performing SSL inspection. See [Troubleshooting: SSL Certificate Error](troubleshooting/proxy.md#symptom-ssl-certificate-error)

### Connection timeout during installation

→ Proxy or firewall blocking network access. See [Troubleshooting: Connection Timeout](troubleshooting/proxy.md#symptom-connection-timeout)

### Not sure what the problem is?

→ Start with [Troubleshooting: Proxy Issues](troubleshooting/proxy.md) - all major symptoms are covered

---

## Additional Resources

- **Main Repository**: [github.com/etalab-ia/rag-facile](https://github.com/etalab-ia/rag-facile)
- **Issue Tracker**: [GitHub Issues](https://github.com/etalab-ia/rag-facile/issues)
- **Contributing**: See [CONTRIBUTING.md](../CONTRIBUTING.md) in repository root

## Document Versions

All documentation is updated as part of the main project. For specific versions:
- Check the [GitHub releases page](https://github.com/etalab-ia/rag-facile/releases)
- Issue #46 fixes included starting from version 0.7.0+

---

**Need help?** 
- Check the relevant troubleshooting guide first
- Review the Quick Navigation section above
- Open an issue on [GitHub](https://github.com/etalab-ia/rag-facile/issues) if you can't find an answer
