# Architecture Analysis — OpenClaw

**Repository:** https://github.com/openclaw/openclaw.git  
**Analysis Date:** 2026-03-18  
**Analyst:** codebase-architecture-analyst  

---

## Project Summary

OpenClaw is a **personal AI assistant platform** that connects 25+ messaging platforms (Discord, Slack, Telegram, WhatsApp, iMessage, etc.) to 20+ LLM providers (OpenAI, Anthropic, Google, xAI, etc.) through a unified WebSocket gateway. It features a two-tier plugin system (channel plugins + provider plugins), an embedded AI agent runtime ("Pi") with 52 skills, and companion apps for macOS, iOS, Android, and web.

---

## Key Metrics

| Metric | Value |
|--------|-------|
| Total source files | 7,838 |
| Primary language | TypeScript (7,085 files) |
| Secondary languages | Swift (605), Kotlin (118), Shell (71) |
| Dependency edges | 20,370 |
| Channel plugins | 25+ |
| Provider plugins | 20+ |
| Agent skills | 52 |
| Extensions total | 76 |
| Circular dependencies | 1 |
| Security findings | 14 (2 CRITICAL, 6 HIGH, 3 MEDIUM, 3 LOW) |

---

## Architecture Overview

```
User Message → Channel Plugin → Gateway → Session Router → Pi Agent → Provider Plugin → LLM API
                                  ↕                          ↕
                            Config/Auth               Tool Execution
                                                     (52 skills)
```

**Key architectural patterns:**
- **Plugin-oriented:** All channels and providers are plugins loaded at runtime via `jiti`
- **Event-driven:** WebSocket gateway at `ws://127.0.0.1:18789` as the control plane
- **Session-based routing:** Messages tagged by channel/user, routed to appropriate provider
- **Monorepo:** pnpm workspace with esbuild compilation, vitest testing, oxlint linting

---

## Output Directory Structure

```
openclaw/20260318_172110/
├── documentation.md              ← This file
│
├── source-files/                 ← File-level analysis
│   ├── file-inventory.json       ← 7,838 files catalogued
│   ├── documentation-map.json    ← Documentation extracted per file
│   ├── function-catalog.json     ← Functions/classes/methods per file
│   └── file-analysis/            ← Individual file analysis results
│
├── dependencies/                 ← Dependency mapping
│   ├── dependency-graph.json     ← 12,136 nodes, 20,370 edges
│   ├── function-dependencies.json ← Function-level usage patterns
│   ├── impact-analysis.json      ← Transitive "what affects what"
│   └── circular-dependencies.json ← 1 circular dependency found
│
├── analysis/                     ← Human-readable reports
│   ├── architecture-overview.md  ← Full system architecture
│   ├── components-guide.md       ← All 76 extensions & core modules
│   ├── technology-decisions.md   ← Rationale for every tech choice
│   └── security-overview.md      ← Security model & trust boundaries
│
├── security/                     ← Vulnerability analysis
│   ├── detailed-security-analysis.md  ← Full narrative security report
│   ├── vulnerability-report.json      ← Machine-readable findings (14 vulns)
│   ├── remediation-guide.md           ← Prioritized fix instructions
│   ├── attack-surface-map.md          ← All input points & trust boundaries
│   ├── dependency-audit.md            ← CVE analysis & supply chain review
│   └── tool-scan-results/
│       ├── detect-secrets/detect-secrets-results.json  ← 7,560 findings
│       ├── njsscan/njsscan-results.json                ← 0 findings
│       └── trivy/trivy-results.json                    ← 37 findings
│
├── visuals/                      ← Mermaid diagrams
│   ├── detailed-architecture.md  ← 6 system architecture diagrams
│   ├── dependency-graphs.md      ← 6 dependency relationship diagrams
│   └── security-model.md         ← 3 security architecture diagrams
│
└── interactive/                  ← Query system
    ├── dependency-query-db.json  ← Pre-computed dependency queries
    └── query-examples.md         ← How to query the dependency data
```

---

## Critical Findings

### Security (Action Required)

1. **2 CRITICAL dependency CVEs** in `fast-xml-parser` 4.5.3 — update to ≥4.5.4
2. **Command injection risk** in bash-tools shell execution
3. **Plugin system** runs arbitrary code without sandboxing
4. **6 additional HIGH severity** code-level findings

See `security/detailed-security-analysis.md` for full details and `security/remediation-guide.md` for fix instructions.

### Architecture

1. **Single circular dependency:** `ui/src/ui/app-settings.ts` ↔ `ui/src/ui/app-chat.ts`
2. **Plugin loader** (`jiti`) has no isolation — any plugin gets full process access
3. **Gateway is a single process** — no horizontal scaling support
4. **Config complexity** — Zod schemas are comprehensive but deeply nested

---

## How to Use This Analysis

1. **New developers:** Start with `analysis/architecture-overview.md` and `analysis/components-guide.md`
2. **Security review:** Start with `security/detailed-security-analysis.md`
3. **Refactoring:** Use `interactive/dependency-query-db.json` to find impact of changes
4. **Technology evaluation:** See `analysis/technology-decisions.md`
5. **Visual understanding:** Open any file in `visuals/` — all diagrams use Mermaid syntax

---

## Tools Used

| Tool | Purpose | Findings |
|------|---------|----------|
| Custom Python analyzers | File inventory, dependency mapping | 7,838 files, 20,370 edges |
| trivy | Dependency CVE scanning | 37 (2 CRITICAL, 17 HIGH) |
| detect-secrets | Secrets detection | 7,560 (mostly false positives) |
| njsscan | Node.js security patterns | 0 |
| AI code review | Manual security analysis | 12 findings (6 HIGH, 3 MEDIUM, 3 LOW) |
