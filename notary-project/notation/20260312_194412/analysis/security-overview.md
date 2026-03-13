# Security Overview — Notation (Notary Project)

**Analysis Date**: 2026-03-12  
**Scope**: All four repositories (notation/v2, notation-go, notation-core-go, notation-plugin-framework-go)

> For the full vulnerability scan results and detailed security audit, see [../security/detailed-security-analysis.md](../security/detailed-security-analysis.md).

---

## Overall Security Posture: **GOOD**

Notation is a security-focused project by design — its entire purpose is supply chain security. The codebase reflects that intent: the cryptographic architecture is sound, the trust model is well-defined, and the project follows modern secure development practices.

**govulncheck** found **zero known CVEs** in any dependency. **gosec** found **38 findings**, all of which are Low/Medium severity and most are conservative false-positives (see detailed analysis).

---

## What The System Does Well

### 1. Cryptographic Design is Correct
- Uses only ECDSA and RSA with appropriate key sizes (≥2048 RSA, ≥P-256 ECDSA)
- Supports NIST-approved algorithms only (RSASSA-PSS, ECDSA with SHA-256/384/512)
- JWS and COSE envelope formats are industry standards (RFC 7515, RFC 9052)
- No custom cryptographic implementations — uses `crypto/x509`, `go-cose`, `golang-jwt`
- Certificate chain validation enforces proper EKU and key usage
- Timestamps (RFC 3161) protect signatures against certificate expiry attacks

### 2. Trust Model is Explicit and Auditable
- Trust policy is declared as a checked-in JSON document, not hidden in flags
- Three verification levels (strict/permissive/audit) give operators control
- Trust store is separate from trust policy — certificates and policy rules are distinct
- Both OCI artifacts and arbitrary blobs have separate trust policy documents

### 3. Plugin Isolation
- Plugins run as **separate processes** — key material never enters the notation process
- IPC via stdin/stdout: well-defined, simple, auditable protocol
- Plugin binaries installed into a dedicated libexec directory
- Checksum validation (`ValidateSHA256Sum`) is performed on plugin binary at install time

### 4. Supply Chain Hygiene
- **Signed commits enforced** in CI (1Password commit signing check in build.yml)
- **OpenSSF Scorecard** evaluated via GitHub Actions workflow
- **CodeQL analysis** runs on every push (workflow: codeql.yml)
- **govulncheck** reports zero known CVEs in the dependency tree
- **Dependabot** configured for automated dependency updates

### 5. Credential Handling
- Registry credentials are never logged
- Main `PersistentPreRun` in main.go explicitly **unsets registry credential env vars** after reading them, preventing downstream leakage
- Credentials read from prompt use `term.ReadPassword()` to avoid echoing

---

## Security Considerations and Minor Issues

### Finding: Integer Conversion in login.go (G115 — LOW practical risk)

`os.Stdin.Fd()` returns a `uintptr`; `term.IsTerminal` and `term.ReadPassword` accept an `int`. On 64-bit systems, the `uintptr → int` conversion is safe for file descriptors (always in range 0–2 for stdin). This is a gosec conservative static analysis flag that does not represent an exploitable vulnerability on any supported platform.

**File**: `cmd/notation/login.go:191-192`  
**Recommendation**: Add explicit bounds check or a `//nolint:gosec` with justification.

### Finding: File Path via Variable (G304 — contextual low risk)

Eight file operations in `internal/osutil/file.go` and `cmd/notation/plugin/install.go` are flagged as "potential file inclusion via variable" (G304). In context:
- All paths in `osutil/file.go` are either derived from the `notation-go/dir` package (which computes paths from OS-managed directories) or passed from callers that have already validated the path
- `plugin/install.go` validates the plugin file path via `os.Stat()` and validates it is a regular file before the open call
- No user-supplied paths are passed to these functions without prior sanitisation

**Recommendation**: For defense-in-depth, add `filepath.Clean()` calls before file opens, and validate that paths are within expected base directories (path traversal guard).

### Finding: Unhandled Errors (G104 — minor code quality)

Twenty-five instances where function return values (including errors) are not checked — mostly in output formatting functions (`fmt.Fprintf`, `io.Writer` calls) and in cleanup/deferred operations. These are consistent with CLI output code where write errors to stdout are not fatal.

**Recommendation**: Handle errors from `fmt.Fprintf` calls where the output is critical (e.g., policy show, trust store list). Low-priority for output formatting paths.

---

## Attack Surface Summary

The attack surface is narrow, which is appropriate for a CLI tool:

1. **User-supplied file paths** (cert add, policy import, plugin install, blob sign/verify) — all validated as regular files before use
2. **Registry references** (sign/verify targets) — resolved and dereferenced via oras-go/v2, which handles URL parsing
3. **Plugin binaries** — isolated subprocesses; SHA-256 checksum validated at install
4. **OCI registry responses** (signature blobs) — parsed via hardened Go standard library
5. **Trust policy JSON** — parsed with standard `encoding/json`; malformed files produce user-visible errors
6. **Certificate files** (PEM/DER from trust store) — parsed via `crypto/x509`

There is **no network server component** — Notation is a CLI client only. There is no persistent daemon, no exposed ports, no incoming request handling.

---

## Dependency Security

- **govulncheck**: 0 known vulnerabilities in reachable code paths
- **golang-jwt/jwt v4.5.2**: patched against JVE-2022-29965 (algorithm confusion) — uses v4 which requires explicit algorithm specification
- **go-cose v1.3.0**: current and actively maintained
- **oras-go/v2 v2.6.0**: current release, actively maintained by CNCF

---

## Summary Recommendations

| Priority | Recommendation |
|----------|---------------|
| Low | Add `filepath.Clean()` + base-directory bounds checks in `osutil/file.go` for defence in depth |
| Low | Handle `fmt.Fprintf` errors in output formatting paths |
| Low | Add `//nolint:gosec G115` with justification comments on `os.Stdin.Fd()` conversions |
| Informational | Ensure plugin checksums (SHA-256) at install time are displayed to users for manual verification |
| Informational | Consider adding SBOM generation (`syft`) to release workflow |
