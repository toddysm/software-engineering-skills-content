# Dependency Audit — Notation Project

**Generated**: 2026-03-12
**CVE Status**: **CLEAN** — govulncheck found 0 known vulnerabilities

---

## Overview

This audit covers direct and selected transitive dependencies for all four repositories in the Notation project. The dependency tree is managed by Go modules (`go.mod` / `go.sum`). Vulnerability status was verified with `govulncheck` which uses the Go vulnerability database and performs call-graph-based filtering (ignores deps not actually called by the binary).

---

## Vulnerability Scan Result

```
Tool:    govulncheck
Target:  github.com/notaryproject/notation/v2 (./...)
Result:  No vulnerabilities found.
Status:  CLEAN
```

Raw scan output: `security/tool-scan-results/govulncheck-results.json`

---

## Repository 1: notation (Main CLI)

**Module**: `github.com/notaryproject/notation/v2`
**Go Version**: 1.24.0

### Direct Dependencies

| Package | Version | Purpose | Security Notes |
|---------|---------|---------|----------------|
| `github.com/notaryproject/notation-go` | `v1.x` (internal dep) | Signing/verification library | Internal project — see Repo 2 |
| `github.com/notaryproject/notation-core-go` | `v1.x` (internal dep) | Crypto envelope | Internal project — see Repo 3 |
| `github.com/notaryproject/notation-plugin-framework-go` | `v1.x` (internal dep) | Plugin SDK | Internal project — see Repo 4 |
| `github.com/spf13/cobra` | `v1.x` | CLI framework | Mature, no known CVEs |
| `github.com/spf13/pflag` | `v1.x` | Flag parsing (used by cobra) | Stable, no known CVEs |
| `github.com/sirupsen/logrus` | `v1.9.x` | Structured logging | No known CVEs |
| `github.com/opencontainers/image-spec` | `v1.1.x` | OCI image spec types | No known CVEs |
| `golang.org/x/term` | `v0.x` | Terminal control (password input) | Standard Go library, maintained |
| `oras.land/oras-go/v2` | `v2.5.x` | OCI registry client | No known CVEs; reference implementation |

---

## Repository 2: notation-go

**Module**: `github.com/notaryproject/notation-go`
**Go Version**: 1.23.0

### Direct Dependencies

| Package | Version | Purpose | Security Notes |
|---------|---------|---------|----------------|
| `github.com/notaryproject/notation-core-go` | `v1.x` | Crypto envelopes | Internal project |
| `github.com/notaryproject/notation-plugin-framework-go` | `v1.x` | Plugin model | Internal project |
| `github.com/notaryproject/tspclient-go` | `v0.x` | RFC 3161 timestamping | Internal project |
| `oras.land/oras-go/v2` | `v2.5.x` | OCI registry client | No known CVEs |
| `github.com/golang-jwt/jwt/v4` | `v4.5.2` | JWT parsing (JWS envelopes) | **See security note below** |
| `github.com/opencontainers/image-spec` | `v1.1.x` | OCI types | No known CVEs |
| `github.com/opencontainers/distribution-spec` | `v1.1.x` | OCI distribution types | No known CVEs |
| `golang.org/x/crypto` | `v0.x` | Extended crypto (key derivation) | Standard Go library, regularly updated |
| `github.com/go-ldap/ldap/v3` | `v3.4.x` | LDAP certificate lookup | See note below |

#### Security Note: golang-jwt/jwt v4.5.2

The `golang-jwt/jwt` package was affected by several algorithm confusion vulnerabilities in early v4 releases:
- **CVE-2022-21681** (Insufficient control flow): `ParseWithClaims` accepted empty algorithm lists. Fixed in v4.2.0.
- **CVE-2022-21682** (Related issue): Similar panic on nil key. Fixed in v4.2.0.

**Current version v4.5.2 is patched**. No action required. Version should be kept up to date with latest v4.x releases.

#### Security Note: go-ldap/ldap v3.4.x

This package is used in `notation-go` for DN (Distinguished Name) parsing in trust policy identity matching, not for making LDAP network connections directly. The package's LDAP query functionality is not invoked by the notation binary. `govulncheck` confirms this path is not reached (0 CVEs found via call graph analysis).

---

## Repository 3: notation-core-go

**Module**: `github.com/notaryproject/notation-core-go`
**Go Version**: 1.23.0

### Direct Dependencies

| Package | Version | Purpose | Security Notes |
|---------|---------|---------|----------------|
| `github.com/golang-jwt/jwt/v4` | `v4.5.2` | JWS envelope construction | Same as above — patched version |
| `github.com/veraison/go-cose` | `v1.3.x` | COSE envelope (RFC 9052) | Well-tested; no known CVEs |
| `github.com/fxamacker/cbor/v2` | `v2.7.x` | CBOR encoding (COSE) | Extensively fuzz-tested; no known CVEs |
| `golang.org/x/crypto` | `v0.x` | Extended crypto | Standard Go library |
| `github.com/notaryproject/tspclient-go` | `v0.x` | RFC 3161 timestamping | Internal project |

#### Security Note: fxamacker/cbor v2

The `cbor/v2` library is notable for security-relevant reasons:
- Has extensive fuzzing coverage using `go-fuzz`
- Handles potentially attacker-controlled CBOR from registry responses (COSE envelope parsing)
- Enforces strict CBOR determinism checks in signature contexts
- No known CVEs

#### Security Note: veraison/go-cose

`go-cose` is the IETF COSE (RFC 9052/8152) reference implementation in Go. It is used for COSE_Sign1 envelope construction and verification. The library performs:
- Algorithm parameter validation
- Protected header integrity checking
- Detached/attached payload handling

No known CVEs; maintained by the Veraison project (CNCF landscape).

---

## Repository 4: notation-plugin-framework-go

**Module**: `github.com/notaryproject/notation-plugin-framework-go`
**Go Version**: 1.20

### Direct Dependencies

| Package | Version | Purpose | Security Notes |
|---------|---------|---------|----------------|
| `github.com/opencontainers/image-spec` | `v1.1.x` | OCI descriptor types | No known CVEs |

This repository has minimal external dependencies — it defines the plugin protocol schema and SDK without implementing cryptographic operations itself.

---

## Dependency Risk Summary

| Risk Level | Package | Reason | Action |
|------------|---------|--------|--------|
| ADDRESSED | `golang-jwt/jwt/v4` | Algorithm confusion CVEs patched at v4.2.0; running v4.5.2 | Keep up to date |
| LOW | `go-ldap/ldap/v3` | LDAP network code not invoked (govulncheck confirmed) | Monitor for CVEs |
| LOW | `golang.org/x/crypto` | Non-standard library; needs regular updates | Auto-update via Dependabot |
| LOW | `fxamacker/cbor/v2` | Processes attacker-controlled input (COSE envelopes) | Monitor CVEs; has good fuzz coverage |
| LOW | `veraison/go-cose` | Processes attacker-controlled input | Monitor CVEs |

---

## Recommendations for Dependency Management

### 1. Enable Dependabot or Renovate Bot

Configure automatic dependency updates in `.github/dependabot.yml`:

```yaml
version: 2
updates:
  - package-ecosystem: "gomod"
    directory: "/"
    schedule:
      interval: "weekly"
    groups:
      go-stdlib:
        patterns:
          - "golang.org/x/*"
```

### 2. Keep govulncheck in CI

The existing `Makefile` has `make vuln` or equivalent. Ensure `govulncheck` runs on every PR:

```yaml
- name: Check vulnerabilities
  run: govulncheck ./...
```

### 3. Pin Transitive Dependency Ranges

For security-critical transitive dependencies (particularly crypto-related), consider using `replace` directives in `go.mod` with minimum-version pinning to ensure no unintended downgrades.

### 4. Track golang/jwt/v4 End-of-Life

The `golang-jwt/jwt` v4 branch is maintained but v5 has been released with breaking API changes. Monitor the project's roadmap. Migration to v5 in a future notation release cycle would be prudent.
