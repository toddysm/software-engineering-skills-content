# Dependency Audit — Agent Governance Toolkit

**Scan date:** 2026-04-26
**Scanner:** Trivy 0.69.3 (filesystem mode, vuln + secret + misconfig)
**Coverage:** Python (`requirements*.txt`, `pyproject.toml`); npm and Go module manifests detected by Trivy.

> **Not yet scanned in this run:** .NET (`dotnet list package --vulnerable`), Rust (`cargo audit`), Go (`govulncheck`), Node.js (`npm audit`). Manual run commands are documented in [detailed-security-analysis.md](detailed-security-analysis.md) §"Tools skipped".

---

## 1. Vulnerable dependencies (Trivy)

| Package | Installed | Fixed | Advisory | Severity | Manifest |
|---|---|---|---|---|---|
| pypdf | 6.7.5 | 6.10.2 | CVE-2026-31826 | MEDIUM | `packages/agent-os/modules/caas/requirements.txt` |
| pypdf | 6.7.5 | 6.9.1 | CVE-2026-33123 | MEDIUM | (same) |
| pypdf | 6.7.5 | 6.9.2 | CVE-2026-33699 | MEDIUM | (same) |
| pypdf | 6.7.5 | 6.10.0 | CVE-2026-40260 | MEDIUM | (same) |
| pypdf | 6.7.5 | 6.10.2 | GHSA-4pxv-j86v-mhcw | MEDIUM | (same) |
| pypdf | 6.7.5 | 6.10.2 | GHSA-7gw9-cf7v-778f | MEDIUM | (same) |
| pypdf | 6.7.5 | 6.10.1 | GHSA-jj6c-8h6c-hppx | MEDIUM | (same) |
| pypdf | 6.7.5 | 6.10.2 | GHSA-x284-j5p8-9c5p | MEDIUM | (same) |
| streamlit | 1.41.0 | 1.54.0 | CVE-2026-33682 | MEDIUM | `packages/agent-os/modules/scak/requirements.txt` |

**Total:** 9 MEDIUM advisories across 2 distinct packages.
**No CRITICAL or HIGH dependency findings** were reported.

### Reachability

- `pypdf` is consumed by `caas/` (Compliance-as-a-Service module) for PDF parsing. The vulnerable functions (PDF object stream parsing, font handling) are reached when AGT processes user-supplied PDFs in compliance workflows. Reachable.
- `streamlit` is the demo dashboard runtime in `scak/`. Reachable when the dashboard is deployed.

Both should be patched in the next release. Bumping is straightforward — see [remediation-guide.md](remediation-guide.md) R4 and R5.

---

## 2. Dependency manifests inventoried

### Python `requirements*.txt` (20+)

```
demo/governance-dashboard/requirements.txt
examples/maf-integration/01-loan-processing/python/requirements.txt
examples/maf-integration/02-customer-service/python/requirements.txt
examples/maf-integration/03-healthcare/python/requirements.txt
examples/maf-integration/04-it-helpdesk/python/requirements.txt
examples/maf-integration/05-devops-deploy/python/requirements.txt
packages/agent-compliance/examples/requirements.txt
packages/agent-os/examples/customer-service/requirements.txt
packages/agent-os/examples/github-reviewer/requirements.txt
packages/agent-os/examples/healthcare-hipaa/requirements.txt
packages/agent-os/examples/legal-review/requirements.txt
packages/agent-os/examples/self-evaluating/requirements.txt
packages/agent-os/examples/slack-compliance/requirements.txt
packages/agent-os/examples/sql-agent/requirements.txt
packages/agent-os/modules/atr/requirements.txt
packages/agent-os/modules/caas/requirements.txt          ← VULN-004
packages/agent-os/modules/cmvk/requirements.txt
packages/agent-os/modules/cmvk/requirements-dev.txt
packages/agent-os/modules/mute-agent/requirements.txt
packages/agent-os/modules/mute-agent/requirements-dev.txt
…
packages/agent-os/modules/scak/requirements.txt          ← VULN-005
```

### Python `pyproject.toml` (20+ integrations)

All under `packages/agentmesh-integrations/` — `langchain-agentmesh`, `langgraph-trust`, `llamaindex-agentmesh`, `crewai-agentmesh`, `haystack-agentmesh`, `openai-agents-agentmesh`, `openai-agents-trust`, `pydantic-ai-governance`, `adk-agentmesh`, `aps-agentmesh`, `a2a-protocol`, `mcp-trust-proxy`, `audit-accountability-export`, `nostr-wot`, `agentmesh-avp`, `template-agentmesh`, `flowise-agentmesh`, `openshell-skill`, `sb-runtime-skill`, `langgraph-trust`, `scopeblind-protect-mcp`.

These packages declare ranges (not pins) for upstream agent frameworks. Trivy reported no vulnerabilities against the resolved versions; recommend running `pip-audit -r <each manifest>` in CI as a defense-in-depth check.

### Other ecosystems

- **.NET:** `agent-governance-dotnet/AgentGovernance.sln`. **Not scanned this run.** Run `cd agent-governance-dotnet && dotnet list package --vulnerable --include-transitive`.
- **Rust:** `agent-governance-rust/Cargo.toml` workspace (`agentmesh`, `agentmesh-mcp`). **Not scanned this run.** Run `cargo audit`.
- **Go:** `agent-governance-golang/go.mod` plus per-module manifests. **Not scanned this run.** Run `govulncheck ./...` per module.
- **TypeScript / npm:** `agent-governance-typescript/package.json`, `packages/agent-os-vscode/package.json`. **Not scanned this run.** Run `npm audit --audit-level=high`.

---

## 3. Supply-chain risk observations

### 3.1 Lock files

| Ecosystem | Lock file | Status |
|---|---|---|
| Python | (no `requirements.lock` / `poetry.lock` at top level) | ⚠️ No global lock file. Each `requirements*.txt` is the de-facto pin. |
| npm | `agent-governance-typescript/package-lock.json`, `packages/agent-os-vscode/package-lock.json` | ✅ Committed |
| Cargo | `agent-governance-rust/Cargo.lock` | ✅ Committed |
| Go | `agent-governance-golang/go.sum` | ✅ Committed |
| .NET | (NuGet lock files not observed at scan root) | ⚠️ Recommend enabling `RestoreLockedMode=true` and committing `packages.lock.json` |

### 3.2 Unpinned external artifacts

The most material supply-chain finding is **unpinned HuggingFace downloads** in `amb/`, `atr/`, and `control-plane/` modules — covered as VULN-001 in the security report.

### 3.3 Postinstall / setup-time code

Reviewed `pyproject.toml` files for `setup.py` shims and entry-point hooks. Nothing unusual: no `install_requires` shell-outs, no postinstall scripts. ESlint/Jest are dev-only in the TS package.

### 3.4 Single-maintainer or typosquat-prone packages

The `packages/agentmesh-integrations/*` directory consumes many third-party agent frameworks (LangChain, LlamaIndex, CrewAI, Haystack, etc.). These are well-known maintained projects. Two integrations consume relatively younger packages — `pydantic-ai-governance` and `flowise-agentmesh` — and should be tracked when their upstream's release cadence changes.

---

## 4. Recommendations

1. **Patch the 2 vulnerable Python packages now** (R4, R5).
2. **Add per-ecosystem CI gates** (R13) so that `dotnet list package --vulnerable`, `cargo audit`, `govulncheck`, `npm audit`, and `pip-audit` run on every PR.
3. **Add Trivy in `--exit-code 1` mode for HIGH/CRITICAL** to fail builds on new high-severity findings.
4. **Generate an SBOM** during release (`syft dir:. -o cyclonedx-json > sbom.json`) and attach it to the published artifact. The repo already publishes Microsoft-signed releases; an SBOM is the next natural step.
5. **Enable Dependabot / Renovate** for all manifests (Python, npm, Cargo, Go, NuGet) if not already.

---

## 5. Verification commands

```sh
# Python (covered by Trivy + pip-audit)
.venv/bin/pip install pip-audit
for r in $(find /Users/toddysm/Documents/Development/agent-governance-toolkit \
            -name "requirements*.txt" -not -path "*/node_modules/*" -not -path "*/.venv/*"); do
  echo "== $r =="
  .venv/bin/pip-audit -r "$r" --format json
done

# .NET
cd /Users/toddysm/Documents/Development/agent-governance-toolkit/agent-governance-dotnet
dotnet restore && dotnet list package --vulnerable --include-transitive

# Rust
cd /Users/toddysm/Documents/Development/agent-governance-toolkit/agent-governance-rust
cargo install cargo-audit --locked
cargo audit --json

# Go
cd /Users/toddysm/Documents/Development/agent-governance-toolkit/agent-governance-golang
go install golang.org/x/vuln/cmd/govulncheck@latest
$(go env GOPATH)/bin/govulncheck ./...

# npm
cd /Users/toddysm/Documents/Development/agent-governance-toolkit/agent-governance-typescript
npm ci && npm audit --json --audit-level=high
```

---

*End of dependency audit.*
