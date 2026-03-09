# regshape — Dependency Audit

**Project:** regshape v0.1.0  
**Analysis Date:** 2026-03-08  
**Tool:** pip-audit  

---

## Runtime Dependencies

| Package | Declared Version | Purpose | Known Vulnerabilities |
|---|---|---|---|
| `click` | >=8.1.0 | CLI framework | None known |
| `requests` | >=2.31.0 | HTTP client | None active |

### click

**Purpose:** Powers the entire CLI layer — argument parsing, command groups, option handling, context passing, output helpers.

**Why click?**
- Battle-tested Python CLI framework
- Excellent decorator-based command definition
- Context object passing (used extensively for global options)
- No heavy dependencies of its own

**Security notes:**
- Click 8.x handles Unicode properly; no known injection vectors
- Argument parsing is safe against typical injection attacks
- No network access; purely local processing

### requests

**Purpose:** All HTTP communication with OCI registries.

**Why requests?**
- Simple, well-understood Python HTTP library
- Handles HTTPS/TLS via `urllib3`
- Session reuse, connection pooling
- Wide adoption = well-audited

**Security notes:**
- TLS certificate verification enabled by default (`verify=True`)
- Regshape uses `requests.get/post/put/delete` with headers — no `verify=False` in production paths
- `--insecure` mode likely passes `verify=False` — this disables TLS validation completely
- Missing timeout configuration (B113 finding) — should be added

---

## Development Environment Dependencies (Known Vulnerabilities)

### gitpython 3.1.0

**How it got in:** Transitive dependency from development tooling (not in `pyproject.toml`)

**Vulnerabilities:**

| ID | CVSS | Description | Fixed In |
|---|---|---|---|
| PYSEC-2022-42992 | CRITICAL | RCE via improper user input validation in git URL handling | 3.1.30 |
| PYSEC-2023-137 | HIGH | Insecure clone options; non-multi options bypass | 3.1.32 |
| PYSEC-2023-161 | HIGH | PATH hijack on Windows for program resolution | 3.1.33 |
| PYSEC-2023-165 | HIGH | RCE via uncontrolled git reference resolution | 3.1.35 |
| PYSEC-2024-4 | HIGH | Incomplete fix for CVE-2023-40590; path traversal | 3.1.41 |

**Remediation:** `pip install "gitpython>=3.1.41"` in all development environments.

---

## Stdlib Dependencies Used

The following Python standard library modules are used and warrant mention:

| Module | Used In | Notes |
|---|---|---|
| `subprocess` | `auth/dockercredstore.py` | Uses `Popen` with list args (no shell injection risk) |
| `hashlib` | `blobs/operations.py` | SHA-256/SHA-512 digest computation |
| `tempfile` | `layout/operations.py` | `mkstemp()` for atomic writes (correct usage) |
| `base64` | `auth/registryauth.py` | Basic auth encoding (stdlib, well-tested) |
| `json` | Many files | Standard JSON parsing; safe against typical attacks |
| `os` | Many files | Path operations; no `os.system()` usage |
| `re` | `models/descriptor.py` | Digest validation regex |
| `logging` | Many files | Standard logging; credentials are redacted before logging |

---

## Dependency Security Scorecard

| Category | Score | Notes |
|---|---|---|
| Runtime dep count | ✅ Excellent | Only 2 runtime deps (click, requests) |
| Stdlib usage | ✅ Good | Appropriate stdlib usage; no risky APIs |
| Dev dep vulnerabilities | ⚠️ Needs action | gitpython needs upgrade |
| Pinning strategy | ⚠️ None | `pyproject.toml` uses `>=` ranges; consider hash pinning for production |
| Transitive surface | ✅ Small | `requests` brings in `urllib3`, `certifi`, `charset-normalizer`, `idna` — all well-maintained |

---

## Recommendations

1. **Immediate:** Upgrade `gitpython` in development environments — 5 HIGH/CRITICAL CVEs
2. **Short-term:** Consider adding `requests[security]` or explicitly pinning `urllib3` version
3. **Long-term:** Consider `pip-compile` with hash verification for production deployments
4. **CI:** Add `pip-audit` to CI pipeline to catch future dependency vulnerabilities automatically

```yaml
# Example GitHub Actions step
- name: Audit Python dependencies
  run: pip-audit --requirement requirements.txt
```
