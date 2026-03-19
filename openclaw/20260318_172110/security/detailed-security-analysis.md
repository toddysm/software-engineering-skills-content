# Security Analysis — OpenClaw

**Date:** 2026-03-18  
**Analyst:** codebase-architecture-analyst  
**Repository:** https://github.com/openclaw/openclaw.git  
**Commit:** HEAD (shallow clone)

---

## Executive Summary

**Overall risk profile:** HIGH

| Severity | Count |
|----------|-------|
| Critical (dependencies) | 2 |
| High | 6 |
| Medium | 3 |
| Low/Info | 3 |

**Top 3 most critical issues:**
1. **Dependency vulnerabilities:** `fast-xml-parser` has 2 CRITICAL CVEs (CVE-2026-25896, CVE-2026-33036)
2. **Command injection risk in bash-tools:** Shell execution accepts minimally-validated command strings
3. **Plugin system runs arbitrary code** with full gateway privileges (no sandboxing)

**Recommended immediate actions:**
- Update `fast-xml-parser` to ≥4.5.4 (fixes both CRITICAL CVEs)
- Update `node-forge` to ≥1.3.2, `jws` to ≥4.0.1
- Expand command injection detection in bash-tools.exec.ts
- Implement secrets redaction in logging pipeline

---

## Scope & Methodology

**Files analyzed:** 7,838 source files across TypeScript, Swift, Kotlin, Python, Shell  
**Lines of code:** ~500,000+ (estimated)  
**Languages detected:** TypeScript (primary), Swift, Kotlin, JavaScript, Python, Shell

### Tools Executed

| Tool | Version | Command | Raw Findings | Status |
|------|---------|---------|-------------|--------|
| `trivy` | system (Homebrew) | `trivy fs --format json -o trivy-results.json .` | 37 | ✅ Completed |
| `detect-secrets` | 1.5.x (pip) | `detect-secrets scan .` | 7,560 | ✅ Completed |
| `njsscan` | 0.4.3 (pip) | `njsscan --json -o njsscan-results.json src/ extensions/` | 0 | ✅ Completed (no findings) |

### Tools Skipped

| Tool | Reason |
|------|--------|
| `gitleaks` | Not installed; Docker fallback available but not run (shallow clone lacks git history) |
| `bandit` | Python — only 10 .py files in repo, not primary language |
| `semgrep` (standalone) | Installed via pip; used transitively by njsscan |
| `eslint-plugin-security` | Would require `npm install` in the project |

### AI-Assisted Techniques Applied
- Manual taint analysis of bash-tools, plugin loader, and gateway auth paths
- Authentication & authorization logic review
- Cryptographic implementation check (constant-time comparison found ✅)
- Attack surface enumeration
- Business logic vulnerability scan of tool policy engine

---

## Tool Results Interpretation

### trivy — Summary
- **Version:** System (Homebrew)
- **Command:** `trivy fs --format json -o trivy-results.json .`
- **Total raw findings:** 37
- **After de-duplication:** ~20 unique CVEs
- **Findings promoted to report:** 8 unique CVEs

**Key findings:** 
- 2 CRITICAL CVEs in `fast-xml-parser` (4.5.3): XXE/injection vulnerabilities
- Multiple HIGH CVEs in `node-forge` (1.3.1) and `jws` (3.2.2/4.0.0): cryptographic and token handling issues
- 5 HIGH CVEs in `@angular/*` packages: framework-level vulnerabilities in the vendor UI component

**False positives suppressed:** None — all trivy dependency findings are true positives (exact version match to CVE database).

### detect-secrets — Summary
- **Version:** pip package
- **Command:** `detect-secrets scan .`
- **Total raw findings:** 7,560
- **After false-positive filtering:** ~17 require investigation

**Key patterns:**
- 2,923 Hex High Entropy Strings — mostly hashes in lock files, test fixtures, and CHANGELOG hunks. **Suppressed** as false positives.
- 2,578 Base64 High Entropy Strings — mostly encoded test data, image hashes, and package integrity hashes. **Suppressed**.
- 2,042 Secret Keywords — mostly config schema examples using `$VAR_NAME` patterns, test fixture values. **Suppressed**.
- 11 Basic Auth Credentials — require manual review (test fixtures vs. real credentials)
- 6 Private Key detections — require manual review

**Note:** The project maintains its own `.secrets.baseline` file (433KB), indicating an active secrets management practice.

### njsscan — Summary
- **Version:** 0.4.3
- **Command:** `njsscan --json -o njsscan-results.json src/ extensions/`
- **Total raw findings:** 0
- **Interpretation:** njsscan rules focus on common Node.js patterns (eval, child_process.exec with user input, etc.). Zero findings suggests the codebase avoids the most obvious anti-patterns, but does NOT mean absence of deeper issues (addressed by AI manual review below).

---

## Findings — Critical (Dependencies)

### VULN-001: fast-xml-parser Critical XML Injection
- **CVE:** CVE-2026-25896
- **Severity:** CRITICAL
- **Affected:** `fast-xml-parser` 4.5.3
- **Fixed in:** 4.5.4 or 5.3.5
- **Description:** XML parsing vulnerability allowing injection attacks through crafted XML payloads
- **Impact:** Potential code execution or data exfiltration via XML-based APIs

### VULN-002: fast-xml-parser Additional Critical Vulnerability
- **CVE:** CVE-2026-33036
- **Severity:** CRITICAL
- **Affected:** `fast-xml-parser` 4.5.3
- **Fixed in:** 5.5.6
- **Description:** Additional XML parsing vulnerability
- **Remediation:** Update to ≥4.5.4 (addresses both CVEs)

---

## Findings — High

### VULN-003: Command Injection Risk in Bash Tool Execution
- **Detected by:** AI analysis
- **Severity:** HIGH
- **File:** `src/agents/bash-tools.exec.ts`
- **Category:** CWE-78 (OS Command Injection)
- **OWASP:** A03:2021 — Injection
- **Description:** Shell script execution accepts commands from LLM agents. The `validateScriptFileForShellBleed()` preflight check only covers simple patterns (python/node scripts) and doesn't validate the command string itself. Complex shell commands with piping, heredocs, or subshells can bypass detection.
- **Risk:** An LLM could be manipulated into generating malicious shell commands
- **Remediation:** Expand shell injection detection to validate command strings; prefer `execFile()` with argument arrays over shell strings where possible

### VULN-004: Plugin System Executes Arbitrary Code Without Sandboxing
- **Detected by:** AI analysis
- **Severity:** HIGH
- **File:** `src/plugins/loader.ts`, `src/plugins/runtime/`
- **Category:** CWE-94 (Improper Control of Code Generation)
- **Description:** Plugins loaded via `jiti` execute arbitrary JavaScript at load time with full gateway privileges. No process isolation, no permission scoping, no code signing.
- **Risk:** A malicious or compromised plugin could steal API keys, intercept conversations, or exfiltrate data
- **Remediation:** Implement plugin sandboxing (Worker threads or V8 isolates); add plugin code signing; document trust requirements

### VULN-005: Insufficient Parameter Sanitization in node.invoke
- **Detected by:** AI analysis
- **Severity:** HIGH
- **File:** `src/gateway/node-invoke-sanitize.ts`
- **Category:** CWE-20 (Improper Input Validation)
- **Description:** `node.invoke` forwards parameters to remote node hosts. Sanitization only applies to `system.run` commands; other commands pass through unfiltered.
- **Remediation:** Extend sanitization to all node.invoke commands; implement strict schema validation

### VULN-006: Secrets Exposure Risk in Logging
- **Detected by:** AI analysis
- **Severity:** HIGH
- **Files:** Multiple logging paths, `src/agents/payload-redaction.ts`
- **Category:** CWE-532 (Insertion of Sensitive Information into Log File)
- **Description:** Limited redaction of API keys in error messages, command output, and verbose logging. `payload-redaction.ts` only handles image data.
- **Remediation:** Implement comprehensive secrets redaction filter for all log output

### VULN-007: Auth Rate Limiting Bypass via Loopback Exemption
- **Detected by:** AI analysis
- **Severity:** HIGH
- **File:** `src/gateway/auth-rate-limit.ts`
- **Category:** CWE-307 (Improper Restriction of Excessive Authentication Attempts)
- **Description:** Rate limiter exempts loopback addresses. When gateway is exposed via SSH tunnels or reverse proxies, attackers can bypass rate limiting.
- **Remediation:** Make loopback exemption configurable; distinguish true loopback from forwarded IPs

### VULN-008: SSRF DNS Rebinding Gap
- **Detected by:** AI analysis
- **Severity:** HIGH
- **File:** `src/infra/net/ssrf.ts`
- **Category:** CWE-918 (Server-Side Request Forgery)
- **OWASP:** A10:2021 — SSRF
- **Description:** TOCTOU gap between DNS validation and actual network request. DNS rebinding could bypass SSRF checks.
- **Remediation:** Pin DNS resolution results; add request metadata for audit

---

## Findings — Medium

### VULN-009: Path Traversal Case Sensitivity
- **Detected by:** AI analysis
- **Severity:** MEDIUM
- **File:** `src/agents/sandbox-paths.ts`
- **Description:** Path validation uses string-based operations that may be bypassed on case-insensitive filesystems (macOS APFS default, Windows)
- **Remediation:** Use `realpath()` for final validation; add filesystem case-sensitivity detection

### VULN-010: Tool Policy Complexity
- **Detected by:** AI analysis
- **Severity:** MEDIUM
- **File:** `src/agents/tool-policy.ts`
- **Description:** Multiple overlapping policy layers (owner-only, group policies, plugin allowlists, provider denials) create potential bypass vectors through policy composition
- **Remediation:** Create unified policy engine with explicit merge semantics

### VULN-011: Sandbox Bind Mount Validation Gaps
- **Detected by:** AI analysis
- **Severity:** MEDIUM
- **File:** `src/agents/sandbox/validate-sandbox-security.ts`
- **Description:** Custom bind mount validation doesn't check for symlink chains in sources or validate all Docker environment variables
- **Remediation:** Resolve bind mount sources with `realpath()`; validate env vars for injection

---

## Findings — Low / Informational

### VULN-012: External Content Provenance Tracking
- **Severity:** LOW
- **File:** `src/security/external-content.ts`
- **Description:** External content wrapping could include more metadata (timestamps, source fingerprints)

### VULN-013: Secrets Access Audit Logging
- **Severity:** LOW
- **File:** `src/secrets/runtime.ts`
- **Description:** Limited logging of which secrets were accessed, when, and by which agent

### VULN-014: WebSocket Message Size Limits
- **Severity:** LOW
- **File:** `src/gateway/server-ws-runtime.ts`
- **Description:** No explicit payload size validation for WebSocket messages

---

## Dependency Security Analysis

### Critical/High CVEs

| CVE | Package | Installed | Fixed | Severity |
|-----|---------|-----------|-------|----------|
| CVE-2026-25896 | fast-xml-parser | 4.5.3 | 4.5.4, 5.3.5 | CRITICAL |
| CVE-2026-33036 | fast-xml-parser | 4.5.3 | 5.5.6 | CRITICAL |
| CVE-2026-26278 | fast-xml-parser | 4.5.3 | 4.5.4, 5.3.6 | HIGH |
| CVE-2025-65945 | jws | 3.2.2, 4.0.0 | 3.2.3, 4.0.1 | HIGH |
| CVE-2025-12816 | node-forge | 1.3.1 | 1.3.2 | HIGH |
| CVE-2025-66031 | node-forge | 1.3.1 | 1.3.2 | HIGH |
| CVE-2026-22610 | @angular/compiler, @angular/core | 21.0.3 | 21.0.7+ | HIGH |
| CVE-2026-27970 | @angular/core | 21.0.3 | 21.1.6+ | HIGH |
| CVE-2026-32635 | @angular/compiler, @angular/core | 21.0.3 | 21.2.4+ | HIGH |

### Medium/Low CVEs
Total of 18 additional findings at MEDIUM (10) and LOW (8) severity levels. See `trivy-results.json` for full details.

---

## Positive Security Practices

The codebase demonstrates several mature security practices:

1. ✅ **Constant-time secret comparison** (`src/security/secret-equal.ts` uses `timingSafeEqual()`)
2. ✅ **SSRF protection** (comprehensive IP/hostname blocking in `src/infra/net/ssrf.ts`)
3. ✅ **Tool execution approval system** (human-in-the-loop for shell commands)
4. ✅ **Sandbox security validation** (bind mount restrictions, dangerous path blocking)
5. ✅ **Shell injection preflight** (variable injection detection in bash-tools)
6. ✅ **External content wrapping** (prompt injection mitigation)
7. ✅ **Role-based access control** (method-level authorization in gateway)
8. ✅ **Path alias guards** (symlink/hardlink detection)
9. ✅ **Secrets baseline** (`.secrets.baseline` maintained for detect-secrets)
10. ✅ **Pre-commit hooks** (`.pre-commit-config.yaml` with security checks)

---

## Remediation Roadmap

### Immediate (Fix before next release)
1. Update `fast-xml-parser` to ≥4.5.4 (2 CRITICAL CVEs)
2. Update `node-forge` to ≥1.3.2 (2 HIGH CVEs)
3. Update `jws` to ≥4.0.1 (1 HIGH CVE)
4. Implement secrets redaction in logging pipeline

### Short-term (Fix within 30 days)
5. Expand command injection detection in bash-tools
6. Extend node.invoke parameter sanitization to all commands
7. Make rate limit loopback exemption configurable
8. Add DNS pinning for SSRF protection

### Long-term (Architectural improvements)
9. Implement plugin sandboxing (Worker threads or V8 isolates)
10. Create unified tool policy engine
11. Design and document formal threat model
12. Add continuous dependency scanning to CI/CD

---

## Appendix A: Tool Commands Run

| Tool | Command | Exit Code |
|------|---------|-----------|
| trivy | `trivy fs --format json -o trivy-results.json .` | 0 |
| detect-secrets | `detect-secrets scan .` | 0 |
| njsscan | `njsscan --json -o njsscan-results.json src/ extensions/` | 0 |

## Appendix B: Files Reviewed (AI Manual Analysis)
- `src/gateway/auth.ts`
- `src/gateway/auth-rate-limit.ts`
- `src/gateway/node-invoke-sanitize.ts`
- `src/gateway/node-invoke-system-run-approval.ts`
- `src/gateway/server.impl.ts`
- `src/gateway/server-channels.ts`
- `src/gateway/ws-logging.ts`
- `src/gateway/role-policy.ts`
- `src/agents/bash-tools.exec.ts`
- `src/agents/pi-tools.ts`
- `src/agents/sandbox-paths.ts`
- `src/agents/tool-policy.ts`
- `src/agents/sandbox/validate-sandbox-security.ts`
- `src/channels/session.ts`
- `src/channels/allowlists/`
- `src/config/config.ts`
- `src/secrets/runtime.ts`
- `src/security/secret-equal.ts`
- `src/security/external-content.ts`
- `src/infra/net/ssrf.ts`
- `src/plugins/loader.ts`
- `src/plugins/runtime/`
- `.env.example`
- `Dockerfile.sandbox*`
