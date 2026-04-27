# Remediation Guide — Agent Governance Toolkit

Prioritized remediations for findings in [detailed-security-analysis.md](detailed-security-analysis.md). Items are ordered Critical → High → Medium → Low.

---

## Priority 1 — High (do before next release)

### R1. Pin HuggingFace downloads to a revision (VULN-001)

**Files:**
- `packages/agent-os/modules/amb/amb_core/hf_utils.py:197`
- `packages/agent-os/modules/atr/atr/hf_utils.py:191`
- `packages/agent-os/modules/control-plane/src/agent_control_plane/hf_utils.py:122` (two call sites)

**Fix pattern:**

```python
# BEFORE
path = hf_hub_download(repo_id=repo_id, filename=filename)
ds = load_dataset(name)

# AFTER — accept revision through the function and require it for production paths
def download_model(repo_id: str, filename: str, revision: str) -> str:
    if not revision or len(revision) < 7:
        raise ValueError("revision (commit SHA) is required for HuggingFace downloads")
    return hf_hub_download(repo_id=repo_id, filename=filename, revision=revision)
```

Add a config field (e.g., `models.<name>.revision`) so revisions are explicit per deployment, and fail-closed if missing.

### R2. Add non-root USER to all Dockerfiles (VULN-002)

Apply this pattern to every Dockerfile flagged in the report:

```dockerfile
FROM python:3.12-slim AS base

# install deps as root
RUN apt-get update && apt-get install --no-install-recommends -y <pkgs> \
    && rm -rf /var/lib/apt/lists/*

# create non-root user
RUN groupadd -r app && useradd -r -g app -u 10001 -s /usr/sbin/nologin -d /home/app -m app
WORKDIR /home/app

# copy app as root, then chown
COPY --chown=app:app . .

# install Python deps as the app user
USER 10001
RUN pip install --user --no-cache-dir -r requirements.txt

ENTRYPOINT ["python", "-m", "agent_os"]
```

For the top-level `Dockerfile` and `.clusterfuzzlite/Dockerfile`, validate that any volume mounts the runtime needs are writeable by UID 10001.

### R3. Harden Kubernetes deployments (VULN-003)

Apply this securityContext to every container in:
- `packages/agent-os/charts/agent-os/templates/deployment-{audit-collector,kernel,policy-server}.yaml`
- `packages/agent-sre/charts/agent-sre/templates/deployments.yaml`
- `packages/agent-sre/deployments/helm/agent-sre/templates/deployment.yaml`

```yaml
spec:
  template:
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        fsGroup: 10001
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: <name>
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
          volumeMounts:
            # add emptyDir volumes for any path the app must write to
            - name: tmp
              mountPath: /tmp
            - name: cache
              mountPath: /home/app/.cache
      volumes:
        - name: tmp
          emptyDir: {}
        - name: cache
          emptyDir: {}
```

---

## Priority 2 — Medium (within 30 days)

### R4. Bump `pypdf` (VULN-004)

In `packages/agent-os/modules/caas/requirements.txt`:

```diff
- pypdf==6.7.5
+ pypdf>=6.10.2
```

Re-run `trivy fs` afterwards to confirm all 8 advisories clear.

### R5. Bump `streamlit` (VULN-005)

In `packages/agent-os/modules/scak/requirements.txt`:

```diff
- streamlit==1.41.0
+ streamlit>=1.54.0
```

### R6. Annotate intentional `subprocess` use (VULN-006)

In `packages/agent-compliance/src/agent_compliance/security/scanner.py` and `packages/agent-discovery/src/agent_discovery/scanners/process.py`, around each flagged call:

```python
# Tool name comes from an internal allow-list (TOOLS dict) — never user input.
# nosec B603 - subprocess invocation with allow-listed tool name
result = subprocess.run([tool_path, *args], capture_output=True, check=False, timeout=30)
```

Add a unit test:

```python
def test_tool_allowlist_is_not_user_tainted():
    from agent_compliance.security.scanner import _ALLOWED_TOOLS
    # _ALLOWED_TOOLS must be a frozenset/tuple constructed at import time
    assert isinstance(_ALLOWED_TOOLS, (frozenset, tuple))
    assert all(isinstance(t, str) for t in _ALLOWED_TOOLS)
```

### R7. Replace `/tmp/...` literals with `tempfile` (VULN-007)

For each `B108` finding (14 sites):

```python
# BEFORE
log_path = "/tmp/agent_run.log"

# AFTER
import tempfile
fd, log_path = tempfile.mkstemp(prefix="agent_run_", suffix=".log")
os.close(fd)
# or for a directory:
work_dir = tempfile.mkdtemp(prefix="agent_run_")
```

### R8. Default `integrations/mcp` to `127.0.0.1` (VULN-008)

In `packages/agent-mesh/src/agentmesh/integrations/mcp/__init__.py:424`:

```python
# BEFORE
host = "0.0.0.0"

# AFTER
host = os.environ.get("AGENTMESH_MCP_HOST", "127.0.0.1")
```

For the example apps under `packages/*/examples/docker-compose/`, leave `0.0.0.0` (correct for containers behind ingress) but add a README note explaining the threat model.

### R9. Fix `apt-get` install commands (VULN-009)

In each of `packages/agent-os/modules/{cmvk,control-plane,scak}/Dockerfile`:

```diff
- RUN apt-get update && apt-get install -y curl gnupg
+ RUN apt-get update && apt-get install --no-install-recommends -y curl gnupg \
+     && rm -rf /var/lib/apt/lists/*
```

### R10. Replace hardcoded demo "passwords" with env-vars

In:
- `examples/maf-integration/04-it-helpdesk/python/main.py:398`
- `examples/maf-integration/05-devops-deploy/python/main.py:397`
- `examples/openai-agents-governed/openai_agents_governance_demo.py` (lines 660, 667, 674)
- `packages/agent-mesh/examples/00-registration-hello-world/simulated_registration.py:202`

```python
# BEFORE
password = "prod-sql-password"

# AFTER
password = os.environ.get("DEMO_DB_PASSWORD", "demo-do-not-use")
```

Provide a `.env.example` in each demo directory.

### R11. Suppress the demo SQL-concat finding (VULN-007 → B608)

In `packages/agent-os/modules/emk/examples/memory_features_demo.py:31`:

```python
# Demo only; real production code uses parameterised queries via emk.repository.
# nosec B608 - demo file
query = f"SELECT * FROM memories WHERE id = {memory_id}"
```

---

## Priority 3 — Long-term / architectural

### R12. Ship a platform-keystore trust-store (VULN-010)

Add new extensions parallel to `FileTrustStore.cs`:

- **.NET:** `AgentGovernance.Extensions.AzureKeyVault.AzureKeyVaultTrustStore`
- **.NET:** `AgentGovernance.Extensions.Dpapi.DpapiTrustStore` (Windows)
- **macOS/Python:** `agent_mesh.identity.keychain_trust_store`
- **Linux:** `agent_mesh.identity.libsecret_trust_store`

Existing `IIdentityRegistry` / `ITrustStore` interfaces in the .NET SDK already imply pluggability, so this is a green-field implementation rather than a refactor.

### R13. Add CI security gates

Augment the existing OpenSSF Scorecard / ClusterFuzzLite pipeline in `.github/workflows/ci.yml`:

```yaml
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Trivy
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'
      - name: Run semgrep OWASP
        uses: returntocorp/semgrep-action@v1
        with:
          config: p/owasp-top-ten p/python p/typescript
      - name: Run gitleaks
        uses: gitleaks/gitleaks-action@v2
      - name: Python deps
        run: pip install pip-audit && pip-audit -r requirements/all.txt
      - name: .NET deps
        run: |
          cd agent-governance-dotnet
          dotnet restore
          dotnet list package --vulnerable --include-transitive | tee dotnet-vuln.txt
          ! grep -q ">" dotnet-vuln.txt   # fail if any vulnerabilities listed
      - name: Rust deps
        run: |
          cd agent-governance-rust
          cargo install cargo-audit --locked
          cargo audit --deny warnings
      - name: Go deps
        run: |
          go install golang.org/x/vuln/cmd/govulncheck@latest
          for m in $(find . -name go.mod); do
            (cd "$(dirname "$m")" && govulncheck ./...)
          done
      - name: npm deps
        run: |
          cd agent-governance-typescript
          npm ci
          npm audit --audit-level=high
```

### R14. Document the trust model for example/demo apps

Create `examples/SECURITY-NOTES.md`:

> Example applications under `examples/`, `demo/`, and `packages/*/examples/` are intended for **local development and container deployment behind an ingress controller**. They bind to `0.0.0.0` and use placeholder credentials. Do not deploy them as-is to a public network.

Link it from each example's README.

---

## Verification

After applying remediations, re-run:

```sh
# from the workspace root with .venv active
.venv/bin/bandit -r /Users/toddysm/Documents/Development/agent-governance-toolkit \
  -f json -o bandit-after.json -x "*/node_modules/*,*/.venv/*,*/test*,*/tests/*"

trivy fs --scanners vuln,secret,misconfig --format json -o trivy-after.json \
  --severity HIGH,CRITICAL --skip-dirs node_modules,.venv,.git,target \
  /Users/toddysm/Documents/Development/agent-governance-toolkit
```

Acceptance criteria:
- `bandit-after.json`: 0 HIGH severity findings, B615 count = 0, B608 count = 0 in non-demo paths.
- `trivy-after.json`: 0 HIGH/CRITICAL vulnerabilities, 0 DS-0002 findings, KSV-0014/KSV-0118 cleared on the listed Helm templates.
