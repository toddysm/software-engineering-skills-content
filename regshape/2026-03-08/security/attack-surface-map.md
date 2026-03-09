# regshape — Attack Surface Map

**Project:** regshape v0.1.0  
**Analysis Date:** 2026-03-08  

---

## Attack Surface Overview

regshape is a **CLI client tool** — its attack surface is limited compared to a server application. The primary risk vectors are:

1. Malicious/compromised remote registry servers sending crafted responses
2. Credential theft via insecure storage or transmission
3. Supply-chain risks via transitive dependencies
4. Insecure operator configuration (`--insecure` mode)

---

## Attack Vectors by Category

### External Network Attack Surface

| Vector | Entry Point | Description | Controls In Place | Residual Risk |
|---|---|---|---|---|
| **Malformed JSON from registry** | All operation responses | Registry returns crafted JSON to cause parsing errors or unexpected behavior | `json.loads()` in model parsers; `OciErrorResponse` parsing | LOW — standard JSON parsing, no eval |
| **Token realm SSRF** | `WWW-Authenticate: Bearer realm=...` | Compromised registry returns internal URL as token realm | None (no realm validation) | LOW — requires registry compromise |
| **Slow registry DoS** | `registryauth.py` auth token requests | Registry stalls; no timeout set | None — CWE-400 finding | **MEDIUM** — needs fix |
| **MITM credential interception** | All HTTPS connections | Attacker intercepts auth tokens in transit | TLS (requests library) | LOW with TLS; HIGH with `--insecure` |
| **Malicious layer data** | Blob download | Downloaded blob with incorrect digest | SHA-256/SHA-512 verification on pull | LOW — digest verified |
| **Redirect attacks** | `requests` HTTP redirects | Chained redirects to unintended endpoints | requests library follows redirects by default | LOW |

### Local System Attack Surface

| Vector | Entry Point | Description | Controls In Place | Residual Risk |
|---|---|---|---|---|
| **Docker config.json exposure** | `~/.docker/config.json` reading | Credentials stored in plain text in config file | Relies on filesystem permissions | LOW — standard practice |
| **Credential helper PATH hijack** | `dockercredstore.py` subprocess | Malicious binary named `docker-credential-X` in PATH | None — PATH lookup used | LOW — requires PATH compromise |
| **Temp file race condition** | OCI Layout writes | Partial write window | `mkstemp` + `os.replace` atomic writes | NONE — fully mitigated |
| **Insecure temp files in tests** | `test_auth_cli.py` | Hardcoded `/tmp/` paths | None in tests | LOW — test-only |
| **CLI argument injection** | All CLI commands | Special characters in registry names or paths | Click framework argument parsing | LOW — Click handles parsing |

### Supply Chain / Dependency Attack Surface

| Dependency | Version | Known CVEs | Risk |
|---|---|---|---|
| `click` | ≥8.1.0 | None known | LOW |
| `requests` | ≥2.31.0 | None active | LOW |
| `gitpython` (dev env) | 3.1.0 | 5 HIGH/CRITICAL CVEs | **HIGH** (dev env only) |
| Python stdlib | 3.10+ | Managed by Python releases | LOW |

### Operator Configuration Attack Surface

| Configuration | Risk | Notes |
|---|---|---|
| `--insecure` flag | HIGH | Disables TLS; credentials sent in cleartext |
| `DOCKER_CONFIG` env var | MEDIUM | Can redirect config directory; could read from untrusted path |
| `--log-file` option | LOW | If pointed to sensitive path; no path traversal mitigations |
| Anonymous access | LOW | May access public repos unintentionally |

---

## Threat Actor Profiles

### Threat Actor 1: Compromised Registry Server
- **Goal:** Steal credentials, execute code on client
- **Capability:** Controls HTTP responses from registry
- **Attack paths:** Token realm SSRF, malformed manifests, credential reflection in error messages
- **Mitigations:** Realm URL validation (not yet implemented), TLS, header sanitization

### Threat Actor 2: Network Attacker (MITM)
- **Goal:** Steal authentication tokens
- **Capability:** Can intercept network traffic
- **Attack paths:** HTTPS downgrade if `--insecure` used; token interception
- **Mitigations:** TLS enabled by default; `--insecure` requires explicit opt-in

### Threat Actor 3: Local System Attacker
- **Goal:** Steal stored credentials; hijack credential helpers
- **Capability:** Write access to PATH or `/tmp/`
- **Attack paths:** PATH injection for credential helper binary, temp file attacks in tests
- **Mitigations:** OS-level controls; credential helper lookup is standard Docker pattern

### Threat Actor 4: Supply Chain Attacker
- **Goal:** Backdoor regshape via transitive dependency  
- **Capability:** Compromise a dependency
- **Attack paths:** Compromise `requests` or `click` PyPI packages
- **Mitigations:** Minimal deps (2 runtime); consider pinning with hash verification in production

---

## Data Flow Security Analysis

| Data Item | Origin | Destination | Encrypted in Transit | Sanitized Before Log |
|---|---|---|---|---|
| Registry credentials | Docker config / CLI | Auth token endpoint | Yes (HTTPS) | Yes (redact_headers) |
| Bearer tokens | Token endpoint | Registry HTTP API | Yes (HTTPS) | Yes (redact_headers) |
| Manifest JSON | Registry | stdout / file | Yes (HTTPS) | N/A |
| Blob data | Registry or file | Registry or file | Yes (HTTPS) for network | N/A |
| Token endpoint URL | WWW-Authenticate header | requests.get() | N/A | N/A |
| Log output | Application | stdout / log file | N/A | Header values redacted |
| OCI Layout files | Registry / filesystem | Local filesystem | N/A | Atomic writes |

---

## Security Controls Inventory

| Control | Location | Effectiveness |
|---|---|---|
| TLS transport | `transport/client.py` (via requests) | HIGH — default for all requests |
| Header redaction | `decorators/sanitization.py` | HIGH — Authorization, Cookie, Set-Cookie, Proxy-Authorization |
| Digest verification | `blobs/operations.py` | HIGH — SHA-256/SHA-512 verified |
| Atomic file writes | `layout/operations.py` | HIGH — prevents partial write state |
| Safe subprocess | `auth/dockercredstore.py` | HIGH — list form, no shell injection |
| Credential priority chain | `auth/credentials.py` | HIGH — well-defined; explicit > helper > stored > anon |
| Strict digest regex | `models/descriptor.py` | MEDIUM — validates sha256/sha512 format |
| Exception hierarchy | `libs/errors.py` | MEDIUM — domain errors don't leak internal details |
| No hardcoded secrets | all files | HIGH — detect-secrets: 0 findings |

---

## Attack Surface Reduction Recommendations

1. **Add request timeouts** — most urgent production hardening
2. **Validate `realm` URL in WWW-Authenticate** — prevents SSRF via malicious registry
3. **Pin dependency hashes** — consider `pip install --require-hashes` for production deployments
4. **Upgrade gitpython** — eliminates 5 HIGH/CRITICAL CVEs from dev environment
5. **Document `--insecure` risks** — prominently warn users that this disables all transport security
6. **Consider `REGSHAPE_NO_INSECURE` env var** — allow organizations to prohibit `--insecure` usage
