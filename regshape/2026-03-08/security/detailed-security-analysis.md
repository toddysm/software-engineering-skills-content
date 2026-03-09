# regshape — Detailed Security Analysis

**Project:** regshape v0.1.0  
**Analysis Date:** 2026-03-08  
**Tools Used:** bandit, semgrep, pip-audit, detect-secrets  
**Source Analyzed:** `src/` (50 production files + 33 test files)

---

## Executive Summary

| Category | Risk Level | Findings |
|---|---|---|
| Static code analysis (bandit) | Low–Medium | 11 MEDIUM, 1,265 LOW |
| Dependency vulnerabilities (pip-audit) | **High** | 5 CVEs in gitpython 3.1.0 (dev-only) |
| Hardcoded secrets (detect-secrets) | None | 0 findings |
| Semantic analysis (semgrep) | Low (false positives) | 9 warnings (logger messages) |
| **Overall production code risk** | **Low** | No critical or high findings in production code |

The production codebase is clean. The only medium-severity findings in production code are **two missing HTTP request timeouts** in `registryauth.py`. The high-severity dependency vulnerabilities are in `gitpython`, which is a development tool dependency (likely pulled in by the test toolchain), not a runtime dependency of `regshape` itself.

---

## 1. Bandit Static Analysis Results

**Total findings:** 1,276  
**Breakdown:**
- HIGH: 0  
- MEDIUM: 11  
- LOW: 1,265  

### 1.1 Medium Severity Findings — Production Code

#### B113: Requests Without Timeout (CWE-400)

**Files:** `regshape/libs/auth/registryauth.py`, lines 116 and 118  
**Severity:** MEDIUM / Confidence: LOW  
**CWE:** [CWE-400](https://cwe.mitre.org/data/definitions/400.html) — Uncontrolled Resource Consumption  

**Description:**  
Two `requests.get()` calls in the token endpoint authentication flow do not specify a `timeout` parameter. A slow or unresponsive registry can cause the process to hang indefinitely.

**Code Pattern:**
```python
# registryauth.py ~line 116-118
response = requests.get(realm, params=params)          # ← no timeout
response = requests.get(realm, params=params, auth=...) # ← no timeout
```

**Risk Assessment:**  
- Primary risk: denial-of-service against the client process (not the server)
- A malicious or slow registry can cause `regshape` to hang indefinitely during auth
- Exploitability: LOW (requires attacker control of registry endpoint or MITM position)
- Impact: LOW in most scenarios; MEDIUM in automated pipelines

**Recommendation:**  
Add a configurable timeout (default 30s) to all `requests` calls:
```python
response = requests.get(realm, params=params, timeout=30)
```
Consider defining `DEFAULT_REQUEST_TIMEOUT = 30` in `libs/constants.py` and using it consistently across `transport/client.py` and `registryauth.py`.

---

### 1.2 Medium Severity Findings — Test Code Only

#### B108: Insecure Temp File Usage (CWE-377)

**File:** `regshape/tests/test_auth_cli.py`, lines 154, 155, 345, 378, 434, 472, 493, 568, 641  
**Severity:** MEDIUM / Confidence: MEDIUM  
**CWE:** [CWE-377](https://cwe.mitre.org/data/definitions/377.html) — Insecure Temporary File  

**Description:**  
Multiple test functions use `/tmp/` prefix strings like `"/tmp/docker_config.json"` for test fixture files. Bandit flags these as potentially insecure because hardcoded `/tmp/` paths share a world-writable directory.

**Risk Assessment:**  
- These are **test-only** findings — they do not appear in production code
- In a CI environment, the risk is negligible (sandboxed runners)
- In a shared developer environment, a symlink attack is theoretically possible but unlikely

**Recommendation:**  
In test code, prefer `tempfile.mkstemp()` or `tempfile.TemporaryDirectory()` for creating test fixture files to eliminate the bandit warning and be safer on shared systems.

---

### 1.3 Low Severity Findings

| Test ID | Count | What It Flags | Risk |
|---|---|---|---|
| B101 | 1,232 | `assert` statements (all in test code) | None — expected in tests |
| B105 | 14 | Hardcoded password-like string parameters | Review; likely test fixtures |
| B106 | 12 | Empty string as password default | Review in context |
| B603 | 4 | `subprocess.Popen` without `shell=True` | Low — shell=False is safer |
| B404 | 1 | `import subprocess` | Informational |
| B112 | 1 | `try`/`except`/`continue` | Code quality, not security |
| B107 | 1 | Hardcoded password in function argument | Review; likely test fixture |

**Notes on B603/B404 (subprocess):**  
`dockercredstore.py` uses `subprocess.Popen` to call credential helper programs. This is intentional and correct. The command is constructed as `["docker-credential-{store}", "get"]` — a list (not a string), so `shell=False` applies. This is the safe pattern for subprocess calls.

---

## 2. Dependency Audit (pip-audit)

**5 vulnerabilities found in 1 package: `gitpython 3.1.0`**

> **Important Context:** `gitpython` does not appear in `regshape`'s `pyproject.toml` as a runtime or development dependency. It is likely installed transitively by a development tool (e.g., a pre-commit hook runner, semgrep, or another tooling package). It is **not** part of regshape's production deployment.

### CVE Details

| ID | Severity | Description | Fixed In |
|---|---|---|---|
| PYSEC-2024-4 | HIGH | Incomplete fix for CVE-2023-40590; Path traversal in git operations | 3.1.41 |
| PYSEC-2022-42992 | CRITICAL | RCE via improper user input validation in git operations | 3.1.30 |
| PYSEC-2023-137 | HIGH | Insecure non-multi options in `clone` / `clone_from` | 3.1.32 |
| PYSEC-2023-161 | HIGH | PATH hijack on Python/Windows during program resolution | 3.1.33 |
| PYSEC-2023-165 | HIGH | Remote code execution via uncontrolled git reference resolution | 3.1.35 |

### Remediation

If `gitpython` is in the development environment:
```bash
pip install "gitpython>=3.1.41"
```

Verify it is NOT a transitive runtime dependency:
```bash
pip show gitpython
# Check "Required-by:" field
```

For CI/CD pipelines, ensure development tools (semgrep, pre-commit, etc.) use updated versions that pull in gitpython ≥ 3.1.41.

---

## 3. Secret Detection (detect-secrets)

**Result: CLEAN — 0 findings**

No hardcoded secrets, API keys, passwords, or tokens were detected in the source tree. The codebase correctly:
- Never hardcodes credentials
- Uses credential resolution with well-defined priority chains
- Redacts sensitive headers before logging

---

## 4. Semgrep Semantic Analysis

**9 findings — all false positives**

All 9 findings are `python-logger-credential-disclosure` warnings in `libs/auth/credentials.py`. Semgrep detected logger calls whose message strings contain words like "credentials", "credential helper", "secret" — but these are plain English log message templates, not actual credential values.

**Example (false positive):**
```python
logger.debug("Using explicit credentials for %s", registry)
# ↑ Semgrep matches on "credentials" in the string, but the actual
#   credential values are never passed to the logger. ✓ Safe.
```

**Actual credential handling:**  
The code logs descriptive messages about credential *sources* and operations, not credential *values*. This is good security hygiene.

**Action:** These findings can be suppressed with `# nosemgrep: python-logger-credential-disclosure` if desired, or added to a `.semgrepignore` file.

---

## 5. Security Posture Assessment

### Strengths

| Strength | Evidence |
|---|---|
| **No hardcoded secrets** | 0 detect-secrets findings; credential resolution via priority chain |
| **Header sanitization** | `sanitization.py` with `SENSITIVE_HEADERS` frozenset; auth headers always redacted |
| **Safe subprocess pattern** | `dockercredstore.py` uses list-form `Popen` (shell=False), never string |
| **TLS by default** | HTTPS used by default; `--insecure` requires explicit opt-in |
| **Atomic file writes** | `os.replace()` after `mkstemp()` prevents partial write state |
| **Digest verification** | Blob downloads verify SHA-256/SHA-512 integrity |
| **Clean dependency surface** | Only 2 runtime deps (`click`, `requests`); minimal attack surface |
| **Proper OCI auth flow** | Short-lived bearer tokens; not storing long-lived tokens |
| **No shell injection** | All subprocess calls use list form; no string interpolation |
| **Input validation** | Descriptor digest regex: strict sha256/sha512 validation |

### Weaknesses and Gaps

| Weakness | Location | Priority |
|---|---|---|
| **Missing request timeouts** | `registryauth.py:116,118` | **Medium** — fix before production use at scale |
| **Transport client timeouts** | `transport/client.py` | **Medium** — all `requests.*` calls need timeout parameter |
| **No SSRF protection** | Token endpoint URL from `WWW-Authenticate` header | **Low** — registry-supplied realm URL could be SSRF vector |
| **No certificate pinning** | Transport layer | **Low** — standard TLS is sufficient for most threat models |
| **Credential helper PATH dependency** | `dockercredstore.py` | **Low** — relies on system PATH for binary lookup |

### OWASP Top 10 Assessment

| OWASP Category | Status | Notes |
|---|---|---|
| A01: Broken Access Control | ✅ Not applicable | regshape is a client; access control is server-side |
| A02: Cryptographic Failures | ⚠️ Partial | No timeouts on auth HTTP calls; TLS otherwise fine |
| A03: Injection | ✅ Clean | No SQL; subprocess uses list form; no shell injection |
| A04: Insecure Design | ✅ Good | Credential priority chain is well-designed |
| A05: Security Misconfiguration | ⚠️ Partial | `--insecure` flag disables all transport security |
| A06: Vulnerable Components | ⚠️ Action needed | gitpython (dev env) needs upgrade |
| A07: Auth Failures | ✅ Good | Bearer token flow correct; Basic auth as fallback |
| A08: Data Integrity Failures | ✅ Good | Digest verification on blob downloads |
| A09: Security Logging | ✅ Good | Headers redacted; sensitive values not logged |
| A10: SSRF | ⚠️ Minor risk | Token realm from server; no URL validation |

---

## 6. Responsible Disclosure Notes

The security findings in this report are all low-to-medium severity. The codebase demonstrates strong security awareness in its design. The recommended remediations are incremental improvements, not critical patches.

**Priority order for remediations:**
1. Add HTTP request timeouts (Medium — simple fix, clear CWE)
2. Upgrade gitpython in dev environment (High CVEs, but dev-only)
3. Document `--insecure` flag security implications in user-facing docs
4. Consider token realm URL validation for SSRF hardening (Low)
