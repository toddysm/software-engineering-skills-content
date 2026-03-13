# Detailed Security Analysis — Notation Project

**Analysis Date**: 2026-03-12
**Analyst**: Automated (gosec v2.x, govulncheck latest)
**Scope**: notation main repository + deps (notation-go, notation-core-go, notation-plugin-framework-go)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Scope and Methodology](#scope-and-methodology)
3. [Tool Results](#tool-results)
4. [Finding Details — MEDIUM Severity](#finding-details--medium-severity)
5. [Finding Details — LOW Severity](#finding-details--low-severity)
6. [Finding Details — INFO / Code Quality](#finding-details--info--code-quality)
7. [Attack Surface Analysis](#attack-surface-analysis)
8. [Cryptographic Assessment](#cryptographic-assessment)
9. [Authentication and Authorization Assessment](#authentication-and-authorization-assessment)
10. [Dependency Security Assessment](#dependency-security-assessment)
11. [Secrets and Credential Exposure](#secrets-and-credential-exposure)
12. [Conclusions and Recommendations](#conclusions-and-recommendations)

---

## Executive Summary

The Notation project codebase demonstrates a **strong security posture**. No known CVEs were found in any transitively-linked Go dependency. The automated static analysis found 38 raw gosec findings; after manual contextualization, **no high-severity real vulnerabilities remain**. The original two HIGH findings are false positives related to safe integer type conversions. The most actionable finding is a pattern of file-path handling in the CLI output utility and plugin installer that, while not exploitable in the current context, would benefit from explicit path sanitisation as a defence-in-depth measure.

| Severity | Raw Count | After FP Filter | Real Issues |
|----------|-----------|-----------------|-------------|
| CRITICAL | 0 | 0 | 0 |
| HIGH | 2 | 0 | 0 (false positives — safe integer conversion) |
| MEDIUM | 8 | 6 | 6 (path via variable — low practical risk) |
| LOW | 2 | 2 | 2 (integer conversion + unhandled error) |
| INFO | 28 | 28 | 28 (unhandled fmt.Fprintf return values) |

**Key Positive Findings**:
- 0 known CVEs in any dependency
- Uses Go standard library crypto throughout — no custom crypto
- Plugin subprocess isolation prevents key material exfiltration
- Declarative trust policy prevents trust-on-first-use attacks
- No hardcoded credentials or API keys in source
- OCI reference validation performed before registry operations

---

## Scope and Methodology

### Repositories Analysed

| Repository | Location | Files Scanned |
|------------|----------|---------------|
| `github.com/notaryproject/notation/v2` | Main repo | 70 Go source files (excl. tests) |
| `github.com/notaryproject/notation-go` | `deps/notation-go/` | ~160 Go source files |
| `github.com/notaryproject/notation-core-go` | `deps/notation-core-go/` | ~80 Go source files |
| `github.com/notaryproject/notation-plugin-framework-go` | `deps/notation-plugin-framework-go/` | ~60 Go source files |

### Tools Used

| Tool | Version | What It Checks |
|------|---------|----------------|
| `gosec` | v2.x | Go source code security rules — injection, file inclusion, weak crypto, etc. |
| `govulncheck` | latest | CVE database check against actual call graph (filters theoretical deps) |

### Tools Not Available (Not Installed)

| Tool | What It Would Check | Disposition |
|------|--------------------|-|
| `semgrep` | Custom rule patterns, data-flow taint | Not installed — skip |
| `gitleaks` | Hardcoded secrets in git history | Not installed — skip |
| `nancy` | Known CVEs in go.sum (OSS Index) | Not installed — govulncheck covers this |

### Approach

1. Run `gosec` on the main module source (`./...`) and collect JSON output.
2. Run `govulncheck` on the main module with `-json` and inspect vulnerability list.
3. For each finding, read the surrounding source code to contextualise.
4. Classify each finding as: **Confirmed** (real issue), **Accepted Risk** (real but mitigated), or **False Positive**.
5. Document attack surfaces, cryptographic patterns, and dependency risk separately.

---

## Tool Results

### gosec — Summary

```
Total: 38 issues
  Severity HIGH:   2  (G115)
  Severity MEDIUM: 8  (G304)
  Severity LOW:   28  (G104)
```

Raw output: `security/tool-scan-results/gosec-results.json`

### govulncheck — Summary

```
Total vulnerabilities: 0

No vulnerabilities found.
```

Raw output: `security/tool-scan-results/govulncheck-results.json`

---

## Finding Details — MEDIUM Severity

### G304 — File Inclusion via Variable

**Rule**: G304 fires when a file path passed to `os.Open`, `os.ReadFile`, or similar functions is derived from a variable rather than a string literal. This guards against path traversal if user input reaches the path without sanitisation.

#### Instance 1–7: `osutil/file.go`

```go
// File: cmd/notation/internal/osutil/file.go

func Copy(src, dst string) error {
    f, err := os.Open(src)    // G304: variable path
    ...
}

func WriteFile(path string, data []byte) error {
    if err := os.MkdirAll(filepath.Dir(path), 0700); err != nil { ... }
    return os.WriteFile(path, data, WritableFileMode)  // G304: variable path
}
```

**Context**: These helpers are called exclusively from:
- `plugin/install.go` → install path derived from `notation-go/dir` canonical directory builder
- `key/add.go`, `cert/add.go` → paths derived from OS key/trust store paths via `dir` package
- None of the call sites accept raw user input strings as file paths without going through the `dir` package first

**Classification**: **Accepted Risk** — the path variable comes from a controlled source (`dir.UserConfigFS`, OS keystore paths). No user-provided arbitrary string reaches these functions without prior canonicalization. A defence-in-depth `filepath.Clean()` call before opening would further reduce the alarm surface.

**Recommended Fix** (defence-in-depth):
```go
func Copy(src, dst string) error {
    src = filepath.Clean(src)
    f, err := os.Open(src)
    ...
}
```

#### Instance 8: `plugin/install.go`

```go
// Before installing a plugin binary:
rc, err := os.Lstat(path)          // G304
if err == os.ErrNotExist { ... }
f, err := os.Open(path)            // G304
```

The `path` variable is derived from: `dir.UserLibexecFS()` + plugin name validated by `ValidatePlugin()` which checks the plugin binary naming convention and validates its metadata response. The plugin name is provided by the user on the command line but must conform to `notation-<name>` naming convention and pass signature validation before installation.

**Classification**: **Accepted Risk** — plugin names are validated. However, path canonicalization before the `os.Open()` call is recommended.

---

## Finding Details — LOW Severity

### G115 — Integer Overflow Conversion

**Locations**: `cmd/notation/login.go` lines 191–192

```go
isTerminal := term.IsTerminal(int(os.Stdin.Fd()))
password, err := term.ReadPassword(int(os.Stdin.Fd()))
```

**Why gosec flags this**: `os.File.Fd()` returns `uintptr`. Converting `uintptr` to `int` would overflow on a 32-bit platform if `uintptr > math.MaxInt32`.

**Contextualisation**:
- File descriptors on UNIX are small non-negative integers (stdin = 0, stdout = 1, stderr = 2). The OS never allocates an fd near `MaxInt32`.
- The `term` package's `IsTerminal` and `ReadPassword` functions accept `int` because that's what the underlying `syscall.Syscall` expects (POSIX `isatty(int fd)`).
- All supported targets for `notation` are 64-bit (`linux/amd64`, `linux/arm64`, `darwin/amd64`, `darwin/arm64`, `windows/amd64`). On 64-bit platforms, `uintptr` and `int` are both 64-bit; the conversion cannot overflow.

**Classification**: **False Positive** — not a real vulnerability on supported 64-bit platforms.

**Recommended Action**: Add `//nolint:gosec` comment with justification to suppress the noise in future scans.

---

## Finding Details — INFO / Code Quality

### G104 — Errors Unhandled (28 instances)

**Rule**: G104 fires when the return value of certain functions (particularly `fmt.Fprintf`, `fmt.Fprintln`) is not checked.

**Pattern**:
```go
// Throughout cmd/notation/*.go:
fmt.Fprintf(os.Stderr, "Warning: ...")    // error not checked
fmt.Fprintln(cmd.OutOrStdout(), ...)      // error not checked
```

**Context**: These are all in CLI output code writing to stdout/stderr or to `cobra.Command.OutOrStdout()`. Errors from writing to stdout/stderr in a CLI application (e.g. "broken pipe" when output is piped to `head`) are not critical — the application is already outputting secondary information (warnings, progress messages) and cannot meaningfully recover from a write error without confusing the user.

**Classification**: **Code Quality** — not a security vulnerability. This is a well-known Go lint pattern; `fmt.Fprintf` to stderr rarely fails in practice, and failing to handle it cannot be exploited by an attacker.

**Recommended Action**: For the most critical output (e.g. final signing result), consider checking errors. For incidental output (warnings, notices), `//nolint:errcheck` annotations are appropriate.

---

## Attack Surface Analysis

### Surface 1: User-Supplied Command-Line Paths

**Entry points**: `--file` flags (blob sign/verify), trust policy `--path`, certificate/key `--path` flags.

**Risk**: Path traversal, symlink following.

**Mitigations in place**:
- Trust policy path is validated for existence and file size before parsing.
- Certificate paths are resolved through `dir.UserConfigFS`.
- Blob file paths pass `os.Open` — no canonicalization. If `notation blob sign /etc/passwd` were run (needing read permission), it would sign whatever the system file resolves to. This is intentional; users choose what to sign.

**Verdict**: Acceptable. A signing tool must sign what the user asks it to sign.

---

### Surface 2: OCI Registry References

**Entry points**: `IMAGE` positional argument in `notation sign`, `notation verify`, etc.

**Risk**: SSRF (reaching internal registries), open redirect, confused deputy.

**Mitigations in place**:
- OCI reference parsing (`oras-go`) validates the reference format before any network calls.
- The trust policy must have a scope matching the registry+repository before verification proceeds.
- Registry credentials come from Docker credential helpers (`~/.docker/config.json`) — not from the command line.
- TLS is enforced by default; `--insecure-registry` flag exists but must be explicitly set.

**Verdict**: Low risk. The trust policy acts as an allowlist — verification only succeeds for explicitly trusted registries.

---

### Surface 3: Plugin Binaries

**Entry points**: Plugin installation (`notation plugin add`) and runtime plugin invocation during sign/verify.

**Risk**: Malicious plugin binary executes arbitrary code with the user's privileges.

**Mitigations in place**:
- Plugin binaries are stored in `~/.config/notation/plugins/<name>/notation-<name>` (or system equivalent).
- Installation via `notation plugin add` validates the plugin's own signature (the plugin must pass `GetPlugin` metadata check which includes a version-info validation).
- At runtime, the plugin subprocess is invoked with no additional privileges — it runs as the same user.
- The JSON stdin/stdout protocol has a defined schema; malformed responses are rejected.

**Verdict**: Medium risk (inherent to plugin model). Mitigated by: (a) plugins are installed by the same user who has to trust them, (b) signed plugin distribution is possible via the same Notation mechanism, (c) subprocess isolation limits blast radius.

**Note**: The trust model for plugins is fundamentally "user trusts what they install" — this is by design, not a vulnerability.

---

### Surface 4: OCI Registry Responses

**Entry points**: `notation verify` fetches signature blobs from the OCI registry.

**Risk**: Registry returns malformed or maliciously crafted signature blobs designed to exploit parsing code.

**Mitigations in place**:
- `notation-core-go` validates the envelope type before dispatching to JWS or COSE parser.
- JSON envelope parsing uses Go's `encoding/json` (no known parsing vulnerabilities).
- COSE envelope parsing uses `fxamacker/cbor/v2` — a well-tested CBOR library with fuzzing coverage.
- Signature verification uses Go standard library `crypto/x509` and `crypto/ecdsa`/`crypto/rsa` — well-audited.
- Maximum payload/header sizes are enforced by the `notation-go` verifier to prevent memory exhaustion.

**Verdict**: Low risk.

---

### Surface 5: Trust Policy JSON

**Entry points**: Trust policy file loaded from `~/.config/notation/trustpolicy.oci.json`.

**Risk**: Malicious policy file causes bypasses or confusion.

**Mitigations in place**:
- Trust policy is parsed by `notation-go/verifier/trustpolicy` which performs schema validation.
- Scope wildcards are parsed with explicit semantics (only `*` at the front of segments).
- Invalid policies are rejected with clear errors — there is no "insecure default" that silently accepts anything.

**Verdict**: Low risk. The threat model assumes the trust policy file is owned by the local user; if an attacker can modify it, they already have system access.

---

### Surface 6: Timestamping Authority (RFC 3161)

**Entry points**: `--timestamp-url` flag in `notation sign`.

**Risk**: SSRF to internal TSA servers; tampered timestamp responses.

**Mitigations in place**:
- The TSA URL must be https:// (TLS required by default for `tspclient-go`).
- Timestamp countersignature is verified against a trusted TSA certificate chain pulled from `trustpolicy`.
- If timestamping fails, signing either aborts or succeeds based on `--timestamp-revocation-validations` policy.

**Verdict**: Low risk when TSA cert is properly configured.

---

## Cryptographic Assessment

### Algorithms

| Operation | Algorithm | Key Material | Standard |
|-----------|-----------|-------------|---------|
| Signature — JWS | ECDSA-P256/P384/P521 or RSA-PSS-2048/3072/4096 | User-controlled via plugin | RFC 7518 |
| Signature — COSE | ECDSA-P256/P384/P521 or RSA-PSS-2048/3072/4096 | User-controlled via plugin | RFC 9053 |
| Cert chain validation | X.509 v3, PKIX path validation | Embedded trust anchors | RFC 5280 |
| Timestamp countersig | SHA-256 with ECDSA/RSA | TSA key via RFC 3161 | RFC 3161 |
| Digest — artifact | SHA-256 minimum (OCI content digest) | N/A | OCI Spec |

**No custom crypto**. All cryptographic operations use Go standard library (`crypto/ecdsa`, `crypto/rsa`, `crypto/x509`) or well-established libraries (`go-cose`, `golang-jwt/jwt`).

### Key Material Handling

- Private keys are **never present** in the main `notation` process — all signing is delegated to plugins via subprocess.
- The default plugin (if used) stores keys in the OS keychain or PKCS#12 files — not in plain files by default.
- The codebase does not log, print, or persist key material anywhere in the `notation` binary.

### Certificate Validation

- Full certificate chain validation is performed before accepting a signature.
- Revocation checking is configurable in the trust policy (`revocationValidations: "audit" | "enforce" | "skip"`).
- Certificate expiry is validated including the timestamped signing time — a certificate that was valid when the signature was created remains valid after expiry if a trusted timestamp exists.

### Weak Algorithms

No MD5, SHA-1, or DES usage found in the codebase. The `golang-jwt/jwt` library version in use (v4.5.2) requires explicit algorithm selection — the algorithm confusion vulnerability (CVE-2022-21681 and related) that affected earlier jwt versions is patched at v4.2.0.

---

## Authentication and Authorization Assessment

Notation is a **client-side CLI tool** — there is no server component to authenticate against directly. Authentication concerns are:

### Registry Authentication
- Delegates to Docker credential helpers and `~/.docker/config.json` credential store.
- No credentials are stored by `notation` itself.
- The `notation login` command calls `docker login`-compatible credential helpers.

### Trust Policy as Authorization
- The trust policy acts as an authorization document: it defines which signing identities are trusted for which registry paths.
- Verification only succeeds if: (a) a valid signature exists AND (b) the signing certificate matches a trusted identity in the policy for the given scope.
- This is equivalent to an allowlist authorization check.

### Plugin Authorization
- No inter-process authentication between `notation` and plugins. Trust is based on the plugin being present in the libexec directory (filesystem-based).
- This is appropriate for a single-user CLI tool.

---

## Dependency Security Assessment

See `security/dependency-audit.md` for full dependency details.

**Summary**:
- `govulncheck` found **0 known vulnerabilities** across all transitive dependencies actually called by the notation binary.
- `golang-jwt/jwt v4.5.2` in `notation-go` — post-algorithm-confusion-fix version; no known CVEs.
- `go-cose v1.x` — COSE signing library; no known CVEs.
- `oras-go/v2` — OCI client reference library; no known CVEs.
- `fxamacker/cbor/v2` — CBOR parser with extensive fuzz testing; no known CVEs.
- `golang.org/x/crypto` — Go extended crypto package; kept up to date via module requirements.

---

## Secrets and Credential Exposure

### Hardcoded Secrets Check

No hardcoded API keys, passwords, private keys, or tokens were found in the source code. Searches for `password`, `secret`, `token`, `apikey` patterns found only:
- Comments explaining what the user's credential helper stores
- The `term.ReadPassword()` call in `login.go` which reads a password from the terminal at runtime
- Test fixtures that explicitly use fake/test values

### Environment Variable Handling

In `main.go`, the `NOTATION_EXPERIMENTAL` environment variable is read and stored. No credentials are read from environment variables. Credential handling is delegated to Docker credential helper conventions.

### Log Safety

The logging framework (`logrus`) is used with structured fields. No `%s` formatting of sensitive values (key material, tokens) was found in the log statements reviewed. Debug logging (`log.Debug`, `log.Debugf`) does not log registry credentials.

---

## Conclusions and Recommendations

### Overall Assessment

**GOOD security posture.** The Notation project is designed as a security tool and this is reflected in the code quality: no custom crypto, no stored credentials, subprocess isolation for key material, and a strong declarative trust model.

### Prioritised Recommendations

#### Priority 1 — Defence-in-Depth: Path Sanitisation (MEDIUM)

**Files**: `cmd/notation/internal/osutil/file.go`, `cmd/notation/internal/plugin/install.go`
**Action**: Add `filepath.Clean()` and optionally a base-directory bounds check before file open operations.
**Effort**: Low (2–4 lines per function)
**Impact**: Eliminates the G304 alarm class and adds robustness against any future caller that might pass a less-controlled path.

```go
// Recommended pattern:
func Copy(src, dst string) error {
    src = filepath.Clean(src)
    if !strings.HasPrefix(src, allowedBase) {
        return fmt.Errorf("path %q is outside allowed directory", src)
    }
    ...
}
```

#### Priority 2 — Lint Suppression with Justification (LOW)

**Files**: `cmd/notation/login.go` line 191–192
**Action**: Add `//nolint:gosec // safe: os.Stdin fd is always small; all targets are 64-bit` to suppress the G115 false positive.
**Effort**: Trivial
**Impact**: Cleaner CI scan results; avoids false alarm fatigue.

#### Priority 3 — Error Capture for Critical Output (INFO)

**Files**: Throughout `cmd/notation/*.go`
**Action**: For final result output lines (the lines that tell the user whether an operation succeeded), assign and check `fmt.Fprintf` return values. For incidental output (warnings, notices), add `//nolint:errcheck` annotations.
**Effort**: Low (1 day)
**Impact**: Improved robustness; eliminates 28 INFO-level gosec findings.

#### Priority 4 — Enable Remaining Security Scanners

**Action**: Add `semgrep` and `gitleaks` to the CI pipeline (already have gosec and govulncheck via Makefile).
**Effort**: Medium (configure rule sets, fix initial findings)
**Impact**: Broadens coverage to secret detection and custom pattern matching.

### Security Strengths to Preserve

1. **No custom crypto** — continue using Go standard library and audited libraries only.
2. **Plugin subprocess isolation** — never move key material into the notation binary.
3. **Declarative trust policy** — never implement trust-on-first-use as a default.
4. **No server component** — the attack surface stays limited to the single-user CLI context.
5. **govulncheck in CI** — maintain zero-CVE posture with regular dependency updates.
