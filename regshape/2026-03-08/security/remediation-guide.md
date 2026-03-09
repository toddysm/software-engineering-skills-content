# regshape — Security Remediation Guide

**Project:** regshape v0.1.0  
**Analysis Date:** 2026-03-08  
**Priority:** Medium → Low  

---

## Remediation #1 — Add HTTP Request Timeouts (Priority: MEDIUM)

**Bandit:** B113 | **CWE:** CWE-400  
**Files:** `libs/auth/registryauth.py` lines 116, 118; `libs/transport/client.py` (all requests calls)

### Background
The OCI authentication flow in `registryauth.py` makes direct `requests.get()` calls to the token endpoint without a timeout. If the registry stalls or the token endpoint is slow, the entire process hangs indefinitely.

The `transport/client.py` calls may also lack explicit timeouts (delegated to `requests` defaults which have no timeout by default).

### Fix

**Step 1:** Add a timeout constant to `libs/constants.py`:
```python
# libs/constants.py
IS_WINDOWS_PLATFORM = sys.platform == 'win32'

# HTTP request timeout in seconds
DEFAULT_REQUEST_TIMEOUT = 30
CONNECT_TIMEOUT = 10
```

**Step 2:** Update `libs/auth/registryauth.py`:
```python
# Before
response = requests.get(realm, params=params)
response = requests.get(realm, params=params, auth=(username, password))

# After
from regshape.libs.constants import DEFAULT_REQUEST_TIMEOUT

response = requests.get(realm, params=params, timeout=DEFAULT_REQUEST_TIMEOUT)
response = requests.get(realm, params=params, auth=(username, password), timeout=DEFAULT_REQUEST_TIMEOUT)
```

**Step 3:** Add timeout to `TransportConfig` dataclass in `libs/transport/client.py`:
```python
@dataclass
class TransportConfig:
    # ... existing fields ...
    request_timeout: int = 30  # seconds; None = no timeout
```

Then pass `timeout=self.config.request_timeout` to each `requests.*` call in `RegistryClient`.

### Testing
Verify the fix works against a slow endpoint using a mock:
```python
import responses

@responses.activate
def test_auth_timeout():
    responses.add(responses.GET, "https://registry.io/token", body=ReadTimeout())
    with pytest.raises(AuthError, match="timeout"):
        authenticate(...)
```

---

## Remediation #2 — Upgrade gitpython (Priority: HIGH for dev env)

**pip-audit:** PYSEC-2022-42992, PYSEC-2023-137, PYSEC-2023-161, PYSEC-2023-165, PYSEC-2024-4  
**Affected package:** gitpython 3.1.0  
**Required version:** ≥ 3.1.41  

### Background
`gitpython` is installed in the current development environment (likely as a transitive dependency of a dev tool). It contains multiple RCE and path traversal vulnerabilities. While `gitpython` is **not** in regshape's production dependencies, it should be upgraded in any environment where developers work.

### Fix

Identify what requires gitpython:
```bash
pip show gitpython | grep "Required-by"
```

Upgrade:
```bash
pip install "gitpython>=3.1.41"
```

Or pin in your development tool configuration (e.g., `requirements-dev.txt`):
```
gitpython>=3.1.41
```

If using pre-commit:
```yaml
# .pre-commit-config.yaml
# Ensure you're on a version that pulls in gitpython>=3.1.41
```

### Verification
```bash
pip show gitpython | grep Version
# Should show 3.1.41 or higher
```

---

## Remediation #3 — Replace Hardcoded Temp Paths in Tests (Priority: LOW)

**Bandit:** B108 | **CWE:** CWE-377  
**File:** `tests/test_auth_cli.py`, lines 154, 155, 345, 378, 434, 472, 493, 568, 641  

### Background
Test fixtures use hardcoded `/tmp/docker_config.json` paths. On shared systems or CI environments with world-writable `/tmp/`, a symlink attack is theoretically possible where pre-existing `/tmp/docker_config.json` could redirect writes.

### Fix

Replace hardcoded paths with `tempfile.TemporaryDirectory()` or `tmp_path` (pytest fixture):

**Before:**
```python
def test_login_stores_credentials():
    config_path = "/tmp/docker_config.json"
    # ... uses config_path ...
```

**After (using pytest `tmp_path`):**
```python
def test_login_stores_credentials(tmp_path):
    config_path = tmp_path / "docker_config.json"
    # ... uses config_path ...
```

Or using `tempfile`:
```python
import tempfile

def test_login_stores_credentials():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "docker_config.json")
        # ... uses config_path ...
```

---

## Remediation #4 — Validate Token Realm URL (Priority: LOW)

**Category:** SSRF (A10 OWASP Top 10)  
**File:** `libs/auth/registryauth.py`, `libs/transport/middleware.py`  

### Background
The token endpoint URL (`realm`) is extracted from the `WWW-Authenticate` header returned by the registry server:
```
WWW-Authenticate: Bearer realm="https://auth.example.com/token",service="...",scope="..."
```

A malicious or compromised registry could return a `realm` pointing to an internal URL (e.g., `http://169.254.169.254/` for cloud IMDS endpoints), potentially enabling SSRF.

### Fix

Add realm URL validation before requesting tokens:
```python
# libs/auth/registryauth.py

from urllib.parse import urlparse

ALLOWED_SCHEMES = {"https", "http"}

def _validate_realm_url(realm: str, registry: str) -> None:
    """Validate the token realm URL to prevent SSRF."""
    parsed = urlparse(realm)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise AuthError(f"Invalid realm scheme: {parsed.scheme}")
    # Optional: require realm host to match registry host
    # registry_host = registry.split(":")[0]
    # if parsed.hostname != registry_host:
    #     raise AuthError(f"Realm host mismatch: {parsed.hostname} vs {registry_host}")
```

Note: The second check (realm host matching registry host) would be too strict for registries that use separate auth servers (like Docker Hub: `registry.hub.docker.com` → `auth.docker.io`). Consider a configurable allow-list.

---

## Remediation #5 — Suppress False-Positive Semgrep Warnings (Priority: LOW)

**Semgrep:** python-logger-credential-disclosure (9 findings)  
**File:** `libs/auth/credentials.py`  

### Background
Semgrep incorrectly flags logger calls whose message strings contain the word "credentials" or "secret" — but the actual credential values are never passed to the logger.

### Fix

Option A — Add `# nosemgrep` inline comments:
```python
logger.debug("Using explicit credentials for %s", registry)  # nosemgrep: python-logger-credential-disclosure
```

Option B — Add to `.semgrepignore`:
```
# .semgrepignore
regshape/libs/auth/credentials.py
```

Option C — Add a Semgrep rule override in your CI configuration to exclude known false-positives from this file.

---

## Summary Table

| # | Finding | Severity | Effort | Impact |
|---|---|---|---|---|
| 1 | Add HTTP request timeouts | MEDIUM | Low (~30 min) | Prevents DoS in automated pipelines |
| 2 | Upgrade gitpython (dev env) | HIGH (dep) | Low (~5 min) | Removes RCE risk in dev toolchain |
| 3 | Fix temp paths in tests | LOW | Low (~1 hr) | Removes CWE-377 in test code |
| 4 | Token realm URL validation | LOW | Medium (~2 hrs) | Prevents SSRF via malicious registry |
| 5 | Suppress semgrep FPs | LOW | Low (~15 min) | Cleaner CI scan output |
