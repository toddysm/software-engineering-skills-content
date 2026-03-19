# Dependency Audit — OpenClaw

## Overview

OpenClaw uses **pnpm** as its package manager in a monorepo workspace configuration. Dependencies are locked via `pnpm-lock.yaml`.

**Runtime:** Node.js ≥22  
**Package manager:** pnpm (workspace protocol)  
**Lock file:** `pnpm-lock.yaml` (present and used for deterministic installs)

---

## Vulnerability Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 2 | Action required |
| HIGH | 7 | Action required |
| MEDIUM | 10 | Review recommended |
| LOW | 8 | Informational |
| **Total** | **27** unique CVEs | |

---

## Critical Vulnerabilities

### fast-xml-parser 4.5.3

| CVE | Severity | Fixed In | Description |
|-----|----------|----------|-------------|
| CVE-2026-25896 | CRITICAL | 4.5.4, 5.3.5 | XML injection via crafted payloads |
| CVE-2026-33036 | CRITICAL | 5.5.6 | Additional XML parsing vulnerability |
| CVE-2026-26278 | HIGH | 4.5.4, 5.3.6 | XML parsing issue |

**Used by:** LLM provider integrations that parse XML responses  
**Upgrade path:** `pnpm update fast-xml-parser@^4.5.4` (minor version bump, likely non-breaking)  
**Risk if not patched:** Potential remote code execution or data exfiltration via crafted XML

---

## High Vulnerabilities

### jws 3.2.2 / 4.0.0

| CVE | Severity | Fixed In | Description |
|-----|----------|----------|-------------|
| CVE-2025-65945 | HIGH | 3.2.3, 4.0.1 | JWT token handling vulnerability |

**Used by:** Authentication/token generation  
**Upgrade path:** Patch version update  
**Risk if not patched:** Token forgery or authentication bypass

### node-forge 1.3.1

| CVE | Severity | Fixed In | Description |
|-----|----------|----------|-------------|
| CVE-2025-12816 | HIGH | 1.3.2 | Cryptographic implementation issue |
| CVE-2025-66031 | HIGH | 1.3.2 | Additional cryptographic vulnerability |

**Used by:** TLS/certificate operations  
**Upgrade path:** Patch version update  
**Risk if not patched:** Weak cryptographic operations

### @angular/compiler, @angular/core 21.0.3

| CVE | Severity | Fixed In | Description |
|-----|----------|----------|-------------|
| CVE-2026-22610 | HIGH | 21.0.7+ | Framework vulnerability |
| CVE-2026-27970 | HIGH | 21.1.6+ | Core framework issue |
| CVE-2026-32635 | HIGH | 21.2.4+ | Compiler/core vulnerability |

**Used by:** Vendor-provided UI components (not core OpenClaw)  
**Upgrade path:** Minor/patch version update within Angular 21.x  
**Risk if not patched:** UI-level vulnerabilities; lower priority if UI is internal-only

---

## Supply Chain Analysis

### Strengths
- **pnpm workspace:** Strict dependency resolution, shared `node_modules` with symlinks
- **Lock file present:** `pnpm-lock.yaml` ensures reproducible builds
- **Secrets baseline:** `.secrets.baseline` maintained (detect-secrets integration)
- **Pre-commit hooks:** `.pre-commit-config.yaml` with security-related checks

### Weaknesses
- **No integrity verification beyond lock file:** Package signatures not verified
- **No dependency scanning in CI:** No automated CVE checking on PRs
- **Plugin dependencies uncontrolled:** Third-party plugins can bring their own deps
- **No SBOM generation:** Software Bill of Materials not generated

### Recommendations

1. **Add trivy to CI pipeline:**
```yaml
# .github/workflows/security.yml
- name: Dependency scan
  uses: aquasecurity/trivy-action@master
  with:
    scan-type: 'fs'
    severity: 'CRITICAL,HIGH'
    exit-code: '1'
```

2. **Enable pnpm audit in CI:**
```yaml
- name: pnpm audit
  run: pnpm audit --audit-level high
```

3. **Generate SBOM:**
```bash
trivy fs --format cyclonedx --output sbom.json .
```

4. **Consider Renovate or Dependabot** for automated dependency update PRs

---

## Dependency Statistics

### Direct Dependencies (from root package.json)
- **Runtime dependencies:** ~30-40 packages
- **Dev dependencies:** ~15-20 packages
- **Total transitive (estimated from lock file):** 1,000+ packages

### Key Runtime Dependencies
| Package | Version | Purpose | Security Notes |
|---------|---------|---------|----------------|
| esbuild | latest | Build tool | Low risk (build-time only) |
| vitest | latest | Test framework | Low risk (dev-time only) |
| zod | latest | Schema validation | Positive (input validation) |
| ws | latest | WebSocket | Check for updates regularly |
| jiti | latest | Plugin loader | Executes arbitrary code by design |
| tsx | latest | TypeScript execution | Development utility |
| oxlint | latest | Linter | Build-time only |

### Workspace Packages
The monorepo contains multiple workspace packages under:
- `src/` — Core gateway functionality
- `extensions/` — 76 channel/provider/tool plugins
- `apps/` — Companion apps (macOS, iOS, Android, Web)
- `Swabble/` — iOS app (Swift)

Each workspace package may have its own dependencies managed by pnpm.

---

## Medium/Low CVE Summary

10 MEDIUM and 8 LOW severity CVEs were detected across transitive dependencies. These typically involve:
- Regex denial of service (ReDoS) in parsing libraries
- Information disclosure in debug output
- Minor cryptographic implementation weaknesses

Full details available in `tool-scan-results/trivy/trivy-results.json`.

---

## Action Items

| Priority | Action | Effort |
|----------|--------|--------|
| P0 | Update fast-xml-parser to ≥4.5.4 | Low |
| P0 | Update node-forge to ≥1.3.2 | Low |
| P0 | Update jws to ≥4.0.1 | Low |
| P1 | Update @angular/* to latest 21.x | Medium |
| P1 | Add dependency scanning to CI | Low |
| P2 | Generate and publish SBOM | Low |
| P2 | Evaluate Renovate/Dependabot adoption | Low |
| P3 | Audit plugin dependency isolation | Medium |
