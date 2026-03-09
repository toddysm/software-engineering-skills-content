# regshape — Comprehensive Architecture & Security Documentation

**Project:** regshape  
**Version:** 0.1.0  
**Analysis Date:** 2026-03-08  
**Analysis Performed By:** GitHub Copilot Codebase Architecture Analyst Skill  

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture Summary](#2-architecture-summary)
3. [Module Inventory](#3-module-inventory)
4. [Component Deep Dives](#4-component-deep-dives)
5. [Data Flows](#5-data-flows)
6. [Dependency Analysis](#6-dependency-analysis)
7. [Security Analysis](#7-security-analysis)
8. [Technology Decisions](#8-technology-decisions)
9. [Testing Coverage](#9-testing-coverage)
10. [Recommended Improvements](#10-recommended-improvements)
11. [Supporting Files Index](#11-supporting-files-index)

---

## 1. Project Overview

`regshape` is a Python CLI tool and reusable library for interacting with OCI-compliant container registries. It implements the [OCI Distribution Specification](https://github.com/opencontainers/distribution-spec) and the [OCI Image Layout Specification](https://github.com/opencontainers/image-spec/blob/main/image-layout.md).

### What It Does

| Capability | Description |
|---|---|
| **Authentication** | Login/logout to container registries; credential storage via Docker config and credential helpers |
| **Manifests** | Get, head, push, delete container image manifests (OCI + Docker formats) |
| **Blobs** | Get, head, push (monolithic + chunked), delete, mount container image layers |
| **Tags** | List and delete image tags |
| **Catalog** | List repositories in a registry |
| **Referrers** | List OCI referrers attached to an image (SBOMs, signatures, attestations) |
| **OCI Image Layout** | Read and write OCI Image Layout format on local filesystem |

### Key Properties

| Attribute | Value |
|---|---|
| Language | Python ≥ 3.10 |
| Runtime Dependencies | 2 (`click`, `requests`) |
| Test Framework | pytest |
| Entry Point | `regshape` CLI command |
| Version | 0.1.0 |
| Platform | Cross-platform (Windows-aware for credential helpers) |

---

## 2. Architecture Summary

regshape employs a clean **two-layer architecture**: a thin CLI layer that delegates all logic to a well-structured library layer.

```
┌─────────────────────────────────────────────────────────────────┐
│  CLI Layer: regshape/cli/                                        │
│  Click-based commands → parse args → call library → format output│
└───────────────────────────────────┬─────────────────────────────┘
                                    │
┌───────────────────────────────────▼─────────────────────────────┐
│  Library Layer: regshape/libs/                                   │
│                                                                  │
│  Transport     Auth           Operations        Models           │
│  ─────────     ────           ──────────        ──────           │
│  client.py     credentials    blobs/            manifest.py      │
│  middleware    dockerconfig   manifests/        descriptor.py    │
│  models        dockercred     tags/             blob.py          │
│                registryauth   catalog/          mediatype.py     │
│                               referrers/        tags.py          │
│  Decorators    Utilities      layout/           catalog.py       │
│  ────────────  ─────────                        referrer.py      │
│  timing        refs.py                          error.py         │
│  scenario      errors.py                                         │
│  output        constants.py                                      │
│  metrics                                                         │
│  sanitization                                                    │
│  call_details                                                    │
└─────────────────────────────────────────────────────────────────┘
                                    │ HTTPS
┌───────────────────────────────────▼─────────────────────────────┐
│  OCI Container Registry (Docker Hub, GHCR, ACR, ECR, Zot, etc.) │
└─────────────────────────────────────────────────────────────────┘
```

### Key Design Patterns

| Pattern | Implementation | Purpose |
|---|---|---|
| **Thin CLI** | All `cli/*.py` have no business logic | Library reusability |
| **Chain of Responsibility** | `MiddlewarePipeline` | Composable HTTP processing |
| **Command Object** | `RegistryRequest`/`RegistryResponse` | Encapsulate HTTP exchange |
| **Strategy** | `AuthMiddleware` (Bearer / Basic) | Pluggable auth schemes |
| **Decorator for Telemetry** | `@track_time`, `@track_scenario` | Non-invasive instrumentation |
| **Atomic Write** | `mkstemp` + `os.replace` | Filesystem consistency |

### Architecture Quality Assessment

| Dimension | Rating | Notes |
|---|---|---|
| **Separation of Concerns** | ★★★★★ | CLI and library are fully decoupled |
| **Modularity** | ★★★★★ | Each subdomain in its own package |
| **Testability** | ★★★★★ | Library functions are pure; no CLI dependency in tests |
| **Extensibility** | ★★★★☆ | Clear extension points; new resource types follow the pattern |
| **Security** | ★★★★☆ | Strong baseline; missing HTTP timeouts |
| **Documentation** | ★★★★☆ | Good docstrings and type hints |
| **Dependency Hygiene** | ★★★★★ | Minimal runtime deps (2); clean separation |

---

## 3. Module Inventory

### Production Source Files (50 files)

#### `regshape/` (root package)
| File | Functions | Classes | Description |
|---|---|---|---|
| `__init__.py` | 0 | 0 | Package entry; empty |

#### `regshape/cli/` (8 files)
| File | Functions | Classes | Description |
|---|---|---|---|
| `__init__.py` | 0 | 0 | Package entry |
| `main.py` | 1 | 0 | Root click group; global options |
| `auth.py` | 3 | 0 | `login`, `logout` commands |
| `blob.py` | 6 | 0 | `head`, `get`, `push`, `delete`, `mount` |
| `catalog.py` | 2 | 0 | `list` command |
| `layout.py` | 15 | 0 | OCI Image Layout CRUD |
| `manifest.py` | 6 | 0 | `get`, `head`, `push`, `delete` |
| `referrer.py` | 2 | 0 | `list` command |
| `tag.py` | 3 | 0 | `list`, `delete` |

#### `regshape/libs/` (42 files)
| File | Functions | Classes | Description |
|---|---|---|---|
| `refs.py` | 2 | 0 | `parse_image_ref()`, `format_ref()` |
| `errors.py` | 0 | 9 | Exception hierarchy |
| `constants.py` | 0 | 0 | `IS_WINDOWS_PLATFORM` |
| `transport/client.py` | 8 | 2 | `RegistryClient`, `TransportConfig` |
| `transport/middleware.py` | 15 | 8 | `MiddlewarePipeline` and middleware types |
| `transport/models.py` | 6 | 2 | `RegistryRequest`, `RegistryResponse` |
| `auth/credentials.py` | 3 | 0 | Credential resolution + storage |
| `auth/dockerconfig.py` | 4 | 0 | Docker config.json reader |
| `auth/dockercredstore.py` | 4 | 0 | Credential helper subprocess interface |
| `auth/registryauth.py` | 1 | 0 | Bearer/Basic authentication |
| `blobs/operations.py` | 6 | 0 | Blob CRUD + mount |
| `manifests/operations.py` | 4 | 0 | Manifest CRUD |
| `tags/operations.py` | 2 | 0 | Tag list + delete |
| `catalog/operations.py` | 2 | 0 | Registry catalog |
| `referrers/operations.py` | 2 | 0 | Referrer list |
| `layout/operations.py` | 13 | 0 | OCI Image Layout filesystem |
| `models/manifest.py` | 7 | 2 | `ImageManifest`, `ImageIndex`, `parse_manifest()` |
| `models/descriptor.py` | 4 | 2 | `Descriptor`, `Platform`; digest regex |
| `models/blob.py` | 2 | 2 | `BlobInfo`, `BlobUploadSession` |
| `models/catalog.py` | 4 | 1 | `RepositoryCatalog` |
| `models/tags.py` | 4 | 1 | `TagList` |
| `models/referrer.py` | 6 | 1 | `ReferrerList` |
| `models/error.py` | 9 | 2 | `OciErrorResponse`, `first_detail()` |
| `models/mediatype.py` | 0 | 0 | OCI + Docker media type constants |
| `decorators/timing.py` | 2 | 0 | `@track_time` |
| `decorators/scenario.py` | 3 | 0 | `@track_scenario(name)` |
| `decorators/output.py` | 3 | 0 | Telemetry rendering (text + NDJSON) |
| `decorators/metrics.py` | 1 | 1 | `PerformanceMetrics` |
| `decorators/sanitization.py` | 2 | 0 | `redact_headers()` |
| `decorators/call_details.py` | 5 | 0 | curl-style debug decorator |

### Test Files (33 files)

| Module Coverage | File |
|---|---|
| Auth (unit) | `test_auth.py` |
| Auth CLI | `test_auth_cli.py` |
| Blob CLI | `test_blob_cli.py` |
| Blob models | `test_blob_model.py` |
| Blob operations | `test_blob_operations.py` |
| Catalog CLI | `test_catalog_cli.py` |
| Catalog model | `test_catalog_model.py` |
| Catalog operations | `test_catalog_operations.py` |
| Middleware integration | `test_client_middleware_integration.py` |
| Debug decorators | `test_debug_calls_enhanced.py` |
| Error models | `test_error_model.py` |
| Layout CLI | `test_layout_cli.py` |
| Layout operations | `test_layout_operations.py` |
| Layout staged | `test_layout_staged_operations.py` |
| Manifest CLI | `test_manifest_cli.py` |
| Manifest operations | `test_manifest_operations.py` |
| Middleware | `test_middleware.py` |
| Manifest models | `test_models_manifest.py` |
| Referrer CLI | `test_referrer_cli.py` |
| Referrer models | `test_referrer_model.py` |
| Referrer operations | `test_referrer_operations.py` |
| Image refs | `test_refs.py` |
| Sanitization | `test_sanitization.py` |
| Tag CLI | `test_tag_cli.py` |
| Tag operations | `test_tag_operations.py` |
| Tag models | `test_tags_model.py` |
| Telemetry JSON | `test_telemetry_json_output.py` |
| Telemetry log file | `test_telemetry_log_file.py` |
| Telemetry metrics | `test_telemetry_metrics.py` |
| Transport client | `test_transport_client.py` |
| Transport models | `test_transport_models.py` |

---

## 4. Component Deep Dives

### 4.1 RegistryClient (Transport Gateway)

`RegistryClient` is the **single point of contact** for all HTTP communication. Every operation module (blobs, manifests, tags, etc.) receives a `RegistryClient` instance and calls methods on it; none of them ever directly use `requests`.

```python
# Construction
config = TransportConfig(
    registry="registry.io",
    username="user",
    password="pass",
    insecure=False,
    verbose=True,
    enable_retry=True
)
client = RegistryClient(config)  # Resolves credentials here

# Usage in operations
response = client.get("/v2/myrepo/manifests/latest", headers={
    "Accept": ",".join(ALL_MANIFEST_MEDIA_TYPES)
})
```

**What `RegistryClient` does:**
1. Constructs `base_url` = `https://registry` (or `http://` if insecure)
2. Builds a `MiddlewarePipeline` with configured middleware
3. Wraps each HTTP method call in a `RegistryRequest`
4. Returns a `RegistryResponse` with status, headers, body, elapsed time

---

### 4.2 Middleware Pipeline

The pipeline runs **in order**: `AuthMiddleware → LoggingMiddleware → RetryMiddleware → HTTP call`.

Each middleware receives the request and a `next` callable to pass to the next middleware:

```
Request:   client → Auth → Log → Retry → HTTP call
Response:  HTTP → Retry → Log → Auth → client
```

**`AuthMiddleware`** is the most important. On a 401 response it:
1. Parses `WWW-Authenticate` header (Bearer or Basic)
2. For Bearer: calls `authenticate()` which POSTs to the token endpoint
3. Adds `Authorization: Bearer {token}` to the request
4. Retries the request once

**`RetryMiddleware`** retries on configurable status codes (429, 5xx) and network exceptions. Uses exponential backoff via `RetryConfig`.

---

### 4.3 Authentication Flow

The full end-to-end authentication chain:

```
User runs: regshape manifest get registry.io/repo:latest

1. CLI calls parse_image_ref() → registry="registry.io"
2. RegistryClient(TransportConfig(...)) created
3. On construction: resolve_credentials("registry.io") called
   a. Check explicit --username/--password → not provided
   b. Read ~/.docker/config.json → check credHelpers
   c. If credHelper found: exec "docker-credential-osxkeychain get"
      → {"Username": "user", "Secret": "pass"}
   d. Else: check auths map → base64 decode "dXNlcjpwYXNz"
   e. Return (username, password) or (None, None)

4. First HTTP request sent WITHOUT credentials
5. Registry responds: 401 Unauthorized
   WWW-Authenticate: Bearer realm="https://auth.io/token",
                            service="registry.io",
                            scope="repository:repo:pull"
6. AuthMiddleware.handle_401():
   a. Parse Bearer challenge
   b. Call registryauth.authenticate(username, password, challenge)
   c. POST https://auth.io/token?service=...&scope=...
      Authorization: Basic {base64(username:password)}
   d. Response: {"access_token": "eyJ..."}
   e. Store token: {"registry.io": "Bearer eyJ..."}
7. Retry original request:
   GET /v2/repo/manifests/latest
   Authorization: Bearer eyJ...
8. 200 OK → parse manifest → return to CLI
```

---

### 4.4 Blob Push — Detailed Flow

```
regshape blob push registry.io/repo myblob.tar.gz

1. CLI: read file, compute sha256 digest
2. head_blob(client, registry, repo, "sha256:{digest}")
   → HEAD /v2/repo/blobs/sha256:{digest}
   → 200: blob already exists, skip push (return existing Descriptor)
   → 404: blob not found, proceed

3. push_blob_monolithic(client, registry, repo, data, "application/octet-stream"):
   a. POST /v2/repo/blobs/uploads/
      → 202 Accepted
      Location: /v2/repo/blobs/uploads/{uuid}?state={state}
   b. PUT /v2/repo/blobs/uploads/{uuid}?digest=sha256:{computed_digest}
      Content-Type: application/octet-stream
      Content-Length: {size}
      Body: {blob data}
      → 201 Created
      Location: /v2/repo/blobs/sha256:{digest}
   c. Return Descriptor(
        mediaType="application/octet-stream",
        digest="sha256:{digest}",
        size={bytes}
      )

4. @track_scenario("push blob") renders telemetry:
   ── telemetry ──
   head_blob         0.045s
   push_blob_mono    1.234s
   ── telemetry ──
```

---

### 4.5 OCI Image Layout

The layout module implements [OCI Image Layout Specification](https://github.com/opencontainers/image-spec/blob/main/image-layout.md) — a filesystem format for storing container images locally.

**Layout directory structure:**
```
myimage/
├── oci-layout              → {"imageLayoutVersion": "1.0.0"}
├── index.json              → ImageIndex (list of manifests)
└── blobs/
    └── sha256/
        ├── {manifest_digest}  → ImageManifest JSON
        ├── {config_digest}    → Image config JSON
        └── {layer_digest}     → Layer tarball
```

**Atomic write guarantee:**
All writes use `_write_atomically()`:
1. `fd, tmp = tempfile.mkstemp(dir=parent, suffix=".tmp")` — creates a temp file in the same directory (same filesystem, so rename is atomic)
2. Write all data to temp file
3. `os.replace(tmp, target)` — atomic rename on POSIX

This means readers of `index.json` or blob files never observe partial writes.

---

### 4.6 Telemetry and Observability

regshape has a built-in telemetry system via decorators. It's designed to be non-invasive.

```python
# Tracking individual operation timing
@track_time
def get_manifest(client, registry, repo, reference):
    # ... actual logic ...
    # After return, (qualname, elapsed) stored in TelemetryConfig.method_timings

# Tracking a multi-step scenario  
@track_scenario("push image")
def push_all_layers(client, ...):
    for layer in layers:
        push_blob_monolithic(...)  # Each call tracked by @track_time
    push_manifest(...)             # Also tracked
    # When push_all_layers returns:
    # Renders ── telemetry ── block showing all inner timings
    # Clears method_timings for next scenario
```

**Output formats:** Plain text blocks and NDJSON (one JSON per line for machine consumption).

**Security:** `redact_headers()` is called before any HTTP debug output is printed, so auth tokens never appear in telemetry.

---

## 5. Data Flows

### 5.1 Request Lifecycle

Every single HTTP request follows this path:
```
Operation Function
  → client.{method}(path, headers, body)
  → RegistryRequest constructed
  → MiddlewarePipeline.execute(request)
      → AuthMiddleware
      → LoggingMiddleware (if verbose)
          → sanitize headers before logging
      → RetryMiddleware (if enabled)
      → requests.{method}(url, headers, data, allow_redirects, verify)
  → Response → RegistryResponse.from_requests_response(r)
  → Return to operation
```

### 5.2 Credential Data Flow

```
Source: CLI --username/--password
   OR: ~/.docker/config.json (credHelpers or auths)
   OR: docker-credential-{store} subprocess output

↓ resolve_credentials() normalizes to (username, password)

↓ Stored in TransportConfig (in memory only)

↓ On 401: authenticate(username, password, challenge)
   → Bearer: POST token_endpoint → receive JWT → "Bearer {jwt}"
   → Basic: base64(username:password) → "Basic {b64}"

↓ Set as Authorization header on retried request

↓ NEVER logged (redact_headers() removes Authorization value)
```

### 5.3 Blob Download Data Flow

```
get_blob(client, registry, repo, "sha256:{expected_digest}")
  → GET /v2/{repo}/blobs/{digest}
  → 200 OK, Content-Type, Content-Length
  → Stream response body
  → Simultaneously compute sha256 hash of received bytes
  → After all bytes received:
    ├─ computed_digest == expected_digest? → ✅ Return bytes/write file
    └─ digest mismatch? → ❌ Raise BlobError("Digest mismatch")
```

---

## 6. Dependency Analysis

### Dependency Topology

The dependency graph is a **strict DAG** — no circular dependencies exist.

**Layer ordering** (most foundational → most operational):

```
Level 0 (no deps): constants.py, errors.py, refs.py,
                   models/descriptor.py, models/error.py,
                   models/mediatype.py, decorators/metrics.py,
                   decorators/sanitization.py

Level 1: models/* (use Level 0)
         decorators/* except sanitization (use Level 0)
         auth/dockerconfig.py, auth/dockercredstore.py

Level 2: auth/credentials.py (uses Level 1)
         transport/models.py
         auth/registryauth.py

Level 3: transport/middleware.py (uses Level 2)
         
Level 4: transport/client.py (uses Level 3)

Level 5: operations/* (use Level 4 + models + decorators)

Level 6: cli/* (use Level 5)
```

### Hub Modules (imported by ≥3 modules)

| Module | Fan-In | Why Central |
|---|---|---|
| `libs/errors.py` | High | Exception base; used by all operations |
| `libs/refs.py` | High | Image ref parsing; used by all CLI commands |
| `libs/transport/client.py` | High | Only HTTP gateway; required by all operations |
| `libs/models/descriptor.py` | High | Core OCI primitive; manifests, blobs, layout all use it |
| `libs/models/mediatype.py` | Medium | Media type constants used across operations |
| `libs/decorators/timing.py` | High | `@track_time` used by every operation |
| `libs/decorators/sanitization.py` | Medium | Used by transport logging |
| `libs/auth/credentials.py` | Medium | Used by transport client + auth CLI |

### Leaf Modules (no internal imports)

These are the most stable, foundational modules:
- `libs/constants.py` — single constant
- `libs/errors.py` — exception classes only
- `libs/refs.py` — only stdlib imports
- `libs/models/descriptor.py` — dataclass, only stdlib
- `libs/models/error.py` — dataclass, stdlib
- `libs/models/mediatype.py` — string constants
- `libs/decorators/metrics.py` — dataclass, stdlib
- `libs/decorators/sanitization.py` — set + stdlib only

---

## 7. Security Analysis

### Security Posture: LOW RISK (Production Code)

No hardcoded secrets. No critical vulnerabilities in production code. Strong security hygiene throughout.

### Findings Summary

| Finding | Severity | Source | Location | Status |
|---|---|---|---|---|
| Missing HTTP request timeouts | **MEDIUM** | bandit B113 | `registryauth.py:116,118` | ⚠️ Fix needed |
| gitpython 5 CVEs | **HIGH** (dev only) | pip-audit | dev env dependency | ⚠️ Upgrade needed |
| Insecure temp files in tests | LOW | bandit B108 | `test_auth_cli.py` | 🔵 Low priority |
| Semgrep logger warnings | INFO | semgrep | `auth/credentials.py` | ✅ False positives |
| Hardcoded secrets | **NONE** | detect-secrets | all files | ✅ Clean |
| Shell injection | **NONE** | bandit B603 | `dockercredstore.py` | ✅ Safe (list form) |

### Security Strengths

1. **No hardcoded secrets** — 0 findings from detect-secrets across all 83 files
2. **Header sanitization** — `Authorization`, `Cookie`, `Proxy-Authorization`, `Set-Cookie` all redacted before any log output
3. **TLS by default** — `--insecure` requires explicit opt-in; there's no accidental HTTP
4. **Blob integrity verification** — SHA-256/SHA-512 digest checked after every download
5. **Atomic file I/O** — OCI Layout writes via `mkstemp` + `os.replace` (no partial write state)
6. **Safe subprocess** — credential helper calls use `["cmd", "arg"]` list form (no shell injection)
7. **Minimal attack surface** — only 2 runtime dependencies

### Critical Fix Required

**Add HTTP timeouts to `libs/auth/registryauth.py`:**

```python
# Current (vulnerable to hanging):
response = requests.get(realm, params=params)

# Fixed:
response = requests.get(realm, params=params, timeout=30)
```

This is a simple one-line change per call site. Without it, a slow registry can hang `regshape` indefinitely.

### OWASP Top 10 Assessment

| Category | Verdict | Notes |
|---|---|---|
| A01 Broken Access Control | ✅ N/A | Client tool; auth is server responsibility |
| A02 Cryptographic Failures | ⚠️ Partial | TLS fine; missing timeout on auth requests (CWE-400) |
| A03 Injection | ✅ Clean | No SQL; safe subprocess; no shell calls |
| A04 Insecure Design | ✅ Good | Credential chain well-designed; Bearer tokens, not stored passwords |
| A05 Security Misconfiguration | ⚠️ Note | `--insecure` removes ALL transport security |
| A06 Vulnerable Components | ⚠️ Dev env | gitpython 3.1.0 has 5 CVEs; not a runtime dep |
| A07 Auth Failures | ✅ Good | Bearer flow correct per OCI spec; Basic as fallback |
| A08 Data Integrity | ✅ Excellent | Digest verification; atomic writes |
| A09 Security Logging | ✅ Excellent | Sensitive headers redacted; no credential logging |
| A10 SSRF | ⚠️ Low risk | Token realm URL not validated; hard to exploit |

---

## 8. Technology Decisions

### Why Python 3.10+
- `match`/`case` available for future OCI spec patterns
- `X | Y` union type syntax in annotations
- Wide adoption in the container/DevOps ecosystem
- Dataclasses with `field()` for clean DTOs

### Why Click (CLI)
- Decorator-based command groups — natural fit for `regshape auth`, `regshape blob`, etc.
- `click.Context` for passing global options (`--insecure`, `--verbose`) to all subcommands without boilerplate
- `CliRunner` for testable CLI without subprocess calls
- Stable and widely adopted; not an unusual dependency

### Why requests (HTTP)
- Synchronous CLI; no event loop needed
- Universal developer familiarity
- Excellent HTTPS/TLS support via `urllib3`
- Simple API; minimal friction
- If async ever needed: `httpx` has near-identical API

### Why Dataclasses (not Pydantic)
- Zero dependencies — `dataclasses` is stdlib
- No validation overhead for internal DTOs
- Registry API responses are manually parsed into dataclasses via factory methods
- Type hints provide self-documentation

### Why Middleware Pattern
- Auth, logging, retry, caching are cross-cutting concerns
- Middleware keeps `RegistryClient` clean and focused
- Each middleware is independently testable
- New behavior added without modifying existing code

---

## 9. Testing Coverage

### Test Architecture

Tests use `pytest` with `unittest.mock` / `pytest-mock` for HTTP mocking. No live registry connection required. `click.testing.CliRunner` enables CLI testing without subprocess.

### Coverage Profile

| Layer | Coverage Type | Notes |
|---|---|---|
| CLI (auth, blob, catalog, layout, manifest, referrer, tag) | Integration | CliRunner + mocked operations |
| Transport (`client.py`, `middleware.py`) | Unit + Integration | Mocked `requests`; real middleware chain |
| Auth (credentials, dockerconfig, dockercredstore, registryauth) | Unit | Mocked filesystem + subprocess |
| Operations (blobs, manifests, tags, catalog, referrers, layout) | Unit | Mocked `RegistryClient` |
| Models (all) | Unit | Pure parsing logic; no mocks needed |
| Decorators (timing, scenario, sanitization, output, metrics) | Unit | Direct invocation |
| Utilities (refs, errors) | Unit | Pure functions |

### Test Count Summary

| Domain | Test Functions | Test Classes |
|---|---|---|
| Auth | 97+ | 20 |
| Blob | 86+ | 12 |
| Catalog | 96+ | 12 |
| Manifest | 63+ | 11 |
| Middleware | 93+ | 28 |
| Layout | 112+ | 24 |
| Tag | 57+ | 7 |
| Referrers | 68+ | 12 |
| Models | 230+ | 30 |
| Transport | 57+ | 10 |
| Telemetry | 32+ | 7 |

---

## 10. Recommended Improvements

### Priority 1 — Fix HTTP Timeouts (Medium Risk, Low Effort)

**File:** `libs/auth/registryauth.py`, lines 116, 118  
**Change:** Add `timeout=30` to both `requests.get()` calls  
**Also:** Add `request_timeout` field to `TransportConfig`; pass it to `RegistryClient` HTTP calls  

```python
# In libs/constants.py
DEFAULT_REQUEST_TIMEOUT = 30

# In libs/auth/registryauth.py
from regshape.libs.constants import DEFAULT_REQUEST_TIMEOUT
response = requests.get(realm, params=params, timeout=DEFAULT_REQUEST_TIMEOUT)
```

---

### Priority 2 — Upgrade gitpython in Dev Environment (High CVEs, Low Effort)

```bash
pip install "gitpython>=3.1.41"
# And add to your dev requirements pin
```

---

### Priority 3 — Replace Hardcoded /tmp/ Paths in Tests (Low Risk, Low Effort)

In `tests/test_auth_cli.py`, replace `/tmp/docker_config.json` paths with the `tmp_path` pytest fixture:

```python
def test_login(tmp_path):  # pytest provides this
    config = tmp_path / "docker_config.json"
    ...
```

---

### Priority 4 — Token Realm URL Validation (Low Risk, Medium Effort)

In `libs/auth/registryauth.py`, validate the `realm` URL from `WWW-Authenticate` before requesting it:

```python
from urllib.parse import urlparse

def _validate_realm(realm: str) -> None:
    parsed = urlparse(realm)
    if parsed.scheme not in ("http", "https"):
        raise AuthError(f"Invalid realm scheme: {parsed.scheme!r}")
```

---

### Priority 5 — CI Security Scans (Low Effort, Ongoing Value)

Add to CI pipeline:
```yaml
- name: Security scan
  run: |
    bandit -r src/ -ll  # Only MEDIUM+ severity
    pip-audit
    detect-secrets scan src/
```

---

### Quality Improvements (Non-Security)

| Improvement | Value |
|---|---|
| Add `py.typed` marker | Enables mypy checking for downstream users |
| Add `CHANGELOG.md` | Version history tracking |
| Add `--timeout` CLI option | Exposes request timeout to users |
| Add `--max-retries` CLI option | Exposes retry config to users |
| Use `logging.getLogger(__name__)` consistently | Better log filtering |
| Add `Content-Digest` header verification | Manifest integrity on download |

---

## 11. Supporting Files Index

All analysis outputs are stored under `regshape/2026-03-08/`:

| Path | Description |
|---|---|
| `documentation.md` | **This file** — comprehensive analysis |
| `analysis/architecture-overview.md` | Detailed architecture with module descriptions, data flows, patterns |
| `analysis/components-guide.md` | Per-component API reference and behavior guide |
| `analysis/security-overview.md` | Security posture summary |
| `analysis/technology-decisions.md` | Rationale for technology choices |
| `visuals/detailed-architecture.md` | Mermaid diagrams: system, CLI tree, middleware, auth, blob push, layout, deps, telemetry, errors, data model |
| `visuals/dependency-graphs.md` | Mermaid dependency graphs: full import graph, external deps, call graphs, coupling matrix |
| `visuals/security-model.md` | Mermaid security diagrams: trust boundaries, credential flow, attack surface, data sensitivity, TLS, subprocess |
| `security/detailed-security-analysis.md` | Full bandit, semgrep, pip-audit, detect-secrets findings with analysis |
| `security/remediation-guide.md` | Step-by-step fix instructions for each finding |
| `security/attack-surface-map.md` | Comprehensive threat model and attack vector catalog |
| `security/dependency-audit.md` | Dependency versions, CVEs, and security scorecard |
| `source-files/file-inventory.json` | Machine-readable per-file function/class inventory (83 files) |
| `dependencies/dependency-graph.json` | Forward + reverse import dependency graph |
| `interactive/dependency-query-db.json` | Query-optimized dependency + inventory database |
| `interactive/query-examples.md` | Python/jq queries for exploring the analysis data |
| `security/tool-scan-results/bandit/bandit-results.json` | Raw bandit output |
| `security/tool-scan-results/semgrep/semgrep-results.json` | Raw semgrep output |
| `security/tool-scan-results/pip-audit/pip-audit-results.json` | Raw pip-audit output |
| `security/tool-scan-results/detect-secrets/detect-secrets-results.json` | Raw detect-secrets output |
