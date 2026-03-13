# Notation Project — Architecture Analysis Documentation

**Project**: [notaryproject/notation](https://github.com/notaryproject/notation) + dependent repositories
**Analysis Date**: 2026-03-12
**Output Directory**: This directory (`20260312_194412/`)
**Analyst**: Automated codebase-architecture-analyst skill

---

## Quick Summary

The **Notation project** is a Go-based CLI tool (`notation`) for signing and verifying OCI artifacts (container images and other content stored in OCI registries) according to the Notary Project specification. It follows a clean **4-tier layered architecture** with strong security properties: no custom crypto, subprocess isolation for key material, and a declarative trust policy model.

**Security Status**: CLEAN — 0 known CVEs, 0 exploitable vulnerabilities found.

---

## Document Map

### Analysis

| Document | Description |
|----------|-------------|
| [analysis/architecture-overview.md](analysis/architecture-overview.md) | **START HERE** — narrative overview of the full architecture, data flows, and technology decisions |
| [analysis/components-guide.md](analysis/components-guide.md) | Component-by-component reference with impact analysis — "what happens if I change X?" |
| [analysis/security-overview.md](analysis/security-overview.md) | One-page security summary — overall posture, key strengths, brief findings list |
| [analysis/technology-decisions.md](analysis/technology-decisions.md) | Why specific technology choices were made (Go, plugin model, trust policy as file, etc.) |

### Security

| Document | Description |
|----------|-------------|
| [security/detailed-security-analysis.md](security/detailed-security-analysis.md) | Full security analysis report — methodology, all findings, attack surfaces, crypto assessment |
| [security/vulnerability-report.json](security/vulnerability-report.json) | Machine-readable findings in JSON (0 CVEs, findings classified) |
| [security/remediation-guide.md](security/remediation-guide.md) | Prioritised step-by-step remediation with before/after code snippets |
| [security/attack-surface-map.md](security/attack-surface-map.md) | Six attack surfaces mapped with mitigations; explicit out-of-scope list (no SQL injection, XSS, etc.) |
| [security/dependency-audit.md](security/dependency-audit.md) | All direct dependencies documented; govulncheck result: **clean** |
| [security/tool-scan-results/gosec-results.json](security/tool-scan-results/gosec-results.json) | Raw gosec output (38 findings) |
| [security/tool-scan-results/govulncheck-results.json](security/tool-scan-results/govulncheck-results.json) | Raw govulncheck output (0 CVEs) |

### Visual Diagrams (Mermaid)

| Document | Description |
|----------|-------------|
| [visuals/detailed-architecture.md](visuals/detailed-architecture.md) | 7 Mermaid diagrams: component tiers, signing flow, verification flow, plugin architecture, trust model, OCI referrers model, envelope selection |
| [visuals/dependency-graphs.md](visuals/dependency-graphs.md) | 5 Mermaid graphs: repo-level deps, package-level deps, signing critical path, verification critical path, external dependency web |
| [visuals/security-model.md](visuals/security-model.md) | 4 Mermaid diagrams: trust boundary map, cryptographic trust chain, verification levels/outcomes, attack surfaces with mitigations |

### Source Files and Dependencies

| Document | Description |
|----------|-------------|
| [source-files/file-inventory.json](source-files/file-inventory.json) | Complete file catalog for all 4 repos with one-line purpose per file |
| [dependencies/dependency-graph.json](dependencies/dependency-graph.json) | Bi-directional dependency graph with package-level detail |

### Interactive Queries

| Document | Description |
|----------|-------------|
| [interactive/dependency-query-db.json](interactive/dependency-query-db.json) | Queryable JSON database of all components, deps, and impact analysis |
| [interactive/query-examples.md](interactive/query-examples.md) | `jq` query examples for exploring the database (security, impact, dependency queries) |

---

## Architecture in Three Paragraphs

The Notation project implements the [Notary Project specification](https://github.com/notaryproject/specifications) in four Go modules arranged as a dependency stack. The **CLI binary** (`notation-cli`) provides the user-facing commands; the **notation-go library** implements the high-level signing and verification logic including trust policy evaluation; the **notation-core-go library** implements the cryptographic envelope formats (JWS and COSE); and the **notation-plugin-framework-go library** defines the subprocess plugin protocol used to keep private key material out of the main process.

Signatures are stored in OCI registries using the OCI v1.1 Referrers API — signatures are separate OCI manifests that reference their subject artifact via a `subject` field. This design means signing doesn't modify the signed artifact's digest. Trust is governed by a **declarative trust policy JSON file** that the user maintains, specifying which certificate identities are trusted for which registry paths and what level of verification to enforce.

Security is design-deep: no custom cryptography (Go standard library throughout), plugin subprocess isolation (private keys never cross into the main process), mandatory certificate chain validation against user-managed trust anchors, and zero dependency CVEs confirmed by `govulncheck`.

---

## Key Numbers

| Metric | Value |
|--------|-------|
| Repositories analysed | 4 |
| Go source files (main repo) | 70 (excl. tests) |
| Architecture tiers | 4 |
| CLI commands | 28 |
| Known CVEs in any dependency | **0** |
| gosec raw findings | 38 |
| Confirmed exploitable findings | **0** |
| False positives (HIGH severity) | 2 |
| Accepted-risk findings (MEDIUM) | 6 |
| Code quality findings (INFO) | 28 |

---

## Repositories Analysed

| Repository | Local Path | Role |
|------------|-----------|------|
| `github.com/notaryproject/notation/v2` | `notation/` | CLI binary |
| `github.com/notaryproject/notation-go` | `notation/deps/notation-go/` | High-level library |
| `github.com/notaryproject/notation-core-go` | `notation/deps/notation-core-go/` | Crypto core |
| `github.com/notaryproject/notation-plugin-framework-go` | `notation/deps/notation-plugin-framework-go/` | Plugin SDK |

Base path: `/Users/toddysm/Documents/Development/notaryproject/`
