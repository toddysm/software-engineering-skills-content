# Agent Governance Toolkit — Codebase Analysis Output

**Analyzed project:** `/Users/toddysm/Documents/Development/agent-governance-toolkit` (v3.2.2, branch `main`)
**Analysis run:** `20260426_154739`
**Skill:** `codebase-architecture-analyst`

## Start here

| Document | Purpose |
|---|---|
| [documentation.md](documentation.md) | **Master report** — executive summary, layout, architecture, tech stack |
| [visuals/detailed-architecture.md](visuals/detailed-architecture.md) | Mermaid architecture diagrams |
| [dependencies/dependency-graph.html](dependencies/dependency-graph.html) | **Interactive** force-directed dependency graph (open in browser) |
| [security/detailed-security-analysis.md](security/detailed-security-analysis.md) | **Detailed security report** — findings, tools, methodology |
| [security/remediation-guide.md](security/remediation-guide.md) | Prioritized fixes with code examples |
| [security/attack-surface-map.md](security/attack-surface-map.md) | Entry points, trust boundaries, defensive controls |
| [security/dependency-audit.md](security/dependency-audit.md) | Dependency CVE audit |
| [interactive/query-examples.md](interactive/query-examples.md) | How to query the dependency database |

## Auto-generated views

| Document | Purpose |
|---|---|
| [analysis/architecture-overview.md](analysis/architecture-overview.md) | Plain-English architecture summary |
| [analysis/components-guide.md](analysis/components-guide.md) | How components relate |
| [analysis/security-overview.md](analysis/security-overview.md) | Security overview (pattern-level) |
| [analysis/technology-decisions.md](analysis/technology-decisions.md) | Technology choices |

## Raw data

| Path | Description |
|---|---|
| [source-files/file-inventory.json](source-files/file-inventory.json) | 2,078 files with purpose, exports, classes, complexity |
| [source-files/file-analysis/](source-files/file-analysis/) | Per-file JSON analysis |
| [source-files/documentation-map.json](source-files/documentation-map.json) | Extracted docstrings & comments |
| [source-files/function-catalog.json](source-files/function-catalog.json) | All functions/classes |
| [dependencies/dependency-graph.json](dependencies/dependency-graph.json) | Module-level imports |
| [dependencies/function-dependencies.json](dependencies/function-dependencies.json) | Function-level usage |
| [dependencies/impact-analysis.json](dependencies/impact-analysis.json) | "What affects what" |
| [dependencies/circular-dependencies.json](dependencies/circular-dependencies.json) | Cycle detection (none found) |
| [security/vulnerability-report.json](security/vulnerability-report.json) | Machine-readable findings |
| [security/security-patterns.json](security/security-patterns.json) | Built-in pattern analyzer output |
| [security/tool-scan-results/](security/tool-scan-results/) | Raw bandit / detect-secrets / trivy output |

## Headline metrics

- **2,078 source files** · 8 languages · ≈530k LOC (217k Python)
- **0 critical security findings** · **3 HIGH** (HF download pinning, Dockerfile root, K8s securityContext) · **7 MEDIUM**
- **9 MEDIUM dependency CVEs** in 2 packages (`pypdf` 6.7.5, `streamlit` 1.41.0)
- **0 circular dependencies** at module level
- **127 detect-secrets findings** — all reviewed; none are verified live credentials

See [documentation.md](documentation.md) for the full executive summary.
