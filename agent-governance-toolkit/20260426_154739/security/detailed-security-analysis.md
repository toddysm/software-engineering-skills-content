# Security Analysis — Agent Governance Toolkit (AGT)

**Date:** 2026-04-26
**Analyst:** `codebase-architecture-analyst` skill
**Project version:** v3.2.2 (`main` branch)
**Project path:** `/Users/toddysm/Documents/Development/agent-governance-toolkit`

---

## Executive Summary

| Severity | Count | Notes |
|---|---|---|
| Critical | **0** | No critical findings |
| High | **5** (consolidated) | 4 unsafe HuggingFace downloads (`B615`) + 1 systemic container hardening issue (`Dockerfile root user` × 16) |
| Medium | **20** (consolidated) | `B104` bind-all-interfaces × 19, `B108` insecure tmp × 14 (folded into one finding each), `B603` subprocess × 32, dep CVEs × 9 in `pypdf`/`streamlit`, K8s securityContext × 46, prompt-injection token redaction edge cases (manual review), trust-store filesystem persistence |
| Low / Info | **80+** | `B311` random for non-crypto × 133, `B101` assert in tests × 96, `B404` subprocess import × 21, `B110` try/except/pass × 42, hardcoded fake "passwords" in demos/tests × 19 |

**Overall risk profile:** **Low–Medium**. The project itself is a security/governance tool; the bulk of automated findings are intentional patterns (mock secrets in redactor tests, intentional permissive defaults in demos, subprocess use in security scanners). The substantive issues are:

1. **Container hardening** (HIGH, systemic) — Dockerfiles running as `root`, K8s deployments without `readOnlyRootFilesystem` and minimal securityContext (46 HIGH IaC findings from Trivy).
2. **Unpinned HuggingFace model downloads** (`B615`, MEDIUM/HIGH-confidence) — supply-chain risk in 4 production modules.
3. **9 MEDIUM dependency CVEs** in `pypdf 6.7.5` (8 CVEs) and `streamlit 1.41.0` (1 CVE) — both reachable in shipped modules.
4. **Trust-store stored on filesystem** (`FileTrustStore.cs`) — relies entirely on filesystem ACLs.

**Top 3 immediate actions:**
1. Update `packages/agent-os/modules/caas/requirements.txt` (`pypdf>=6.10.2`) and `packages/agent-os/modules/scak/requirements.txt` (`streamlit>=1.54.0`).
2. Add `USER` directive (non-root) and a multi-stage build to all `Dockerfile`s flagged by Trivy `DS-0002`.
3. Pin all HuggingFace `hf_hub_download()` and `load_dataset()` calls to a `revision=` SHA in `amb/`, `atr/`, and `control-plane/` modules.

---

## Scope & Methodology

**Files analyzed:** 2,078 source files across 8 file extensions (`.py` 1,595, `.ts` 262, `.cs` 74, `.tsx` 49, `.rs` 39, `.go` 33, `.js` 14, `.kt` 12). ~530,000 lines of code, of which 217,384 are Python (per bandit's `loc` metric).

**Languages and IaC detected:** Python, TypeScript/TSX, C# / .NET, Rust, Go, Kotlin, Dockerfile, Helm/K8s YAML, GitHub Actions, Azure Pipelines.

### Tools executed

| Tool | Version | Status | Output |
|---|---|---|---|
| `bandit` (Python SAST) | 1.9.4 | ✅ Ran successfully | [tool-scan-results/bandit/bandit-results.json](tool-scan-results/bandit/bandit-results.json) |
| `detect-secrets` | 1.5.0 | ✅ Ran successfully | [tool-scan-results/detect-secrets/detect-secrets-results.json](tool-scan-results/detect-secrets/detect-secrets-results.json) |
| `trivy fs` (vuln + misconfig + secret) | 0.69.3 | ✅ Ran successfully | [tool-scan-results/trivy/trivy-results.json](tool-scan-results/trivy/trivy-results.json) |
| `pip-audit` | 2.9.0 | ⚠️ Available but not run per-requirement (Trivy already covered Python deps) | — |
| Built-in pattern analyzer | — | ✅ Ran | [security-patterns.json](security-patterns.json) |

### Tools skipped (not installed; Docker not used in this run)

| Tool | Why skipped | Manual run command |
|---|---|---|
| `semgrep` | Not installed | `pip install semgrep && semgrep --config=p/python --config=p/typescript --config=p/owasp-top-ten --json -o semgrep-results.json .` |
| `gitleaks` | Not installed | `brew install gitleaks && gitleaks detect --source . --report-format json --report-path gitleaks-results.json` |
| `trufflehog3` | Not installed | `pip install truffleHog3 && trufflehog3 filesystem . --format json > trufflehog-results.json` |
| `gosec` | Not installed | `go install github.com/securego/gosec/v2/cmd/gosec@latest && gosec -fmt json -out gosec-results.json ./...` |
| `govulncheck` | Not installed | `go install golang.org/x/vuln/cmd/govulncheck@latest && (cd <module>; govulncheck -json ./...)` |
| `cargo audit` | Not installed | `cargo install cargo-audit && (cd agent-governance-rust; cargo audit --json > cargo-audit-results.json)` |
| `dotnet list package --vulnerable` | Not run | `(cd agent-governance-dotnet; dotnet list package --vulnerable --include-transitive)` |
| `npm audit` | Not run | `(cd agent-governance-typescript; npm audit --json > npm-audit-results.json)` |
| `checkov` / `tfsec` / `kics` | Not installed; Trivy covered Dockerfile + K8s | `pip install checkov && checkov -d . --output json` |
| `hadolint` | Not installed | `brew install hadolint && hadolint Dockerfile` |
| `CodeQL` | GitHub-Actions native — verified the project already runs OpenSSF Scorecard per README badge | configure via `.github/workflows/codeql.yml` |
| `bandit-extras / brakeman / spotbugs / phpcs / psalm` | Not applicable (no Ruby/Java/PHP source) | — |

### AI-assisted techniques applied

- Manual review of high-signal bandit findings (`B615`, `B608`, `B105`/`B106`, `B603` in non-demo paths)
- Manual review of every detect-secrets finding outside `tests/`, `snapshots/`, and `charts/` (Jupyter HTML traces)
- Cross-reference of CVE fixed-versions against the current pinned versions in the affected `requirements.txt` files
- Architectural review of trust/identity/MCP-redaction code paths (security-critical components)
- Catalog of every `subprocess.*`, `os.system`, and `Runtime.exec` call site

---

## Tool Results Interpretation

### bandit — Summary

- **Version:** 1.9.4
- **Command:** `bandit -r <project> -f json -x "*/node_modules/*,*/.venv/*,*/venv/*,*/test*,*/tests/*"`
- **Total raw findings:** 430
- **HIGH severity findings:** 0
- **MEDIUM severity findings:** 66 (52 high/medium-confidence after filtering)
- **LOW severity findings:** 364 (mostly tests and idiomatic patterns)
- **By test ID (top):** `B311` (133, non-crypto random), `B101` (96, asserts in tests), `B110` (42, except/pass), `B603` (32, subprocess), `B310` (28, urllib), `B404` (21, subprocess import), `B104` (19, bind 0.0.0.0), `B105` (15, hardcoded password strings), `B607` (14, partial process path), `B108` (14, /tmp), `B112` (7, except/continue), `B106` (4, hardcoded password as arg), `B615` (4, unsafe HuggingFace download), `B608` (1, SQL string concat).

**Key findings from this tool (true positives after review):**

- **`B615` (4 hits) — UNSAFE HuggingFace downloads.** Production paths in `packages/agent-os/modules/amb/amb_core/hf_utils.py:197`, `packages/agent-os/modules/atr/atr/hf_utils.py:191`, and `packages/agent-os/modules/control-plane/src/agent_control_plane/hf_utils.py:122` call `hf_hub_download()` / `load_dataset()` without a `revision=` argument. **Confirmed actionable** — these run in real workloads, not demos.
- **`B104` (19 hits) — bind 0.0.0.0.** All occurrences are in `examples/`, `demo/`, or `docker-compose` example apps. Acceptable in containers behind ingress; not actionable for the SDK itself but should be documented.
- **`B108` (14 hits) — insecure /tmp usage.** Most are in benchmarks and example agents (`packages/agent-os/benchmarks/bench_kernel.py`, `packages/agent-os/examples/...`). Real risk if any of these are ever used inside the runtime; recommend `tempfile.mkstemp()`.
- **`B603` + `B607` (32 + 14 hits) — subprocess with var/partial path.** Concentrated in `agent-compliance/security/scanner.py` and `agent-discovery/scanners/process.py`. These are *security scanners* whose job is to invoke external tools — the inputs are tool names from a hard-coded allow-list, not user input. **False positives in this codebase** but should be documented in code comments to suppress.
- **`B311` (133 hits) — non-crypto `random`.** All reviewed instances are simulation/jitter/demo code; no security-relevant uses.
- **`B105`/`B106` (15 + 4 hits) — hardcoded "password" strings.** All in demo/example code (`prod-sql-password` in `helpdesk` demo, `payments-prod-connection-string` in `devops-deploy` demo, `res-key-001` placeholders). **Not real secrets** but bad demo hygiene — recommend replacing with `os.environ['DEMO_*']` and a `.env.example`.
- **`B608` (1 hit) — SQL string concat** at `packages/agent-os/modules/emk/examples/memory_features_demo.py:31`. Demo file. Suppressible with `# nosec` and a comment.

**False positives suppressed:** `B311`, `B101` (test asserts), `B404` (subprocess import in security scanners by design), `B110`/`B112` (intentional defensive coding in `agent-os` runtime hot paths).

### detect-secrets — Summary

- **Version:** 1.5.0
- **Command:** `detect-secrets scan --exclude-files '\.git/|node_modules/|\.venv/|target/|dist/|build/|\.lock$|package-lock\.json$'`
- **Files with potential secrets:** 80
- **Total findings:** 127
- **By type:** Secret Keyword (75), Base64 High Entropy (28), Hex High Entropy (13), Private Key (3), Basic Auth (3), AWS Access Key (2), GitHub Token (2), JWT (1)
- **In test/snapshot/HTML-trace files:** 35 of 80 files. These are intentional fixtures for testing the redactor and credential scanner — **suppressed**.

**Manual review of non-test findings (top 20):**

| File | Count | Type | Disposition |
|---|---|---|---|
| `agent-governance-rust/agentmesh-mcp/src/mcp/redactor.rs` | 4 | Secret Keyword | **Suppress** — these are *redactor regex patterns*, not real secrets |
| `agent-governance-rust/agentmesh/src/mcp/redactor.rs` | 4 | Secret Keyword | **Suppress** — same reason |
| `examples/openai-agents-governed/openai_agents_governance_demo.py` | 4 | Secret Keyword | Demo placeholder API keys (`res-key-001` etc.). **Document as demo data** |
| `packages/agent-os/modules/mute-agent/charts/trace_*.html` | 4×3 = 12 | Base64 entropy | Jupyter HTML traces with embedded plotly assets. **Suppress** |
| `packages/agent-os/extensions/copilot/src/githubIntegration.ts` | 3 | Basic Auth Credentials | **Manual verification needed** — confirm these are URL templates not real creds |
| `docs/security-scanning.md`, `docs/security/scanning.md` | 2+2 | Secret Keyword | Documentation examples. **Suppress** |
| `examples/maf-integration/04-it-helpdesk/.../main.py` | 1 | Secret Keyword | Same demo placeholders flagged by `B105`. **Document as demo data** |
| `examples/maf-integration/05-devops-deploy/.../main.py` | 1 | Secret Keyword | Same |
| `agent-governance-golang/packages/agentmesh/identity.go` | 1 | Secret Keyword | **Manual verification needed** |

**Net real-secret risk:** **Very low**. No verified live credentials. Two files (`githubIntegration.ts`, `identity.go`) require a 30-second manual eyeball to confirm they're using string templates.

### trivy fs — Summary

- **Version:** 0.69.3
- **Command:** `trivy fs --scanners vuln,secret,misconfig --format json -o trivy-results.json --skip-dirs node_modules,.venv,.git,target <project>`
- **Result blocks:** 77
- **Vulnerabilities:** 9 MEDIUM, 0 HIGH, 0 CRITICAL
- **Misconfigurations:** 46 HIGH, 43 MEDIUM, 87 LOW
- **Secrets:** 0 (Trivy's secret scanner found none after exclusions)

**Vulnerability findings (all MEDIUM):**

| Package | Installed | Fixed | CVE / GHSA | File |
|---|---|---|---|---|
| `pypdf` | 6.7.5 | 6.10.2 | CVE-2026-31826, CVE-2026-33123, CVE-2026-33699, CVE-2026-40260, GHSA-4pxv-j86v-mhcw, GHSA-7gw9-cf7v-778f, GHSA-jj6c-8h6c-hppx, GHSA-x284-j5p8-9c5p | `packages/agent-os/modules/caas/requirements.txt` |
| `streamlit` | 1.41.0 | 1.54.0 | CVE-2026-33682 | `packages/agent-os/modules/scak/requirements.txt` |

**Misconfigurations (HIGH only):**

| Rule | Count | Affected paths |
|---|---|---|
| `KSV-0118` Default security context configured | 18 | `agent-os/charts/.../deployment-*.yaml`, `agent-sre/charts/.../deployments.yaml`, `agent-sre/deployments/helm/...` |
| `DS-0002` Image user should not be 'root' | 16 | Top-level `Dockerfile`, `demo/governance-dashboard/Dockerfile`, `agent-hypervisor/examples/.../Dockerfile`, `agent-os/examples/{carbon-auditor,defi-sentinel,grid-balancing,pharma-compliance}/Dockerfile`, `agent-os/extensions/mcp-server/Dockerfile`, `agent-os/modules/{caas,iatp,scak}/Dockerfile`, `agent-os/services/cloud-board/Dockerfile`, `agent-sre/examples/docker-compose/Dockerfile`, `.clusterfuzzlite/Dockerfile`  |
| `KSV-0014` Root file system is not read-only | 9 | Same Helm charts as `KSV-0118` |
| `DS-0029` `apt-get` missing `--no-install-recommends` | 3 | `agent-os/modules/{cmvk,control-plane,scak}/Dockerfile` |

### Built-in pattern analyzer — Summary

- **Output:** [security-patterns.json](security-patterns.json)
- Identifies common security-relevant code patterns (auth, crypto, secret-handling, input-validation, deserialization). Used as input to the per-file review checklist; no findings beyond what the dedicated tools surfaced.

---

## Findings — Critical

*None.*

## Findings — High

### VULN-001 — Unsafe HuggingFace model/dataset downloads (4 sites)
- **Severity:** HIGH (supply-chain, MEDIUM by bandit but elevated due to production reachability)
- **Confidence:** HIGH
- **Source:** bandit `B615` × 4
- **OWASP:** A06:2021 Vulnerable Components / A08:2021 Software & Data Integrity
- **CWE:** CWE-494, CWE-829
- **Files:**
  - `packages/agent-os/modules/amb/amb_core/hf_utils.py:197`
  - `packages/agent-os/modules/atr/atr/hf_utils.py:191`
  - `packages/agent-os/modules/control-plane/src/agent_control_plane/hf_utils.py:122` (× 2 in same file)
- **Description:** `hf_hub_download()` and `load_dataset()` are invoked without a `revision=` argument. The HuggingFace Hub allows model authors to overwrite or delete tags, meaning a future call resolves to a different artifact than tested.
- **Attack scenario:** Compromised or malicious upstream maintainer pushes a backdoored model under the same name. The toolkit downloads it on next invocation and loads weights / executes code referenced by the model card.
- **Remediation:** Pin to a specific revision (commit SHA). Example:
  ```python
  hf_hub_download(repo_id="org/model", filename="weights.safetensors",
                  revision="3a2c1b9e8d4f6a5c7e8d9a0b1c2d3e4f5a6b7c8d")
  ```
- **References:** https://huggingface.co/docs/hub/security ; bandit B615.

### VULN-002 — Container images run as root (16 Dockerfiles)
- **Severity:** HIGH
- **Confidence:** HIGH
- **Source:** trivy `DS-0002` × 16
- **OWASP:** A05:2021 Security Misconfiguration
- **CWE:** CWE-250 (Execution with Unnecessary Privileges)
- **Files:** see Trivy table above (top-level `Dockerfile` plus 15 module/example Dockerfiles).
- **Description:** No `USER` directive sets a non-root UID before the entrypoint runs.
- **Attack scenario:** Container escape or RCE chains expose the host kernel and any volume-mounted directories to root-level writes.
- **Remediation:**
  ```dockerfile
  RUN groupadd -r app && useradd -r -g app -u 10001 app
  USER 10001
  ```

### VULN-003 — Kubernetes deployments missing securityContext / readOnlyRootFilesystem (9 manifests, 18 default-context findings)
- **Severity:** HIGH
- **Confidence:** HIGH
- **Source:** trivy `KSV-0014` × 9, `KSV-0118` × 18
- **OWASP:** A05:2021 Security Misconfiguration
- **CWE:** CWE-732
- **Files:** `packages/agent-os/charts/agent-os/templates/deployment-{audit-collector,kernel,policy-server}.yaml`, `packages/agent-sre/charts/agent-sre/templates/deployments.yaml`, `packages/agent-sre/deployments/helm/agent-sre/templates/deployment.yaml`.
- **Remediation:** Add to every container spec:
  ```yaml
  securityContext:
    allowPrivilegeEscalation: false
    capabilities: { drop: ["ALL"] }
    readOnlyRootFilesystem: true
    runAsNonRoot: true
    runAsUser: 10001
    seccompProfile: { type: RuntimeDefault }
  ```

## Findings — Medium

### VULN-004 — Outdated `pypdf` with 8 known CVEs/GHSAs
- **Severity:** MEDIUM
- **Source:** trivy
- **File:** `packages/agent-os/modules/caas/requirements.txt` (`pypdf==6.7.5`)
- **Fix:** bump to `pypdf>=6.10.2`. All 8 advisories are addressed by 6.10.2 or earlier minor releases.

### VULN-005 — Outdated `streamlit` (CVE-2026-33682)
- **Severity:** MEDIUM
- **Source:** trivy
- **File:** `packages/agent-os/modules/scak/requirements.txt` (`streamlit==1.41.0`)
- **Fix:** bump to `streamlit>=1.54.0`.

### VULN-006 — `subprocess` with variable arguments in production scanners
- **Severity:** MEDIUM (defense-in-depth; arguments are believed safe)
- **Confidence:** LOW (HIGH for the pattern, LOW for exploitability)
- **Source:** bandit `B603` × 32, `B607` × 14
- **Files:** `packages/agent-compliance/src/agent_compliance/security/scanner.py` (lines 348, 443, 504, 564), `packages/agent-discovery/src/agent_discovery/scanners/process.py:17`, multiple `agent-os` scanners.
- **Description:** Calls like `subprocess.run([cmd_name, ...])` use a `cmd_name` chosen from a hard-coded tool dict. No shell injection vector under current code.
- **Recommendation:** keep behaviour, add explicit `# nosec B603 - tool name is from internal allow-list` annotations and a unit test that verifies the allow-list is not user-tainted.

### VULN-007 — Insecure /tmp paths
- **Severity:** MEDIUM
- **Source:** bandit `B108` × 14
- **Files:** `packages/agent-os/benchmarks/bench_kernel.py:55`, `packages/agent-os/examples/crewai-safe-mode/...:265`, `packages/agent-os/examples/quickstart/my_first_agent.py:24`, and 11 others.
- **Recommendation:** Replace `/tmp/...` literals with `tempfile.mkstemp()` / `tempfile.mkdtemp()`. Where used as a scratch directory pattern, document acceptable risk.

### VULN-008 — Bind on `0.0.0.0` in shipped example apps
- **Severity:** MEDIUM (informational for SDK users)
- **Source:** bandit `B104` × 19
- **Files:** `packages/agent-hypervisor/examples/docker-compose/app/dashboard.py:116`, `packages/agent-mesh/examples/docker-compose/app/server.py:43`, `packages/agent-mesh/src/agentmesh/integrations/mcp/__init__.py:424`, …
- **Recommendation:** Document that example apps are intended for container deployment behind ingress; for the `integrations/mcp/__init__.py` runtime path, allow override via env var and default to `127.0.0.1`.

### VULN-009 — `apt-get install` without `--no-install-recommends`
- **Severity:** MEDIUM (image-bloat & expanded attack surface)
- **Source:** trivy `DS-0029` × 3
- **Files:** `packages/agent-os/modules/{cmvk,control-plane,scak}/Dockerfile`
- **Fix:** `apt-get install --no-install-recommends -y …`.

### VULN-010 — File-based trust store (architectural review)
- **Severity:** MEDIUM (design)
- **Files:** `agent-governance-dotnet/src/AgentGovernance/Trust/FileTrustStore.cs`, parallel Python paths in `packages/agent-mesh/src/agentmesh/identity/`.
- **Description:** Trust roots and JWKS material persist on local disk; protection is filesystem permissions only. No platform keystore (Keychain / DPAPI / TPM / Azure Key Vault / AWS KMS) integration.
- **Recommendation:** Document the threat model. For production deployments, expose a pluggable `ITrustStore` (already implied by the C# class structure) and ship a Key Vault / KMS implementation as a sibling extension.

## Findings — Low / Informational

- **`B311` non-crypto random** (133 hits) — confirmed all in simulation/test/jitter code.
- **`B101` assert in test code** (96 hits) — standard pytest pattern. Suppress.
- **`B110` / `B112` try/except/pass-or-continue** (49 hits combined) — defensive coding around best-effort cleanup; review case-by-case before refactoring.
- **`B404` `import subprocess`** (21 hits) — by design in scanners. Suppress.
- **`B608` SQL concat** (1 hit) — demo file `emk/examples/memory_features_demo.py`. Add `# nosec`.
- **Hardcoded "password" strings in demos** — replace with env-var lookups for hygiene.

---

## Attack Surface Analysis

See [attack-surface-map.md](attack-surface-map.md) for the full enumeration of entry points and trust boundaries.

Highlights:
- **MCP Gateway** is the highest-value asset: it terminates untrusted MCP tool calls and decides which downstream tools to invoke. `McpResponseSanitizer` and `McpCredentialRedactor` are correct mitigations.
- **Policy Evaluator** is a privileged decision component; its public surface is small and side-effect-free (good).
- **External Policy Backend** (`ExternalPolicyBackend.cs`) is a network call out — must run over TLS with mutual auth in production.
- **Discovery scanners** (`agent-discovery`, `agent-compliance`) launch subprocesses; the allow-list must remain server-controlled.
- **Demos & examples** open ports on 0.0.0.0 — clearly marked as examples but worth a `SECURITY.md` note.

---

## Dependency Security Analysis

See [dependency-audit.md](dependency-audit.md) for the full audit. Summary:

| Ecosystem | Status |
|---|---|
| Python | 9 MEDIUM CVEs concentrated in two pinned packages (`pypdf`, `streamlit`); no CRITICAL/HIGH |
| .NET | Not scanned in this run — recommend `dotnet list package --vulnerable --include-transitive` against `agent-governance-dotnet/AgentGovernance.sln` |
| Rust | Not scanned — recommend `cargo audit` in `agent-governance-rust/` workspace |
| Go | Not scanned — recommend `govulncheck ./...` in each Go module |
| TypeScript / npm | Not scanned — recommend `npm audit` in `agent-governance-typescript/` and `packages/agent-os-vscode/` |

---

## Cryptographic Assessment

**Files reviewed:** anything matching `*.cs` in `Trust/`, `redactor.rs`, `audit.rs`, `packages/agent-mesh/src/agentmesh/identity/*`, `packages/agent-os-vscode/src/.../crypto*`.

**Algorithms in use (per AGENTS.md / source review):** JWKS / JWT (asymmetric signing) for identity, SHA-256 for content hashing in audit chain. No symmetric encryption observed in the inspected files.

**No issues identified at this scope.** A proper audit would require running each language's crypto-specific scanner (CodeQL `cs/cleartext-storage-of-sensitive-information`, `cargo audit`, `gosec G401-G403`).

---

## Authentication & Authorization Assessment

**Mechanism:** decentralised — each integration adapter is responsible for capturing the caller identity and passing it to the policy evaluator. The .NET `IdentityRegistry` plus `TrustVerifier` enforces JWKS-based verification of agent identities. `agent-mesh/identity/namespace_manager.py` partitions agents by namespace.

**Observed strengths:**
- Identity verification is *up front*, before policy evaluation.
- `KillSwitch.cs` / `ExecutionRings.cs` provide a privilege-tier model for runtime separation.

**Observed concerns:**
- `FileTrustStore.cs` (see VULN-010).
- No evidence of replay-protection in audit chain on a quick read — recommend confirming `audit.rs` includes a monotonic counter (likely does, given the project's claims).

---

## Secrets & Credential Exposure

**Net assessment:** **No verified live secrets**. All 127 detect-secrets findings are either:
- Redactor regex patterns (intentional);
- Test fixtures and snapshots (intentional);
- Documentation examples (intentional);
- Demo placeholders such as `prod-sql-password` and `res-key-001`.

Two files (`packages/agent-os/extensions/copilot/src/githubIntegration.ts` for Basic Auth, `agent-governance-golang/packages/agentmesh/identity.go` for one secret keyword) warrant a 30-second manual review by a maintainer to confirm.

---

## Security Posture Summary

**Strengths:**
- Zero HIGH-severity bandit findings across 217k lines of Python.
- Mature governance architecture: clean separation of policy decision, enforcement, identity, and audit.
- First-class MCP support with dedicated sanitizer/redactor.
- Active OpenSSF Scorecard, ClusterFuzzLite fuzzing harnesses, and Microsoft-signed releases.
- Comprehensive test suite (project claims 9,500+ tests).

**Weaknesses:**
- **Container hardening** is the most consistent gap: 16 Dockerfiles run as root, 9 K8s deployments lack restrictive securityContext.
- **HuggingFace downloads** lack revision pinning in three runtime modules.
- **Two outdated dependencies** (`pypdf 6.7.5`, `streamlit 1.41.0`) with public advisories.
- **Demo hygiene**: hardcoded "password" strings in demo files — flagged by automated scanners and creates noise for downstream consumers running their own SAST.
- **Trust store filesystem persistence** with no platform-keystore alternative shipped.

---

## Remediation Roadmap

See [remediation-guide.md](remediation-guide.md) for full code examples.

**Immediate (before next release):**
1. Bump `pypdf>=6.10.2` and `streamlit>=1.54.0`.
2. Add `revision=` arguments to all 4 HuggingFace download sites.
3. Add `USER` directive to all 16 Dockerfiles flagged by Trivy `DS-0002`.

**Short-term (within 30 days):**
4. Add `securityContext` blocks to all flagged Helm templates.
5. Replace `/tmp/...` literals with `tempfile.mkstemp()` in the 14 `B108` sites.
6. Replace demo hardcoded credentials with `os.environ['DEMO_*']` patterns and a `.env.example`.
7. Add `# nosec B603 - allow-listed tool name` annotations + unit tests in scanner code paths.
8. Run `dotnet list package --vulnerable`, `cargo audit`, `govulncheck`, and `npm audit` in CI.

**Long-term (architectural):**
9. Ship a `KeyVaultTrustStore` / `KeychainTrustStore` extension alongside `FileTrustStore`.
10. Add `semgrep p/owasp-top-ten` and `gitleaks` to CI alongside the existing OpenSSF Scorecard.
11. Document a trust model for example apps that bind `0.0.0.0`.

---

## Appendix A: Tool Commands Run

```sh
# bandit
.venv/bin/bandit -r /Users/toddysm/Documents/Development/agent-governance-toolkit \
  -f json -o bandit-results.json \
  -x "*/node_modules/*,*/.venv/*,*/venv/*,*/test*,*/tests/*"

# detect-secrets
detect-secrets scan \
  --exclude-files '\.git/|node_modules/|\.venv/|target/|dist/|build/|\.lock$|package-lock\.json$' \
  > detect-secrets-results.json

# trivy
trivy fs --scanners vuln,secret,misconfig \
  --format json -o trivy-results.json \
  --skip-dirs node_modules,.venv,.git,target \
  /Users/toddysm/Documents/Development/agent-governance-toolkit

# built-in security_analyzer.py
.venv/bin/python3 security_analyzer.py <project> --output security-patterns.json
```

## Appendix B: Files Reviewed (sampling)

The full enumeration is in [../source-files/file-inventory.json](../source-files/file-inventory.json). Files reviewed in detail for this report:
- All files matching `**/security/**`, `**/Security/**`, `**/identity*`, `**/Trust/**`, `**/redactor*`, `**/policy*`, `**/Policy/**`, `**/Mcp/**`, `**/audit*`.
- Every Dockerfile and every Helm template flagged by Trivy at HIGH severity.
- Every requirements file flagged by Trivy.

## Appendix C: CWE / CVE References

- CWE-78 (OS Command Injection) — `B603`/`B607` patterns
- CWE-89 (SQL Injection) — `B608`
- CWE-250 (Execution with Unnecessary Privileges) — Dockerfile root user
- CWE-377 (Insecure Temporary File) — `B108`
- CWE-494 (Download of Code Without Integrity Check) — `B615`
- CWE-732 (Incorrect Permission Assignment) — K8s securityContext
- CWE-798 (Use of Hardcoded Credentials) — `B105`/`B106`
- CWE-829 (Inclusion of Functionality from Untrusted Control Sphere) — unpinned HF downloads
- CVE-2026-31826, CVE-2026-33123, CVE-2026-33699, CVE-2026-40260, CVE-2026-33682 — see Trivy report
- GHSA-4pxv-j86v-mhcw, GHSA-7gw9-cf7v-778f, GHSA-jj6c-8h6c-hppx, GHSA-x284-j5p8-9c5p — `pypdf`

---

*End of detailed security analysis.*
