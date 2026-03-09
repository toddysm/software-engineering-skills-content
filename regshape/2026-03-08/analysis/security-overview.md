# regshape — Security Overview

**Project:** regshape v0.1.0  
**Analysis Date:** 2026-03-08  

---

## Security Posture Summary

regshape has a **strong security baseline** for a developer CLI tool. The codebase demonstrates security-conscious design throughout: credentials are never hardcoded, sensitive headers are redacted before logging, all network communication uses TLS by default, and blob downloads verify cryptographic digests.

**Overall Risk Rating: LOW** *(for production code; dev environment has elevated risk due to gitpython)*

---

## Key Security Controls

| Control | Status | Location |
|---|---|---|
| No hardcoded secrets | ✅ PASS | All files — detect-secrets: 0 findings |
| TLS by default | ✅ PASS | `transport/client.py` — HTTPS unless `--insecure` |
| Header sanitization | ✅ PASS | `decorators/sanitization.py` — Authorization, Cookie redacted |
| Digest verification | ✅ PASS | `blobs/operations.py` — SHA-256/SHA-512 post-download |
| Atomic file writes | ✅ PASS | `layout/operations.py` — mkstemp + os.replace |
| Safe subprocess | ✅ PASS | `auth/dockercredstore.py` — list form, no shell |
| HTTP timeouts | ❌ MISSING | `auth/registryauth.py:116,118` — **needs fix** |
| Realm URL validation | ❌ MISSING | `auth/registryauth.py` — SSRF vector |
| Dev dep vulnerabilities | ⚠️ ACTION | `gitpython 3.1.0` — 5 CVEs, needs upgrade |

---

## Security Findings by Priority

### Priority 1: Add HTTP Request Timeouts (Medium Risk)

**Location:** `libs/auth/registryauth.py` lines 116, 118  
**Bandit ID:** B113 | **CWE:** CWE-400

Two `requests.get()` calls to the token endpoint have no timeout. A slow or adversarial registry can hang the process indefinitely. In automated pipelines this can cause CI deadlocks.

**Fix:**
```python
response = requests.get(realm, params=params, timeout=30)
```

See [remediation-guide.md](./remediation-guide.md#remediation-1) for full details.

---

### Priority 2: Upgrade gitpython in Dev Environment (High Risk — Dev Only)

**Package:** `gitpython 3.1.0`  
**CVEs:** PYSEC-2022-42992 (CRITICAL), PYSEC-2023-137, -161, -165 (HIGH), PYSEC-2024-4 (HIGH)

**Note:** `gitpython` is **not** a runtime dependency of regshape — it's installed via the development toolchain. It should be upgraded in all developer/CI environments.

**Fix:** `pip install "gitpython>=3.1.41"`

---

### Priority 3: Replace Hardcoded /tmp/ Paths in Tests (Low Risk)

**Location:** `tests/test_auth_cli.py` (9 occurrences)  
**Bandit ID:** B108 | **CWE:** CWE-377

Hardcoded `/tmp/docker_config.json` in test fixtures. Test-only; not in production code.

**Fix:** Use `tmp_path` pytest fixture or `tempfile.TemporaryDirectory()`.

---

### Non-Issues (False Positives / Low Concern)

| Finding | Count | Assessment |
|---|---|---|
| B101 assert statements | 1,232 | All in test files — expected |
| B603 subprocess | 4 | `dockercredstore.py` uses list form — safe |
| Semgrep logger warnings | 9 | False positives — logger messages, not credential values |

---

## What This Codebase Gets Right

**1. Credential Management**  
The priority chain (explicit → credHelper → docker config → anon) follows Docker's own model. Credential helpers mean credentials can go to OS keychains rather than file-based storage.

**2. Header Sanitization**  
`SENSITIVE_HEADERS = frozenset({"authorization", "proxy-authorization", "cookie", "set-cookie"})` ensures that even with verbose logging enabled, auth tokens never appear in logs. The implementation preserves the scheme keyword (e.g., `Bearer`) which is useful for debugging without exposing the token value.

**3. Blob Integrity**  
Every blob download verifies the SHA-256 (or SHA-512) digest after transfer. This protects against both data corruption and MITM attacks that could substitute malicious blob data. The `Descriptor` model also validates the digest format via regex before any network call.

**4. Atomic Writes**  
OCI Image Layout writes use `tempfile.mkstemp()` + `os.replace()` — an atomic operation on POSIX. Under no circumstances does a reader see a partially written manifest or blob.

**5. Minimal Dependency Surface**  
Only 2 runtime dependencies (`click` and `requests`). Fewer dependencies = smaller attack surface for supply-chain attacks.
