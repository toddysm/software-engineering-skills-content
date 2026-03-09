# regshape — Architecture Overview

**Project:** regshape  
**Version:** 0.1.0  
**Analysis Date:** 2026-03-08  
**Language:** Python ≥ 3.10  

---

## Executive Summary

`regshape` is a Python CLI tool and library for interacting with OCI-compliant container registries. It implements the [OCI Distribution Specification](https://github.com/opencontainers/distribution-spec) and [OCI Image Layout Specification](https://github.com/opencontainers/image-spec/blob/main/image-layout.md) as both a command-line interface (via Click) and a reusable Python library.

The codebase follows a clean two-layer architecture:
1. **CLI Layer** — user-facing `click` commands that parse arguments and delegate to the library
2. **Library Layer** — domain logic organized by capability (transport, auth, operations per resource type, models)

The design is cohesive, well-structured, and production-ready in terms of feature breadth. It does not yet have extensive HTTP timeouts configured, which is a noted gap.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        regshape CLI                              │
│  (main.py → auth, blob, catalog, layout, manifest,              │
│             referrer, tag)                                       │
└───────────────────────┬─────────────────────────────────────────┘
                        │  delegates to
┌───────────────────────▼─────────────────────────────────────────┐
│                    Library Layer (libs/)                         │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │  Operations  │  │   Transport  │  │       Auth             │ │
│  │  blobs/      │  │  client.py   │  │  credentials.py        │ │
│  │  manifests/  │  │  middleware  │  │  dockerconfig.py       │ │
│  │  tags/       │  │  .py         │  │  dockercredstore.py    │ │
│  │  catalog/    │  │  models.py   │  │  registryauth.py       │ │
│  │  referrers/  │  └──────────────┘  └────────────────────────┘ │
│  │  layout/     │                                                │
│  └──────────────┘  ┌──────────────┐  ┌────────────────────────┐ │
│                    │    Models    │  │     Decorators         │ │
│                    │  manifest    │  │  timing / scenario     │ │
│                    │  descriptor  │  │  metrics / output      │ │
│                    │  blob / tags │  │  sanitization          │ │
│                    │  catalog     │  │  call_details          │ │
│                    │  referrer    │  └────────────────────────┘ │
│                    │  error       │                              │
│                    │  mediatype   │                              │
│                    └──────────────┘                              │
└─────────────────────────────────────────────────────────────────┘
                        │  HTTP
┌───────────────────────▼─────────────────────────────────────────┐
│              OCI-Compatible Container Registry                   │
│   (Docker Hub, GHCR, ACR, ECR, Zot, Distribution, etc.)         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Module Structure

### Root Package
| Path | Purpose |
|---|---|
| `regshape/__init__.py` | Package init (empty) |
| `regshape/cli/` | Click CLI commands |
| `regshape/libs/` | Reusable domain library |

### CLI Layer (`regshape/cli/`)

| Module | Commands | Key Functions |
|---|---|---|
| `main.py` | `regshape` (group) | Global options: `--insecure`, `--verbose`, `--break`, `--break-rules`, `--log-file` |
| `auth.py` | `login`, `logout` | Credential resolution and verification via direct HTTP; credential storage |
| `blob.py` | `head`, `get`, `push`, `delete`, `mount` | Blob operations; streaming output |
| `catalog.py` | `list` | Registry catalog listing |
| `layout.py` | Full OCI Image Layout CRUD | Push/pull images to/from filesystem layouts |
| `manifest.py` | `get`, `head`, `push`, `delete` | Manifest operations |
| `referrer.py` | `list` | List image referrers (SBOM, signatures, etc.) |
| `tag.py` | `list`, `delete` | Tag management |

The CLI modules are thin wrappers: they parse arguments, construct a `RegistryClient`, call library functions, and format output. No business logic lives in the CLI layer.

### Transport Layer (`regshape/libs/transport/`)

The transport layer is the single HTTP gateway. All registry communication goes through `RegistryClient`. It supports a configurable middleware pipeline.

**`RegistryClient`** (`client.py`)
- Resolves credentials once at construction time
- Exposes `get()`, `head()`, `put()`, `delete()`, `post()`, `patch()` methods
- Each method constructs a `RegistryRequest`, runs it through the middleware pipeline, returns a `RegistryResponse`
- Holds a `TransportConfig` dataclass: `base_url`, `credentials`, optional Logging/Retry/Caching middleware config
- `base_url` property: constructs `https://` (or `http://` if `--insecure`) URL

**`MiddlewarePipeline`** (`middleware.py`)
- Ordered FIFO pipeline
- `AuthMiddleware`: handles 401 → reads `WWW-Authenticate` header → calls `authenticate()` → retries once
- `LoggingMiddleware`: logs request/response in curl-style debug format
- `RetryMiddleware`: retries on configurable status codes and exceptions; exponential back-off via `RetryConfig`
- `CachingMiddleware`: stub / extensible caching layer

**`RegistryRequest` / `RegistryResponse`** (`models.py`)
- Typed dataclasses wrapping method, URL, headers, body, status
- `body: Optional[Union[bytes, Iterable[bytes]]]` supports streaming
- `from_requests_response()` factory on `RegistryResponse`

### Auth Layer (`regshape/libs/auth/`)

| Module | Purpose |
|---|---|
| `credentials.py` | `resolve_credentials()` — priority chain; `store_credentials()`, `erase_credentials()` |
| `dockerconfig.py` | Read Docker config.json; search order: explicit → `DOCKER_CONFIG` env → `~/.docker/config.json` |
| `dockercredstore.py` | Speak to `docker-credential-{store}` helpers via subprocess |
| `registryauth.py` | `authenticate()` → Bearer token (OCI spec) or Basic auth |

**Credential Resolution Priority Order:**
1. Explicit `--username`/`--password` arguments
2. `credHelpers` entry in Docker config for the registry
3. `auths` section of Docker config (Base64 username:password)
4. Anonymous (no credentials)

**Authentication Flow:**
1. First request sent without credentials
2. 401 response triggers `AuthMiddleware`
3. `WWW-Authenticate` header parsed for `Bearer realm` or `Basic realm`
4. Bearer: exchange credentials at token endpoint, get short-lived JWT
5. Basic: Base64-encode `{username}:{password}` as `Authorization: Basic ...`
6. Retry original request with auth header

### Operations Layer (`regshape/libs/{blobs,manifests,tags,catalog,referrers,layout}/`)

Each subdomain has an `operations.py` with pure functions taking a `RegistryClient` and domain parameters.

| Module | Key Functions |
|---|---|
| `blobs/operations.py` | `head_blob()`, `get_blob()`, `push_blob_monolithic()`, `push_blob_chunked()`, `delete_blob()`, `mount_blob()` |
| `manifests/operations.py` | `get_manifest()`, `head_manifest()`, `push_manifest()`, `delete_manifest()` |
| `tags/operations.py` | `list_tags()` (paginated), `delete_tag()` |
| `catalog/operations.py` | `list_catalog()`, `list_catalog_all()` (follows `Link` headers) |
| `referrers/operations.py` | `list_referrers()`, `list_referrers_all()` with `artifactType` filtering |
| `layout/operations.py` | OCI Image Layout filesystem read/write; atomic writes |

**Notable patterns:**
- All operation functions are decorated with `@track_time` for telemetry
- Blob get uses streaming + digest verification (SHA-256 or SHA-512)
- Atomic filesystem writes: `tempfile.mkstemp` + `os.replace` (prevents partial writes)
- Pagination: follows `Link: <url>; rel="next"` headers throughout

### Models Layer (`regshape/libs/models/`)

| Module | Classes |
|---|---|
| `manifest.py` | `ImageManifest`, `ImageIndex`, `parse_manifest()` factory |
| `descriptor.py` | `Descriptor`, `Platform`; strict digest regex (sha256/sha512) |
| `blob.py` | `BlobInfo`, `BlobUploadSession` |
| `catalog.py` | `RepositoryCatalog` |
| `tags.py` | `TagList` |
| `referrer.py` | `ReferrerList` |
| `error.py` | `OciErrorResponse`, `first_detail()` |
| `mediatype.py` | OCI + Docker media type string constants + frozensets |

**Media type constants:**
- `OCI_IMAGE_MANIFEST = "application/vnd.oci.image.manifest.v1+json"`
- `OCI_IMAGE_INDEX = "application/vnd.oci.image.index.v1+json"`
- `DOCKER_MANIFEST_V2 = "application/vnd.docker.distribution.manifest.v2+json"`
- `DOCKER_MANIFEST_LIST_V2 = "application/vnd.docker.distribution.manifest.list.v2+json"`
- `ALL_MANIFEST_MEDIA_TYPES` frozenset covers both OCI and Docker variants

### Decorators Layer (`regshape/libs/decorators/`)

| Module | Purpose |
|---|---|
| `timing.py` | `@track_time` — accumulates elapsed times into `TelemetryConfig.method_timings` |
| `scenario.py` | `@track_scenario(name)` — wraps multi-step workflows, renders telemetry block |
| `output.py` | `print_telemetry_block()`, `flush_telemetry()`, `telemetry_write()`; text + NDJSON output |
| `metrics.py` | `PerformanceMetrics` — request counts, bytes, retries, errors, status codes |
| `call_details.py` | `http_request()` — curl-style debug decorator; `format_curl_debug()` |
| `sanitization.py` | `redact_headers()` — redacts `Authorization`, `Cookie`, `Set-Cookie`, `Proxy-Authorization` |

### Utilities

| Module | Purpose |
|---|---|
| `libs/refs.py` | `parse_image_ref()` → `(registry, repo, reference)`; handles tags, digests, ports, localhost |
| `libs/errors.py` | Exception hierarchy: `RegShapeError` → domain-specific errors |
| `libs/constants.py` | `IS_WINDOWS_PLATFORM` flag |

---

## Data Flow

### Typical Command Flow (e.g., `regshape manifest get myregistry.io/repo:tag`)

```
1. CLI (manifest.py)
   ├─ parse_image_ref("myregistry.io/repo:tag") → (registry, repo, "tag")
   ├─ build TransportConfig
   ├─ RegistryClient(config)
   │     └─ resolve_credentials(registry) → (username, password)
   └─ get_manifest(client, registry, repo, "tag")

2. get_manifest() (manifests/operations.py)
   └─ client.get(f"/{repo}/manifests/{reference}", headers={Accept: all_types})

3. RegistryClient.get() (transport/client.py)
   └─ MiddlewarePipeline.execute(request)

4. MiddlewarePipeline (transport/middleware.py)
   ├─ AuthMiddleware: pass through (no auth yet)
   ├─ LoggingMiddleware: log curl-style request
   └─ requests.get(url, headers, ...)

5a. If 200: 
    ├─ parse_manifest(body, media_type) → ImageManifest | ImageIndex
    └─ return to CLI; CLI formats and prints output

5b. If 401:
    ├─ AuthMiddleware reads WWW-Authenticate: Bearer realm="...",service="...",scope="..."
    ├─ registryauth.authenticate(credentials, challenge)
    │     └─ POST token endpoint → JWT access_token
    ├─ Retry with Authorization: Bearer {token}
    └─ proceed to 5a
```

### Blob Push Flow (monolithic)

```
1. CLI blob push: read file, compute sha256 digest
2. head_blob() → check if blob exists (skip if 200)
3. POST /v2/{repo}/blobs/uploads/ → get upload URL (202)
4. PUT {upload_url}?digest={digest} with body → 201 Created
5. Return Descriptor(mediaType, digest, size)
```

### OCI Image Layout Write Flow

```
1. layout/operations.py: _write_atomically(path, data)
   ├─ tempfile.mkstemp(dir=parent, suffix=".tmp")
   ├─ write data to temp file
   └─ os.replace(tmp_path, target_path)  ← atomic on POSIX
```

---

## Configuration Model

### Global CLI Options (passed as Click context)
| Option | Type | Default | Purpose |
|---|---|---|---|
| `--insecure` | flag | False | Use HTTP instead of HTTPS |
| `--verbose` | flag | False | Enable curl-style HTTP debug |
| `--break` | flag | False | Raise exceptions instead of clean errors |
| `--break-rules` | flag | False | Skip verification steps |
| `--log-file` | path | None | Write log output to file |

### Credential Resolution (`libs/auth/credentials.py`)
Priority (highest to lowest):
1. Explicit `--username` / `--password` CLI arguments
2. `credHelpers` map in `~/.docker/config.json`
3. `auths` map in `~/.docker/config.json`
4. `DOCKER_CONFIG` environment variable override for config path
5. Anonymous access

---

## Error Handling Strategy

### Exception Hierarchy
```
RegShapeError (base)
├── AuthError           — authentication/authorization failures
├── ManifestError       — manifest operation failures
├── TagError            — tag operation failures
├── BlobError           — blob operation failures
├── CatalogError        — catalog operation failures
│   └── CatalogNotSupportedError  — registry doesn't support catalog API
├── ReferrerError       — referrer operation failures
└── LayoutError         — OCI Image Layout filesystem failures
```

### Error surfaces
- HTTP ≥ 400 responses: `OciErrorResponse` parsed from JSON body; `first_detail()` extracts message
- Subprocess errors (credential helpers): logged, fallback to anonymous
- Filesystem errors: `LayoutError` raised with context
- Auth failures: `AuthError` includes registry URL and underlying cause

---

## Testing Strategy

The test suite (`tests/`) is comprehensive:

| Test Module | What It Covers |
|---|---|
| `test_auth.py`, `test_auth_cli.py` | Auth flows, credential resolution, login/logout CLI |
| `test_blob_operations.py`, `test_blob_cli.py` | Blob push/get/head/delete/mount |
| `test_manifest_operations.py`, `test_manifest_cli.py` | Manifest CRUD |
| `test_middleware.py`, `test_client_middleware_integration.py` | Middleware pipeline behavior |
| `test_transport_client.py`, `test_transport_models.py` | HTTP client layer |
| `test_layout_operations.py`, `test_layout_staged_operations.py` | OCI Layout filesystem |
| `test_sanitization.py`, `test_debug_calls_enhanced.py` | Header redaction, curl-style debug |
| `test_telemetry_*.py` | Telemetry output formats (text, JSON, NDJSON) |
| `test_refs.py` | Image reference parsing edge cases |
| `test_models_manifest.py`, `test_error_model.py`, etc. | Model parsing/validation |

Tests use `pytest` with `pytest-mock`/`unittest.mock` for HTTP mocking. No live registry connection is required.

---

## Key Design Patterns

| Pattern | Where Used | Why |
|---|---|---|
| **Command Object** | `RegistryRequest`/`RegistryResponse` dataclasses | Encapsulate HTTP exchange; enable middleware chaining |
| **Chain of Responsibility** | `MiddlewarePipeline` | Composable HTTP processing (auth, logging, retry, caching) |
| **Strategy** | Auth: Bearer vs Basic | Pluggable auth based on `WWW-Authenticate` challenge |
| **Delegate / Thin CLI** | All `cli/*.py` modules | Business logic stays in library; CLI is pure I/O |
| **Atomic Write** | `layout/operations.py` | `mkstemp` + `os.replace` prevents partial filesystem state |
| **Decorator for Telemetry** | `@track_time`, `@track_scenario` | Non-invasive performance instrumentation |
| **Frozenset Constants** | `mediatype.py` | Type-safe media type collection membership checks |

---

## Dependencies

### Runtime
| Package | Version Constraint | Purpose |
|---|---|---|
| `click` | `>=8.1.0` | CLI framework (commands, options, arguments, contexts) |
| `requests` | `>=2.31.0` | HTTP client for registry API calls |

### Development / Testing
| Package | Version Constraint | Purpose |
|---|---|---|
| `pytest` | `>=7.4.0` | Test framework |

The minimal dependency count (2 runtime packages) is a deliberate design choice — maximum portability.

---

## Scalability and Extension Points

1. **New resource types**: Add `cli/{type}.py` + `libs/{type}/operations.py`; register with `main.py`
2. **New middleware**: Implement `Middleware` protocol; add to `MiddlewarePipeline`
3. **New auth schemes**: Add handler in `registryauth.py`; extend `authenticate()` branching
4. **New output formats**: Extend `decorators/output.py`
5. **New credential backends**: Add resolver in `auth/credentials.py` priority chain
